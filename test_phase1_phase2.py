#!/usr/bin/env python3
"""
Комплексный тест всех изменений Фазы 1 и Фазы 2
"""

import sys
from modules.texts.gender_utils import personalize_text
from modules.texts.common import COMMON_TEXTS
from modules.texts.cards import CARDS_TEXTS
from modules.texts.settings import SETTINGS_TEXTS

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def print_header(text):
    """Печатает заголовок раздела"""
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")

def print_test(name, passed):
    """Печатает результат теста"""
    status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"{status} {name}")
    return passed

def run_tests():
    """Запускает все тесты"""
    print(f"\n{Colors.YELLOW}🧪 ТЕСТИРОВАНИЕ ИЗМЕНЕНИЙ ФАЗЫ 1 И ФАЗЫ 2{Colors.END}")
    
    passed = 0
    failed = 0
    
    # =========================
    # ФАЗА 1: ТЕСТЫ
    # =========================
    
    print_header("ФАЗА 1: ИСПРАВЛЕНИЕ БАГА ДУБЛИРОВАНИЯ")
    
    # Тест 1.1: Исправлен ли текст в cards.py?
    cards_welcome = CARDS_TEXTS["card_of_day"]["welcome"]
    test1 = "Готов{ready}" not in cards_welcome and "Ты{ready}" in cards_welcome
    if print_test("1.1. Текст cards.py исправлен (нет 'Готов{ready}')", test1):
        passed += 1
    else:
        failed += 1
        print(f"    {Colors.RED}Текст: {cards_welcome}{Colors.END}")
    
    # Тест 1.2: Персонализация работает без дублирования (female)
    user_female = {"name": "Анна", "gender": "female", "has_name": True}
    result = personalize_text(cards_welcome, user_female)
    test2 = "готоваа" not in result and "готова" in result
    if print_test("1.2. Персонализация female работает без дублирования", test2):
        passed += 1
        print(f"    {Colors.BLUE}Результат: {result}{Colors.END}")
    else:
        failed += 1
        print(f"    {Colors.RED}Результат: {result}{Colors.END}")
    
    # Тест 1.3: Персонализация работает без дублирования (male)
    user_male = {"name": "Иван", "gender": "male", "has_name": True}
    result = personalize_text(cards_welcome, user_male)
    test3 = "готовов" not in result and "готов" in result
    if print_test("1.3. Персонализация male работает без дублирования", test3):
        passed += 1
        print(f"    {Colors.BLUE}Результат: {result}{Colors.END}")
    else:
        failed += 1
        print(f"    {Colors.RED}Результат: {result}{Colors.END}")
    
    print_header("ФАЗА 1: ПРОВЕРКА НОВЫХ СЕКЦИЙ")
    
    # Тест 1.4: Добавлены ли новые секции в common.py?
    test4 = all(key in COMMON_TEXTS for key in [
        "subscription_check", "onboarding", "reminders", 
        "referral", "name_change", "feedback_request"
    ])
    if print_test("1.4. Все новые секции добавлены в common.py", test4):
        passed += 1
    else:
        failed += 1
    
    # =========================
    # ФАЗА 2: ТЕСТЫ
    # =========================
    
    print_header("ФАЗА 2: SETTINGS.PY СОЗДАН")
    
    # Тест 2.1: Создан ли settings.py?
    test5 = SETTINGS_TEXTS is not None
    if print_test("2.1. Модуль settings.py создан и импортирован", test5):
        passed += 1
    else:
        failed += 1
    
    # Тест 2.2: Есть ли все нужные секции?
    test6 = all(key in SETTINGS_TEXTS for key in [
        "menu", "profile", "reminders", "invite", "feedback", "about", "buttons"
    ])
    if print_test("2.2. Все секции присутствуют в settings.py", test6):
        passed += 1
    else:
        failed += 1
    
    print_header("ФАЗА 2: УНИФИКАЦИЯ ЭМОДЗИ ОБРАТНОЙ СВЯЗИ")
    
    # Тест 2.3: Эмодзи в common.py
    test7 = "💌" in COMMON_TEXTS["feedback"]["thank_you"]
    if print_test("2.3. Эмодзи 💌 в common.py feedback.thank_you", test7):
        passed += 1
    else:
        failed += 1
        print(f"    {Colors.RED}Текст: {COMMON_TEXTS['feedback']['thank_you']}{Colors.END}")
    
    # Тест 2.4: Эмодзи в common.py (sent)
    test8 = "💌" in COMMON_TEXTS["feedback"]["sent"]
    if print_test("2.4. Эмодзи 💌 в common.py feedback.sent", test8):
        passed += 1
    else:
        failed += 1
        print(f"    {Colors.RED}Текст: {COMMON_TEXTS['feedback']['sent']}{Colors.END}")
    
    # Тест 2.5: Эмодзи в cards.py
    test9 = "💌" in CARDS_TEXTS["feedback"]["thank_you"]
    if print_test("2.5. Эмодзи 💌 в cards.py feedback.thank_you", test9):
        passed += 1
    else:
        failed += 1
        print(f"    {Colors.RED}Текст: {CARDS_TEXTS['feedback']['thank_you']}{Colors.END}")
    
    # Тест 2.6: Нет больше 🌿 в feedback
    test10 = "🌿" not in CARDS_TEXTS["feedback"]["thank_you"]
    if print_test("2.6. Убран 🌿 из cards.py feedback", test10):
        passed += 1
    else:
        failed += 1
    
    print_header("ФАЗА 2: КНОПКА 'ПРОДОЛЖИТЬ'")
    
    # Тест 2.7: Добавлен ли ➡️ к "Продолжить"?
    test11 = "➡️" in COMMON_TEXTS["navigation"]["continue"]
    if print_test("2.7. Эмодзи ➡️ добавлен к 'Продолжить'", test11):
        passed += 1
        print(f"    {Colors.BLUE}Текст: {COMMON_TEXTS['navigation']['continue']}{Colors.END}")
    else:
        failed += 1
        print(f"    {Colors.RED}Текст: {COMMON_TEXTS['navigation']['continue']}{Colors.END}")
    
    # Тест 2.8: Согласованность с "Далее"
    test12 = "➡️" in COMMON_TEXTS["navigation"]["next"]
    if print_test("2.8. Эмодзи ➡️ есть в 'Далее' (согласованность)", test12):
        passed += 1
    else:
        failed += 1
    
    print_header("ФАЗА 2: ПРОВЕРКА ПАТТЕРНОВ {ready}")
    
    # Тест 2.9: Исправлен ли good_job?
    good_job = COMMON_TEXTS["encouragement"]["good_job"]
    test13 = "Ты{ready}" in good_job and "молодец{ready}" not in good_job
    if print_test("2.9. Паттерн good_job исправлен (нет дублирования)", test13):
        passed += 1
    else:
        failed += 1
        print(f"    {Colors.RED}Текст: {good_job}{Colors.END}")
    
    # Тест 2.10: Убран ли {ready} из keep_going?
    keep_going = COMMON_TEXTS["encouragement"]["keep_going"]
    test14 = "{ready}" not in keep_going
    if print_test("2.10. Убран {ready} из keep_going", test14):
        passed += 1
    else:
        failed += 1
        print(f"    {Colors.RED}Текст: {keep_going}{Colors.END}")
    
    # Тест 2.11: Исправлен ли welcome_back?
    welcome_back = COMMON_TEXTS["onboarding"]["welcome_back"]
    test15 = "Ты{ready}" in welcome_back and "Готов{ready}" not in welcome_back
    if print_test("2.11. Паттерн welcome_back исправлен", test15):
        passed += 1
    else:
        failed += 1
        print(f"    {Colors.RED}Текст: {welcome_back}{Colors.END}")
    
    # =========================
    # КОМПЛЕКСНЫЕ ТЕСТЫ
    # =========================
    
    print_header("КОМПЛЕКСНЫЕ ТЕСТЫ ПЕРСОНАЛИЗАЦИИ")
    
    # Тест 3.1: Полная персонализация с именем и ready (female)
    test_text = "Привет{name_part}! Ты{ready} начать?"
    result = personalize_text(test_text, user_female)
    test16 = result == "Привет, Анна! Ты готова начать?"
    if print_test("3.1. Полная персонализация (female)", test16):
        passed += 1
        print(f"    {Colors.BLUE}Результат: {result}{Colors.END}")
    else:
        failed += 1
        print(f"    {Colors.RED}Ожидалось: 'Привет, Анна! Ты готова начать?'{Colors.END}")
        print(f"    {Colors.RED}Получено: {result}{Colors.END}")
    
    # Тест 3.2: Полная персонализация (male)
    result = personalize_text(test_text, user_male)
    test17 = result == "Привет, Иван! Ты готов начать?"
    if print_test("3.2. Полная персонализация (male)", test17):
        passed += 1
        print(f"    {Colors.BLUE}Результат: {result}{Colors.END}")
    else:
        failed += 1
        print(f"    {Colors.RED}Ожидалось: 'Привет, Иван! Ты готов начать?'{Colors.END}")
        print(f"    {Colors.RED}Получено: {result}{Colors.END}")
    
    # Тест 3.3: Без имени (neutral)
    user_neutral = {"name": None, "gender": "neutral", "has_name": False}
    result = personalize_text(test_text, user_neutral)
    test18 = result == "Привет! Ты готовы начать?"
    if print_test("3.3. Персонализация без имени (neutral)", test18):
        passed += 1
        print(f"    {Colors.BLUE}Результат: {result}{Colors.END}")
    else:
        failed += 1
        print(f"    {Colors.RED}Ожидалось: 'Привет! Ты готовы начать?'{Colors.END}")
        print(f"    {Colors.RED}Получено: {result}{Colors.END}")
    
    # =========================
    # ИТОГИ
    # =========================
    
    print_header("ИТОГИ ТЕСТИРОВАНИЯ")
    
    total = passed + failed
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"\n{Colors.CYAN}Всего тестов:{Colors.END} {total}")
    print(f"{Colors.GREEN}✅ Успешно:{Colors.END} {passed}")
    if failed > 0:
        print(f"{Colors.RED}❌ Провалено:{Colors.END} {failed}")
    print(f"{Colors.CYAN}Процент успеха:{Colors.END} {percentage:.1f}%\n")
    
    if failed == 0:
        print(f"{Colors.GREEN}{'='*70}{Colors.END}")
        print(f"{Colors.GREEN}🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! ИЗМЕНЕНИЯ РАБОТАЮТ КОРРЕКТНО! 🎉{Colors.END}")
        print(f"{Colors.GREEN}{'='*70}{Colors.END}\n")
    else:
        print(f"{Colors.YELLOW}{'='*70}{Colors.END}")
        print(f"{Colors.YELLOW}⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ. ТРЕБУЕТСЯ ДОРАБОТКА.{Colors.END}")
        print(f"{Colors.YELLOW}{'='*70}{Colors.END}\n")
    
    return failed == 0

if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n{Colors.RED}❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ТЕСТИРОВАНИИ:{Colors.END}")
        print(f"{Colors.RED}{e}{Colors.END}\n")
        import traceback
        traceback.print_exc()
        sys.exit(2)

