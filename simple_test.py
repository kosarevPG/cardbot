#!/usr/bin/env python3
# Простой тест исправлений

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test():
    try:
        from modules.texts.gender_utils import personalize_text
        
        # Тест 1: Основной текст с именем
        text1 = "Привет{name_part}! Ты{ready} готов{ready} начать?"
        user1 = {'name': 'Анна', 'gender': 'female', 'has_name': True}
        result1 = personalize_text(text1, user1)
        print(f"Тест 1: '{result1}'")
        
        # Ожидаемый результат: "Привет, Анна! Ты готова начать?"
        expected1 = "Привет, Анна! Ты готова начать?"
        if result1 == expected1:
            print("✅ Тест 1 ПРОЙДЕН")
        else:
            print(f"❌ Тест 1 ПРОВАЛЕН. Ожидалось: '{expected1}'")
        
        # Тест 2: Без имени
        text2 = "Привет{name_part}! Ты{ready} готов{ready} начать?"
        user2 = {'name': '', 'gender': 'neutral', 'has_name': False}
        result2 = personalize_text(text2, user2)
        print(f"Тест 2: '{result2}'")
        
        # Ожидаемый результат: "Привет! Ты готовы начать?"
        expected2 = "Привет! Ты готовы начать?"
        if result2 == expected2:
            print("✅ Тест 2 ПРОЙДЕН")
        else:
            print(f"❌ Тест 2 ПРОВАЛЕН. Ожидалось: '{expected2}'")
        
        # Тест 3: Мужской пол
        text3 = "Отлично, {name}! Ты{ready} справил{ready}ся!"
        user3 = {'name': 'Иван', 'gender': 'male', 'has_name': True}
        result3 = personalize_text(text3, user3)
        print(f"Тест 3: '{result3}'")
        
        # Ожидаемый результат: "Отлично, Иван! Ты справился!"
        expected3 = "Отлично, Иван! Ты справился!"
        if result3 == expected3:
            print("✅ Тест 3 ПРОЙДЕН")
        else:
            print(f"❌ Тест 3 ПРОВАЛЕН. Ожидалось: '{expected3}'")
        
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test()

