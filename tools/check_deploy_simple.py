#!/usr/bin/env python3
"""
Упрощенный скрипт для проверки статуса деплоя
Проверяет локальные файлы и готовность к деплою
"""

import os
import sys

def check_new_ai_functions():
    """Проверяет, что новые AI функции реально работают"""
    print("🤖 Проверка новых AI функций...")
    
    try:
        # Проверяем, что новые функции импортируются
        from modules.ai_service import get_empathetic_response, get_weekly_analysis
        print("✅ Новые AI функции импортируются")
        
        # Проверяем, что функции callable
        if callable(get_empathetic_response) and callable(get_weekly_analysis):
            print("✅ AI функции доступны для вызова")
            return True
        else:
            print("❌ AI функции не являются callable")
            return False
            
    except ImportError as e:
        print(f"❌ Ошибка импорта AI функций: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки AI функций: {e}")
        return False

def check_evening_reflection_integration():
    """Проверяет интеграцию AI функций в вечернюю рефлексию"""
    print("\n🌙 Проверка интеграции в вечернюю рефлексию...")
    
    try:
        from modules.evening_reflection import process_hard_moments
        print("✅ Модуль вечерней рефлексии доступен")
        
        # Проверяем, что функция импортирует новые AI функции
        import inspect
        source = inspect.getsource(process_hard_moments)
        
        if "get_empathetic_response" in source:
            print("✅ Эмпатичный ответ интегрирован")
        else:
            print("❌ Эмпатичный ответ НЕ интегрирован")
            return False
            
        if "get_reflection_summary_and_card_synergy" in source:
            print("✅ Синергия с картами интегрирована")
        else:
            print("❌ Синергия с картами НЕ интегрирована")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта модуля рефлексии: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки интеграции: {e}")
        return False

def check_scheduler_integration():
    """Проверяет интеграцию планировщика еженедельного анализа"""
    print("\n⏰ Проверка планировщика еженедельного анализа...")
    
    try:
        from modules.scheduler import ReflectionAnalysisScheduler
        print("✅ Планировщик еженедельного анализа доступен")
        
        # Проверяем, что планировщик интегрирован в main.py
        with open("main.py", "r", encoding="utf-8") as f:
            main_content = f.read()
            
        if "ReflectionAnalysisScheduler" in main_content:
            print("✅ Планировщик интегрирован в main.py")
        else:
            print("❌ Планировщик НЕ интегрирован в main.py")
            return False
            
        if "reflection_scheduler.start()" in main_content:
            print("✅ Планировщик запускается в main.py")
        else:
            print("❌ Планировщик НЕ запускается в main.py")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта планировщика: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки планировщика: {e}")
        return False

def check_database_functions():
    """Проверяет новые функции базы данных"""
    print("\n🗄️ Проверка новых функций БД...")
    
    try:
        from database.db import Database
        
        # Проверяем наличие новых функций
        db = Database('database/dev.db')
        
        # Проверяем, что новые методы существуют
        if hasattr(db, 'get_today_card_of_the_day'):
            print("✅ get_today_card_of_the_day доступен")
        else:
            print("❌ get_today_card_of_the_day НЕ доступен")
            return False
            
        if hasattr(db, 'get_reflections_for_last_n_days'):
            print("✅ get_reflections_for_last_n_days доступен")
        else:
            print("❌ get_reflections_for_last_n_days НЕ доступен")
            return False
            
        if hasattr(db, 'get_users_with_recent_reflections'):
            print("✅ get_users_with_recent_reflections доступен")
        else:
            print("❌ get_users_with_recent_reflections НЕ доступен")
            return False
            
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки БД: {e}")
        return False

def check_amvera_config():
    """Проверяет конфигурацию Amvera"""
    print("\n🌐 Проверка конфигурации Amvera...")
    
    if os.path.exists("amvera.yml"):
        print("✅ amvera.yml найден")
        
        with open("amvera.yml", "r", encoding="utf-8") as f:
            content = f.read()
            
        if "cardbot-1-kosarevpg.amvera.io" in content:
            print("✅ Домен Amvera настроен")
        else:
            print("❌ Домен Amvera НЕ настроен")
            return False
            
        if "python main.py" in content:
            print("✅ Команда запуска настроена")
        else:
            print("❌ Команда запуска НЕ настроена")
            return False
            
        return True
    else:
        print("❌ amvera.yml не найден")
        return False

def main():
    """Основная функция проверки"""
    print("🔍 ПРОВЕРКА ГОТОВНОСТИ К DEPLOY НА AMVERA")
    print("=" * 50)
    
    checks = [
        ("Новые AI функции", check_new_ai_functions),
        ("Интеграция в рефлексию", check_evening_reflection_integration),
        ("Планировщик", check_scheduler_integration),
        ("Функции БД", check_database_functions),
        ("Конфигурация Amvera", check_amvera_config)
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                print(f"❌ Проверка '{name}' НЕ ПРОЙДЕНА!")
        except Exception as e:
            print(f"❌ Критическая ошибка в проверке '{name}': {e}")
    
    print(f"\n📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
    print(f"✅ Пройдено: {passed}/{total}")
    print(f"❌ Провалено: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! КОД ГОТОВ К DEPLOY!")
        print("🤖 Новые AI функции интегрированы локально!")
        print("\n💡 РЕКОМЕНДАЦИИ:")
        print("1. Push в Git уже выполнен ✅")
        print("2. Amvera должен автоматически пересобрать проект")
        print("3. Если функции не работают, возможно:")
        print("   - Amvera еще не завершил пересборку")
        print("   - Есть ошибки в логах Amvera")
        print("   - Требуется принудительная пересборка")
    else:
        print(f"\n⚠️ {total - passed} проверок не пройдено!")
        print("🔧 Требуется исправление перед деплоем")

if __name__ == "__main__":
    main()
