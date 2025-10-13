#!/usr/bin/env python3
# Простой тест системы текстов

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тестирует импорты всех модулей"""
    try:
        print("🧪 Тестирование импортов...")
        
        # Тест импорта базы данных
        from database.db import Database
        print("✅ Database импортирован")
        
        # Тест импорта утилит гендера
        from modules.texts.gender_utils import determine_gender_by_name, personalize_text
        print("✅ Gender utils импортированы")
        
        # Тест импорта текстов
        from modules.texts import LEARNING_TEXTS, CARDS_TEXTS, COMMON_TEXTS
        print("✅ Тексты импортированы")
        
        # Тест функций
        result = determine_gender_by_name('Анна')
        print(f"✅ Определение пола работает: 'Анна' -> '{result}'")
        
        # Тест персонализации
        text = "Привет{name_part}! Ты{ready} готов{ready} начать?"
        user_info = {'name': 'Анна', 'gender': 'female', 'has_name': True}
        result = personalize_text(text, user_info)
        print(f"✅ Персонализация работает: '{result[:50]}...'")
        
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)

