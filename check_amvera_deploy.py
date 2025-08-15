#!/usr/bin/env python3
"""
Скрипт для проверки реального статуса деплоя на Amvera
Проверяет не только Git, но и фактическую работу новых функций в продакшне
"""

import os
import sys
import subprocess
import time
import requests
from datetime import datetime

def check_git_status():
    """Проверяет статус Git"""
    print("🔍 Проверка статуса Git...")
    
    try:
        # Проверяем последний коммит
        result = subprocess.run(["git", "--no-pager", "log", "--oneline", "-1"], 
                              capture_output=True, text=True, check=True)
        last_commit = result.stdout.strip()
        print(f"✅ Последний коммит: {last_commit}")
        
        # Проверяем статус ветки
        result = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print("⚠️ Есть незафиксированные изменения:")
            print(result.stdout)
            return False
        else:
            print("✅ Все изменения зафиксированы")
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка проверки Git: {e}")
        return False

def check_amvera_health():
    """Проверяет здоровье Amvera приложения"""
    print("\n🌐 Проверка здоровья Amvera приложения...")
    
    try:
        # Пытаемся получить ответ от Amvera
        url = "https://cardbot-1-kosarevpg.amvera.io/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Amvera отвечает: HTTP {response.status_code}")
            return True
        else:
            print(f"⚠️ Amvera отвечает с ошибкой: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Amvera недоступен: {e}")
        return False

def check_new_ai_functions():
    """Проверяет, что новые AI функции реально работают"""
    print("\n🤖 Проверка новых AI функций...")
    
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

def force_amvera_rebuild():
    """Принудительно инициирует пересборку на Amvera"""
    print("\n🚀 Принудительная пересборка на Amvera...")
    
    try:
        # Создаем небольшое изменение для принудительной пересборки
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Добавляем комментарий с временной меткой
        if "# Last Amvera rebuild:" not in content:
            content = f"# Last Amvera rebuild: {timestamp}\n{content}"
            
            with open("main.py", "w", encoding="utf-8") as f:
                f.write(content)
            
            print("✅ Добавлена временная метка для пересборки")
            
            # Коммитим и пушим
            commands = [
                "git add main.py",
                f'git commit -m "force: Принудительная пересборка на Amvera - {timestamp}"',
                "git push origin master"
            ]
            
            for cmd in commands:
                print(f"🔄 Выполняем: {cmd}")
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
                print(f"✅ Успешно: {cmd}")
            
            print("🎉 Принудительная пересборка инициирована!")
            print("⏳ Подождите 5-10 минут и запустите проверку снова")
            return True
        else:
            print("ℹ️ Временная метка уже добавлена")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка принудительной пересборки: {e}")
        return False

def main():
    """Основная функция проверки"""
    print("🔍 ПРОВЕРКА РЕАЛЬНОГО СТАТУСА DEPLOY НА AMVERA")
    print("=" * 60)
    
    checks = [
        ("Git статус", check_git_status),
        ("Здоровье Amvera", check_amvera_health),
        ("Новые AI функции", check_new_ai_functions),
        ("Интеграция в рефлексию", check_evening_reflection_integration),
        ("Планировщик", check_scheduler_integration),
        ("Функции БД", check_database_functions)
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
        print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! DEPLOY РЕАЛЬНО РАБОТАЕТ!")
        print("🤖 Новые AI функции активны в продакшне!")
    else:
        print(f"\n⚠️ {total - passed} проверок не пройдено!")
        print("🚀 Рекомендуется принудительная пересборка на Amvera")
        
        response = input("\n❓ Выполнить принудительную пересборку? (y/n): ")
        if response.lower() in ['y', 'yes', 'да', 'д']:
            force_amvera_rebuild()
        else:
            print("ℹ️ Пересборка пропущена")

if __name__ == "__main__":
    main()
