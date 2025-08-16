#!/usr/bin/env python3
"""
Быстрая проверка воронки карты дня
"""

import sqlite3
import os

DB_PATH = "database/dev.db"

def quick_check():
    if not os.path.exists(DB_PATH):
        print("❌ База данных не найдена")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Все шаги
        cursor = conn.execute("""
            SELECT step, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND timestamp >= datetime('now', '-7 days')
            GROUP BY step
            ORDER BY count DESC
        """)
        
        steps = cursor.fetchall()
        
        print("📊 ВСЕ ШАГИ ВОРОНКИ (за 7 дней):")
        for step in steps:
            print(f"  • {step['step']}: {step['count']}")
        
        # Основная воронка
        print("\n📈 ОСНОВНАЯ ВОРОНКА:")
        
        steps_data = {}
        for step_name in ['started', 'initial_resource_selected', 'request_type_selected', 'card_drawn', 'initial_response_provided', 'ai_reflection_choice', 'completed']:
            cursor = conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = ?
                AND timestamp >= datetime('now', '-7 days')
            """, (step_name,))
            count = cursor.fetchone()['count']
            steps_data[step_name] = count
        
        step_names = {
            'started': '1️⃣ Начали сессию',
            'initial_resource_selected': '2️⃣ Выбрали ресурс', 
            'request_type_selected': '3️⃣ Выбрали тип запроса',
            'card_drawn': '4️⃣ Вытянули карту',
            'initial_response_provided': '5️⃣ Написали ассоциацию',
            'ai_reflection_choice': '6️⃣ Выбрали диалог',
            'completed': '7️⃣ Завершили'
        }
        
        for step, count in steps_data.items():
            print(f"  {step_names[step]}: {count}")
        
        # Конверсия
        if steps_data['started'] > 0:
            conversion = (steps_data['completed'] / steps_data['started']) * 100
            print(f"\n✅ КОНВЕРСИЯ: {steps_data['completed']}/{steps_data['started']} = {conversion:.1f}%")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    quick_check() 