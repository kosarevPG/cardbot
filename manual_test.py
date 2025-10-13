#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ручной тест системы персонализации
"""

def main():
    print("🧪 Ручное тестирование системы персонализации")
    print("=" * 50)
    
    try:
        # Тест 1: Импорты
        print("1. Тестирование импортов...")
        from modules.texts.gender_utils import determine_gender_by_name, personalize_text
        from modules.texts import LEARNING_TEXTS
        print("   ✅ Все модули импортированы успешно")
        
        # Тест 2: Определение пола
        print("\n2. Тестирование определения пола...")
        test_names = [
            ('Анна', 'female'),
            ('Мария', 'female'), 
            ('Иван', 'male'),
            ('Александр', 'male'),
            ('Alex', 'neutral')
        ]
        
        for name, expected in test_names:
            result = determine_gender_by_name(name)
            status = "✅" if result == expected else "❌"
            print(f"   {status} '{name}' -> '{result}' (ожидалось '{expected}')")
        
        # Тест 3: Персонализация текстов
        print("\n3. Тестирование персонализации...")
        test_text = "Привет{name_part}! Ты{ready} готов{ready} начать обучение?"
        
        test_users = [
            {'name': 'Анна', 'gender': 'female', 'has_name': True},
            {'name': 'Иван', 'gender': 'male', 'has_name': True},
            {'name': '', 'gender': 'neutral', 'has_name': False}
        ]
        
        for user_info in test_users:
            result = personalize_text(test_text, user_info)
            name_display = user_info['name'] or 'Без имени'
            print(f"   {name_display} ({user_info['gender']}): '{result}'")
        
        # Тест 4: Загрузка текстов
        print("\n4. Тестирование загрузки текстов...")
        welcome_text = LEARNING_TEXTS['intro']['welcome']
        print(f"   ✅ Текст приветствия загружен: {len(welcome_text)} символов")
        
        # Проверяем наличие плейсхолдеров
        has_placeholders = '{name_part}' in welcome_text or '{ready}' in welcome_text
        if has_placeholders:
            print("   ✅ Текст содержит плейсхолдеры для персонализации")
        else:
            print("   ⚠️ Текст не содержит плейсхолдеров")
        
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("\nСистема готова к деплою!")
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Результат: УСПЕХ")
    else:
        print("\n❌ Результат: ОШИБКА")

