#!/usr/bin/env python3
"""
Проверка данных в базе
"""

import sqlite3
import os

DB_PATH = "database/dev.db"

def check_db():
    if not os.path.exists(DB_PATH):
        print("❌ База данных не найдена")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Проверяем таблицу scenario_logs
        cursor = conn.execute("SELECT COUNT(*) as count FROM scenario_logs")
        total_logs = cursor.fetchone()['count']
        print(f"📊 Всего записей в scenario_logs: {total_logs}")
        
        if total_logs > 0:
            # Последние записи
            cursor = conn.execute("""
                SELECT scenario, step, user_id, timestamp 
                FROM scenario_logs 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            recent = cursor.fetchall()
            
            print("\n🕒 ПОСЛЕДНИЕ 10 ЗАПИСЕЙ:")
            for record in recent:
                print(f"  • {record['timestamp']} - {record['scenario']} - {record['step']} - user {record['user_id']}")
            
            # Статистика по сценариям
            cursor = conn.execute("""
                SELECT scenario, COUNT(*) as count
                FROM scenario_logs 
                GROUP BY scenario
                ORDER BY count DESC
            """)
            scenarios = cursor.fetchall()
            
            print("\n📈 СТАТИСТИКА ПО СЦЕНАРИЯМ:")
            for scenario in scenarios:
                print(f"  • {scenario['scenario']}: {scenario['count']} записей")
            
            # Статистика по шагам card_of_day
            cursor = conn.execute("""
                SELECT step, COUNT(*) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day'
                GROUP BY step
                ORDER BY count DESC
            """)
            card_steps = cursor.fetchall()
            
            print("\n🎴 ШАГИ КАРТЫ ДНЯ:")
            for step in card_steps:
                print(f"  • {step['step']}: {step['count']}")
        
        # Проверяем другие таблицы
        cursor = conn.execute("SELECT COUNT(*) as count FROM user_actions")
        actions = cursor.fetchone()['count']
        print(f"\n📝 Записей в user_actions: {actions}")
        
        cursor = conn.execute("SELECT COUNT(*) as count FROM users")
        users = cursor.fetchone()['count']
        print(f"👥 Пользователей в users: {users}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db() 