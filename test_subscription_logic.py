#!/usr/bin/env python3
"""
Тестовый скрипт для проверки логики проверки подписки после первого завершения сценария "Карта дня"
"""

import os
import sys
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config_local import TIMEZONE
except ImportError:
    from config import TIMEZONE

from database.db import Database

def test_subscription_logic():
    """Тестирует логику проверки подписки после первого завершения сценария"""
    print("🧪 Тестирование логики проверки подписки...")
    
    # Инициализируем БД
    db_path = "database/test_subscription.db"
    db = Database(db_path)
    
    # Тестовый пользователь
    test_user_id = 123456789
    
    print(f"📊 Тестируем логику для пользователя {test_user_id}")
    
    # 1. Проверяем, что пользователь еще не завершил сценарий "Карта дня"
    has_completed = db.has_completed_scenario_first_time(test_user_id, 'card_of_day')
    print(f"✅ До завершения сценария: {has_completed} (ожидается False)")
    
    if has_completed:
        print("❌ Ошибка: пользователь не должен был завершить сценарий")
        return False
    
    # 2. Симулируем первое завершение сценария "Карта дня"
    print(f"\n📊 Симулируем первое завершение сценария 'Карта дня'")
    
    session_id = db.start_user_scenario(test_user_id, 'card_of_day')
    print(f"✅ Сценарий начат с session_id: {session_id}")
    
    # Логируем шаги
    db.log_scenario_step(test_user_id, 'card_of_day', 'started', {
        'session_id': session_id,
        'today': datetime.now(TIMEZONE).date().isoformat()
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'initial_resource_selected', {
        'resource': '😊 Хорошо',
        'session_id': session_id
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'card_drawn', {
        'card_number': 15,
        'session_id': session_id
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'completed', {
        'card_number': 15,
        'session_id': session_id
    })
    
    # Завершаем сценарий
    db.complete_user_scenario(test_user_id, 'card_of_day', session_id)
    print("✅ Сценарий 'Карта дня' завершен")
    
    # 3. Проверяем, что пользователь теперь завершил сценарий впервые
    has_completed = db.has_completed_scenario_first_time(test_user_id, 'card_of_day')
    print(f"✅ После первого завершения: {has_completed} (ожидается True)")
    
    if not has_completed:
        print("❌ Ошибка: пользователь должен был завершить сценарий впервые")
        return False
    
    # 4. Симулируем второе завершение сценария
    print(f"\n📊 Симулируем второе завершение сценария 'Карта дня'")
    
    session_id_2 = db.start_user_scenario(test_user_id, 'card_of_day')
    db.log_scenario_step(test_user_id, 'card_of_day', 'started', {
        'session_id': session_id_2,
        'today': datetime.now(TIMEZONE).date().isoformat()
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'completed', {
        'card_number': 20,
        'session_id': session_id_2
    })
    
    db.complete_user_scenario(test_user_id, 'card_of_day', session_id_2)
    print("✅ Второй сценарий 'Карта дня' завершен")
    
    # 5. Проверяем, что функция все еще возвращает True (после любого завершения)
    has_completed = db.has_completed_scenario_first_time(test_user_id, 'card_of_day')
    print(f"✅ После второго завершения: {has_completed} (ожидается True - сценарий завершен хотя бы раз)")
    
    if not has_completed:
        print("❌ Ошибка: функция должна возвращать True после любого завершения сценария")
        return False
    
    # 6. Проверяем историю сценариев
    print(f"\n📊 История сценариев пользователя:")
    history = db.get_user_scenario_history(test_user_id, 'card_of_day')
    for scenario in history:
        print(f"  • Статус: {scenario['status']}, Session ID: {scenario['session_id'][:20]}...")
    
    print("\n✅ Тестирование завершено успешно!")
    print(f"📁 Тестовая БД создана: {db_path}")
    
    return True

if __name__ == "__main__":
    test_subscription_logic()
