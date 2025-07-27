#!/usr/bin/env python3
"""
Миграция данных из таблицы actions в user_requests
"""
import sqlite3
import json
import os
from datetime import datetime

def migrate_actions_to_requests():
    """Мигрирует данные из actions в user_requests"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🚀 Миграция данных из actions в user_requests")
        print(f"📁 БД: {db_path}")
        
        migrated_count = 0
        
        # 1. Мигрируем card_request записи
        print(f"\n📝 Мигрируем card_request записи...")
        cursor = conn.execute("""
            SELECT user_id, details, timestamp 
            FROM actions 
            WHERE action = 'card_request' 
            AND details LIKE '%reflection_question%'
            ORDER BY timestamp DESC
        """)
        
        card_requests = cursor.fetchall()
        print(f"  🔍 Найдено {len(card_requests)} card_request записей")
        
        for row in card_requests:
            try:
                details = json.loads(row['details'])
                reflection_question = details.get('reflection_question')
                
                if reflection_question:
                    user_id = row['user_id']
                    timestamp = row['timestamp']
                    session_id = f"card_request_{user_id}_{migrated_count}"
                    
                    # Проверяем дубликаты
                    cursor = conn.execute(
                        "SELECT id FROM user_requests WHERE user_id = ? AND request_text = ? AND session_id = ?",
                        (user_id, reflection_question, session_id)
                    )
                    
                    if not cursor.fetchone():
                        conn.execute(
                            "INSERT INTO user_requests (user_id, request_text, timestamp, session_id) VALUES (?, ?, ?, ?)",
                            (user_id, reflection_question, timestamp, session_id)
                        )
                        migrated_count += 1
                        print(f"  ✅ Мигрирован card_request: {reflection_question[:50]}...")
                    else:
                        print(f"  ⏭️ Пропущен (дубликат): {reflection_question[:50]}...")
            
            except Exception as e:
                print(f"  ❌ Ошибка при обработке card_request: {e}")
        
        # 2. Мигрируем set_request записи
        print(f"\n📝 Мигрируем set_request записи...")
        cursor = conn.execute("""
            SELECT user_id, details, timestamp 
            FROM actions 
            WHERE action = 'set_request' 
            AND details LIKE '%request%'
            ORDER BY timestamp DESC
        """)
        
        set_requests = cursor.fetchall()
        print(f"  🔍 Найдено {len(set_requests)} set_request записей")
        
        for row in set_requests:
            try:
                details = json.loads(row['details'])
                request_text = details.get('request')
                
                if request_text:
                    user_id = row['user_id']
                    timestamp = row['timestamp']
                    session_id = f"set_request_{user_id}_{migrated_count}"
                    
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
                        print(f"  ✅ Мигрирован set_request: {request_text[:50]}...")
                    else:
                        print(f"  ⏭️ Пропущен (дубликат): {request_text[:50]}...")
            
            except Exception as e:
                print(f"  ❌ Ошибка при обработке set_request: {e}")
        
        # 3. Мигрируем request_text_provided записи
        print(f"\n📝 Мигрируем request_text_provided записи...")
        cursor = conn.execute("""
            SELECT user_id, details, timestamp 
            FROM actions 
            WHERE action = 'request_text_provided' 
            AND details LIKE '%request%'
            ORDER BY timestamp DESC
        """)
        
        text_requests = cursor.fetchall()
        print(f"  🔍 Найдено {len(text_requests)} request_text_provided записей")
        
        for row in text_requests:
            try:
                details = json.loads(row['details'])
                request_text = details.get('request')
                
                if request_text:
                    user_id = row['user_id']
                    timestamp = row['timestamp']
                    session_id = f"text_provided_{user_id}_{migrated_count}"
                    
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
                        print(f"  ✅ Мигрирован request_text_provided: {request_text[:50]}...")
                    else:
                        print(f"  ⏭️ Пропущен (дубликат): {request_text[:50]}...")
            
            except Exception as e:
                print(f"  ❌ Ошибка при обработке request_text_provided: {e}")
        
        # Сохраняем изменения
        conn.commit()
        
        # Проверяем результат
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        total_requests = cursor.fetchone()[0]
        
        print(f"\n🎉 Миграция завершена!")
        print(f"📊 Всего запросов в user_requests: {total_requests}")
        print(f"✅ Мигрировано новых запросов: {migrated_count}")
        
        # Показываем примеры
        cursor = conn.execute("""
            SELECT ur.request_text, ur.timestamp, u.name, u.username 
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
                print(f"  {i}. {name} {username}: {row['request_text'][:60]}...")
                print(f"     📅 {row['timestamp']}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка миграции: {e}")
        return False

if __name__ == "__main__":
    success = migrate_actions_to_requests()
    if success:
        print("\n✅ Миграция успешно завершена!")
    else:
        print("\n❌ Миграция завершилась с ошибками!") 