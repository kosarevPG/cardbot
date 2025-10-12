#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для управления гендерами пользователей в базе данных.
Позволяет просматривать, устанавливать и обновлять пол пользователей.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import Database

def show_users_with_genders(db_path: str):
    """Показывает всех пользователей с их гендерами"""
    db = Database(db_path)
    
    try:
        cursor = db.conn.execute("""
            SELECT user_id, name, username, first_name, gender, first_seen
            FROM users 
            ORDER BY user_id
        """)
        users = cursor.fetchall()
        
        if not users:
            print("Пользователи не найдены.")
            return
        
        print(f"{'ID':<10} {'Имя':<20} {'Username':<20} {'Пол':<8} {'Дата регистрации':<20}")
        print("-" * 80)
        
        for user in users:
            user_id, name, username, first_name, gender, first_seen = user
            display_name = first_name or name or username or "Не указано"
            display_username = username or "Не указан"
            
            print(f"{user_id:<10} {display_name:<20} {display_username:<20} {gender:<8} {first_seen or 'Не указана':<20}")
            
    except Exception as e:
        print(f"Ошибка при получении пользователей: {e}")

def set_user_gender(db_path: str, user_id: int, gender: str):
    """Устанавливает гендер пользователя"""
    if gender not in ['male', 'female', 'neutral']:
        print("Ошибка: гендер должен быть 'male', 'female' или 'neutral'")
        return
    
    db = Database(db_path)
    
    try:
        # Проверяем, существует ли пользователь
        cursor = db.conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            print(f"Пользователь с ID {user_id} не найден.")
            return
        
        # Обновляем гендер
        db.conn.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))
        db.conn.commit()
        
        print(f"✅ Гендер пользователя {user_id} установлен как '{gender}'")
        
    except Exception as e:
        print(f"Ошибка при обновлении гендера: {e}")

def bulk_set_genders(db_path: str):
    """Массовая установка гендеров через интерактивный режим"""
    db = Database(db_path)
    
    try:
        cursor = db.conn.execute("""
            SELECT user_id, name, username, first_name, gender
            FROM users 
            ORDER BY user_id
        """)
        users = cursor.fetchall()
        
        if not users:
            print("Пользователи не найдены.")
            return
        
        print("=== Массовая установка гендеров ===")
        print("Введите гендер для каждого пользователя (male/female/neutral/enter для пропуска):")
        print()
        
        for user in users:
            user_id, name, username, first_name, current_gender = user
            display_name = first_name or name or username or "Не указано"
            
            print(f"ID: {user_id}, Имя: {display_name}, Текущий пол: {current_gender}")
            
            while True:
                gender_input = input("Новый пол (male/female/neutral/enter для пропуска): ").strip().lower()
                
                if not gender_input:  # Enter для пропуска
                    print("Пропущен.")
                    break
                elif gender_input in ['male', 'female', 'neutral']:
                    db.conn.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender_input, user_id))
                    db.conn.commit()
                    print(f"✅ Установлен пол '{gender_input}'")
                    break
                else:
                    print("Неверный ввод. Используйте: male, female, neutral или Enter для пропуска.")
        
        print("Готово!")
        
    except Exception as e:
        print(f"Ошибка при массовой установке: {e}")

def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python manage_user_genders.py <путь_к_бд> [команда] [параметры]")
        print()
        print("Команды:")
        print("  list                    - Показать всех пользователей")
        print("  set <user_id> <gender>  - Установить пол пользователя")
        print("  bulk                    - Массовая установка полов")
        print()
        print("Примеры:")
        print("  python manage_user_genders.py data/bot.db list")
        print("  python manage_user_genders.py data/bot.db set 123456789 female")
        print("  python manage_user_genders.py data/bot.db bulk")
        return
    
    db_path = sys.argv[1]
    
    if not os.path.exists(db_path):
        print(f"Ошибка: База данных {db_path} не найдена.")
        return
    
    if len(sys.argv) == 2:
        # Только путь к БД - показываем список
        show_users_with_genders(db_path)
    elif len(sys.argv) >= 3:
        command = sys.argv[2].lower()
        
        if command == "list":
            show_users_with_genders(db_path)
        elif command == "set" and len(sys.argv) == 5:
            try:
                user_id = int(sys.argv[3])
                gender = sys.argv[4]
                set_user_gender(db_path, user_id, gender)
            except ValueError:
                print("Ошибка: user_id должен быть числом")
        elif command == "bulk":
            bulk_set_genders(db_path)
        else:
            print("Неверная команда или параметры. Используйте 'python manage_user_genders.py' для справки.")

if __name__ == "__main__":
    main()
