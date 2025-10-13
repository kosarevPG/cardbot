#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def debug_session_id():
    """Отладка session_id в v_events."""
    db_path = "bot (10).db"
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return
    
    print(f"📁 База данных: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print('\n=== ПРОВЕРКА session_id В v_events ===')
    try:
        cursor = conn.execute("""
            SELECT 
                event,
                session_id,
                COUNT(*) as count
            FROM v_events 
            WHERE d_local = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            GROUP BY event, session_id
            ORDER BY event, count DESC
        """)
        rows = cursor.fetchall()
        if rows:
            print('✅ session_id в v_events:')
            for row in rows:
                print(f'  {row["event"]} | {row["session_id"]}: {row["count"]} событий')
        else:
            print('❌ Нет данных в v_events')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    print('\n=== ПРОВЕРКА session_id В scenario_logs ===')
    try:
        cursor = conn.execute("""
            SELECT 
                step,
                JSON_EXTRACT(metadata, '$.session_id') as session_id,
                COUNT(*) as count
            FROM scenario_logs 
            WHERE DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            AND user_id NOT IN (SELECT user_id FROM ignored_users)
            GROUP BY step, JSON_EXTRACT(metadata, '$.session_id')
            ORDER BY step, count DESC
        """)
        rows = cursor.fetchall()
        if rows:
            print('✅ session_id в scenario_logs (без админов):')
            for row in rows:
                print(f'  {row["step"]} | {row["session_id"]}: {row["count"]} событий')
        else:
            print('❌ Нет данных в scenario_logs')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    print('\n=== ТЕСТ ЗАПРОСА ФУНКЦИИ ===')
    try:
        # Тест запроса из функции с v_events
        print('Тест с v_events:')
        cursor = conn.execute("""
            SELECT 
                event,
                COUNT(DISTINCT session_id) as count
            FROM v_events
            WHERE scenario = 'card_of_day' AND d_local = date('now', '+3 hours')
            GROUP BY event
        """)
        rows = cursor.fetchall()
        for row in rows:
            print(f'  {row["event"]}: {row["count"]} уникальных сессий')
    except Exception as e:
        print(f'❌ Ошибка в запросе v_events: {e}')
    
    try:
        # Тест запроса из функции с scenario_logs
        print('\nТест с scenario_logs:')
        cursor = conn.execute("""
            SELECT 
                step,
                COUNT(DISTINCT JSON_EXTRACT(metadata, '$.session_id')) as count
            FROM scenario_logs
            WHERE scenario = 'card_of_day' AND DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            GROUP BY step
        """)
        rows = cursor.fetchall()
        for row in rows:
            print(f'  {row["step"]}: {row["count"]} уникальных сессий')
    except Exception as e:
        print(f'❌ Ошибка в запросе scenario_logs: {e}')
    
    conn.close()

if __name__ == "__main__":
    debug_session_id()

