#!/usr/bin/env python3
"""
Скрипт для деплоя текущих изменений в продакшн
"""
import os
import subprocess
import sys

def deploy_current_changes():
    """Деплой текущих изменений в продакшн"""
    print("🚀 Начинаем деплой текущих изменений в продакшн...")
    
    # Проверяем, что мы в правильной директории
    if not os.path.exists("main.py"):
        print("❌ Ошибка: main.py не найден.")
        return False
    
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
        "git commit -m 'Add first_seen functionality and fix production errors'",
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
    print("🔧 Изменения:")
    print("  - Добавлена функциональность first_seen")
    print("  - Исправлены ошибки в main.py")
    print("  - Обновлена структура базы данных")
    return True

if __name__ == "__main__":
    success = deploy_current_changes()
    sys.exit(0 if success else 1) 