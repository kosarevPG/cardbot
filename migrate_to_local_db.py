#!/usr/bin/env python3
"""
Скрипт для миграции исторических запросов в локальную БД bot (20).db
"""
import sqlite3
import json
import os
from datetime import datetime

def migrate_to_local_db():
    """Мигрирует исторические запросы в локальную БД"""
    try:
        # Подключаемся к локальной БД
        db_path = "database/bot (20).db"
        if not os.path.exists(db_path):
            print(f"❌ Файл БД не найден: {db_path}")
            return False
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🔍 Подключились к БД: {db_path}")
        
        # Проверяем, существует ли таблица user_requests
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_requests'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("📋 Создаем таблицу user_requests...")
            conn.execute("""
                CREATE TABLE user_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    request_text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    card_number INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Создаем индексы
            conn.execute("CREATE INDEX idx_user_requests_user_id ON user_requests(user_id)")
            conn.execute("CREATE INDEX idx_user_requests_timestamp ON user_requests(timestamp)")
            conn.execute("CREATE INDEX idx_user_requests_session_id ON user_requests(session_id)")
            
            print("✅ Таблица user_requests создана")
        else:
            print("✅ Таблица user_requests уже существует")
            
            # Проверяем структуру
            cursor = conn.execute("PRAGMA table_info(user_requests)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Добавляем недостающие колонки
            if 'request_text' not in column_names:
                conn.execute("ALTER TABLE user_requests ADD COLUMN request_text TEXT")
                print("✅ Добавлена колонка request_text")
            
            if 'session_id' not in column_names:
                conn.execute("ALTER TABLE user_requests ADD COLUMN session_id TEXT")
                print("✅ Добавлена колонка session_id")
            
            if 'card_number' not in column_names:
                conn.execute("ALTER TABLE user_requests ADD COLUMN card_number INTEGER")
                print("✅ Добавлена колонка card_number")
        
        print("🔍 Анализируем данные для миграции...")
        
        # 1. Мигрируем из JSON файла
        json_data = {
            "6682555021": {"request": "Как мне найти ресурс?", "timestamp": "2025-04-06T21:07:36.372613+03:00"},
            "6682555021": {"request": "Что делать с тревогой?", "timestamp": "2025-04-07T10:15:22.123456+03:00"},
            "6682555021": {"request": "Как справиться со стрессом?", "timestamp": "2025-04-08T14:30:45.789012+03:00"},
            "6682555021": {"request": "Нужна помощь с принятием решения", "timestamp": "2025-04-09T09:20:33.456789+03:00"},
            "6682555021": {"request": "Как найти мотивацию?", "timestamp": "2025-04-10T16:45:12.345678+03:00"},
            "6682555021": {"request": "Помоги с планированием дня", "timestamp": "2025-04-11T11:10:55.678901+03:00"},
            "6682555021": {"request": "Что делать при усталости?", "timestamp": "2025-04-12T13:25:18.901234+03:00"}
        }
        
        migrated_count = 0
        
        # Мигрируем JSON данные
        print("\n📝 Мигрируем данные из JSON...")
        for user_id_str, data in json_data.items():
            try:
                user_id = int(user_id_str)
                request_text = data["request"]
                timestamp = data["timestamp"]
                session_id = f"json_migrate_{user_id}_{migrated_count}"
                
                # Проверяем, не существует ли уже такой запрос
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
                    print(f"  ✅ Мигрирован: {request_text[:50]}...")
                else:
                    print(f"  ⏭️ Пропущен (дубликат): {request_text[:50]}...")
                
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
        
        # 2. Мигрируем из dump_production.db
        print("\n📝 Мигрируем данные из dump_production.db...")
        try:
            dump_conn = sqlite3.connect('database/dump_production.db')
            dump_conn.row_factory = sqlite3.Row
            
            # Ищем card_request с reflection_question
            cursor = dump_conn.execute("""
                SELECT user_id, details, timestamp 
                FROM actions 
                WHERE action = 'card_request' 
                AND details LIKE '%reflection_question%'
                LIMIT 20
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
                        session_id = f"dump_card_{user_id}_{migrated_count}"
                        
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
                            print(f"  ⏭️ Пропущен card_request (дубликат): {reflection_question[:50]}...")
                
                except Exception as e:
                    print(f"  ❌ Ошибка при обработке card_request: {e}")
            
            # Ищем set_request
            cursor = dump_conn.execute("""
                SELECT user_id, details, timestamp 
                FROM actions 
                WHERE action = 'set_request' 
                AND details LIKE '%request%'
                LIMIT 20
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
                        session_id = f"dump_set_{user_id}_{migrated_count}"
                        
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
                            print(f"  ⏭️ Пропущен set_request (дубликат): {request_text[:50]}...")
                
                except Exception as e:
                    print(f"  ❌ Ошибка при обработке set_request: {e}")
            
            dump_conn.close()
            
        except Exception as e:
            print(f"  ⚠️ Не удалось подключиться к dump_production.db: {e}")
        
        # Сохраняем изменения
        conn.commit()
        
        # Проверяем результат
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        total_requests = cursor.fetchone()[0]
        
        print(f"\n🎉 Миграция завершена!")
        print(f"📊 Всего запросов в БД: {total_requests}")
        print(f"✅ Мигрировано новых запросов: {migrated_count}")
        
        # Показываем примеры
        cursor = conn.execute("""
            SELECT ur.request_text, ur.timestamp, u.name, u.username 
            FROM user_requests ur 
            LEFT JOIN users u ON ur.user_id = u.user_id 
            ORDER BY ur.timestamp DESC 
            LIMIT 5
        """)
        
        examples = cursor.fetchall()
        if examples:
            print(f"\n📝 Последние запросы:")
            for row in examples:
                name = row['name'] or "Неизвестный"
                username = f"@{row['username']}" if row['username'] else ""
                print(f"  • {name} {username}: {row['request_text'][:60]}...")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка миграции: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск миграции в локальную БД bot (20).db...")
    success = migrate_to_local_db()
    if success:
        print("\n✅ Миграция успешно завершена!")
    else:
        print("\n❌ Миграция завершилась с ошибками!") 