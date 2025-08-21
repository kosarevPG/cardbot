#!/usr/bin/env python3
"""
Скрипт для очистки проекта перед деплоем на Amvera
Удаляет большие файлы и папки, которые не нужны для работы бота
"""

import os
import shutil
import glob

def cleanup_project():
    """Очищает проект от ненужных файлов"""
    
    print("🧹 Начинаю очистку проекта для деплоя...")
    
    # Список папок для удаления
    folders_to_remove = [
        "tools",
        "__pycache__",
        ".pytest_cache",
        ".coverage",
        "htmlcov"
    ]
    
    # Список файлов для удаления
    files_to_remove = [
        "*.db",
        "*.log",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.so",
        "*.egg",
        "*.egg-info"
    ]
    
    # Удаляем папки
    for folder in folders_to_remove:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"✅ Удалена папка: {folder}")
            except Exception as e:
                print(f"❌ Ошибка удаления папки {folder}: {e}")
    
    # Удаляем файлы по паттернам
    for pattern in files_to_remove:
        for file_path in glob.glob(pattern, recursive=True):
            try:
                os.remove(file_path)
                print(f"✅ Удален файл: {file_path}")
            except Exception as e:
                print(f"❌ Ошибка удаления файла {file_path}: {e}")
    
    # Удаляем базы данных из папки database
    db_folder = "database"
    if os.path.exists(db_folder):
        for file_path in glob.glob(os.path.join(db_folder, "*.db")):
            try:
                os.remove(file_path)
                print(f"✅ Удалена БД: {file_path}")
            except Exception as e:
                print(f"❌ Ошибка удаления БД {file_path}: {e}")
    
    print("\n🎉 Очистка завершена!")
    
    # Показываем новый размер
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk("."):
        if ".git" in root:
            continue
        for file in files:
            try:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
                file_count += 1
            except:
                pass
    
    size_mb = total_size / (1024 * 1024)
    print(f"📊 Новый размер проекта: {size_mb:.2f} MB ({file_count} файлов)")

if __name__ == "__main__":
    cleanup_project()
