#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправленной персонализации
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_fixed_personalization():
    """Тестирует исправленную персонализацию"""
    print("🧪 Тестирование исправленной персонализации")
    print("=" * 50)
    
    try:
        from modules.texts.gender_utils import personalize_text, GenderDeclension
        
        # Тестовые тексты
        test_texts = [
            "Привет{name_part}! Ты{ready} готов{ready} начать?",
            "Отлично, {name}! Ты{ready} справил{ready}ся!",
            "Твой{your} запрос очень хорош.",
            "Ты{ready} уверен{ready} в себе?"
        ]
        
        # Тестовые пользователи
        test_users = [
            {'name': 'Анна', 'gender': 'female', 'has_name': True},
            {'name': 'Иван', 'gender': 'male', 'has_name': True},
            {'name': '', 'gender': 'neutral', 'has_name': False}
        ]
        
        print("1. Тестирование персонализации текстов:")
        print()
        
        for i, text in enumerate(test_texts, 1):
            print(f"Текст {i}: '{text}'")
            
            for user_info in test_users:
                result = personalize_text(text, user_info)
                name_display = user_info['name'] or 'Без имени'
                print(f"  {name_display} ({user_info['gender']}): '{result}'")
            print()
        
        # Тестируем склонения отдельно
        print("2. Тестирование склонений:")
        test_declensions = [
            "Ты{ready} готов{ready} начать?",
            "Ты{ready} уверен{ready} в себе?"
        ]
        
        for text in test_declensions:
            print(f"Исходный: '{text}'")
            for gender in ['male', 'female', 'neutral']:
                result = GenderDeclension.apply_declension(text, gender)
                print(f"  {gender}: '{result}'")
            print()
        
        print("✅ Тестирование завершено!")
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_fixed_personalization()
    print(f"\nРезультат: {'УСПЕХ' if success else 'ОШИБКА'}")
    sys.exit(0 if success else 1)

