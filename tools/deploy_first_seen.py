#!/usr/bin/env python3
"""
Скрипт для деплоя функциональности first_seen
"""

import os
import subprocess
import sys

def deploy_first_seen():
    """Деплой функциональности first_seen"""
    print("🚀 Начинаем деплой функциональности first_seen...")
    
    # Проверяем, что мы в правильной директории
    if not os.path.exists("main.py"):
        print("❌ Ошибка: main.py не найден. Убедитесь, что вы в корневой папке проекта.")
        return False
    
    # Проверяем, что файл database/db.py существует
    if not os.path.exists("database/db.py"):
        print("❌ Ошибка: database/db.py не найден.")
        return False
    
    # Проверяем синтаксис Python
    print("🔍 Проверяем синтаксис Python...")
    files_to_check = ["main.py", "database/db.py"]
    
    for file_path in files_to_check:
        try:
            result = subprocess.run([sys.executable, "-m", "py_compile", file_path], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Синтаксис {file_path} корректен")
            else:
                print(f"❌ Ошибка синтаксиса в {file_path}: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Ошибка при проверке синтаксиса {file_path}: {e}")
            return False
    
    print("✅ Все проверки пройдены успешно")
    
    # Команды для деплоя
    commands = [
        "git add .",
        "git commit -m 'Add first_seen functionality - Track user first visit timestamp'",
        "git push origin master"
    ]
    
    for cmd in commands:
        print(f"🔄 Выполняем: {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            print(f"✅ Успешно: {cmd}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка при выполнении '{cmd}': {e}")
            print(f"stderr: {e.stderr}")
            return False
    
    print("🎉 Деплой завершен успешно!")
    print("📝 Проверьте логи в продакшене через несколько минут")
    print("🔧 Добавленная функциональность:")
    print("  - Поле first_seen в таблице users")
    print("  - Автоматическая установка first_seen для новых пользователей")
    print("  - Статистика новых пользователей в админ-панели")
    print("  - Методы для работы с first_seen в Database")
    return True

if __name__ == "__main__":
    success = deploy_first_seen()
    sys.exit(0 if success else 1) 