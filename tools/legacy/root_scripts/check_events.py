#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def check_events():
    """Проверяет события в scenario_logs."""
    db_path = "bot (8).db"
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return
    
    print(f"📁 База данных: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print('\n=== ВСЕ СОБЫТИЯ ЗА СЕГОДНЯ ===')
    try:
        cursor = conn.execute("""
            SELECT step, COUNT(*) as count
            FROM scenario_logs 
            WHERE DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            GROUP BY step
            ORDER BY count DESC
        """)
        rows = cursor.fetchall()
        for row in rows:
            print(f'  {row["step"]}: {row["count"]}')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    print('\n=== МЕТАДАННЫЕ С СЕГОДНЯ (содержащие deck) ===')
    try:
        cursor = conn.execute("""
            SELECT step, metadata
            FROM scenario_logs 
            WHERE DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            AND metadata LIKE '%deck%'
            LIMIT 5
        """)
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                print(f'  {row["step"]}: {row["metadata"]}')
        else:
            print('❌ Нет метаданных с deck')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    print('\n=== ПОСЛЕДНИЕ 5 СОБЫТИЙ СЕГОДНЯ ===')
    try:
        cursor = conn.execute("""
            SELECT step, metadata, timestamp
            FROM scenario_logs 
            WHERE DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        for row in rows:
            print(f'  {row["timestamp"]} | {row["step"]}: {row["metadata"]}')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    conn.close()

if __name__ == "__main__":
    check_events()
