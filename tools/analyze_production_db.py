#!/usr/bin/env python3
"""
Анализ структуры скачанной production БД bot (20).db
"""
import sqlite3
import os

def analyze_production_db():
    """Анализирует структуру production БД"""
    try:
        db_path = "database/bot (20).db"
        if not os.path.exists(db_path):
            print(f"❌ Файл БД не найден: {db_path}")
            return
            
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🔍 Анализируем БД: {db_path}")
        
        # Получаем список всех таблиц
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\n📋 Все таблицы в БД:")
        for table in tables:
            print(f"  • {table[0]}")
        
        # Проверяем таблицу user_requests
        print(f"\n🔍 Проверяем таблицу user_requests:")
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_requests'")
        user_requests_exists = cursor.fetchone() is not None
        
        if user_requests_exists:
            cursor = conn.execute("PRAGMA table_info(user_requests)")
            columns = cursor.fetchall()
            print(f"  ✅ Таблица user_requests существует")
            print(f"  📋 Структура user_requests:")
            for col in columns:
                print(f"    • {col[1]} ({col[2]})")
            
            # Проверяем количество записей
            cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
            count = cursor.fetchone()[0]
            print(f"  📊 Записей в user_requests: {count}")
        else:
            print(f"  ❌ Таблица user_requests не существует")
        
        # Проверяем таблицу actions
        print(f"\n🔍 Проверяем таблицу actions:")
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='actions'")
        actions_exists = cursor.fetchone() is not None
        
        if actions_exists:
            cursor = conn.execute("PRAGMA table_info(actions)")
            columns = cursor.fetchall()
            print(f"  ✅ Таблица actions существует")
            print(f"  📋 Структура actions:")
            for col in columns:
                print(f"    • {col[1]} ({col[2]})")
            
            # Проверяем количество записей
            cursor = conn.execute("SELECT COUNT(*) FROM actions")
            count = cursor.fetchone()[0]
            print(f"  📊 Записей в actions: {count}")
            
            # Проверяем типы действий
            cursor = conn.execute("SELECT action, COUNT(*) as count FROM actions GROUP BY action ORDER BY count DESC")
            action_types = cursor.fetchall()
            print(f"  📝 Типы действий:")
            for row in action_types:
                print(f"    • {row['action']}: {row['count']}")
        else:
            print(f"  ❌ Таблица actions не существует")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")

if __name__ == "__main__":
    analyze_production_db() 