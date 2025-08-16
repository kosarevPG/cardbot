#!/usr/bin/env python3
"""
Поиск конкретной записи в таблице actions
"""
import sqlite3
import json

def find_specific_action():
    """Ищет конкретную запись в actions"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🔍 Ищем запись с ID 8481")
        print(f"📁 БД: {db_path}")
        
        # Ищем конкретную запись по ID
        cursor = conn.execute("""
            SELECT * FROM actions 
            WHERE id = 8481
        """)
        
        action = cursor.fetchone()
        if action:
            print(f"\n✅ Найдена запись:")
            print(f"📝 ID: {action['id']}")
            print(f"👤 User ID: {action['user_id']}")
            print(f"👤 Username: {action['username']}")
            print(f"👤 Name: {action['name']}")
            print(f"🏷️ Action: {action['action']}")
            print(f"📅 Timestamp: {action['timestamp']}")
            
            if action['details']:
                try:
                    details = json.loads(action['details'])
                    print(f"📄 Details: {json.dumps(details, indent=2, ensure_ascii=False)}")
                except:
                    print(f"📄 Details (raw): {action['details']}")
            
            # Проверяем, есть ли эта запись в user_requests
            cursor2 = conn.execute("""
                SELECT * FROM user_requests 
                WHERE user_id = ?
            """, (action['user_id'],))
            
            user_requests = cursor2.fetchall()
            if user_requests:
                print(f"\n✅ Найдено в user_requests: {len(user_requests)} записей")
                for ur in user_requests:
                    print(f"  • ID: {ur['id']} | Text: {ur['request_text'][:50]}... | Time: {ur['timestamp'][:16]}")
            else:
                print(f"\n❌ Записей в user_requests для пользователя {action['user_id']} не найдено")
        else:
            print(f"\n❌ Запись с ID 8481 не найдена")
            
            # Проверяем максимальный ID в таблице
            cursor = conn.execute("SELECT MAX(id) FROM actions")
            max_id = cursor.fetchone()[0]
            print(f"📊 Максимальный ID в actions: {max_id}")
            
            # Ищем записи с user_id 1740579634
            cursor = conn.execute("""
                SELECT * FROM actions 
                WHERE user_id = 1740579634
                ORDER BY timestamp DESC
            """)
            
            user_actions = cursor.fetchall()
            if user_actions:
                print(f"\n🔍 Найдено {len(user_actions)} записей для пользователя 1740579634:")
                for i, row in enumerate(user_actions[:5], 1):
                    print(f"\n  {i}. ID: {row['id']} | Action: {row['action']} | Time: {row['timestamp'][:16]}")
                    if row['details']:
                        try:
                            details = json.loads(row['details'])
                            if 'response' in details:
                                print(f"     💬 Response: {details['response'][:50]}...")
                        except:
                            print(f"     📄 Details: {row['details'][:50]}...")
            else:
                print(f"\n❌ Записей для пользователя 1740579634 не найдено")
        
        # Проверяем все initial_response_provided
        print(f"\n🔍 Все записи initial_response_provided:")
        cursor = conn.execute("""
            SELECT id, user_id, action, details, timestamp
            FROM actions 
            WHERE action = 'initial_response_provided'
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
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    find_specific_action() 