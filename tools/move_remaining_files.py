#!/usr/bin/env python3
"""
Скрипт для перемещения оставшихся файлов, которые не были перемещены первым скриптом
"""

import os
import shutil
import glob

def move_remaining_files():
    """Перемещает оставшиеся вспомогательные файлы"""
    print("🔧 Перемещение оставшихся файлов...")
    
    # Файлы, которые нужно переместить
    files_to_move = [
        "quick_deploy.py",
        "force_amvera_rebuild.py", 
        "simple_test.py",
        "push_fix.py",
        "fix_deploy.bat",
        "fix_amvera_deploy.py",
        "ection && git push origin master",
        "rollback_production.py",
        "monitor_deployment.py",
        "monitor_production_deployment.py",
        "direct_db_analysis.py",
        "final_comparison.py",
        "find_specific_action.py",
        "fix_table_structure.py",
        "deduplicate_requests.py",
        "db_web_client.py",
        "compare_logics.py",
        "create_user_requests_table.py",
        "calculate_dau_from_user_scenarios.py",
        "add_initial_response.py",
        "add_missing_requests.py",
        "advanced_db_client.py",
        "et --hard c3ffc63",
        "how c3ffc63 --oneline",
        "secure_sqlite_web.py",
        "security_analysis.py",
        "security_monitor_realtime.py",
        "connect_to_production_db.py",
        "authenticated_db_client.py",
        "simple_db_check.py",
        "security_monitor.log",
        "security_monitor.sql",
        "quick_period_test.py",
        "quick_funnel_check.py",
        "init_production.py",
        "quick_check_dump.py",
        "view_scenario_data.py"
    ]
    
    moved_count = 0
    for file_path in files_to_move:
        if os.path.exists(file_path):
            try:
                dest = f"tools/{file_path}"
                shutil.move(file_path, dest)
                print(f"✅ Перемещен: {file_path} → tools/")
                moved_count += 1
            except Exception as e:
                print(f"❌ Ошибка при перемещении {file_path}: {e}")
    
    print(f"\n📊 Перемещено файлов: {moved_count}")
    return moved_count

def check_final_structure():
    """Проверяет финальную структуру проекта"""
    print("\n🔍 Проверка финальной структуры...")
    
    # Файлы, которые ДОЛЖНЫ остаться в корне
    required_files = [
        "main.py",
        "requirements.txt", 
        "amvera.yml",
        "config.py",
        "config_local.py",
        "README.md",
        ".gitignore",
        "pyproject.toml",
        "uv.lock",
        ".replit"
    ]
    
    # Папки, которые ДОЛЖНЫ остаться в корне
    required_dirs = [
        "modules",
        "database", 
        "cards",
        "data",
        "config",
        ".github"
    ]
    
    print("\n📁 Файлы в корне:")
    root_files = [f for f in os.listdir(".") if os.path.isfile(f)]
    for file in sorted(root_files):
        if file in required_files:
            print(f"✅ {file} (основной)")
        else:
            print(f"⚠️ {file} (возможно, нужно переместить)")
    
    print("\n📁 Папки в корне:")
    root_dirs = [d for d in os.listdir(".") if os.path.isdir(d)]
    for dir_name in sorted(root_dirs):
        if dir_name in required_dirs:
            print(f"✅ {dir_name}/ (основная)")
        elif dir_name == "tools":
            print(f"📁 {dir_name}/ (вспомогательные файлы)")
        else:
            print(f"⚠️ {dir_name}/ (возможно, нужно переместить)")

def main():
    """Основная функция"""
    print("🔧 ДОРАБОТКА РЕОРГАНИЗАЦИИ ПРОЕКТА")
    print("=" * 50)
    
    # Перемещаем оставшиеся файлы
    moved_count = move_remaining_files()
    
    # Проверяем финальную структуру
    check_final_structure()
    
    print(f"\n🎉 ДОРАБОТКА ЗАВЕРШЕНА!")
    print(f"📁 Перемещено дополнительных файлов: {moved_count}")
    print("\n🚀 Теперь проект должен быть полностью организован!")

if __name__ == "__main__":
    main()
