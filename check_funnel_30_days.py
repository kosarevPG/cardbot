#!/usr/bin/env python3
"""
Проверка воронки за 30 дней
"""

import sqlite3
import os

DB_PATH = "database/dev.db"

def check_funnel_30_days():
    if not os.path.exists(DB_PATH):
        print("❌ База данных не найдена")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        print("📊 ВОРОНКА 'КАРТА ДНЯ' (за 30 дней)")
        print("=" * 50)
        
        # Основные шаги воронки
        steps_data = {}
        step_names = {
            'started': '1️⃣ Начали сессию',
            'initial_resource_selected': '2️⃣ Выбрали ресурс', 
            'request_type_selected': '3️⃣ Выбрали тип запроса',
            'card_drawn': '4️⃣ Вытянули карту',
            'initial_response_provided': '5️⃣ Написали ассоциацию',
            'ai_reflection_choice': '6️⃣ Выбрали диалог',
            'completed': '7️⃣ Завершили'
        }
        
        for step_name in step_names.keys():
            cursor = conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = ?
                AND timestamp >= datetime('now', '-30 days')
            """, (step_name,))
            count = cursor.fetchone()['count']
            steps_data[step_name] = count
        
        # Выводим воронку
        for step, count in steps_data.items():
            print(f"  {step_names[step]}: {count}")
        
        # Конверсия
        if steps_data['started'] > 0:
            conversion = (steps_data['completed'] / steps_data['started']) * 100
            print(f"\n✅ КОНВЕРСИЯ: {steps_data['completed']}/{steps_data['started']} = {conversion:.1f}%")
            
            # Анализ потерь
            print(f"\n🚨 АНАЛИЗ ПОТЕРЬ:")
            print(f"  • Шаг 1→2: {steps_data['started'] - steps_data['initial_resource_selected']} ({((steps_data['started'] - steps_data['initial_resource_selected']) / steps_data['started'] * 100):.1f}%)")
            print(f"  • Шаг 2→3: {steps_data['initial_resource_selected'] - steps_data['request_type_selected']} ({((steps_data['initial_resource_selected'] - steps_data['request_type_selected']) / steps_data['started'] * 100):.1f}%)")
            print(f"  • Шаг 3→4: {steps_data['request_type_selected'] - steps_data['card_drawn']} ({((steps_data['request_type_selected'] - steps_data['card_drawn']) / steps_data['started'] * 100):.1f}%)")
            print(f"  • Шаг 4→5: {steps_data['card_drawn'] - steps_data['initial_response_provided']} ({((steps_data['card_drawn'] - steps_data['initial_response_provided']) / steps_data['started'] * 100):.1f}%)")
            print(f"  • Шаг 5→6: {steps_data['initial_response_provided'] - steps_data['ai_reflection_choice']} ({((steps_data['initial_response_provided'] - steps_data['ai_reflection_choice']) / steps_data['started'] * 100):.1f}%)")
            print(f"  • Шаг 6→7: {steps_data['ai_reflection_choice'] - steps_data['completed']} ({((steps_data['ai_reflection_choice'] - steps_data['completed']) / steps_data['started'] * 100):.1f}%)")
        
        # Дополнительные метрики
        print(f"\n🔍 ДОПОЛНИТЕЛЬНЫЕ МЕТРИКИ:")
        
        # Текстовые запросы
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'text_request_provided'
            AND timestamp >= datetime('now', '-30 days')
        """)
        text_requests = cursor.fetchone()['count']
        print(f"  • Написали текстовый запрос: {text_requests}")
        
        # AI ответы
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'ai_response_1_provided'
            AND timestamp >= datetime('now', '-30 days')
        """)
        ai_response_1 = cursor.fetchone()['count']
        print(f"  • Получили AI ответ 1: {ai_response_1}")
        
        # Изменение настроения
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'mood_change_recorded'
            AND timestamp >= datetime('now', '-30 days')
        """)
        mood_change = cursor.fetchone()['count']
        print(f"  • Записали изменение настроения: {mood_change}")
        
        # Оценка полезности
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'usefulness_rating'
            AND timestamp >= datetime('now', '-30 days')
        """)
        usefulness_rating = cursor.fetchone()['count']
        print(f"  • Оценили полезность: {usefulness_rating}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_funnel_30_days() 