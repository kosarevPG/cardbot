#!/usr/bin/env python3
"""
Скрипт для отката к рабочей версии из резервной копии
"""

import os
import shutil
import subprocess
import sys

def rollback_to_working_version():
    """Откат к рабочей версии из резервной копии"""
    print("🔄 Начинаем откат к рабочей версии...")
    
    backup_dir = "backup_20250729_223246"
    if not os.path.exists(backup_dir):
        print(f"❌ Ошибка: Директория {backup_dir} не найдена")
        return False
    
    # Файлы для восстановления
    files_to_restore = [
        ("main.py", "main.py"),
        ("modules/card_of_the_day.py", "modules/card_of_the_day.py"),
        ("modules/evening_reflection.py", "modules/evening_reflection.py"),
        ("modules/ai_service.py", "modules/ai_service.py"),
        ("modules/user_management.py", "modules/user_management.py"),
        ("database/db.py", "database/db.py"),
        ("config.py", "config.py")
    ]
    
    restored_files = []
    
    for backup_file, target_file in files_to_restore:
        backup_path = os.path.join(backup_dir, backup_file)
        if os.path.exists(backup_path):
            try:
                # Создаем резервную копию текущего файла
                if os.path.exists(target_file):
                    backup_current = f"{target_file}.backup_before_rollback"
                    shutil.copy2(target_file, backup_current)
                    print(f"📦 Создана резервная копия: {backup_current}")
                
                # Восстанавливаем файл
                shutil.copy2(backup_path, target_file)
                restored_files.append(target_file)
                print(f"✅ Восстановлен: {target_file}")
                
            except Exception as e:
                print(f"❌ Ошибка при восстановлении {target_file}: {e}")
                return False
        else:
            print(f"⚠️  Файл {backup_path} не найден, пропускаем")
    
    print(f"✅ Восстановлено {len(restored_files)} файлов")
    
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
    
    # Команды для деплоя отката
    commands = [
        "git add .",
        "git commit -m 'Rollback to working version from backup'",
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
    
    print("🎉 Откат завершен успешно!")
    print("📝 Проверьте логи в продакшене через несколько минут")
    return True

if __name__ == "__main__":
    success = rollback_to_working_version()
    sys.exit(0 if success else 1) 