#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для применения миграции добавления столбца gender.
Безопасно добавляет столбец только если его еще нет.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import Database

def apply_gender_migration(db_path: str):
    """Применяет миграцию добавления столбца gender"""
    
    print(f"Применяю миграцию для базы данных: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Ошибка: База данных {db_path} не найдена.")
        return False
    
    try:
        db = Database(db_path)
        
        # Проверяем, есть ли уже столбец gender
        cursor = db.conn.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'gender' in columns:
            print("✅ Столбец 'gender' уже существует в таблице users.")
            return True
        
        # Добавляем столбец gender
        print("Добавляю столбец 'gender' в таблицу users...")
        db.conn.execute("ALTER TABLE users ADD COLUMN gender TEXT DEFAULT 'neutral'")
        db.conn.commit()
        
        print("✅ Миграция успешно применена!")
        print("Столбец 'gender' добавлен с значением по умолчанию 'neutral'.")
        print()
        print("Теперь вы можете:")
        print("1. Просмотреть пользователей: python tools/manage_user_genders.py data/bot.db list")
        print("2. Установить пол конкретному пользователю: python tools/manage_user_genders.py data/bot.db set <user_id> <gender>")
        print("3. Массово установить полы: python tools/manage_user_genders.py data/bot.db bulk")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при применении миграции: {e}")
        return False

def main():
    """Главная функция"""
    if len(sys.argv) != 2:
        print("Использование: python apply_gender_migration.py <путь_к_бд>")
        print("Пример: python apply_gender_migration.py data/bot.db")
        return
    
    db_path = sys.argv[1]
    success = apply_gender_migration(db_path)
    
    if success:
        print("\n🎉 Миграция завершена успешно!")
    else:
        print("\n💥 Миграция не удалась!")
        sys.exit(1)

if __name__ == "__main__":
    main()

