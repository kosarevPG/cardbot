#!/usr/bin/env python3
"""
Скрипт для восстановления и рефакторинга main.py.
Запускать из корня проекта: python REBUILD_MAIN.py
"""
import os

# Устанавливаем рабочую директорию
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

print(f"Рабочая директория: {os.getcwd()}")
print("=" * 80)
print("ВОССТАНОВЛЕНИЕ И РЕФАКТОРИНГ main.py")
print("=" * 80)
print()

# Читаем исходный файл
source_file = "main (actual).py"
target_file = "main.py"

print(f"[1/5] Чтение {source_file}...")
with open(source_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f"✅ Прочитано {len(lines)} строк")

# Находим ключевые строки
import_line = None
admin_start = None
admin_end = None

for i, line in enumerate(lines):
    if "from modules.marketplace_commands import" in line:
        import_line = i
    # ИСПРАВЛЕНИЕ: Ищем make_admin_handler, а НЕ make_admin_user_profile_handler
    if line.strip() == "def make_admin_handler(db: Database, logger_service: LoggingService):":
        admin_start = i
    if line.strip().startswith("async def handle_admin_text_input(message: types.Message"):
        admin_end = i

print(f"\n[2/5] Анализ структуры...")
print(f"   Точка вставки импортов: строка {import_line + 1}")
print(f"   Начало админских функций: строка {admin_start + 1}")
print(f"   Конец админских функций: строка {admin_end + 1}")
print(f"   Удаляется строк: {admin_end - admin_start}")

# Создаём новый контент
new_lines = []

# Часть 1: До точки вставки импортов
new_lines.extend(lines[:import_line + 1])

# Вставляем новые импорты
new_imports = """
# Модули покупки и обучения
from modules.purchase_menu import handle_purchase_menu, handle_purchase_callbacks, get_purchase_menu
from modules.learn_cards import register_learn_cards_handlers, start_learning

# Админская панель (рефакторинг - модульная структура)
from modules.admin import (
    make_admin_handler,
    make_admin_callback_handler,
    show_admin_main_menu,
    make_admin_user_profile_handler
)
"""
new_lines.append(new_imports)
print(f"\n[3/5] Добавлены импорты")

# Часть 2: От точки вставки до начала админских функций
new_lines.extend(lines[import_line + 1:admin_start])

# Комментарий о рефакторинге
refactor_comment = """
# =============================================================================
# АДМИНСКИЕ ПАНЕЛЬНЫЕ ФУНКЦИИ ПЕРЕНЕСЕНЫ В modules/admin/
# Удалено ~1590 строк кода для улучшения структуры проекта.
# Все функции теперь импортируются из модулей:
# - modules/admin/core.py - основные обработчики и роутинг callback'ов
# - modules/admin/dashboard.py - дашборды и метрики (dashboard, retention, funnel, value, decks, reflections, logs)
# - modules/admin/users.py - управление пользователями (users, users_list, requests)
# - modules/admin/posts.py - управление постами и рассылками
# =============================================================================

"""
new_lines.append(refactor_comment)
print(f"[4/5] Удалены админские функции ({admin_end - admin_start} строк)")

# Часть 3: После админских функций
new_lines.extend(lines[admin_end:])

# Записываем
with open(target_file, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"\n[5/5] Записан {target_file}")
print(f"   Было строк: {len(lines)}")
print(f"   Стало строк: {len(new_lines)}")
print(f"   Уменьшение: {len(lines) - len(new_lines)} строк")

print("\n" + "=" * 80)
print("✅ УСПЕШНО ЗАВЕРШЕНО!")
print("=" * 80)
print("\nФайл main.py создан и готов к использованию.")
print("Следующий шаг: добавить регистрацию обработчиков для learn_cards")
print()

