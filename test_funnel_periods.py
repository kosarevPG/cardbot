#!/usr/bin/env python3
"""
Тестирование воронки с разными периодами
"""

import sqlite3
import os

DB_PATH = "database/dev.db"

def test_funnel_periods():
    if not os.path.exists(DB_PATH):
        print("❌ База данных не найдена")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        periods = [1, 7, 30]
        
        for days in periods:
            print(f"\n📊 ВОРОНКА 'КАРТА ДНЯ' (за {days} {'день' if days == 1 else 'дней'})")
            print("=" * 60)
            
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
                    AND timestamp >= datetime('now', '-{days} days')
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
                print(f"🚨 ПОТЕРИ:")
                if steps_data['started'] - steps_data['initial_resource_selected'] > 0:
                    print(f"  • Шаг 1→2: {steps_data['started'] - steps_data['initial_resource_selected']} ({((steps_data['started'] - steps_data['initial_resource_selected']) / steps_data['started'] * 100):.1f}%)")
                if steps_data['initial_resource_selected'] - steps_data['request_type_selected'] > 0:
                    print(f"  • Шаг 2→3: {steps_data['initial_resource_selected'] - steps_data['request_type_selected']} ({((steps_data['initial_resource_selected'] - steps_data['request_type_selected']) / steps_data['started'] * 100):.1f}%)")
                if steps_data['request_type_selected'] - steps_data['card_drawn'] > 0:
                    print(f"  • Шаг 3→4: {steps_data['request_type_selected'] - steps_data['card_drawn']} ({((steps_data['request_type_selected'] - steps_data['card_drawn']) / steps_data['started'] * 100):.1f}%)")
                if steps_data['card_drawn'] - steps_data['initial_response_provided'] > 0:
                    print(f"  • Шаг 4→5: {steps_data['card_drawn'] - steps_data['initial_response_provided']} ({((steps_data['card_drawn'] - steps_data['initial_response_provided']) / steps_data['started'] * 100):.1f}%)")
                if steps_data['initial_response_provided'] - steps_data['ai_reflection_choice'] > 0:
                    print(f"  • Шаг 5→6: {steps_data['initial_response_provided'] - steps_data['ai_reflection_choice']} ({((steps_data['initial_response_provided'] - steps_data['ai_reflection_choice']) / steps_data['started'] * 100):.1f}%)")
                if steps_data['ai_reflection_choice'] - steps_data['completed'] > 0:
                    print(f"  • Шаг 6→7: {steps_data['ai_reflection_choice'] - steps_data['completed']} ({((steps_data['ai_reflection_choice'] - steps_data['completed']) / steps_data['started'] * 100):.1f}%)")
            else:
                print(f"\n✅ Нет данных за {days} {'день' if days == 1 else 'дней'}")
        
        print(f"\n🎯 РЕКОМЕНДАЦИИ:")
        print(f"  • Используйте 'Сегодня' для оперативного мониторинга")
        print(f"  • Используйте '7 дней' для еженедельного анализа")
        print(f"  • Используйте '30 дней' для долгосрочных трендов")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_funnel_periods() 