#!/usr/bin/env python3
"""
Простой тест логики проверки подписки
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import Database

def test():
    print("🧪 Простой тест логики проверки подписки...")
    
    # Инициализируем БД
    db = Database("database/test_simple.db")
    
    # Тестовый пользователь
    test_user_id = 999999999
    
    print(f"📊 Тестируем логику для пользователя {test_user_id}")
    
    # 1. Проверяем, что пользователь еще не завершил сценарий
    has_completed = db.has_completed_scenario_first_time(test_user_id, 'card_of_day')
    print(f"✅ До завершения сценария: {has_completed} (ожидается False)")
    
    if has_completed:
        print("❌ Ошибка: пользователь не должен был завершить сценарий")
        return False
    
    # 2. Симулируем завершение сценария
    print(f"\n📊 Симулируем завершение сценария 'Карта дня'")
    
    session_id = db.start_user_scenario(test_user_id, 'card_of_day')
    print(f"✅ Сценарий начат с session_id: {session_id}")
    
    # Завершаем сценарий
    db.complete_user_scenario(test_user_id, 'card_of_day', session_id)
    print("✅ Сценарий 'Карта дня' завершен")
    
    # 3. Проверяем, что пользователь теперь завершил сценарий
    has_completed = db.has_completed_scenario_first_time(test_user_id, 'card_of_day')
    print(f"✅ После завершения: {has_completed} (ожидается True)")
    
    if not has_completed:
        print("❌ Ошибка: пользователь должен был завершить сценарий")
        return False
    
    print("\n✅ Тестирование завершено успешно!")
    return True

if __name__ == "__main__":
    test()
