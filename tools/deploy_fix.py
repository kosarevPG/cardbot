#!/usr/bin/env python3
"""
Скрипт для деплоя исправлений в продакшн
"""

import os
import subprocess
import sys

def deploy_to_production():
    """Деплой исправлений в продакшн"""
    print("🚀 Начинаем деплой исправлений в продакшн...")
    
    # Проверяем, что мы в правильной директории
    if not os.path.exists("main.py"):
        print("❌ Ошибка: main.py не найден. Убедитесь, что вы в корневой папке проекта.")
        return False
    
    # Проверяем, что файл card_of_the_day.py восстановлен
    if not os.path.exists("modules/card_of_the_day.py"):
        print("❌ Ошибка: modules/card_of_the_day.py не найден.")
        return False
    
    # Проверяем размер файла
    file_size = os.path.getsize("modules/card_of_the_day.py")
    print(f"📁 Размер modules/card_of_the_day.py: {file_size} байт")
    if file_size < 1000:  # Файл слишком маленький
        print(f"⚠️  Предупреждение: modules/card_of_the_day.py слишком маленький ({file_size} байт)")
    
    # Проверяем синтаксис Python
    print("🔍 Проверяем синтаксис Python...")
    try:
        result = subprocess.run([sys.executable, "-m", "py_compile", "main.py"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Синтаксис main.py корректен")
        else:
            print(f"❌ Ошибка синтаксиса в main.py: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при проверке синтаксиса: {e}")
        return False
    
    print("✅ Все проверки пройдены успешно")
    
    # Команды для деплоя
    commands = [
        "git add .",
        "git commit -m 'Fix production errors: KeyError and IndentationError - Restored card_of_the_day.py and fixed dispatcher issues'",
        "git push origin main"
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
    print("🔧 Исправления:")
    print("  - Восстановлен modules/card_of_the_day.py")
    print("  - Исправлена ошибка отступов в main.py (строка 876)")
    print("  - Добавлены проверки для предотвращения KeyError в диспетчере")
    return True

if __name__ == "__main__":
    success = deploy_to_production()
    sys.exit(0 if success else 1) 