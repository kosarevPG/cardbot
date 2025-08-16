#!/usr/bin/env python3
"""
Проверка конкретной записи в таблице actions
"""
import sqlite3
import json

def check_missing_action():
    """Проверяет конкретную запись в actions"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🔍 Проверяем запись в actions")
        print(f"📁 БД: {db_path}")
        
        # Ищем конкретную запись
        cursor = conn.execute("""
            SELECT * FROM actions 
            WHERE id = 8481 OR user_id = 1740579634 OR action_type = 'initial_response_provided'
            ORDER BY timestamp DESC
        """)
        
        actions = cursor.fetchall()
        print(f"\n📋 Найдено {len(actions)} записей:")
        
        for row in actions:
            print(f"\n📝 ID: {row['id']}")
            print(f"👤 User ID: {row['user_id']}")
            print(f"🏷️ Action: {row['action_type']}")
            print(f"📅 Timestamp: {row['timestamp']}")
            
            if row['details']:
                try:
                    details = json.loads(row['details'])
                    print(f"📄 Details: {json.dumps(details, indent=2, ensure_ascii=False)}")
                except:
                    print(f"📄 Details (raw): {row['details']}")
            
            # Проверяем, есть ли эта запись в user_requests
            cursor2 = conn.execute("""
                SELECT * FROM user_requests 
                WHERE user_id = ? AND request_text LIKE ?
            """, (row['user_id'], '%Чувство что произойдут хорошие собития%'))
            
            user_requests = cursor2.fetchall()
            if user_requests:
                print(f"✅ Найдено в user_requests: {len(user_requests)} записей")
                for ur in user_requests:
                    print(f"  • ID: {ur['id']}, Text: {ur['request_text'][:50]}...")
            else:
                print(f"❌ НЕ найдено в user_requests")
        
        # Проверяем все initial_response_provided
        print(f"\n🔍 Все записи initial_response_provided:")
        cursor = conn.execute("""
            SELECT id, user_id, action_type, details, timestamp
            FROM actions 
            WHERE action_type = 'initial_response_provided'
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        initial_responses = cursor.fetchall()
        for row in initial_responses:
            print(f"\n📝 ID: {row['id']} | User: {row['user_id']} | Time: {row['timestamp'][:16]}")
            if row['details']:
                try:
                    details = json.loads(row['details'])
                    response = details.get('response', 'Нет response')
                    print(f"💬 Response: {response[:50]}...")
                except:
                    print(f"💬 Details: {row['details'][:50]}...")
        
        # Проверяем, есть ли пользователь 1740579634 в user_requests
        print(f"\n🔍 Проверяем пользователя 1740579634 в user_requests:")
        cursor = conn.execute("""
            SELECT * FROM user_requests 
            WHERE user_id = 1740579634
            ORDER BY timestamp DESC
        """)
        
        user_requests = cursor.fetchall()
        if user_requests:
            print(f"✅ Найдено {len(user_requests)} записей для пользователя 1740579634:")
            for ur in user_requests:
                print(f"  • ID: {ur['id']} | Text: {ur['request_text'][:50]}... | Time: {ur['timestamp'][:16]}")
        else:
            print(f"❌ Записей для пользователя 1740579634 не найдено")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    check_missing_action() 