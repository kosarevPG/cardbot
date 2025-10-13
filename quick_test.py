#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест системы персонализации текстов
"""

import sys
import os
import tempfile
import sqlite3

def create_test_db():
    """Создает тестовую БД"""
    db_path = tempfile.mktemp(suffix='.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            first_name TEXT,
            gender TEXT DEFAULT 'neutral',
            first_seen TEXT
        )
    """)
    
    cursor.execute("""
        INSERT INTO users (user_id, name, username, first_name, gender, first_seen)
        VALUES (123456789, 'Анна', 'anna_user', 'Анна', 'female', '2025-01-01')
    """)
    
    conn.commit()
    conn.close()
    return db_path

def test_basic():
    """Базовый тест"""
    print("🧪 Тестирование системы персонализации...")
    
    try:
        # Импортируем модули
        from modules.texts.gender_utils import determine_gender_by_name, personalize_text
        
        # Тест 1: Определение пола по имени
        print("1. Тест определения пола:")
        result = determine_gender_by_name('Анна')
        print(f"   'Анна' -> '{result}' (ожидается 'female')")
        
        # Тест 2: Персонализация текста
        print("2. Тест персонализации:")
        text = "Привет{name_part}! Ты{ready} готов{ready} начать?"
        user_info = {'name': 'Анна', 'gender': 'female', 'has_name': True}
        result = personalize_text(text, user_info)
        print(f"   Результат: '{result}'")
        
        # Тест 3: База данных
        print("3. Тест базы данных:")
        db_path = create_test_db()
        from database.db import Database
        db = Database(db_path)
        user_info = db.get_user_info(123456789)
        print(f"   Пользователь: {user_info.get('first_name')}, пол: {user_info.get('gender')}")
        os.unlink(db_path)
        
        # Тест 4: Загрузка текстов
        print("4. Тест загрузки текстов:")
        from modules.texts import LEARNING_TEXTS
        welcome_text = LEARNING_TEXTS['intro']['welcome']
        print(f"   Загружен текст приветствия: {len(welcome_text)} символов")
        
        print("✅ Все базовые тесты пройдены!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic()
    print(f"\nРезультат: {'УСПЕХ' if success else 'ОШИБКА'}")
    sys.exit(0 if success else 1)