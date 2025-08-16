#!/usr/bin/env python3
"""
Расширенная миграция всех типов запросов из actions в user_requests
"""
import sqlite3
import json
import os
from datetime import datetime

def migrate_all_requests():
    """Мигрирует все типы запросов из actions в user_requests"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🚀 Расширенная миграция всех типов запросов")
        print(f"📁 БД: {db_path}")
        
        migrated_count = 0
        
        # 1. typed_question_submitted
        print(f"\n📝 Мигрируем typed_question_submitted...")
        cursor = conn.execute("""
            SELECT user_id, details, timestamp 
            FROM actions 
            WHERE action = 'typed_question_submitted' 
            AND details LIKE '%request%'
            ORDER BY timestamp DESC
        """)
        
        typed_questions = cursor.fetchall()
        print(f"  🔍 Найдено {len(typed_questions)} записей")
        
        for row in typed_questions:
            try:
                details = json.loads(row['details'])
                request_text = details.get('request')
                
                if request_text:
                    user_id = row['user_id']
                    timestamp = row['timestamp']
                    session_id = f"typed_question_{user_id}_{migrated_count}"
                    
                    # Проверяем дубликаты
                    cursor = conn.execute(
                        "SELECT id FROM user_requests WHERE user_id = ? AND request_text = ? AND session_id = ?",
                        (user_id, request_text, session_id)
                    )
                    
                    if not cursor.fetchone():
                        conn.execute(
                            "INSERT INTO user_requests (user_id, request_text, timestamp, session_id) VALUES (?, ?, ?, ?)",
                            (user_id, request_text, timestamp, session_id)
                        )
                        migrated_count += 1
                        print(f"  ✅ Мигрирован typed_question: {request_text[:50]}...")
                    else:
                        print(f"  ⏭️ Пропущен (дубликат): {request_text[:50]}...")
            
            except Exception as e:
                print(f"  ❌ Ошибка при обработке typed_question: {e}")
        
        # 2. initial_response_provided (только с непустыми request)
        print(f"\n📝 Мигрируем initial_response_provided...")
        cursor = conn.execute("""
            SELECT user_id, details, timestamp 
            FROM actions 
            WHERE action = 'initial_response_provided' 
            AND details LIKE '%request%'
            ORDER BY timestamp DESC
        """)
        
        initial_responses = cursor.fetchall()
        print(f"  🔍 Найдено {len(initial_responses)} записей")
        
        for row in initial_responses:
            try:
                details = json.loads(row['details'])
                request_text = details.get('request')
                
                if request_text and request_text.strip():  # Проверяем, что запрос не пустой
                    user_id = row['user_id']
                    timestamp = row['timestamp']
                    card_number = details.get('card_number')
                    session_id = f"initial_response_{user_id}_{migrated_count}"
                    
                    # Проверяем дубликаты
                    cursor = conn.execute(
                        "SELECT id FROM user_requests WHERE user_id = ? AND request_text = ? AND session_id = ?",
                        (user_id, request_text, session_id)
                    )
                    
                    if not cursor.fetchone():
                        conn.execute(
                            "INSERT INTO user_requests (user_id, request_text, timestamp, session_id, card_number) VALUES (?, ?, ?, ?, ?)",
                            (user_id, request_text, timestamp, session_id, card_number)
                        )
                        migrated_count += 1
                        print(f"  ✅ Мигрирован initial_response: {request_text[:50]}...")
                    else:
                        print(f"  ⏭️ Пропущен (дубликат): {request_text[:50]}...")
            
            except Exception as e:
                print(f"  ❌ Ошибка при обработке initial_response: {e}")
        
        # 3. initial_response (только с непустыми request)
        print(f"\n📝 Мигрируем initial_response...")
        cursor = conn.execute("""
            SELECT user_id, details, timestamp 
            FROM actions 
            WHERE action = 'initial_response' 
            AND details LIKE '%request%'
            ORDER BY timestamp DESC
        """)
        
        initial_responses_old = cursor.fetchall()
        print(f"  🔍 Найдено {len(initial_responses_old)} записей")
        
        for row in initial_responses_old:
            try:
                details = json.loads(row['details'])
                request_text = details.get('request')
                
                if request_text and request_text.strip():  # Проверяем, что запрос не пустой
                    user_id = row['user_id']
                    timestamp = row['timestamp']
                    card_number = details.get('card_number')
                    session_id = f"initial_response_old_{user_id}_{migrated_count}"
                    
                    # Проверяем дубликаты
                    cursor = conn.execute(
                        "SELECT id FROM user_requests WHERE user_id = ? AND request_text = ? AND session_id = ?",
                        (user_id, request_text, session_id)
                    )
                    
                    if not cursor.fetchone():
                        conn.execute(
                            "INSERT INTO user_requests (user_id, request_text, timestamp, session_id, card_number) VALUES (?, ?, ?, ?, ?)",
                            (user_id, request_text, timestamp, session_id, card_number)
                        )
                        migrated_count += 1
                        print(f"  ✅ Мигрирован initial_response_old: {request_text[:50]}...")
                    else:
                        print(f"  ⏭️ Пропущен (дубликат): {request_text[:50]}...")
            
            except Exception as e:
                print(f"  ❌ Ошибка при обработке initial_response_old: {e}")
        
        # 4. card_drawn_with_request
        print(f"\n📝 Мигрируем card_drawn_with_request...")
        cursor = conn.execute("""
            SELECT user_id, details, timestamp 
            FROM actions 
            WHERE action = 'card_drawn_with_request' 
            AND details LIKE '%request%'
            ORDER BY timestamp DESC
        """)
        
        card_drawn_requests = cursor.fetchall()
        print(f"  🔍 Найдено {len(card_drawn_requests)} записей")
        
        for row in card_drawn_requests:
            try:
                details = json.loads(row['details'])
                request_text = details.get('request')
                
                if request_text:
                    user_id = row['user_id']
                    timestamp = row['timestamp']
                    card_number = details.get('card_number')
                    session_id = f"card_drawn_request_{user_id}_{migrated_count}"
                    
                    # Проверяем дубликаты
                    cursor = conn.execute(
                        "SELECT id FROM user_requests WHERE user_id = ? AND request_text = ? AND session_id = ?",
                        (user_id, request_text, session_id)
                    )
                    
                    if not cursor.fetchone():
                        conn.execute(
                            "INSERT INTO user_requests (user_id, request_text, timestamp, session_id, card_number) VALUES (?, ?, ?, ?, ?)",
                            (user_id, request_text, timestamp, session_id, card_number)
                        )
                        migrated_count += 1
                        print(f"  ✅ Мигрирован card_drawn_request: {request_text[:50]}...")
                    else:
                        print(f"  ⏭️ Пропущен (дубликат): {request_text[:50]}...")
            
            except Exception as e:
                print(f"  ❌ Ошибка при обработке card_drawn_request: {e}")
        
        # Сохраняем изменения
        conn.commit()
        
        # Проверяем результат
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        total_requests = cursor.fetchone()[0]
        
        print(f"\n🎉 Расширенная миграция завершена!")
        print(f"📊 Всего запросов в user_requests: {total_requests}")
        print(f"✅ Мигрировано новых запросов: {migrated_count}")
        
        # Показываем примеры
        cursor = conn.execute("""
            SELECT ur.request_text, ur.timestamp, u.name, u.username, ur.card_number
            FROM user_requests ur 
            LEFT JOIN users u ON ur.user_id = u.user_id 
            ORDER BY ur.timestamp DESC 
            LIMIT 10
        """)
        
        examples = cursor.fetchall()
        if examples:
            print(f"\n📝 Последние запросы:")
            for i, row in enumerate(examples, 1):
                name = row['name'] or "Неизвестный"
                username = f"@{row['username']}" if row['username'] else ""
                card_number = row['card_number'] or "N/A"
                
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
                
                print(f"  {i}. {formatted_date} | {name} {username} | Карта: {card_number}")
                print(f"     💬 {request_text}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка миграции: {e}")
        return False

if __name__ == "__main__":
    success = migrate_all_requests()
    if success:
        print("\n✅ Расширенная миграция успешно завершена!")
    else:
        print("\n❌ Миграция завершилась с ошибками!") 