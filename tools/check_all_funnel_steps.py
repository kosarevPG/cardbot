#!/usr/bin/env python3
"""
Скрипт для проверки всех возможных шагов воронки "Карта дня"
"""

import sqlite3
import json
from datetime import datetime, timedelta
import os

# Путь к базе данных
DB_PATH = "database/dev.db"

def check_all_funnel_steps(days=7):
    """Проверяет все возможные шаги воронки карты дня"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        print(f"🔍 ПРОВЕРКА ВСЕХ ШАГОВ ВОРОНКИ 'КАРТА ДНЯ' (за {days} дней)")
        print("=" * 80)
        
        # Получаем все уникальные шаги для сценария card_of_day
        cursor = conn.execute(f"""
            SELECT DISTINCT step, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND timestamp >= datetime('now', '-{days} days')
            GROUP BY step
            ORDER BY count DESC
        """)
        
        steps = cursor.fetchall()
        
        print(f"\n📊 ВСЕ ЗАЛОГИРОВАННЫЕ ШАГИ:")
        for step in steps:
            print(f"  • {step['step']}: {step['count']} событий")
        
        # Определяем правильную последовательность шагов
        expected_steps = [
            'started',
            'initial_resource_selected', 
            'request_type_selected',
            'text_request_provided',  # опционально
            'card_drawn',
            'initial_response_provided',
            'ai_reflection_choice',
            'ai_response_1_provided',  # опционально
            'ai_response_2_provided',  # опционально
            'ai_response_3_provided',  # опционально
            'mood_change_recorded',
            'completed',
            'usefulness_rating',
            'already_used_today'  # опционально
        ]
        
        print(f"\n🎯 ОЖИДАЕМАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ ШАГОВ:")
        for i, step in enumerate(expected_steps, 1):
            count = next((s['count'] for s in steps if s['step'] == step), 0)
            status = "✅" if count > 0 else "❌"
            print(f"  {i:2d}. {status} {step}: {count} событий")
        
        # Проверяем основные шаги воронки
        print(f"\n📈 ОСНОВНАЯ ВОРОНКА:")
        
        # Шаг 1: Начали сессию
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'started'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        started = cursor.fetchone()['count']
        print(f"1️⃣ Начали сессию: {started} пользователей")
        
        # Шаг 2: Выбрали ресурс
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'initial_resource_selected'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        resource_selected = cursor.fetchone()['count']
        print(f"2️⃣ Выбрали ресурс: {resource_selected} пользователей")
        
        # Шаг 3: Выбрали тип запроса
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'request_type_selected'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        request_type_selected = cursor.fetchone()['count']
        print(f"3️⃣ Выбрали тип запроса: {request_type_selected} пользователей")
        
        # Шаг 4: Вытянули карту
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'card_drawn'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        card_drawn = cursor.fetchone()['count']
        print(f"4️⃣ Вытянули карту: {card_drawn} пользователей")
        
        # Шаг 5: Написали первую ассоциацию
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'initial_response_provided'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        initial_response_provided = cursor.fetchone()['count']
        print(f"5️⃣ Написали ассоциацию: {initial_response_provided} пользователей")
        
        # Шаг 6: Выбрали углубляющий диалог
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'ai_reflection_choice'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        ai_reflection_choice = cursor.fetchone()['count']
        print(f"6️⃣ Выбрали углубляющий диалог: {ai_reflection_choice} пользователей")
        
        # Шаг 7: Завершили сценарий
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'completed'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        completed = cursor.fetchone()['count']
        print(f"7️⃣ Завершили сценарий: {completed} пользователей")
        
        # Анализ потерь
        print(f"\n🚨 АНАЛИЗ ПОТЕРЬ:")
        if started > 0:
            print(f"  • Шаг 1→2: {started - resource_selected} пользователей ({((started - resource_selected) / started * 100):.1f}%)")
            print(f"  • Шаг 2→3: {resource_selected - request_type_selected} пользователей ({((resource_selected - request_type_selected) / started * 100):.1f}%)")
            print(f"  • Шаг 3→4: {request_type_selected - card_drawn} пользователей ({((request_type_selected - card_drawn) / started * 100):.1f}%)")
            print(f"  • Шаг 4→5: {card_drawn - initial_response_provided} пользователей ({((card_drawn - initial_response_provided) / started * 100):.1f}%)")
            print(f"  • Шаг 5→6: {initial_response_provided - ai_reflection_choice} пользователей ({((initial_response_provided - ai_reflection_choice) / started * 100):.1f}%)")
            print(f"  • Шаг 6→7: {ai_reflection_choice - completed} пользователей ({((ai_reflection_choice - completed) / started * 100):.1f}%)")
        
        # Проверяем опциональные шаги
        print(f"\n🔍 ОПЦИОНАЛЬНЫЕ ШАГИ:")
        
        # Текстовые запросы
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'text_request_provided'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        text_requests = cursor.fetchone()['count']
        print(f"  • Написали текстовый запрос: {text_requests} пользователей")
        
        # AI ответы
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'ai_response_1_provided'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        ai_response_1 = cursor.fetchone()['count']
        print(f"  • Получили AI ответ 1: {ai_response_1} пользователей")
        
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'ai_response_2_provided'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        ai_response_2 = cursor.fetchone()['count']
        print(f"  • Получили AI ответ 2: {ai_response_2} пользователей")
        
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'ai_response_3_provided'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        ai_response_3 = cursor.fetchone()['count']
        print(f"  • Получили AI ответ 3: {ai_response_3} пользователей")
        
        # Изменение настроения
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'mood_change_recorded'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        mood_change = cursor.fetchone()['count']
        print(f"  • Записали изменение настроения: {mood_change} пользователей")
        
        # Оценка полезности
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'usefulness_rating'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        usefulness_rating = cursor.fetchone()['count']
        print(f"  • Оценили полезность: {usefulness_rating} пользователей")
        
        # Уже использовали сегодня
        cursor = conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'already_used_today'
            AND timestamp >= datetime('now', '-{days} days')
        """)
        already_used = cursor.fetchone()['count']
        print(f"  • Уже использовали сегодня: {already_used} пользователей")
        
        print(f"\n✅ ИТОГОВАЯ КОНВЕРСИЯ: {completed}/{started} = {(completed/started*100):.1f}%" if started > 0 else "\n✅ Нет данных")
        
        # Проверяем, есть ли шаги, которые не логируются
        logged_steps = {step['step'] for step in steps}
        missing_steps = set(expected_steps) - logged_steps
        
        if missing_steps:
            print(f"\n⚠️ ШАГИ, КОТОРЫЕ НЕ ЛОГИРУЮТСЯ:")
            for step in missing_steps:
                print(f"  • {step}")
        
        # Проверяем неожиданные шаги
        unexpected_steps = logged_steps - set(expected_steps)
        if unexpected_steps:
            print(f"\n❓ НЕОЖИДАННЫЕ ШАГИ:")
            for step in unexpected_steps:
                print(f"  • {step}")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_all_funnel_steps(7) 