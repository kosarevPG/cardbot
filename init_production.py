#!/usr/bin/env python3
"""
Скрипт инициализации для production
Автоматически создает таблицу user_requests при запуске
"""
import sqlite3
import os
import sys

def init_production():
    """Инициализирует production БД"""
    try:
        # Используем production БД
        db_path = "/data/bot.db"
        if not os.path.exists(db_path):
            print(f"Production БД не найдена: {db_path}")
            return
        
        conn = sqlite3.connect(db_path)
        
        # Проверяем, существует ли таблица user_requests
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_requests'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("Создаем таблицу user_requests...")
            
            # Создаем таблицу
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
            
            print("Таблица user_requests создана успешно!")
        else:
            # Проверяем структуру
            cursor = conn.execute("PRAGMA table_info(user_requests)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Добавляем недостающие колонки
            if 'request_text' not in column_names:
                conn.execute("ALTER TABLE user_requests ADD COLUMN request_text TEXT")
                print("Добавлена колонка request_text")
            
            if 'session_id' not in column_names:
                conn.execute("ALTER TABLE user_requests ADD COLUMN session_id TEXT")
                print("Добавлена колонка session_id")
            
            if 'card_number' not in column_names:
                conn.execute("ALTER TABLE user_requests ADD COLUMN card_number INTEGER")
                print("Добавлена колонка card_number")
        
        conn.commit()
        conn.close()
        print("Production инициализация завершена")
        
    except Exception as e:
        print(f"Ошибка инициализации: {e}")

if __name__ == "__main__":
    init_production() 