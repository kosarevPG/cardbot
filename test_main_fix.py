#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для проверки исправления дублирования функций main в main.py
"""

import ast
import sys

def check_main_functions():
    """Проверяет количество функций main в файле main.py"""
    
    print("🔍 Проверка исправления дублирования функций main...")
    
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Парсим файл как AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"   ❌ Синтаксическая ошибка в main.py: {e}")
            return False
        
        # Считаем функции main
        main_functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == 'main':
                main_functions.append(node.lineno)
        
        print(f"   📊 Найдено функций main: {len(main_functions)}")
        
        if len(main_functions) == 1:
            print(f"   ✅ Исправлено! Осталась только одна функция main на строке {main_functions[0]}")
            return True
        elif len(main_functions) == 0:
            print("   ❌ Ошибка: не найдено ни одной функции main!")
            return False
        else:
            print(f"   ❌ Проблема: найдено {len(main_functions)} функций main на строках {main_functions}")
            return False
            
    except FileNotFoundError:
        print("   ❌ Файл main.py не найден")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка при проверке: {e}")
        return False

def check_parse_mode_setup():
    """Проверяет настройку parse_mode в main.py"""
    
    print("\n🔍 Проверка настройки parse_mode...")
    
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем инициализацию бота с parse_mode
        if 'parse_mode=ParseMode.HTML' in content:
            print("   ✅ Найдена настройка parse_mode=ParseMode.HTML по умолчанию")
            return True
        else:
            print("   ❌ Не найдена настройка parse_mode=ParseMode.HTML")
            return False
            
    except FileNotFoundError:
        print("   ❌ Файл main.py не найден")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка при проверке: {e}")
        return False

def check_learn_cards_parse_mode():
    """Проверяет использование parse_mode в learn_cards.py"""
    
    print("\n🔍 Проверка parse_mode в learn_cards.py...")
    
    try:
        with open('modules/learn_cards.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Считаем использование parse_mode
        parse_mode_count = content.count('parse_mode="HTML"')
        message_answer_count = content.count('.answer(')
        
        print(f"   📊 Найдено {parse_mode_count} использований parse_mode='HTML'")
        print(f"   📊 Найдено {message_answer_count} отправок сообщений")
        
        if parse_mode_count > 0:
            print("   ✅ parse_mode='HTML' используется в коде")
            return True
        else:
            print("   ❌ parse_mode='HTML' не найден в коде")
            return False
            
    except FileNotFoundError:
        print("   ❌ Файл modules/learn_cards.py не найден")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка при проверке: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск проверки исправлений...")
    
    # Проверяем все исправления
    main_fix_ok = check_main_functions()
    parse_mode_ok = check_parse_mode_setup()
    learn_cards_ok = check_learn_cards_parse_mode()
    
    print("\n📋 Результаты проверки:")
    print(f"   {'✅' if main_fix_ok else '❌'} Дублирование функций main исправлено")
    print(f"   {'✅' if parse_mode_ok else '❌'} parse_mode настроен по умолчанию")
    print(f"   {'✅' if learn_cards_ok else '❌'} parse_mode используется в learn_cards.py")
    
    if main_fix_ok and parse_mode_ok and learn_cards_ok:
        print("\n🎉 Все исправления применены успешно!")
        print("   HTML-форматирование должно теперь работать корректно.")
    else:
        print("\n⚠️  Некоторые исправления требуют внимания.")
    
    print("\n💡 Следующие шаги:")
    print("   1. Задеплойте изменения: git add . && git commit -m 'Fix HTML formatting' && git push")
    print("   2. Протестируйте команды /learn_cards и /practice")
    print("   3. Проверьте, что HTML-теги отображаются корректно")
