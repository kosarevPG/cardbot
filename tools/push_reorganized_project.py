#!/usr/bin/env python3
"""
Скрипт для отправки реорганизованного проекта в GitHub
"""

import os
import subprocess
import sys

def run_command(command, description):
    """Выполняет команду и выводит результат"""
    print(f"🔄 {description}: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Успешно: {description}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при {description}: {e}")
        print(f"stderr: {e.stderr}")
        return False

def check_git_status():
    """Проверяет статус Git"""
    print("🔍 Проверка статуса Git...")
    
    try:
        result = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True, check=True)
        
        if result.stdout.strip():
            print("📝 Обнаружены изменения для коммита:")
            print(result.stdout)
            return True
        else:
            print("ℹ️ Нет изменений для коммита")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка проверки Git статуса: {e}")
        return False

def push_to_github():
    """Отправляет проект в GitHub"""
    print("🚀 Отправка реорганизованного проекта в GitHub...")
    
    # Проверяем статус
    if not check_git_status():
        print("ℹ️ Нет изменений для отправки")
        return True
    
    # Команды для отправки
    commands = [
        ("git add .", "Добавление всех изменений"),
        ("git commit -m \"feat: Реорганизация проекта - очистка корня, организация инструментов в tools/\"", "Создание коммита"),
        ("git push origin master", "Отправка в GitHub")
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            print(f"❌ Ошибка при {description}. Остановка.")
            return False
    
    print("\n🎉 ПРОЕКТ УСПЕШНО ОТПРАВЛЕН В GITHUB!")
    return True

def show_final_structure():
    """Показывает финальную структуру проекта"""
    print("\n📁 ФИНАЛЬНАЯ СТРУКТУРА ПРОЕКТА:")
    print("=" * 50)
    
    print("\n🚀 Корневая папка (только для бота):")
    root_files = [f for f in os.listdir(".") if os.path.isfile(f) and not f.startswith('.')]
    root_dirs = [d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith('.')]
    
    for file in sorted(root_files):
        if file in ["main.py", "requirements.txt", "amvera.yml", "config.py", "README.md"]:
            print(f"  ✅ {file}")
        else:
            print(f"  📄 {file}")
    
    for dir_name in sorted(root_dirs):
        if dir_name in ["modules", "database", "cards", "data"]:
            print(f"  📁 {dir_name}/ (основная)")
        elif dir_name == "tools":
            print(f"  🛠️ {dir_name}/ (вспомогательные файлы)")
        else:
            print(f"  📁 {dir_name}/")
    
    print(f"\n📊 Статистика:")
    print(f"  • Файлов в корне: {len(root_files)}")
    print(f"  • Папок в корне: {len(root_dirs)}")
    
    # Подсчитываем файлы в tools/
    tools_dir = "tools"
    if os.path.exists(tools_dir):
        tools_files = []
        for root, dirs, files in os.walk(tools_dir):
            tools_files.extend(files)
        print(f"  • Файлов в tools/: {len(tools_files)}")

def main():
    """Основная функция"""
    print("🚀 ОТПРАВКА РЕОРГАНИЗОВАННОГО ПРОЕКТА В GITHUB")
    print("=" * 60)
    
    # Проверяем, что мы в правильной директории
    if not os.path.exists("main.py"):
        print("❌ Ошибка: main.py не найден. Убедитесь, что вы в корне проекта.")
        return False
    
    if not os.path.exists("tools/"):
        print("❌ Ошибка: папка tools/ не найдена. Реорганизация не завершена.")
        return False
    
    # Отправляем в GitHub
    if push_to_github():
        # Показываем финальную структуру
        show_final_structure()
        
        print("\n🎯 РЕЗУЛЬТАТ:")
        print("✅ Проект реорганизован")
        print("✅ Структура очищена")
        print("✅ Файлы отправлены в GitHub")
        print("✅ Amvera получит только нужные файлы")
        
        print("\n🚀 Следующие шаги:")
        print("1. Проверьте изменения в GitHub")
        print("2. Amvera автоматически начнет пересборку")
        print("3. Новые функции станут активны через 5-10 минут")
        
        return True
    else:
        print("\n❌ ОШИБКА ПРИ ОТПРАВКЕ В GITHUB")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
