#!/usr/bin/env python3
"""
Главный скрипт для запуска всех тестов новых AI функций
"""
import sys
import os
import subprocess
import time

def run_test_file(test_file, description):
    """Запуск отдельного тестового файла"""
    print(f"\n{'='*60}")
    print(f"ЗАПУСК ТЕСТА: {description}")
    print(f"Файл: {test_file}")
    print('='*60)
    
    start_time = time.time()
    
    try:
        # Запускаем тест как подпроцесс
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, 
                              text=True, 
                              timeout=300)  # 5 минут таймаут
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            print("ТЕСТ ПРОЙДЕН УСПЕШНО")
            print(f"Время выполнения: {duration:.2f} сек")
            if result.stdout:
                print("\nВЫВОД ТЕСТА:")
                print(result.stdout)
            return True
        else:
            print("ТЕСТ ПРОВАЛЕН")
            print(f"Время выполнения: {duration:.2f} сек")
            if result.stdout:
                print("\nВЫВОД ТЕСТА:")
                print(result.stdout)
            if result.stderr:
                print("\nОШИБКИ ТЕСТА:")
                print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("ТЕСТ ПРЕВЫСИЛ ВРЕМЯ ВЫПОЛНЕНИЯ (5 минут)")
        return False
    except Exception as e:
        print(f"ОШИБКА ЗАПУСКА ТЕСТА: {e}")
        return False

def run_basic_functionality_test():
    """Запуск базового теста функциональности"""
    print(f"\n{'='*60}")
    print("БАЗОВЫЙ ТЕСТ ФУНКЦИОНАЛЬНОСТИ")
    print('='*60)
    
    try:
        from test_functionality import run_all_tests
        return run_all_tests()
    except Exception as e:
        print(f"Ошибка запуска базового теста: {e}")
        return False

def main():
    """Главная функция запуска всех тестов"""
    print("ЗАПУСК ПОЛНОГО ТЕСТИРОВАНИЯ НОВЫХ AI ФУНКЦИЙ")
    print("=" * 60)
    
    # Список тестов для запуска
    tests = [
        ("test_ai_functions.py", "AI функции (эмпатичный ответ, еженедельный анализ, синергия карт)"),
        ("test_scheduler_new.py", "Планировщик еженедельного анализа"),
        ("test_evening_reflection_integration.py", "Интеграция AI функций в вечернюю рефлексию")
    ]
    
    # Запускаем базовый тест функциональности
    print("\nЗапуск базового теста функциональности...")
    basic_test_passed = run_basic_functionality_test()
    
    # Запускаем специализированные тесты
    test_results = []
    for test_file, description in tests:
        if os.path.exists(test_file):
            result = run_test_file(test_file, description)
            test_results.append((description, result))
        else:
            print(f"Файл {test_file} не найден, пропускаем")
            test_results.append((description, False))
    
    # Выводим итоги
    print(f"\n{'='*60}")
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print('='*60)
    
    print(f"Базовый тест функциональности: {'ПРОЙДЕН' if basic_test_passed else 'ПРОВАЛЕН'}")
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for description, result in test_results:
        status = "ПРОЙДЕН" if result else "ПРОВАЛЕН"
        print(f"{description}: {status}")
        if result:
            passed_tests += 1
    
    print(f"\nОБЩИЙ РЕЗУЛЬТАТ: {passed_tests}/{total_tests} специализированных тестов пройдено")
    
    # Определяем общий результат
    all_tests_passed = basic_test_passed and (passed_tests == total_tests)
    
    if all_tests_passed:
        print("\nВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        print("Система готова к деплою в продакшн!")
        return True
    else:
        print(f"\n{total_tests - passed_tests} специализированных тестов не пройдено")
        if not basic_test_passed:
            print("Базовый тест функциональности не пройден")
        print("Требуется исправление ошибок перед деплоем")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
