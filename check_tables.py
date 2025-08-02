#!/usr/bin/env python3
"""
Скрипт для проверки таблиц в базе данных
"""

import sqlite3
import os

def check_tables():
    """Проверяет таблицы в базе данных"""
    print("🔍 Проверка таблиц в базе данных")
    print("=" * 50)
    
    # Проверяем локальную базу данных
    local_db = "database/bot.db"
    if os.path.exists(local_db):
        print(f"📁 Локальная база данных: {local_db}")
        try:
            conn = sqlite3.connect(local_db)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print("📋 Таблицы в локальной базе:")
            for table in tables:
                print(f"  ✅ {table[0]}")
            
            conn.close()
        except Exception as e:
            print(f"❌ Ошибка при проверке локальной БД: {e}")
    else:
        print(f"❌ Локальная база данных не найдена: {local_db}")
    
    print()
    
    # Проверяем production базу данных (если доступна)
    prod_db = "/data/bot.db"
    if os.path.exists(prod_db):
        print(f"🌐 Production база данных: {prod_db}")
        try:
            conn = sqlite3.connect(prod_db)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print("📋 Таблицы в production базе:")
            for table in tables:
                print(f"  ✅ {table[0]}")
            
            conn.close()
        except Exception as e:
            print(f"❌ Ошибка при проверке production БД: {e}")
    else:
        print(f"ℹ️  Production база данных недоступна: {prod_db}")

if __name__ == '__main__':
    check_tables() 