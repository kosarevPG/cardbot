#!/usr/bin/env python3
"""
Быстрая проверка периодов воронки
"""

import sqlite3
import os

DB_PATH = "database/dev.db"

def quick_test():
    if not os.path.exists(DB_PATH):
        print("❌ База данных не найдена")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        print("📊 ТЕСТ ВОРОНКИ ПО ПЕРИОДАМ")
        print("=" * 40)
        
        for days in [1, 7, 30]:
            cursor = conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = 'started'
                AND timestamp >= datetime('now', '-{days} days')
            """)
            started = cursor.fetchone()['count']
            
            cursor = conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = 'completed'
                AND timestamp >= datetime('now', '-{days} days')
            """)
            completed = cursor.fetchone()['count']
            
            period_name = {1: "Сегодня", 7: "7 дней", 30: "30 дней"}[days]
            conversion = (completed / started * 100) if started > 0 else 0
            
            print(f"{period_name}: {completed}/{started} = {conversion:.1f}%")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    quick_test() 