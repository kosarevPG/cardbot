#!/usr/bin/env python3
"""
Добавление недостающих запросов из initial_response_provided
"""
import sqlite3
import json
from datetime import datetime

def add_missing_requests():
    """Добавляет недостающие запросы из initial_response_provided"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🔍 Добавляем недостающие запросы из initial_response_provided")
        print(f"📁 БД: {db_path}")
        
        # Находим все initial_response_provided
        cursor = conn.execute("""
            SELECT id, user_id, username, name, action, details, timestamp
            FROM actions 
            WHERE action = 'initial_response_provided'
            ORDER BY timestamp DESC
        """)
        
        initial_responses = cursor.fetchall()
        print(f"📊 Найдено {len(initial_responses)} записей initial_response_provided")
        
        added_count = 0
        skipped_count = 0
        
        for row in initial_responses:
            try:
                details = json.loads(row['details'])
                response_text = details.get('response', '')
                session_id = details.get('session_id', '')
                
                if not response_text:
                    print(f"⚠️ Пропускаем ID {row['id']}: нет response")
                    skipped_count += 1
                    continue
                
                # Проверяем, есть ли уже такой запрос в user_requests
                cursor2 = conn.execute("""
                    SELECT id FROM user_requests 
                    WHERE user_id = ? AND request_text = ?
                """, (row['user_id'], response_text))
                
                existing = cursor2.fetchone()
                if existing:
                    print(f"⏭️ Пропускаем ID {row['id']}: уже есть в user_requests")
                    skipped_count += 1
                    continue
                
                # Добавляем запрос в user_requests
                conn.execute("""
                    INSERT INTO user_requests (user_id, request_text, timestamp, session_id)
                    VALUES (?, ?, ?, ?)
                """, (row['user_id'], response_text, row['timestamp'], session_id))
                
                print(f"✅ Добавлен ID {row['id']}: User {row['user_id']} - '{response_text[:50]}...'")
                added_count += 1
                
            except Exception as e:
                print(f"❌ Ошибка при обработке ID {row['id']}: {e}")
                skipped_count += 1
        
        # Сохраняем изменения
        conn.commit()
        
        # Проверяем результат
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        total_after = cursor.fetchone()[0]
        
        print(f"\n🎉 Добавление завершено!")
        print(f"📊 Добавлено записей: {added_count}")
        print(f"📊 Пропущено записей: {skipped_count}")
        print(f"📊 Всего записей в user_requests: {total_after}")
        
        # Показываем примеры добавленных запросов
        if added_count > 0:
            cursor = conn.execute("""
                SELECT ur.request_text, ur.timestamp, u.name, u.username, ur.user_id
                FROM user_requests ur 
                LEFT JOIN users u ON ur.user_id = u.user_id 
                ORDER BY ur.timestamp DESC 
                LIMIT 5
            """)
            
            examples = cursor.fetchall()
            print(f"\n📝 Последние добавленные запросы:")
            for i, row in enumerate(examples, 1):
                name = row['name'] or "Неизвестный"
                username = f"@{row['username']}" if row['username'] else ""
                user_id = row['user_id']
                
                # Форматируем дату
                try:
                    dt = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                    formatted_date = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    formatted_date = row['timestamp'][:16]
                
                # Обрезаем длинный текст
                request_text = row['request_text']
                if len(request_text) > 60:
                    request_text = request_text[:60] + "..."
                
                print(f"  {i}. {formatted_date} | {name} {username} (ID: {user_id})")
                print(f"     💬 {request_text}")
        
        # Проверяем конкретную запись
        cursor = conn.execute("""
            SELECT * FROM user_requests 
            WHERE user_id = 1740579634
            ORDER BY timestamp DESC
        """)
        
        oleg_requests = cursor.fetchall()
        if oleg_requests:
            print(f"\n✅ Запросы Олега (1740579634) в user_requests:")
            for ur in oleg_requests:
                print(f"  • ID: {ur['id']} | Text: {ur['request_text'][:50]}... | Time: {ur['timestamp'][:16]}")
        else:
            print(f"\n❌ Запросы Олега (1740579634) не найдены")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении: {e}")
        return False

if __name__ == "__main__":
    success = add_missing_requests()
    if success:
        print("\n✅ Добавление успешно завершено!")
    else:
        print("\n❌ Добавление завершилось с ошибками!") 