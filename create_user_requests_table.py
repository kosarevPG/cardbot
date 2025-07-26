#!/usr/bin/env python3
"""
Скрипт для создания таблицы user_requests в production БД
"""
import sqlite3
import sys
import os

def create_user_requests_table():
    """Создает таблицу user_requests в production БД"""
    print("🔧 СОЗДАНИЕ ТАБЛИЦЫ user_requests В PRODUCTION")
    print("=" * 50)
    
    try:
        # Используем production БД
        db_path = "/data/bot.db"
        if not os.path.exists(db_path):
            print(f"❌ Production БД не найдена: {db_path}")
            print("Убедитесь, что скрипт запущен на Amvera")
            return
        
        print(f"📁 Используем production БД: {db_path}")
        conn = sqlite3.connect(db_path)
        
        # Проверяем, существует ли таблица
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_requests'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            print("⚠️ Таблица user_requests уже существует!")
            
            # Проверяем структуру
            cursor = conn.execute("PRAGMA table_info(user_requests)")
            columns = cursor.fetchall()
            print("📋 Текущая структура:")
            for col in columns:
                print(f"  • {col[1]} ({col[2]})")
            
            # Проверяем, есть ли нужные колонки
            column_names = [col[1] for col in columns]
            required_columns = ['user_id', 'request_text', 'timestamp', 'session_id', 'card_number']
            
            missing_columns = [col for col in required_columns if col not in column_names]
            if missing_columns:
                print(f"❌ Отсутствуют колонки: {missing_columns}")
                print("Нужно добавить недостающие колонки")
                
                for col in missing_columns:
                    if col == 'request_text':
                        conn.execute("ALTER TABLE user_requests ADD COLUMN request_text TEXT")
                        print(f"  ✅ Добавлена колонка: {col}")
                    elif col == 'session_id':
                        conn.execute("ALTER TABLE user_requests ADD COLUMN session_id TEXT")
                        print(f"  ✅ Добавлена колонка: {col}")
                    elif col == 'card_number':
                        conn.execute("ALTER TABLE user_requests ADD COLUMN card_number INTEGER")
                        print(f"  ✅ Добавлена колонка: {col}")
            else:
                print("✅ Все необходимые колонки присутствуют")
        else:
            print("📋 Создаем таблицу user_requests...")
            
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
            
            print("✅ Таблица user_requests создана успешно!")
            print("✅ Индексы созданы")
        
        # Проверяем результат
        cursor = conn.execute("PRAGMA table_info(user_requests)")
        columns = cursor.fetchall()
        print(f"\n📋 ФИНАЛЬНАЯ СТРУКТУРА ТАБЛИЦЫ user_requests:")
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
        
        # Количество записей
        cursor = conn.execute("SELECT COUNT(*) as count FROM user_requests")
        count = cursor.fetchone()[0]
        print(f"📊 Записей в таблице: {count}")
        
        conn.commit()
        conn.close()
        print(f"\n✅ ОПЕРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        
    except Exception as e:
        print(f"❌ Ошибка создания таблицы: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_user_requests_table() 