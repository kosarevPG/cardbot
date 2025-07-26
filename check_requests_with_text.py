#!/usr/bin/env python3
"""
Скрипт для поиска запросов с текстом в таблице actions
"""
import sqlite3
import json
from datetime import datetime

def check_requests_with_text():
    """Ищет запросы с текстом в таблице actions"""
    print("🔍 ПОИСК ЗАПРОСОВ С ТЕКСТОМ В ACTIONS")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('database/dump_production.db')
        conn.row_factory = sqlite3.Row
        
        # Ищем записи с reflection_question
        cursor = conn.execute("""
            SELECT user_id, username, name, details, timestamp
            FROM actions 
            WHERE action = 'card_request' 
            AND details LIKE '%reflection_question%'
            ORDER BY timestamp DESC
            LIMIT 15
        """)
        
        requests_with_text = 0
        for row in cursor.fetchall():
            requests_with_text += 1
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
            
            print(f"\n🔸 ЗАПРОС С ТЕКСТОМ #{requests_with_text}")
            print(f"   📅 Дата: {formatted_date}")
            print(f"   👤 Пользователь: {user_id} | {name} | @{username}")
            print(f"   🎴 Карта: {card_number}")
            print(f"   💬 Запрос: «{reflection_question}»")
            print(f"   {'─' * 50}")
        
        print(f"\n📊 ИТОГО ЗАПРОСОВ С ТЕКСТОМ: {requests_with_text}")
        
        # Общая статистика
        cursor = conn.execute("SELECT COUNT(*) as total FROM actions WHERE action = 'card_request'")
        total_requests = cursor.fetchone()['total']
        
        cursor = conn.execute("SELECT COUNT(*) as with_text FROM actions WHERE action = 'card_request' AND details LIKE '%reflection_question%'")
        with_text = cursor.fetchone()['with_text']
        
        print(f"\n📈 СТАТИСТИКА:")
        print(f"  • Всего card_request: {total_requests}")
        print(f"  • С текстом запроса: {with_text}")
        print(f"  • Без текста: {total_requests - with_text}")
        
        # Проверяем другие типы действий, которые могут содержать запросы
        print(f"\n🔍 ПРОВЕРКА ДРУГИХ ТИПОВ ДЕЙСТВИЙ:")
        
        action_types = ['set_request', 'first_grok_response', 'second_grok_response', 'third_grok_response']
        for action_type in action_types:
            cursor = conn.execute("SELECT COUNT(*) as count FROM actions WHERE action = ?", (action_type,))
            count = cursor.fetchone()['count']
            print(f"  • {action_type}: {count} записей")
            
            if count > 0:
                cursor = conn.execute("""
                    SELECT user_id, details, timestamp
                    FROM actions 
                    WHERE action = ?
                    ORDER BY timestamp DESC
                    LIMIT 2
                """, (action_type,))
                
                for row in cursor.fetchall():
                    details = row['details']
                    try:
                        details_data = json.loads(details)
                        if isinstance(details_data, dict) and 'request' in details_data:
                            print(f"    - Найден запрос: «{details_data['request']}»")
                    except:
                        if 'request' in str(details):
                            print(f"    - Возможный запрос в details")
        
        conn.close()
        print(f"\n✅ АНАЛИЗ ЗАВЕРШЕН")
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_requests_with_text() 