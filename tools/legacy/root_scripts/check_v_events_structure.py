#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def check_v_events_structure():
    """Проверяет структуру v_events и данные в ней."""
    db_path = "bot (10).db"
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return
    
    print(f"📁 База данных: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print('\n=== СТРУКТУРА v_events ===')
    try:
        cursor = conn.execute("PRAGMA table_info(v_events)")
        columns = cursor.fetchall()
        if columns:
            print('✅ Структура v_events:')
            for col in columns:
                print(f'  {col["name"]}: {col["type"]}')
        else:
            print('❌ Не удалось получить структуру v_events')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    print('\n=== ДАННЫЕ В v_events ЗА СЕГОДНЯ ===')
    try:
        cursor = conn.execute("""
            SELECT 
                event,
                COUNT(*) as total_count,
                COUNT(DISTINCT session_id) as unique_sessions,
                COUNT(DISTINCT user_id) as unique_users
            FROM v_events 
            WHERE d_local = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            GROUP BY event
            ORDER BY total_count DESC
        """)
        rows = cursor.fetchall()
        if rows:
            print('✅ События в v_events за сегодня:')
            for row in rows:
                print(f'  {row["event"]}: {row["total_count"]} событий, {row["unique_sessions"]} сессий, {row["unique_users"]} пользователей')
        else:
            print('❌ Нет данных в v_events за сегодня')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    print('\n=== ПРОВЕРКА session_id В v_events ===')
    try:
        cursor = conn.execute("""
            SELECT 
                session_id,
                COUNT(*) as count
            FROM v_events 
            WHERE d_local = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            GROUP BY session_id
            ORDER BY count DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        if rows:
            print('✅ session_id в v_events:')
            for row in rows:
                print(f'  {row["session_id"]}: {row["count"]} событий')
        else:
            print('❌ Нет session_id в v_events')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    print('\n=== СРАВНЕНИЕ С scenario_logs ===')
    try:
        cursor = conn.execute("""
            SELECT 
                step,
                COUNT(*) as total_count,
                COUNT(DISTINCT JSON_EXTRACT(metadata, '$.session_id')) as unique_sessions,
                COUNT(DISTINCT user_id) as unique_users
            FROM scenario_logs 
            WHERE DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            AND user_id NOT IN (SELECT user_id FROM ignored_users)
            GROUP BY step
            ORDER BY total_count DESC
        """)
        rows = cursor.fetchall()
        if rows:
            print('✅ События в scenario_logs за сегодня (без админов):')
            for row in rows:
                print(f'  {row["step"]}: {row["total_count"]} событий, {row["unique_sessions"]} сессий, {row["unique_users"]} пользователей')
        else:
            print('❌ Нет данных в scenario_logs за сегодня')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    conn.close()

if __name__ == "__main__":
    check_v_events_structure()

