#!/usr/bin/env python3
"""
Скрипт для тестирования системы логирования сценариев
"""

import os
import sys
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config_local import TIMEZONE
except ImportError:
    from config import TIMEZONE

from database.db import Database

def test_scenario_logging():
    """Тестирует систему логирования сценариев"""
    print("🧪 Тестирование системы логирования сценариев...")
    
    # Инициализируем БД
    db_path = "database/test_scenario.db"
    db = Database(db_path)
    
    # Тестовый пользователь
    test_user_id = 123456789
    
    print(f"📊 Тестируем сценарий 'Карта дня' для пользователя {test_user_id}")
    
    # Симулируем сценарий "Карта дня"
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
        'session_id': session_id,
        'user_request': 'Как улучшить отношения с коллегами?'
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'initial_response_provided', {
        'session_id': session_id,
        'response_length': 45
    })
    
    # Завершаем сценарий
    db.complete_user_scenario(test_user_id, 'card_of_day', session_id)
    db.log_scenario_step(test_user_id, 'card_of_day', 'completed', {
        'card_number': 15,
        'session_id': session_id,
        'initial_resource': '😊 Хорошо',
        'final_resource': '😊 Хорошо'
    })
    
    print("✅ Сценарий 'Карта дня' завершен")
    
    # Тестируем сценарий "Вечерняя рефлексия"
    print(f"📊 Тестируем сценарий 'Вечерняя рефлексия' для пользователя {test_user_id}")
    
    session_id_2 = db.start_user_scenario(test_user_id, 'evening_reflection')
    print(f"✅ Сценарий начат с session_id: {session_id_2}")
    
    # Логируем шаги
    db.log_scenario_step(test_user_id, 'evening_reflection', 'started', {
        'session_id': session_id_2,
        'today': datetime.now(TIMEZONE).date().isoformat()
    })
    
    db.log_scenario_step(test_user_id, 'evening_reflection', 'good_moments_provided', {
        'session_id': session_id_2,
        'answer_length': 67
    })
    
    db.log_scenario_step(test_user_id, 'evening_reflection', 'gratitude_provided', {
        'session_id': session_id_2,
        'answer_length': 89
    })
    
    db.log_scenario_step(test_user_id, 'evening_reflection', 'hard_moments_provided', {
        'session_id': session_id_2,
        'answer_length': 123
    })
    
    # Завершаем сценарий
    db.complete_user_scenario(test_user_id, 'evening_reflection', session_id_2)
    db.log_scenario_step(test_user_id, 'evening_reflection', 'completed', {
        'session_id': session_id_2,
        'ai_summary_generated': True,
        'good_moments_length': 67,
        'gratitude_length': 89,
        'hard_moments_length': 123
    })
    
    print("✅ Сценарий 'Вечерняя рефлексия' завершен")
    
    # Тестируем брошенный сценарий
    print(f"📊 Тестируем брошенный сценарий для пользователя {test_user_id}")
    
    session_id_3 = db.start_user_scenario(test_user_id, 'card_of_day')
    db.log_scenario_step(test_user_id, 'card_of_day', 'started', {
        'session_id': session_id_3,
        'today': datetime.now(TIMEZONE).date().isoformat()
    })
    
    # Бросаем сценарий
    db.abandon_user_scenario(test_user_id, 'card_of_day', session_id_3)
    db.log_scenario_step(test_user_id, 'card_of_day', 'abandoned', {
        'session_id': session_id_3,
        'reason': 'user_left'
    })
    
    print("✅ Брошенный сценарий обработан")
    
    # Получаем статистику
    print("\n📈 Получаем статистику...")
    
    card_stats = db.get_scenario_stats('card_of_day', 1)
    reflection_stats = db.get_scenario_stats('evening_reflection', 1)
    
    print(f"🎴 Статистика 'Карта дня' (за 1 день):")
    if card_stats:
        print(f"  • Запусков: {card_stats['total_starts']}")
        print(f"  • Завершений: {card_stats['total_completions']}")
        print(f"  • Брошено: {card_stats['total_abandoned']}")
        print(f"  • Процент завершения: {card_stats['completion_rate']:.1f}%")
        print(f"  • Среднее шагов: {card_stats['avg_steps']}")
    
    print(f"\n🌙 Статистика 'Вечерняя рефлексия' (за 1 день):")
    if reflection_stats:
        print(f"  • Запусков: {reflection_stats['total_starts']}")
        print(f"  • Завершений: {reflection_stats['total_completions']}")
        print(f"  • Брошено: {reflection_stats['total_abandoned']}")
        print(f"  • Процент завершения: {reflection_stats['completion_rate']:.1f}%")
        print(f"  • Среднее шагов: {reflection_stats['avg_steps']}")
    
    # Получаем статистику по шагам
    card_steps = db.get_scenario_step_stats('card_of_day', 1)
    reflection_steps = db.get_scenario_step_stats('evening_reflection', 1)
    
    print(f"\n🎴 Популярные шаги 'Карта дня':")
    for step in card_steps:
        print(f"  • {step['step']}: {step['count']} раз")
    
    print(f"\n🌙 Популярные шаги 'Вечерняя рефлексия':")
    for step in reflection_steps:
        print(f"  • {step['step']}: {step['count']} раз")
    
    # Получаем историю пользователя
    print(f"\n👤 История сценариев пользователя {test_user_id}:")
    user_history = db.get_user_scenario_history(test_user_id)
    for scenario in user_history:
        print(f"  • {scenario['scenario']}: {scenario['status']} (шагов: {scenario['steps_count']})")
    
    # Закрываем соединение
    db.close()
    
    print("\n✅ Тестирование завершено успешно!")
    print(f"📁 Тестовая БД создана: {db_path}")

if __name__ == "__main__":
    test_scenario_logging() 