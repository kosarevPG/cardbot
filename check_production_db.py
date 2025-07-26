#!/usr/bin/env python3
"""
Скрипт для проверки структуры production БД
"""
import sqlite3
import sys
import os

def check_production_db():
    """Проверяет структуру production БД"""
    print("🔍 ПРОВЕРКА СТРУКТУРЫ PRODUCTION БД")
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
        conn.row_factory = sqlite3.Row
        
        # Получаем список таблиц
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        print(f"📊 Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"  • {table}")
        
        # Проверяем таблицу user_requests
        if 'user_requests' in tables:
            print(f"\n📋 СТРУКТУРА ТАБЛИЦЫ user_requests:")
            cursor = conn.execute("PRAGMA table_info(user_requests)")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  • {col['name']} ({col['type']})")
            
            # Количество записей
            cursor = conn.execute("SELECT COUNT(*) as count FROM user_requests")
            count = cursor.fetchone()['count']
            print(f"  📊 Записей: {count}")
        else:
            print(f"\n❌ ТАБЛИЦА user_requests НЕ НАЙДЕНА!")
            print("Нужно создать таблицу user_requests")
        
        # Проверяем таблицу actions
        if 'actions' in tables:
            print(f"\n📋 СТРУКТУРА ТАБЛИЦЫ actions:")
            cursor = conn.execute("PRAGMA table_info(actions)")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  • {col['name']} ({col['type']})")
            
            # Количество записей
            cursor = conn.execute("SELECT COUNT(*) as count FROM actions")
            count = cursor.fetchone()['count']
            print(f"  📊 Записей: {count}")
        
        conn.close()
        print(f"\n✅ ПРОВЕРКА ЗАВЕРШЕНА")
        
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_production_db() 