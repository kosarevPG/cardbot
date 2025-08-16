#!/usr/bin/env python3
"""
Скрипт для исправления amvera.yml и деплоя
"""

import os
import subprocess
import sys

def run_command(command, description):
    """Выполняет команду и выводит результат"""
    print(f"\n🔄 {description}...")
    print(f"Команда: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {description} успешно выполнено")
            if result.stdout:
                print(f"Вывод: {result.stdout}")
        else:
            print(f"❌ Ошибка при {description}")
            print(f"Ошибка: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение при {description}: {e}")
        return False
    
    return True

def main():
    print("🚀 Исправляем конфигурацию Amvera и деплоим")
    
    # Проверяем статус Git
    if not run_command("git status", "Проверка статуса Git"):
        return
    
    # Добавляем изменения
    if not run_command("git add amvera.yml", "Добавление amvera.yml"):
        return
    
    # Делаем коммит
    if not run_command('git commit -m "Fix amvera.yml - Remove problematic run section"', "Создание коммита"):
        return
    
    # Пушим изменения
    if not run_command("git push origin master", "Отправка изменений"):
        return
    
    print("\n🎉 Деплой завершен!")
    print("📊 Веб-интерфейс должен быть доступен по адресу: https://cardbot-kosarevpg.amvera.io")
    print("🔐 Логин: admin")
    print("🔑 Пароль: root")
    print("\n⏳ Подождите несколько минут, пока изменения применятся на сервере")

if __name__ == "__main__":
    main() 