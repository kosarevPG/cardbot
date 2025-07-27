#!/usr/bin/env python3
"""
Скрипт для проверки результата миграции в bot (20).db
"""
import sqlite3
import os

def check_migration_result():
    """Проверяет результат миграции"""
    try:
        db_path = "database/bot (20).db"
        if not os.path.exists(db_path):
            print(f"❌ Файл БД не найден: {db_path}")
            return
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🔍 Проверяем БД: {db_path}")
        
        # Проверяем, существует ли таблица user_requests
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_requests'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("❌ Таблица user_requests не найдена!")
            return
        
        print("✅ Таблица user_requests существует")
        
        # Проверяем структуру таблицы
        cursor = conn.execute("PRAGMA table_info(user_requests)")
        columns = cursor.fetchall()
        print(f"📋 Структура таблицы user_requests:")
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
        
        # Проверяем количество записей
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        total_requests = cursor.fetchone()[0]
        print(f"\n📊 Всего запросов в БД: {total_requests}")
        
        if total_requests > 0:
            # Показываем примеры
            cursor = conn.execute("""
                SELECT ur.request_text, ur.timestamp, u.name, u.username 
                FROM user_requests ur 
                LEFT JOIN users u ON ur.user_id = u.user_id 
                ORDER BY ur.timestamp DESC 
                LIMIT 10
            """)
            
            examples = cursor.fetchall()
            print(f"\n📝 Последние запросы:")
            for i, row in enumerate(examples, 1):
                name = row['name'] or "Неизвестный"
                username = f"@{row['username']}" if row['username'] else ""
                print(f"  {i}. {name} {username}: {row['request_text'][:60]}...")
                print(f"     📅 {row['timestamp']}")
        else:
            print("⚠️ Запросов в БД нет!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")

if __name__ == "__main__":
    check_migration_result() 