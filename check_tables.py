#!/usr/bin/env python3
"""
Проверка структуры БД и таблиц
"""
import sqlite3

def check_database_structure():
    """Проверяет структуру БД"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        
        print(f"🔍 Проверяем структуру БД")
        print(f"📁 БД: {db_path}")
        
        # Получаем список всех таблиц
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\n📋 Таблицы в БД:")
        for table in tables:
            table_name = table[0]
            print(f"  • {table_name}")
            
            # Показываем структуру каждой таблицы
            cursor2 = conn.execute(f"PRAGMA table_info({table_name})")
            columns = cursor2.fetchall()
            print(f"    Колонки:")
            for col in columns:
                print(f"      - {col[1]} ({col[2]})")
            
            # Показываем количество записей
            cursor3 = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor3.fetchone()[0]
            print(f"    Записей: {count}")
            print()
        
        # Проверяем конкретно таблицу actions
        if any('actions' in table[0] for table in tables):
            print(f"🔍 Проверяем таблицу actions:")
            cursor = conn.execute("SELECT * FROM actions LIMIT 5")
            actions = cursor.fetchall()
            
            if actions:
                print(f"📝 Первые 5 записей:")
                for i, action in enumerate(actions, 1):
                    print(f"  {i}. {action}")
            else:
                print(f"📝 Записей в actions нет")
        else:
            print(f"❌ Таблица actions не найдена")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    check_database_structure() 