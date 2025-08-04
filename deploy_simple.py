#!/usr/bin/env python3
"""
Простой скрипт для деплоя изменений в продакшн
"""

import os
import subprocess
import sys
from datetime import datetime

def check_syntax():
    """Проверяет синтаксис Python файлов"""
    print("🔍 Проверяем синтаксис Python...")
    
    files_to_check = [
        "main.py",
        "modules/ai_service.py",
        "database/db.py"
    ]
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            print(f"⚠️ Файл не найден: {file_path}")
            continue
            
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
    
    return True

def create_backup():
    """Создает бэкап измененных файлов"""
    print("📦 Создаем бэкап...")
    
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        "modules/ai_service.py",
        "main.py"
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_file_path = os.path.join(backup_dir, file_path)
            os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
            with open(file_path, 'r', encoding='utf-8') as src:
                with open(backup_file_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            print(f"✅ Бэкап: {file_path}")
    
    print(f"📦 Бэкап создан в: {backup_dir}")
    return backup_dir

def deploy_to_production():
    """Выполняет деплой в продакшн"""
    print("🚀 Начинаем деплой в продакшн...")
    
    # Проверяем статус git
    try:
        result = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print("📝 Обнаружены изменения в git:")
            print(result.stdout)
        else:
            print("ℹ️ Нет изменений для коммита")
            return True
    except Exception as e:
        print(f"❌ Ошибка при проверке git статуса: {e}")
        return False
    
    # Команды для деплоя
    commands = [
        "git add .",
        "git commit -m \"Update AI service: fix feminine gender addressing\"",
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
    
    return True

def main():
    """Основная функция"""
    print("🚀 ПРОСТОЙ ДЕПЛОЙ В ПРОДАКШН")
    print("=" * 50)
    
    # Шаг 1: Проверка синтаксиса
    if not check_syntax():
        print("❌ ОШИБКИ СИНТАКСИСА. ДЕПЛОЙ ПРЕРВАН.")
        return False
    
    # Шаг 2: Создание бэкапа
    backup_dir = create_backup()
    
    # Шаг 3: Деплой
    if not deploy_to_production():
        print("❌ ОШИБКА ПРИ ДЕПЛОЕ.")
        return False
    
    print("\n✅ ДЕПЛОЙ УСПЕШНО ЗАВЕРШЕН!")
    print("\n📋 ИЗМЕНЕНИЯ:")
    print("  • Обновлен AI сервис для обращения к пользователям в женском роде")
    print("  • Добавлены проверки на запрещенные ссылки и markdown")
    print("  • Улучшены fallback сообщения")
    
    print(f"\n📦 Бэкап сохранен в: {backup_dir}")
    print("\n⏰ Деплой на Amvera займет 2-3 минуты")
    print("🔍 Проверьте логи в админке через 5 минут")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 