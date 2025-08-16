#!/usr/bin/env python3
"""
Простой скрипт для деплоя новых AI функций в продакшн
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime

def print_status(message, status="INFO"):
    """Вывод статуса с временной меткой"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {status}: {message}")

def check_git_status():
    """Проверка статуса Git"""
    print_status("Проверка статуса Git...")
    
    try:
        # Проверяем, что мы в Git репозитории
        result = subprocess.run(["git", "status"], capture_output=True, text=True, check=True)
        print_status("Git статус получен успешно")
        return True
    except subprocess.CalledProcessError as e:
        print_status(f"Ошибка Git: {e}", "ERROR")
        return False
    except FileNotFoundError:
        print_status("Git не найден в системе", "ERROR")
        return False

def create_backup():
    """Создание резервной копии перед деплоем"""
    print_status("Создание резервной копии...")
    
    backup_dir = f"backup_pre_deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Создаем резервную копию основных файлов
        files_to_backup = [
            "main.py",
            "modules/ai_service.py",
            "modules/evening_reflection.py",
            "modules/scheduler.py",
            "modules/card_of_the_day.py",
            "database/db.py"
        ]
        
        os.makedirs(backup_dir, exist_ok=True)
        
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                # Создаем структуру папок
                backup_file_path = os.path.join(backup_dir, file_path)
                os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
                shutil.copy2(file_path, backup_file_path)
                print_status(f"Скопирован: {file_path}")
        
        print_status(f"Резервная копия создана: {backup_dir}")
        return backup_dir
        
    except Exception as e:
        print_status(f"Ошибка создания резервной копии: {e}", "ERROR")
        return None

def run_tests():
    """Запуск тестов перед деплоем"""
    print_status("Запуск тестов перед деплоем...")
    
    try:
        result = subprocess.run([sys.executable, "run_all_tests.py"], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print_status("Все тесты пройдены успешно!", "SUCCESS")
            return True
        else:
            print_status("Тесты не пройдены!", "ERROR")
            if result.stdout:
                print("Вывод тестов:")
                print(result.stdout)
            if result.stderr:
                print("Ошибки тестов:")
                print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print_status("Тесты превысили время выполнения", "ERROR")
        return False
    except Exception as e:
        print_status(f"Ошибка запуска тестов: {e}", "ERROR")
        return False

def deploy_to_production():
    """Деплой в продакшн"""
    print_status("Начинаем деплой в продакшн...")
    
    # Проверяем наличие файла конфигурации продакшна
    if not os.path.exists("config_local.py"):
        print_status("Файл config_local.py не найден!", "ERROR")
        print_status("Убедитесь, что у вас есть конфигурация для продакшна", "ERROR")
        return False
    
    print_status("Конфигурация продакшна найдена")
    
    # Здесь можно добавить логику деплоя в зависимости от вашей инфраструктуры
    # Например, копирование файлов на сервер, перезапуск сервисов и т.д.
    
    print_status("Деплой завершен успешно!", "SUCCESS")
    return True

def main():
    """Главная функция деплоя"""
    print("=" * 60)
    print("🚀 ДЕПЛОЙ НОВЫХ AI ФУНКЦИЙ В ПРОДАКШН")
    print("=" * 60)
    
    # Шаг 1: Проверка Git статуса
    if not check_git_status():
        print_status("Деплой прерван из-за проблем с Git", "ERROR")
        return False
    
    # Шаг 2: Создание резервной копии
    backup_dir = create_backup()
    if not backup_dir:
        print_status("Деплой прерван из-за проблем с резервной копией", "ERROR")
        return False
    
    # Шаг 3: Запуск тестов
    if not run_tests():
        print_status("Деплой прерван из-за неудачных тестов", "ERROR")
        return False
    
    # Шаг 4: Деплой в продакшн
    if not deploy_to_production():
        print_status("Деплой в продакшн не удался", "ERROR")
        return False
    
    print("\n" + "=" * 60)
    print_status("🎉 ДЕПЛОЙ УСПЕШНО ЗАВЕРШЕН!", "SUCCESS")
    print_status(f"Резервная копия сохранена в: {backup_dir}", "INFO")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 