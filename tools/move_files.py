#!/usr/bin/env python3
"""
Скрипт для перемещения вспомогательных файлов в папку tools/
"""

import os
import shutil
import glob
from pathlib import Path

def create_tools_directory():
    """Создает папку tools/ если её нет"""
    tools_dir = Path("tools")
    if not tools_dir.exists():
        tools_dir.mkdir()
        print("✅ Создана папка tools/")
    else:
        print("ℹ️ Папка tools/ уже существует")

def move_test_files():
    """Перемещает тестовые файлы"""
    test_files = glob.glob("test_*.py") + ["run_all_tests.py"]
    for file_path in test_files:
        if os.path.exists(file_path):
            dest = f"tools/{file_path}"
            shutil.move(file_path, dest)
            print(f"✅ Перемещен: {file_path} → tools/")

def move_check_files():
    """Перемещает файлы проверок"""
    check_files = glob.glob("check_*.py")
    for file_path in check_files:
        if os.path.exists(file_path):
            dest = f"tools/{file_path}"
            shutil.move(file_path, dest)
            print(f"✅ Перемещен: {file_path} → tools/")

def move_debug_files():
    """Перемещает файлы отладки"""
    debug_files = glob.glob("debug_*.py")
    for file_path in debug_files:
        if os.path.exists(file_path):
            dest = f"tools/{file_path}"
            shutil.move(file_path, dest)
            print(f"✅ Перемещен: {file_path} → tools/")

def move_deploy_files():
    """Перемещает файлы деплоя"""
    deploy_files = glob.glob("deploy_*.py") + glob.glob("deploy_*.bat") + glob.glob("deploy_*.ps1") + ["deploy.cmd"]
    for file_path in deploy_files:
        if os.path.exists(file_path):
            dest = f"tools/{file_path}"
            shutil.move(file_path, dest)
            print(f"✅ Перемещен: {file_path} → tools/")

def move_migrate_files():
    """Перемещает файлы миграции"""
    migrate_files = glob.glob("migrate_*.py") + glob.glob("production_*.py")
    for file_path in migrate_files:
        if os.path.exists(file_path):
            dest = f"tools/{file_path}"
            shutil.move(file_path, dest)
            print(f"✅ Перемещен: {file_path} → tools/")

def move_analysis_files():
    """Перемещает аналитические файлы"""
    analysis_files = glob.glob("analyze_*.py") + glob.glob("dashboard_*.py") + glob.glob("detailed_*.py") + glob.glob("verify_*.py")
    for file_path in analysis_files:
        if os.path.exists(file_path):
            dest = f"tools/{file_path}"
            shutil.move(file_path, dest)
            print(f"✅ Перемещен: {file_path} → tools/")

def move_documentation():
    """Перемещает документацию"""
    md_files = glob.glob("*.md")
    for file_path in md_files:
        if file_path not in ["README.md", "tools/REORGANIZATION_PLAN.md"]:
            if os.path.exists(file_path):
                dest = f"tools/{file_path}"
                shutil.move(file_path, dest)
                print(f"✅ Перемещен: {file_path} → tools/")

def move_backup_directories():
    """Перемещает папки бэкапов"""
    backup_dirs = glob.glob("backup_*")
    for dir_path in backup_dirs:
        if os.path.isdir(dir_path):
            dest = f"tools/{dir_path}"
            shutil.move(dir_path, dest)
            print(f"✅ Перемещена папка: {dir_path} → tools/")

def move_temporary_files():
    """Перемещает временные файлы"""
    temp_files = ["tatus", "h origin master", "ection && git push origin master"]
    for file_path in temp_files:
        if os.path.exists(file_path):
            dest = f"tools/{file_path}"
            shutil.move(file_path, dest)
            print(f"✅ Перемещен: {file_path} → tools/")

def update_gitignore():
    """Обновляет .gitignore"""
    gitignore_path = ".gitignore"
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "tools/" not in content:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n# Tools directory (вспомогательные файлы)\ntools/\n")
            print("✅ Обновлен .gitignore")
        else:
            print("ℹ️ .gitignore уже содержит tools/")

def create_readme():
    """Создает README.md в корне"""
    readme_content = """# 🤖 CardBot - Telegram Bot

## 📁 Структура проекта

### Основные файлы
- `main.py` - главный файл бота
- `requirements.txt` - зависимости Python
- `amvera.yml` - конфигурация для Amvera
- `config.py` - конфигурация бота

### Основные папки
- `modules/` - модули бота (AI, карты дня, рефлексия)
- `database/` - база данных и схемы
- `cards/` - изображения карт дня
- `data/` - данные пользователей

### Вспомогательные файлы
Все вспомогательные файлы (тесты, деплой, миграции, документация) находятся в папке `tools/`.

## 🚀 Запуск

```bash
python main.py
```

## 📚 Документация

Подробная документация находится в папке `tools/`.
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("✅ Создан README.md")

def main():
    """Основная функция"""
    print("🚀 РЕОРГАНИЗАЦИЯ ПРОЕКТА CARDBOT")
    print("=" * 50)
    
    # Создаем папку tools/
    create_tools_directory()
    
    # Перемещаем файлы по категориям
    print("\n📁 Перемещение файлов...")
    move_test_files()
    move_check_files()
    move_debug_files()
    move_deploy_files()
    move_migrate_files()
    move_analysis_files()
    move_documentation()
    move_backup_directories()
    move_temporary_files()
    
    # Обновляем конфигурацию
    print("\n⚙️ Обновление конфигурации...")
    update_gitignore()
    create_readme()
    
    print("\n🎉 РЕОРГАНИЗАЦИЯ ЗАВЕРШЕНА!")
    print("\n📋 Что сделано:")
    print("✅ Создана папка tools/")
    print("✅ Перемещены все вспомогательные файлы")
    print("✅ Обновлен .gitignore")
    print("✅ Создан README.md")
    print("\n🚀 Теперь в корне остались только файлы, необходимые для бота!")
    print("📁 Все вспомогательные файлы находятся в tools/")

if __name__ == "__main__":
    main()
