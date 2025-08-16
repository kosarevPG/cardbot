#!/usr/bin/env python3
"""
Скрипт для анализа данных в dump_production.db
"""
import sqlite3
import sys
import os

def analyze_dump_production():
    """Анализирует структуру и данные в dump_production.db"""
    print("🔍 АНАЛИЗ DUMP_PRODUCTION.DB")
    print("=" * 50)
    
    try:
        db_path = "database/dump_production.db"
        if not os.path.exists(db_path):
            print(f"❌ Файл {db_path} не найден")
            return
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Получаем список таблиц
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        print(f"📊 Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"  • {table}")
        
        print(f"\n📋 ДЕТАЛЬНЫЙ АНАЛИЗ ТАБЛИЦ:")
        
        for table in tables:
            print(f"\n🔸 ТАБЛИЦА: {table}")
            print("-" * 30)
            
            # Количество записей
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            print(f"  📊 Записей: {count}")
            
            if count > 0:
                # Структура таблицы
                cursor = conn.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                print(f"  📝 Столбцы:")
                for col in columns:
                    print(f"    • {col['name']} ({col['type']})")
                
                # Примеры данных
                cursor = conn.execute(f"SELECT * FROM {table} LIMIT 3")
                rows = cursor.fetchall()
                print(f"  📄 Примеры данных:")
                for i, row in enumerate(rows, 1):
                    print(f"    {i}. {dict(row)}")
                
                # Если это таблица с запросами, показываем больше деталей
                if 'request' in [col['name'] for col in columns] or 'user_id' in [col['name'] for col in columns]:
                    print(f"  🔍 Дополнительная информация:")
                    
                    # Уникальные пользователи
                    if 'user_id' in [col['name'] for col in columns]:
                        cursor = conn.execute(f"SELECT COUNT(DISTINCT user_id) as unique_users FROM {table}")
                        unique_users = cursor.fetchone()['unique_users']
                        print(f"    • Уникальных пользователей: {unique_users}")
                    
                    # Последние записи
                    if 'timestamp' in [col['name'] for col in columns]:
                        cursor = conn.execute(f"SELECT * FROM {table} ORDER BY timestamp DESC LIMIT 2")
                        recent = cursor.fetchall()
                        print(f"    • Последние записи:")
                        for row in recent:
                            print(f"      - {dict(row)}")
        
        conn.close()
        print(f"\n✅ АНАЛИЗ ЗАВЕРШЕН")
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_dump_production() 