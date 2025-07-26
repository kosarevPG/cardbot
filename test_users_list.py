#!/usr/bin/env python3
"""
Тестирование функциональности списка пользователей
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import Database

def test_users_list_functionality():
    """Тестирует функциональность списка пользователей"""
    print("🧪 ТЕСТИРОВАНИЕ СПИСКА ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 60)
    
    try:
        db = Database('database/dev.db')
        
        print("👥 Получение всех пользователей...")
        all_users = db.get_all_users()
        print(f"✅ Всего пользователей в БД: {len(all_users)}")
        
        # Получаем список исключаемых пользователей
        try:
            from config_local import NO_LOGS_USERS
        except ImportError:
            from config import NO_LOGS_USERS
        
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        filtered_users = [uid for uid in all_users if uid not in excluded_users]
        print(f"✅ Пользователей после исключения: {len(filtered_users)}")
        
        if filtered_users:
            print(f"\n📋 Детальная информация о пользователях:")
            for i, uid in enumerate(filtered_users[:10], 1):  # Показываем первые 10
                user_data = db.get_user(uid)
                if user_data:
                    name = user_data.get("name", "Без имени")
                    username = user_data.get("username", "")
                    username_display = f"@{username}" if username else "без username"
                    
                    # Получаем последнее действие
                    user_actions = db.get_actions(uid)
                    last_action_time = "Нет действий"
                    if user_actions:
                        last_action = user_actions[-1]
                        raw_timestamp = last_action.get("timestamp")
                        try:
                            from datetime import datetime
                            if isinstance(raw_timestamp, datetime):
                                last_action_time = raw_timestamp.strftime("%Y-%m-%d %H:%M")
                            elif isinstance(raw_timestamp, str):
                                last_action_dt = datetime.fromisoformat(raw_timestamp.replace('Z', '+00:00'))
                                last_action_time = last_action_dt.strftime("%Y-%m-%d %H:%M")
                        except:
                            last_action_time = "Ошибка даты"
                    
                    print(f"\n{i}. ID: {uid}")
                    print(f"   Имя: {name}")
                    print(f"   Username: {username_display}")
                    print(f"   Последнее действие: {last_action_time}")
                    print(f"   {'─' * 40}")
        else:
            print("Пока нет пользователей для отображения")
        
        print(f"\n✅ ПРОВЕРКА ЗАВЕРШЕНА УСПЕШНО!")
        print(f"\n📋 ИНСТРУКЦИЯ ДЛЯ ТЕСТИРОВАНИЯ В БОТЕ:")
        print(f"1. Отправьте команду /admin")
        print(f"2. Нажмите кнопку '👥 Пользователи'")
        print(f"3. Нажмите кнопку '📋 Список пользователей'")
        print(f"4. Проверьте отображение списка пользователей")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_users_list_functionality() 