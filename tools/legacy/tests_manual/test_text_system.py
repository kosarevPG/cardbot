#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки системы персонализации текстов.
Тестирует все компоненты перед деплоем.
"""

import sys
import os
import tempfile
import sqlite3

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_test_database():
    """Создает тестовую базу данных с пользователями"""
    db_path = tempfile.mktemp(suffix='.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Создаем таблицу users
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
    
    # Добавляем тестовых пользователей
    test_users = [
        (123456789, 'Анна', 'anna_user', 'Анна', 'female', '2025-01-01'),
        (987654321, 'Иван', 'ivan_user', 'Иван', 'male', '2025-01-02'),
        (555666777, 'Alex', 'alex_user', 'Alex', 'neutral', '2025-01-03'),
        (111222333, 'Мария', 'maria_user', 'Мария', 'female', '2025-01-04'),
        (444555666, 'TestUser', 'test_user', None, 'neutral', '2025-01-05'),  # Без имени
    ]
    
    cursor.executemany("""
        INSERT INTO users (user_id, name, username, first_name, gender, first_seen)
        VALUES (?, ?, ?, ?, ?, ?)
    """, test_users)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Создана тестовая база данных: {db_path}")
    return db_path

def test_database_operations():
    """Тестирует операции с базой данных"""
    print("\n🧪 Тестирование операций с базой данных...")
    
    try:
        from database.db import Database
        
        db_path = create_test_database()
        db = Database(db_path)
        
        # Тестируем получение информации о пользователях
        test_cases = [
            (123456789, 'Анна', 'female'),
            (987654321, 'Иван', 'male'),
            (555666777, 'Alex', 'neutral'),
            (444555666, 'TestUser', 'neutral'),
            (999999999, None, 'neutral')  # Несуществующий пользователь
        ]
        
        for user_id, expected_name, expected_gender in test_cases:
            user_info = db.get_user_info(user_id)
            if user_info:
                actual_name = user_info.get('first_name') or user_info.get('name')
                actual_gender = user_info.get('gender', 'neutral')
                
                name_match = (actual_name == expected_name)
                gender_match = (actual_gender == expected_gender)
                
                status = "✅" if name_match and gender_match else "❌"
                print(f"  {status} ID {user_id}: имя='{actual_name}' (ожидалось '{expected_name}'), пол='{actual_gender}' (ожидался '{expected_gender}')")
            else:
                if expected_name is None:
                    print(f"  ✅ ID {user_id}: пользователь не найден (ожидалось)")
                else:
                    print(f"  ❌ ID {user_id}: пользователь не найден (неожиданно)")
        
        # Очищаем тестовую базу
        os.unlink(db_path)
        print("✅ Тестирование базы данных завершено")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании базы данных: {e}")
        return False

def test_gender_utils():
    """Тестирует утилиты для работы с гендером"""
    print("\n🧪 Тестирование утилит гендера...")
    
    try:
        from modules.texts.gender_utils import (
            determine_gender_by_name, 
            personalize_text, 
            get_user_info_for_text
        )
        from database.db import Database
        
        # Тестируем определение пола по имени
        name_tests = [
            ('Анна', 'female'),
            ('Мария', 'female'),
            ('Иван', 'male'),
            ('Александр', 'male'),
            ('Alex', 'neutral'),
            ('TestUser', 'neutral'),
            ('', 'neutral'),
            (None, 'neutral')
        ]
        
        print("  Тестирование определения пола по имени:")
        for name, expected in name_tests:
            result = determine_gender_by_name(name)
            status = "✅" if result == expected else "❌"
            print(f"    {status} '{name}' -> '{result}' (ожидалось '{expected}')")
        
        # Тестируем персонализацию текстов
        print("\n  Тестирование персонализации текстов:")
        
        test_texts = [
            "Привет{name_part}! Ты{ready} готов{ready} начать?",
            "Отлично, {name}! Ты{ready} справил{ready}ся!",
            "Твой{your} запрос очень хорош."
        ]
        
        test_users = [
            {'name': 'Анна', 'gender': 'female', 'has_name': True},
            {'name': 'Иван', 'gender': 'male', 'has_name': True},
            {'name': '', 'gender': 'neutral', 'has_name': False}
        ]
        
        for text in test_texts:
            print(f"\n    Текст: '{text}'")
            for user_info in test_users:
                result = personalize_text(text, user_info)
                print(f"      {user_info['name'] or 'Без имени'} ({user_info['gender']}): '{result}'")
        
        print("✅ Тестирование утилит гендера завершено")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании утилит гендера: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_text_loading():
    """Тестирует загрузку текстов"""
    print("\n🧪 Тестирование загрузки текстов...")
    
    try:
        from modules.texts import (
            LEARNING_TEXTS, 
            CARDS_TEXTS, 
            COMMON_TEXTS, 
            ERROR_TEXTS, 
            MARKETPLACE_TEXTS
        )
        
        # Проверяем, что все модули текстов загружаются
        text_modules = {
            'LEARNING_TEXTS': LEARNING_TEXTS,
            'CARDS_TEXTS': CARDS_TEXTS,
            'COMMON_TEXTS': COMMON_TEXTS,
            'ERROR_TEXTS': ERROR_TEXTS,
            'MARKETPLACE_TEXTS': MARKETPLACE_TEXTS
        }
        
        for module_name, module_texts in text_modules.items():
            if isinstance(module_texts, dict) and len(module_texts) > 0:
                print(f"  ✅ {module_name}: загружен, {len(module_texts)} разделов")
            else:
                print(f"  ❌ {module_name}: пустой или не словарь")
                return False
        
        # Проверяем наличие ключевых текстов
        key_texts = [
            ('LEARNING_TEXTS', 'intro.welcome'),
            ('LEARNING_TEXTS', 'entry_poll.q1.question'),
            ('CARDS_TEXTS', 'card_of_day.welcome'),
            ('COMMON_TEXTS', 'greetings.start')
        ]
        
        print("\n  Проверка ключевых текстов:")
        for module_name, text_key in key_texts:
            module_texts = text_modules[module_name]
            
            # Получаем значение по вложенному ключу
            keys = text_key.split('.')
            current = module_texts
            try:
                for key in keys:
                    current = current[key]
                
                if current and isinstance(current, str) and len(current.strip()) > 0:
                    print(f"    ✅ {module_name}.{text_key}: найден")
                else:
                    print(f"    ❌ {module_name}.{text_key}: пустой")
                    return False
            except KeyError:
                print(f"    ❌ {module_name}.{text_key}: не найден")
                return False
        
        print("✅ Тестирование загрузки текстов завершено")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании загрузки текстов: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_integration():
    """Тестирует полную интеграцию системы"""
    print("\n🧪 Тестирование полной интеграции...")
    
    try:
        from modules.texts.gender_utils import get_personalized_text
        from modules.texts import LEARNING_TEXTS
        from database.db import Database
        
        db_path = create_test_database()
        db = Database(db_path)
        
        # Тестируем получение персонализированных текстов
        test_cases = [
            (123456789, 'intro.welcome', 'Анна', 'female'),
            (987654321, 'intro.welcome', 'Иван', 'male'),
            (555666777, 'intro.welcome', 'Alex', 'neutral'),
            (444555666, 'intro.welcome', 'TestUser', 'neutral')
        ]
        
        print("  Тестирование персонализированных текстов:")
        for user_id, text_key, expected_name, expected_gender in test_cases:
            try:
                personalized_text = get_personalized_text(text_key, LEARNING_TEXTS, user_id, db)
                
                # Проверяем, что текст персонализирован
                has_personalization = (
                    (expected_name and expected_name in personalized_text) or
                    ('{name}' not in personalized_text and '{name_part}' not in personalized_text)
                )
                
                status = "✅" if has_personalization else "❌"
                print(f"    {status} ID {user_id} ({expected_gender}): получен персонализированный текст")
                print(f"        '{personalized_text[:100]}...'")
                
            except Exception as e:
                print(f"    ❌ ID {user_id}: ошибка получения текста - {e}")
                return False
        
        # Очищаем тестовую базу
        os.unlink(db_path)
        print("✅ Тестирование полной интеграции завершено")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании полной интеграции: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция тестирования"""
    print("🚀 Запуск комплексного тестирования системы персонализации текстов")
    print("=" * 70)
    
    tests = [
        ("База данных", test_database_operations),
        ("Утилиты гендера", test_gender_utils),
        ("Загрузка текстов", test_text_loading),
        ("Полная интеграция", test_full_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    # Итоговый отчет
    print("\n" + "=" * 70)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{status:<15} {test_name}")
        if result:
            passed += 1
    
    print("-" * 70)
    print(f"Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к деплою.")
        return True
    else:
        print("💥 ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ! Необходимо исправить ошибки.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

