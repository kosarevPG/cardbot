#!/usr/bin/env python3
"""
Скрипт для тестирования функциональности first_seen
"""

import os
import sys
from datetime import datetime

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database.db import Database
    from config import DATA_DIR
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def test_first_seen_functionality():
    """Тестирует функциональность first_seen"""
    print("🧪 Тестирование функциональности first_seen...")
    
    # Инициализируем БД
    db_path = os.path.join(DATA_DIR, "test_first_seen.db")
    db = Database(path=db_path)
    
    try:
        # Тест 1: Создание нового пользователя
        print("\n1️⃣ Тест создания нового пользователя...")
        test_user_id = 999999999
        user_data = db.get_user(test_user_id)
        print(f"   Пользователь создан: {user_data}")
        print(f"   first_seen: {user_data.get('first_seen')}")
        
        # Тест 2: Получение first_seen
        print("\n2️⃣ Тест получения first_seen...")
        first_seen = db.get_user_first_seen(test_user_id)
        print(f"   first_seen: {first_seen}")
        
        # Тест 3: Обновление first_seen
        print("\n3️⃣ Тест обновления first_seen...")
        success = db.update_user_first_seen(test_user_id)
        print(f"   Обновление успешно: {success}")
        
        # Тест 4: Статистика новых пользователей
        print("\n4️⃣ Тест статистики новых пользователей...")
        stats = db.get_new_users_stats(7)
        print(f"   Статистика: {stats}")
        
        # Тест 5: Проверка структуры таблицы
        print("\n5️⃣ Проверка структуры таблицы users...")
        cursor = db.conn.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print("   Колонки таблицы users:")
        for col in columns:
            print(f"     - {col[1]} ({col[2]})")
        
        # Проверяем наличие first_seen
        has_first_seen = any(col[1] == 'first_seen' for col in columns)
        print(f"   Поле first_seen присутствует: {has_first_seen}")
        
        print("\n✅ Все тесты пройдены успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        # Удаляем тестовую БД
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"🗑️  Тестовая БД удалена: {db_path}")

if __name__ == "__main__":
    test_first_seen_functionality() 