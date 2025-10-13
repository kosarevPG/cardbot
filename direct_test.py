#!/usr/bin/env python3
# Прямой тест персонализации

def test_personalization():
    print("🧪 ТЕСТИРОВАНИЕ ПЕРСОНАЛИЗАЦИИ")
    print("=" * 40)
    
    # Симулируем логику персонализации
    def personalize_text(base_text, user_info):
        text = base_text
        gender = user_info.get('gender', 'neutral')
        name = user_info.get('name', '')
        has_name = user_info.get('has_name', False)
        
        # Обрабатываем имя
        if has_name and name:
            text = text.replace('{name}', name)
            if '{name_part}' in text:
                name_part = f", {name}" if has_name else ""
                text = text.replace('{name_part}', name_part)
        else:
            text = text.replace('{name}', '')
            text = text.replace('{name_part}', '')
            text = text.replace(', ', '')
            text = text.replace('  ', ' ')
        
        # Применяем склонения
        if '{ready}' in text:
            if gender == 'female':
                text = text.replace('{ready}', 'а')
            elif gender == 'male':
                text = text.replace('{ready}', '')
            else:  # neutral
                text = text.replace('{ready}', 'ы')
        
        # Притяжательные
        if '{your}' in text:
            if gender == 'female':
                text = text.replace('{your}', 'твоя')
            else:
                text = text.replace('{your}', 'твой')
        
        return text.strip()
    
    # Тесты
    tests = [
        {
            'name': 'Тест 1: Анна (female)',
            'text': 'Привет{name_part}! Ты{ready} готов{ready} начать?',
            'user': {'name': 'Анна', 'gender': 'female', 'has_name': True},
            'expected': 'Привет, Анна! Ты готова начать?'
        },
        {
            'name': 'Тест 2: Без имени (neutral)',
            'text': 'Привет{name_part}! Ты{ready} готов{ready} начать?',
            'user': {'name': '', 'gender': 'neutral', 'has_name': False},
            'expected': 'Привет! Ты готовы начать?'
        },
        {
            'name': 'Тест 3: Иван (male)',
            'text': 'Отлично, {name}! Ты{ready} справил{ready}ся!',
            'user': {'name': 'Иван', 'gender': 'male', 'has_name': True},
            'expected': 'Отлично, Иван! Ты справился!'
        },
        {
            'name': 'Тест 4: Притяжательные (female)',
            'text': 'Твой{your} запрос очень хорош.',
            'user': {'name': 'Мария', 'gender': 'female', 'has_name': True},
            'expected': 'Твоя запрос очень хорош.'
        }
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        result = personalize_text(test['text'], test['user'])
        success = result == test['expected']
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        
        print(f"{status} {test['name']}")
        print(f"   Результат: '{result}'")
        if not success:
            print(f"   Ожидалось: '{test['expected']}'")
        print()
        
        if success:
            passed += 1
    
    print("=" * 40)
    print(f"РЕЗУЛЬТАТ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("✅ Нет двойных окончаний")
        print("✅ Доверительное обращение 'ты'")
        print("✅ Правильные склонения по полу")
        print("✅ Корректная обработка имен")
        return True
    else:
        print("💥 ЕСТЬ ПРОВАЛЕННЫЕ ТЕСТЫ!")
        return False

if __name__ == "__main__":
    test_personalization()

