#!/usr/bin/env python3
"""
Скрипт для исправления структуры таблицы user_requests
"""
import sqlite3
import os

def fix_table_structure():
    """Исправляет структуру таблицы user_requests"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🔍 Проверяем структуру таблицы user_requests в {db_path}")
        
        # Проверяем текущую структуру
        cursor = conn.execute("PRAGMA table_info(user_requests)")
        columns = cursor.fetchall()
        print(f"📋 Текущая структура таблицы user_requests:")
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
        
        # Проверяем, есть ли колонка id
        column_names = [col[1] for col in columns]
        
        if 'id' not in column_names:
            print("\n❌ Колонка 'id' отсутствует! Создаем новую таблицу...")
            
            # Создаем новую таблицу с правильной структурой
            conn.execute("DROP TABLE IF EXISTS user_requests")
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
            
            conn.commit()
            print("✅ Таблица user_requests пересоздана с правильной структурой")
        else:
            print("✅ Структура таблицы корректна")
        
        # Проверяем результат
        cursor = conn.execute("PRAGMA table_info(user_requests)")
        columns = cursor.fetchall()
        print(f"\n📋 Финальная структура таблицы user_requests:")
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении структуры: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Исправление структуры таблицы user_requests...")
    success = fix_table_structure()
    if success:
        print("\n✅ Структура таблицы исправлена!")
    else:
        print("\n❌ Ошибка при исправлении структуры!") 