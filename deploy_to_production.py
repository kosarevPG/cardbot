#!/usr/bin/env python3
"""
Скрипт для деплоя в продакшн
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime

def create_backup():
    """Создает бэкап текущих файлов"""
    print("📦 СОЗДАНИЕ БЭКАПА...")
    
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Файлы для бэкапа
    files_to_backup = [
        'main.py',
        'database/db.py',
        'modules/card_of_the_day.py'
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            # Создаем директории если нужно
            backup_file_path = os.path.join(backup_dir, file_path)
            os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
            
            # Копируем файл
            shutil.copy2(file_path, backup_file_path)
            print(f"✅ Бэкап: {file_path}")
        else:
            print(f"⚠️ Файл не найден: {file_path}")
    
    print(f"📦 Бэкап создан в: {backup_dir}")
    return backup_dir

def check_files_exist():
    """Проверяет наличие всех необходимых файлов"""
    print("\n📁 ПРОВЕРКА ФАЙЛОВ...")
    
    required_files = [
        'main.py',
        'database/db.py',
        'modules/card_of_the_day.py'
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - НЕ НАЙДЕН")
            all_exist = False
    
    return all_exist

def run_tests():
    """Запускает тесты перед деплоем"""
    print("\n🧪 ЗАПУСК ТЕСТОВ...")
    
    try:
        # Запускаем проверку готовности
        result = subprocess.run([sys.executable, 'check_production_readiness.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Тесты пройдены успешно")
            return True
        else:
            print("❌ Тесты не пройдены:")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при запуске тестов: {e}")
        return False

def deploy_files():
    """Выполняет деплой файлов"""
    print("\n🚀 ВЫПОЛНЕНИЕ ДЕПЛОЯ...")
    
    # Здесь должны быть команды для копирования файлов на сервер
    # Это пример для локального деплоя
    
    print("📋 ФАЙЛЫ ДЛЯ ДЕПЛОЯ:")
    print("  • main.py")
    print("  • database/db.py")
    print("  • modules/card_of_the_day.py")
    
    print("\n🔧 КОМАНДЫ ДЛЯ ДЕПЛОЯ:")
    print("1. Остановить продакшн бота")
    print("2. Скопировать файлы:")
    print("   scp main.py user@server:/path/to/bot/")
    print("   scp database/db.py user@server:/path/to/bot/database/")
    print("   scp modules/card_of_the_day.py user@server:/path/to/bot/modules/")
    print("3. Запустить продакшн бота")
    
    return True

def main():
    """Основная функция деплоя"""
    print("🚀 ДЕПЛОЙ В ПРОДАКШН")
    print("=" * 50)
    
    # Шаг 1: Создание бэкапа
    backup_dir = create_backup()
    
    # Шаг 2: Проверка файлов
    if not check_files_exist():
        print("❌ НЕ ВСЕ ФАЙЛЫ НАЙДЕНЫ. ДЕПЛОЙ ПРЕРВАН.")
        return False
    
    # Шаг 3: Запуск тестов
    if not run_tests():
        print("❌ ТЕСТЫ НЕ ПРОЙДЕНЫ. ДЕПЛОЙ ПРЕРВАН.")
        return False
    
    # Шаг 4: Деплой файлов
    if not deploy_files():
        print("❌ ОШИБКА ПРИ ДЕПЛОЕ.")
        return False
    
    print("\n✅ ДЕПЛОЙ ГОТОВ К ВЫПОЛНЕНИЮ")
    print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Остановить продакшн бота")
    print("2. Скопировать файлы на сервер")
    print("3. Запустить продакшн бота")
    print("4. Протестировать воронку в админке")
    
    print(f"\n📦 Бэкап сохранен в: {backup_dir}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 