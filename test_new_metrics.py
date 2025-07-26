#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новых метрик логирования сценария "Карта дня"
"""

import os
import sys
import json
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config_local import TIMEZONE, DB_PATH
except ImportError:
    from config import TIMEZONE
    DB_PATH = None

from database.db import Database

def test_new_metrics():
    """Тестирует новые метрики логирования"""
    print("🧪 Тестирование новых метрик логирования...")
    
    # Определяем путь к БД
    if DB_PATH and os.path.exists(DB_PATH):
        db_path = DB_PATH
        print(f"📁 Используем dev БД: {db_path}")
    else:
        db_path = "database/dev.db"
        if not os.path.exists(db_path):
            db_path = "database/bot.db"
        print(f"📁 Используем БД: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ БД не найдена: {db_path}")
        return
    
    # Инициализируем БД
    db = Database(db_path)
    
    # Тестовый пользователь
    test_user_id = 999999999
    
    print(f"\n📊 Симулируем полный сценарий 'Карта дня' для пользователя {test_user_id}")
    
    # Симулируем полный сценарий с новыми метриками
    session_id = db.start_user_scenario(test_user_id, 'card_of_day')
    print(f"✅ Сценарий начат с session_id: {session_id}")
    
    # Логируем шаги с новыми метриками
    db.log_scenario_step(test_user_id, 'card_of_day', 'started', {
        'session_id': session_id,
        'today': datetime.now(TIMEZONE).date().isoformat()
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'initial_resource_selected', {
        'resource': '😊 Хорошо',
        'session_id': session_id
    })
    
    # 1. Тип запроса (текстовый)
    db.log_scenario_step(test_user_id, 'card_of_day', 'text_request_provided', {
        'request_length': 45,
        'session_id': session_id
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'card_drawn', {
        'card_number': 25,
        'session_id': session_id,
        'user_request': 'Как улучшить отношения с коллегами?'
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'initial_response_provided', {
        'session_id': session_id,
        'response_length': 67
    })
    
    # 2. Выбор рефлексии с ИИ (да)
    db.log_scenario_step(test_user_id, 'card_of_day', 'ai_reflection_choice', {
        'choice': 'yes',
        'session_id': session_id
    })
    
    # 3. Ответы на ИИ-вопросы
    db.log_scenario_step(test_user_id, 'card_of_day', 'ai_response_1_provided', {
        'response_length': 89,
        'session_id': session_id
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'ai_response_2_provided', {
        'response_length': 123,
        'session_id': session_id
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'ai_response_3_provided', {
        'response_length': 156,
        'session_id': session_id
    })
    
    # 4. Изменение самочувствия (улучшилось)
    db.log_scenario_step(test_user_id, 'card_of_day', 'mood_change_recorded', {
        'initial_resource': '😊 Хорошо',
        'final_resource': '🤩 Отлично',
        'change_direction': 'better',
        'session_id': session_id
    })
    
    # 5. Оценка полезности (помогло)
    db.log_scenario_step(test_user_id, 'card_of_day', 'usefulness_rating', {
        'rating': 'helped',
        'card_number': 25,
        'session_id': session_id
    })
    
    # Завершаем сценарий
    db.complete_user_scenario(test_user_id, 'card_of_day', session_id)
    db.log_scenario_step(test_user_id, 'card_of_day', 'completed', {
        'card_number': 25,
        'session_id': session_id,
        'initial_resource': '😊 Хорошо',
        'final_resource': '🤩 Отлично'
    })
    
    print("✅ Полный сценарий с новыми метриками завершен")
    
    # Тестируем второй сценарий с другими параметрами
    print(f"\n📊 Симулируем второй сценарий с другими параметрами")
    
    session_id_2 = db.start_user_scenario(test_user_id, 'card_of_day')
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'started', {
        'session_id': session_id_2,
        'today': datetime.now(TIMEZONE).date().isoformat()
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'initial_resource_selected', {
        'resource': '😐 Средне',
        'session_id': session_id_2
    })
    
    # Мысленный запрос
    db.log_scenario_step(test_user_id, 'card_of_day', 'request_type_selected', {
        'request_type': 'mental',
        'session_id': session_id_2
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'card_drawn', {
        'card_number': 15,
        'session_id': session_id_2
    })
    
    db.log_scenario_step(test_user_id, 'card_of_day', 'initial_response_provided', {
        'session_id': session_id_2,
        'response_length': 45
    })
    
    # Отказ от ИИ-рефлексии
    db.log_scenario_step(test_user_id, 'card_of_day', 'ai_reflection_choice', {
        'choice': 'no',
        'session_id': session_id_2
    })
    
    # Ухудшение самочувствия
    db.log_scenario_step(test_user_id, 'card_of_day', 'mood_change_recorded', {
        'initial_resource': '😐 Средне',
        'final_resource': '😔 Низко',
        'change_direction': 'worse',
        'session_id': session_id_2
    })
    
    # Оценка "недостаточно глубоко"
    db.log_scenario_step(test_user_id, 'card_of_day', 'usefulness_rating', {
        'rating': 'notdeep',
        'card_number': 15,
        'session_id': session_id_2
    })
    
    db.complete_user_scenario(test_user_id, 'card_of_day', session_id_2)
    db.log_scenario_step(test_user_id, 'card_of_day', 'completed', {
        'card_number': 15,
        'session_id': session_id_2,
        'initial_resource': '😐 Средне',
        'final_resource': '😔 Низко'
    })
    
    print("✅ Второй сценарий завершен")
    
    # Получаем статистику
    print("\n📈 Получаем статистику новых метрик...")
    
    # Проверяем новые метрики
    try:
        cursor = db.conn.execute("""
            SELECT step, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step IN ('text_request_provided', 'request_type_selected', 'ai_reflection_choice', 
                        'ai_response_1_provided', 'ai_response_2_provided', 'ai_response_3_provided',
                        'mood_change_recorded', 'usefulness_rating')
            AND timestamp >= datetime('now', '-1 day')
            GROUP BY step
        """)
        
        new_metrics = cursor.fetchall()
        print(f"\n🎴 Новые метрики (за 1 день):")
        for metric in new_metrics:
            print(f"  • {metric['step']}: {metric['count']} раз")
        
        # Детальный анализ
        print(f"\n📊 Детальный анализ:")
        
        # Тип запроса
        text_req = sum(1 for m in new_metrics if m['step'] == 'text_request_provided')
        mental_req = sum(1 for m in new_metrics if m['step'] == 'request_type_selected')
        print(f"  📝 Запросы: {text_req} текстовых, {mental_req} мысленных")
        
        # ИИ-рефлексия
        ai_yes = sum(1 for m in new_metrics if m['step'] == 'ai_reflection_choice')
        print(f"  🤖 ИИ-рефлексия: {ai_yes} выборов")
        
        # Ответы на ИИ-вопросы
        ai_1 = sum(1 for m in new_metrics if m['step'] == 'ai_response_1_provided')
        ai_2 = sum(1 for m in new_metrics if m['step'] == 'ai_response_2_provided')
        ai_3 = sum(1 for m in new_metrics if m['step'] == 'ai_response_3_provided')
        print(f"  💬 ИИ-ответы: {ai_1}→{ai_2}→{ai_3}")
        
        # Самочувствие
        mood_changes = sum(1 for m in new_metrics if m['step'] == 'mood_change_recorded')
        print(f"  😊 Изменения самочувствия: {mood_changes}")
        
        # Оценки
        ratings = sum(1 for m in new_metrics if m['step'] == 'usefulness_rating')
        print(f"  ⭐ Оценки полезности: {ratings}")
        
    except Exception as e:
        print(f"❌ Ошибка при анализе новых метрик: {e}")
    
    # Закрываем соединение
    db.close()
    
    print("\n✅ Тестирование новых метрик завершено!")

if __name__ == "__main__":
    test_new_metrics() 