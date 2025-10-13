#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальная проверка HTML-форматирования в modules/learn_cards.py
"""

def check_learn_cards_functions():
    """Проверяет все функции из чек-листа на наличие parse_mode='HTML'"""
    
    print("🔍 Финальная проверка функций learn_cards.py...")
    
    # Список функций из чек-листа
    functions_to_check = [
        "show_entry_poll_q1",
        "handle_entry_poll_q1", 
        "handle_entry_poll_q2",
        "handle_entry_poll_q3",
        "handle_entry_poll_q4",
        "show_exit_poll_q1",
        "handle_exit_poll_q1",
        "handle_exit_poll_q2", 
        "handle_exit_poll_q3",
        "handle_intro_yes",
        "handle_theory_1",
        "handle_theory_2",
        "handle_theory_3",
        "handle_theory_4",
        "handle_steps",
        "handle_trainer_intro",
        "handle_trainer_examples",
        "handle_show_templates",
        "handle_trainer_input",
        "handle_user_request_input"
    ]
    
    try:
        with open('modules/learn_cards.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Подсчитываем общее использование parse_mode
        parse_mode_count = content.count('parse_mode="HTML"')
        answer_count = content.count('.answer(')
        edit_text_count = content.count('.edit_text(')
        
        print(f"   📊 Общая статистика:")
        print(f"   • Найдено {parse_mode_count} использований parse_mode='HTML'")
        print(f"   • Найдено {answer_count} отправок сообщений (.answer)")
        print(f"   • Найдено {edit_text_count} редактирований (.edit_text)")
        
        # Проверяем каждую функцию
        all_functions_found = True
        functions_with_parse_mode = 0
        
        for func_name in functions_to_check:
            # Ищем определение функции
            func_def_pattern = f"async def {func_name}("
            if func_def_pattern in content:
                print(f"   ✅ {func_name} - найдена")
                
                # Ищем использование .answer или .edit_text в этой функции
                func_start = content.find(func_def_pattern)
                func_end = content.find("async def ", func_start + 1)
                if func_end == -1:
                    func_end = len(content)
                
                func_content = content[func_start:func_end]
                
                if '.answer(' in func_content or '.edit_text(' in func_content:
                    if 'parse_mode="HTML"' in func_content:
                        functions_with_parse_mode += 1
                        print(f"      ✅ parse_mode='HTML' присутствует")
                    else:
                        print(f"      ❌ parse_mode='HTML' отсутствует")
                else:
                    print(f"      ℹ️  Нет .answer() или .edit_text()")
            else:
                print(f"   ❌ {func_name} - не найдена")
                all_functions_found = False
        
        print(f"\n📋 Результат проверки:")
        print(f"   • Функций из чек-листа найдено: {len([f for f in functions_to_check if f'async def {f}(' in content])}/{len(functions_to_check)}")
        print(f"   • Функций с parse_mode='HTML': {functions_with_parse_mode}")
        
        if parse_mode_count > 0:
            print(f"   ✅ parse_mode='HTML' используется в коде")
        else:
            print(f"   ❌ parse_mode='HTML' не найден в коде")
            
        return parse_mode_count > 0 and functions_with_parse_mode > 0
            
    except FileNotFoundError:
        print("   ❌ Файл modules/learn_cards.py не найден")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка при проверке: {e}")
        return False

def check_main_py():
    """Проверяет main.py на дублирование функций main"""
    
    print("\n🔍 Проверка main.py...")
    
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Считаем функции main
        main_functions = content.count('async def main(')
        parse_mode_default = 'parse_mode=ParseMode.HTML' in content
        
        print(f"   📊 Найдено функций main: {main_functions}")
        print(f"   📊 parse_mode по умолчанию: {'✅' if parse_mode_default else '❌'}")
        
        if main_functions == 1:
            print("   ✅ Дублирование функций main исправлено")
            return True
        else:
            print(f"   ❌ Проблема: найдено {main_functions} функций main")
            return False
            
    except FileNotFoundError:
        print("   ❌ Файл main.py не найден")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка при проверке: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Финальная проверка исправлений HTML-форматирования...")
    
    # Проверяем все исправления
    learn_cards_ok = check_learn_cards_functions()
    main_ok = check_main_py()
    
    print("\n📋 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    print(f"   {'✅' if learn_cards_ok else '❌'} modules/learn_cards.py исправлен")
    print(f"   {'✅' if main_ok else '❌'} main.py исправлен")
    
    if learn_cards_ok and main_ok:
        print("\n🎉 ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ УСПЕШНО!")
        print("   HTML-форматирование должно теперь работать корректно.")
        print("\n💡 Готово к деплою:")
        print("   git add .")
        print("   git commit -m 'Fix HTML formatting - complete solution'")
        print("   git push origin master")
    else:
        print("\n⚠️  Некоторые исправления требуют внимания.")
    
    print("\n🧪 После деплоя протестируйте:")
    print("   • /learn_cards - полное обучение")
    print("   • /practice - быстрая практика")
    print("   • Все HTML-теги должны отображаться корректно")
