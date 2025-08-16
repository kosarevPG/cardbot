#!/usr/bin/env python3
"""
Скрипт для детального анализа потерь пользователей в воронке "Карта дня"
"""

import sqlite3
import json
from datetime import datetime, timedelta
import os

# Путь к базе данных
DB_PATH = "database/dev.db"

def analyze_user_dropoffs(days=7):
    """Анализирует детальные потери пользователей в воронке"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        print(f"🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ПОТЕРЬ ПОЛЬЗОВАТЕЛЕЙ (за {days} дней)")
        print("=" * 70)
        
        # 1. Пользователи, которые начали сессию
        cursor = conn.execute(f"""
            SELECT DISTINCT user_id, timestamp
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'started'
            AND timestamp >= datetime('now', '-{days} days')
            ORDER BY timestamp DESC
        """)
        started_users = {row['user_id']: row['timestamp'] for row in cursor.fetchall()}
        
        # 2. Пользователи, которые выбрали ресурс
        cursor = conn.execute(f"""
            SELECT DISTINCT user_id, timestamp
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'initial_resource_selected'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        resource_users = {row['user_id']: row['timestamp'] for row in cursor.fetchall()}
        
        # 3. Пользователи, которые вытянули карту
        cursor = conn.execute(f"""
            SELECT DISTINCT user_id, timestamp
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'card_drawn'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        card_users = {row['user_id']: row['timestamp'] for row in cursor.fetchall()}
        
        # 4. Пользователи, которые выбрали углубляющий диалог
        cursor = conn.execute(f"""
            SELECT DISTINCT user_id, timestamp
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'ai_reflection_choice'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        ai_choice_users = {row['user_id']: row['timestamp'] for row in cursor.fetchall()}
        
        # 5. Пользователи, которые завершили сценарий
        cursor = conn.execute(f"""
            SELECT DISTINCT user_id, timestamp
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'completed'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        completed_users = {row['user_id']: row['timestamp'] for row in cursor.fetchall()}
        
        print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
        print(f"  • Начали сессию: {len(started_users)} пользователей")
        print(f"  • Выбрали ресурс: {len(resource_users)} пользователей")
        print(f"  • Вытянули карту: {len(card_users)} пользователей")
        print(f"  • Выбрали углубляющий диалог: {len(ai_choice_users)} пользователей")
        print(f"  • Завершили сценарий: {len(completed_users)} пользователей")
        
        # Анализ потерь на каждом шаге
        print(f"\n🚨 АНАЛИЗ ПОТЕРЬ:")
        
        # Потеря 1: Начали → Выбрали ресурс
        lost_after_start = set(started_users.keys()) - set(resource_users.keys())
        if lost_after_start:
            print(f"\n❌ ПОТЕРЯ 1: Начали сессию, но не выбрали ресурс ({len(lost_after_start)} пользователей)")
            print("   Пользователи:")
            for user_id in list(lost_after_start)[:10]:  # Показываем первые 10
                start_time = started_users[user_id]
                print(f"     • ID {user_id} - начал в {start_time}")
            if len(lost_after_start) > 10:
                print(f"     ... и еще {len(lost_after_start) - 10} пользователей")
        
        # Потеря 2: Выбрали ресурс → Вытянули карту
        lost_after_resource = set(resource_users.keys()) - set(card_users.keys())
        if lost_after_resource:
            print(f"\n❌ ПОТЕРЯ 2: Выбрали ресурс, но не вытянули карту ({len(lost_after_resource)} пользователей)")
            print("   Пользователи:")
            for user_id in list(lost_after_resource)[:10]:
                resource_time = resource_users[user_id]
                print(f"     • ID {user_id} - выбрал ресурс в {resource_time}")
            if len(lost_after_resource) > 10:
                print(f"     ... и еще {len(lost_after_resource) - 10} пользователей")
        
        # Потеря 3: Вытянули карту → Выбрали углубляющий диалог
        lost_after_card = set(card_users.keys()) - set(ai_choice_users.keys())
        if lost_after_card:
            print(f"\n❌ ПОТЕРЯ 3: Вытянули карту, но не выбрали углубляющий диалог ({len(lost_after_card)} пользователей)")
            print("   Пользователи:")
            for user_id in list(lost_after_card)[:10]:
                card_time = card_users[user_id]
                print(f"     • ID {user_id} - вытянул карту в {card_time}")
            if len(lost_after_card) > 10:
                print(f"     ... и еще {len(lost_after_card) - 10} пользователей")
        
        # Потеря 4: Выбрали углубляющий диалог → Завершили сценарий
        lost_after_ai_choice = set(ai_choice_users.keys()) - set(completed_users.keys())
        if lost_after_ai_choice:
            print(f"\n❌ ПОТЕРЯ 4: Выбрали углубляющий диалог, но не завершили сценарий ({len(lost_after_ai_choice)} пользователей)")
            print("   Пользователи:")
            for user_id in list(lost_after_ai_choice)[:10]:
                ai_time = ai_choice_users[user_id]
                print(f"     • ID {user_id} - выбрал диалог в {ai_time}")
            if len(lost_after_ai_choice) > 10:
                print(f"     ... и еще {len(lost_after_ai_choice) - 10} пользователей")
        
        # Анализ времени между шагами
        print(f"\n⏱️ АНАЛИЗ ВРЕМЕНИ МЕЖДУ ШАГАМИ:")
        
        # Время от начала до выбора ресурса
        if started_users and resource_users:
            times_to_resource = []
            for user_id in set(started_users.keys()) & set(resource_users.keys()):
                start_time = datetime.fromisoformat(started_users[user_id].replace('Z', '+00:00'))
                resource_time = datetime.fromisoformat(resource_users[user_id].replace('Z', '+00:00'))
                time_diff = (resource_time - start_time).total_seconds()
                times_to_resource.append(time_diff)
            
            if times_to_resource:
                avg_time = sum(times_to_resource) / len(times_to_resource)
                print(f"  • Среднее время от начала до выбора ресурса: {avg_time:.1f} секунд")
        
        # Время от выбора ресурса до вытягивания карты
        if resource_users and card_users:
            times_to_card = []
            for user_id in set(resource_users.keys()) & set(card_users.keys()):
                resource_time = datetime.fromisoformat(resource_users[user_id].replace('Z', '+00:00'))
                card_time = datetime.fromisoformat(card_users[user_id].replace('Z', '+00:00'))
                time_diff = (card_time - resource_time).total_seconds()
                times_to_card.append(time_diff)
            
            if times_to_card:
                avg_time = sum(times_to_card) / len(times_to_card)
                print(f"  • Среднее время от выбора ресурса до карты: {avg_time:.1f} секунд")
        
        # Детальный анализ одного пользователя (пример)
        print(f"\n🔍 ПРИМЕР ДЕТАЛЬНОГО АНАЛИЗА ПОЛЬЗОВАТЕЛЯ:")
        if started_users:
            example_user = list(started_users.keys())[0]
            print(f"   Пользователь ID {example_user}:")
            
            # Получаем все шаги этого пользователя
            cursor = conn.execute(f"""
                SELECT step, timestamp, metadata
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND user_id = ?
                AND timestamp >= datetime('now', '-{days} days')
                ORDER BY timestamp
            """, (example_user,))
            user_steps = cursor.fetchall()
            
            for step in user_steps:
                print(f"     • {step['step']} - {step['timestamp']}")
                if step['metadata']:
                    try:
                        meta = json.loads(step['metadata'])
                        if meta:
                            print(f"       Метаданные: {meta}")
                    except:
                        pass
        
        print(f"\n✅ РЕКОМЕНДАЦИИ:")
        if lost_after_start:
            print(f"  • КРИТИЧНО: {len(lost_after_start)} пользователей не выбрали ресурс")
            print(f"    → Проверить кнопки выбора ресурса")
            print(f"    → Проверить обработчик process_initial_resource_callback")
        
        if lost_after_resource:
            print(f"  • ВАЖНО: {len(lost_after_resource)} пользователей не вытянули карту")
            print(f"    → Проверить логику выбора карты")
            print(f"    → Проверить функцию draw_card_direct")
        
        if lost_after_card:
            print(f"  • СРЕДНЕ: {len(lost_after_card)} пользователей не выбрали диалог")
            print(f"    → Возможно, пользователи не хотят углубляться")
        
        if lost_after_ai_choice:
            print(f"  • МАЛО: {len(lost_after_ai_choice)} пользователей не завершили сценарий")
            print(f"    → Проверить логику завершения")
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    analyze_user_dropoffs(7) 