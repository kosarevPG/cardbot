"""
Быстрый тест персонализации
"""
print("="*60)
print("🚀 ТЕСТИРОВАНИЕ ПЕРСОНАЛИЗАЦИИ")
print("="*60)

# Тест 1: Импорты
print("\n🔧 Тест 1: Проверка импортов...")
try:
    from modules.texts.gender_utils import personalize_text, get_user_info_for_text
    from modules.texts.learning import LEARNING_TEXTS
    from modules.texts.cards import CARDS_TEXTS
    from modules.texts.errors import ERROR_TEXTS
    print("✅ Все модули импортированы успешно")
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    exit(1)

# Тест 2: Базовая персонализация
print("\n🔧 Тест 2: Базовая персонализация...")

test_cases = [
    ("female", "Анна", "Привет{name_part}! Ты готов{ready} начать?"),
    ("male", "Иван", "Привет{name_part}! Ты готов{ready} начать?"),
    ("neutral", None, "Привет{name_part}! Ты готов{ready} начать?"),
]

for gender, name, template in test_cases:
    user_info = {
        'gender': gender,
        'name': name,
        'has_name': bool(name)
    }
    result = personalize_text(template, user_info)
    print(f"\n  Гендер: {gender}, Имя: {name or 'Нет'}")
    print(f"  Шаблон: {template}")
    print(f"  Результат: {result}")

# Тест 3: Проверка текстов
print("\n🔧 Тест 3: Проверка структуры текстов...")

texts_to_check = [
    ("LEARNING_TEXTS", LEARNING_TEXTS, ["intro.welcome", "theory_1", "entry_poll.q1.question"]),
    ("CARDS_TEXTS", CARDS_TEXTS, ["card_of_day.deck_selection", "card_of_day.drawing_card"]),
    ("ERROR_TEXTS", ERROR_TEXTS, ["admin.training_logs_load_error", "permissions.access_denied"])
]

all_ok = True
for name, texts_dict, keys_to_check in texts_to_check:
    print(f"\n  Проверяю {name}:")
    for key in keys_to_check:
        # Проверяем вложенный ключ
        keys = key.split('.')
        current = texts_dict
        found = True
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                found = False
                break
        
        if found and isinstance(current, str):
            print(f"    ✅ {key}: {current[:50]}...")
        else:
            print(f"    ❌ {key}: НЕ НАЙДЕН!")
            all_ok = False

# Тест 4: Проверка склонений
print("\n🔧 Тест 4: Проверка склонений...")

declension_tests = [
    ("female", "Ты готов{ready}", "Ты готова"),
    ("male", "Ты готов{ready}", "Ты готов"),
    ("neutral", "Ты готов{ready}", "Ты готовы"),
]

for gender, template, expected in declension_tests:
    user_info = {'gender': gender, 'name': None, 'has_name': False}
    result = personalize_text(template, user_info)
    status = "✅" if result == expected else "❌"
    print(f"  {status} {gender}: '{template}' -> '{result}' (ожидалось: '{expected}')")

# Финальный результат
print("\n" + "="*60)
if all_ok:
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
else:
    print("⚠️ НЕКОТОРЫЕ ТЕКСТЫ НЕ НАЙДЕНЫ!")
print("="*60)


