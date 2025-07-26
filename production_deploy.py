#!/usr/bin/env python3
"""
Скрипт для безопасного деплоя в production
Проверяет все необходимые условия перед миграцией
"""
import os
import sys
import sqlite3
from datetime import datetime

def check_config():
    """Проверяет конфигурацию production"""
    print("🔍 Проверка конфигурации production...")
    
    try:
        from config import ADMIN_ID, ADMIN_IDS, NO_LOGS_USERS, TOKEN
        print(f"✅ ADMIN_ID: {ADMIN_ID}")
        print(f"✅ ADMIN_IDS: {ADMIN_IDS}")
        print(f"✅ NO_LOGS_USERS: {len(NO_LOGS_USERS)} пользователей")
        print(f"✅ TOKEN: {'*' * 10 + TOKEN[-10:] if TOKEN else 'НЕ НАЙДЕН'}")
        
        # Проверяем, что ADMIN_ID в списке исключений
        if ADMIN_ID in NO_LOGS_USERS:
            print("✅ ADMIN_ID корректно исключен из статистики")
        else:
            print("❌ ВНИМАНИЕ: ADMIN_ID НЕ исключен из статистики!")
            return False
            
        return True
    except ImportError as e:
        print(f"❌ Ошибка импорта config.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка проверки конфигурации: {e}")
        return False

def check_database_structure():
    """Проверяет структуру БД"""
    print("\n🗄️ Проверка структуры БД...")
    
    try:
        from database.db import Database
        
        # Проверяем локальную БД
        db = Database('database/dev.db')
        
        # Проверяем наличие ключевых таблиц
        required_tables = ['users', 'scenario_logs', 'user_scenarios']
        existing_tables = []
        
        cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for row in cursor.fetchall():
            existing_tables.append(row['name'])
        
        print(f"✅ Найдено таблиц: {len(existing_tables)}")
        for table in required_tables:
            if table in existing_tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} - ОТСУТСТВУЕТ!")
                return False
        
        # Проверяем миграции
        print("\n🔄 Проверка миграций...")
        db._run_migrations()
        print("✅ Миграции выполнены успешно")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки БД: {e}")
        return False

def check_requirements():
    """Проверяет requirements.txt"""
    print("\n📦 Проверка зависимостей...")
    
    required_packages = [
        'aiogram',
        'pytz', 
        'requests',
        'pydantic-core',
        'httpx',
        'sqlite-web'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - ОТСУТСТВУЕТ!")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Отсутствуют пакеты: {missing_packages}")
        return False
    
    return True

def check_files():
    """Проверяет наличие ключевых файлов"""
    print("\n📁 Проверка файлов...")
    
    required_files = [
        'main.py',
        'config.py',
        'database/db.py',
        'modules/logging_service.py',
        'modules/user_management.py',
        'requirements.txt',
        'amvera.yml'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - ОТСУТСТВУЕТ!")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Отсутствуют файлы: {missing_files}")
        return False
    
    return True

def generate_deployment_commands():
    """Генерирует команды для деплоя"""
    print("\n🚀 Команды для деплоя:")
    print("=" * 50)
    print("# 1. Добавить все изменения в git")
    print("git add .")
    print("git commit -m \"feat: add admin panel, advanced user stats, and scenario logging\"")
    print()
    print("# 2. Отправить в GitHub")
    print("git push origin main")
    print()
    print("# 3. Amvera автоматически получит изменения и перезапустит бота")
    print()
    print("# 4. Проверить логи Amvera после деплоя")
    print("# Логи должны показать успешную инициализацию БД и миграции")
    print()
    print("# 5. Протестировать функции в production")
    print("# - /admin - админская панель")
    print("# - /user_profile - расширенный профиль")
    print("# - /scenario_stats - статистика сценариев")

def main():
    """Основная функция проверки"""
    print("🔍 ПРОВЕРКА ГОТОВНОСТИ К DEPLOY В PRODUCTION")
    print("=" * 60)
    
    checks = [
        ("Конфигурация", check_config),
        ("Структура БД", check_database_structure),
        ("Зависимости", check_requirements),
        ("Файлы", check_files)
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
        print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! ГОТОВ К DEPLOY!")
        generate_deployment_commands()
    else:
        print("\n⚠️ ЕСТЬ ПРОБЛЕМЫ! ИСПРАВИТЕ ИХ ПЕРЕД DEPLOY!")
        print("Проверьте логи выше и исправьте найденные проблемы.")

if __name__ == "__main__":
    main() 