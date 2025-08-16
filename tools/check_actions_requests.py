#!/usr/bin/env python3
"""
Скрипт для анализа запросов в таблице actions из dump_production.db
"""
import sqlite3
import json
from datetime import datetime

def check_actions_requests():
    """Анализирует запросы в таблице actions"""
    print("🔍 АНАЛИЗ ЗАПРОСОВ В ТАБЛИЦЕ ACTIONS")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('database/dump_production.db')
        conn.row_factory = sqlite3.Row
        
        # Проверяем типы действий
        cursor = conn.execute("SELECT DISTINCT action FROM actions ORDER BY action")
        actions = [row['action'] for row in cursor.fetchall()]
        print(f"📊 Типы действий в таблице actions:")
        for action in actions:
            cursor = conn.execute("SELECT COUNT(*) as count FROM actions WHERE action = ?", (action,))
            count = cursor.fetchone()['count']
            print(f"  • {action}: {count} записей")
        
        # Ищем записи с запросами (card_request)
        print(f"\n📋 АНАЛИЗ ЗАПИСЕЙ card_request:")
        cursor = conn.execute("""
            SELECT user_id, username, name, details, timestamp
            FROM actions 
            WHERE action = 'card_request'
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        requests_found = 0
        for row in cursor.fetchall():
            requests_found += 1
            user_id = row['user_id']
            username = row['username'] or "без username"
            name = row['name'] or "Без имени"
            details = row['details']
            timestamp = row['timestamp']
            
            # Парсим details (JSON)
            try:
                details_data = json.loads(details)
                card_number = details_data.get('card_number', 'N/A')
                reflection_question = details_data.get('reflection_question', '')
            except:
                card_number = 'N/A'
                reflection_question = details_data if isinstance(details_data, str) else str(details_data)
            
            # Форматируем дату
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%d.%m.%Y %H:%M')
            except:
                formatted_date = timestamp
            
            print(f"\n🔸 ЗАПРОС #{requests_found}")
            print(f"   📅 Дата: {formatted_date}")
            print(f"   👤 Пользователь: {user_id} | {name} | @{username}")
            print(f"   🎴 Карта: {card_number}")
            if reflection_question:
                print(f"   💬 Вопрос: «{reflection_question}»")
            print(f"   {'─' * 50}")
        
        print(f"\n📊 ИТОГО НАЙДЕНО ЗАПРОСОВ: {requests_found}")
        
        # Статистика по пользователям
        cursor = conn.execute("""
            SELECT user_id, COUNT(*) as requests_count
            FROM actions 
            WHERE action = 'card_request'
            GROUP BY user_id
            ORDER BY requests_count DESC
            LIMIT 5
        """)
        
        print(f"\n👥 ТОП-5 ПОЛЬЗОВАТЕЛЕЙ ПО КОЛИЧЕСТВУ ЗАПРОСОВ:")
        for row in cursor.fetchall():
            user_id = row['user_id']
            count = row['requests_count']
            print(f"  • {user_id}: {count} запросов")
        
        conn.close()
        print(f"\n✅ АНАЛИЗ ЗАВЕРШЕН")
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_actions_requests() 