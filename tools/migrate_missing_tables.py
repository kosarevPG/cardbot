#!/usr/bin/env python3
"""
Скрипт для миграции недостающих таблиц в production базу данных
"""

import sqlite3
import os
from datetime import datetime

def migrate_missing_tables():
    """Мигрирует недостающие таблицы из локальной БД в production"""
    print("🚀 Миграция недостающих таблиц")
    print("=" * 50)
    
    local_db = "database/bot.db"
    prod_db = "/data/bot.db"
    
    if not os.path.exists(local_db):
        print(f"❌ Локальная база данных не найдена: {local_db}")
        return
    
    if not os.path.exists(prod_db):
        print(f"❌ Production база данных не найдена: {prod_db}")
        return
    
    try:
        # Подключаемся к обеим базам данных
        local_conn = sqlite3.connect(local_db)
        prod_conn = sqlite3.connect(prod_db)
        
        # Список таблиц для миграции
        tables_to_migrate = [
            'user_requests',
            'scenario_logs', 
            'user_scenarios',
            'posts',
            'mailings'
        ]
        
        for table in tables_to_migrate:
            print(f"\n📋 Миграция таблицы: {table}")
            
            # Проверяем, существует ли таблица в production
            cursor = prod_conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"  ⚠️  Таблица {table} уже существует в production")
                continue
            
            # Получаем схему таблицы из локальной БД
            cursor = local_conn.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
            schema = cursor.fetchone()
            
            if not schema:
                print(f"  ❌ Таблица {table} не найдена в локальной БД")
                continue
            
            # Создаем таблицу в production
            print(f"  🔨 Создание таблицы {table}")
            prod_conn.execute(schema[0])
            
            # Копируем данные (если есть)
            try:
                cursor = local_conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                if count > 0:
                    print(f"  📥 Копирование {count} записей")
                    cursor = local_conn.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    
                    # Получаем названия колонок
                    cursor = local_conn.execute(f"PRAGMA table_info({table})")
                    columns = [col[1] for col in cursor.fetchall()]
                    placeholders = ','.join(['?' for _ in columns])
                    
                    # Вставляем данные
                    prod_conn.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
                else:
                    print(f"  ℹ️  Таблица {table} пустая")
                    
            except Exception as e:
                print(f"  ⚠️  Ошибка при копировании данных: {e}")
            
            prod_conn.commit()
            print(f"  ✅ Таблица {table} успешно создана")
        
        # Создаем индексы для новых таблиц
        print(f"\n🔍 Создание индексов")
        indexes_to_create = [
            ("user_requests", "user_id"),
            ("user_requests", "timestamp"),
            ("scenario_logs", "user_id"),
            ("scenario_logs", "scenario"),
            ("scenario_logs", "timestamp"),
            ("user_scenarios", "user_id"),
            ("user_scenarios", "scenario"),
            ("user_scenarios", "started_at"),
            ("posts", "created_at"),
            ("mailings", "created_at")
        ]
        
        for table, column in indexes_to_create:
            try:
                index_name = f"idx_{table}_{column}"
                prod_conn.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})")
                print(f"  ✅ Индекс {index_name} создан")
            except Exception as e:
                print(f"  ⚠️  Ошибка создания индекса {index_name}: {e}")
        
        prod_conn.commit()
        local_conn.close()
        prod_conn.close()
        
        print(f"\n🎉 Миграция завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")

def verify_migration():
    """Проверяет результат миграции"""
    print(f"\n🔍 Проверка результата миграции")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect("/data/bot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        required_tables = [
            'user_requests',
            'scenario_logs', 
            'user_scenarios',
            'posts',
            'mailings'
        ]
        
        print("📋 Проверка таблиц:")
        for table in required_tables:
            if any(table in t[0] for t in tables):
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} - ОТСУТСТВУЕТ")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")

if __name__ == '__main__':
    migrate_missing_tables()
    verify_migration() 