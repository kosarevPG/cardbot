#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def debug_metrics_mismatch():
    """Отладка несоответствия метрик."""
    db_path = "bot (10).db"
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return
    
    print(f"📁 База данных: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print('\n=== СРАВНЕНИЕ МЕТРИК ===')
    
    # 1. Проверяем card_drawn за сегодня
    print('\n1️⃣ События card_drawn за сегодня:')
    try:
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_cards,
                COUNT(DISTINCT user_id) as unique_users,
                GROUP_CONCAT(DISTINCT user_id) as user_ids
            FROM scenario_logs 
            WHERE DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            AND step = 'card_drawn'
        """)
        row = cursor.fetchone()
        if row:
            print(f'  Всего карт: {row["total_cards"]}')
            print(f'  Уникальных пользователей: {row["unique_users"]}')
            print(f'  ID пользователей: {row["user_ids"]}')
        else:
            print('  ❌ Нет данных')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    # 2. Проверяем card_drawn с исключением админов
    print('\n2️⃣ События card_drawn за сегодня (без админов):')
    try:
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_cards,
                COUNT(DISTINCT user_id) as unique_users,
                GROUP_CONCAT(DISTINCT user_id) as user_ids
            FROM scenario_logs 
            WHERE DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            AND step = 'card_drawn'
            AND user_id NOT IN (171507422, 6682555021)
        """)
        row = cursor.fetchone()
        if row:
            print(f'  Всего карт: {row["total_cards"]}')
            print(f'  Уникальных пользователей: {row["unique_users"]}')
            print(f'  ID пользователей: {row["user_ids"]}')
        else:
            print('  ❌ Нет данных')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    # 3. Проверяем deck_selected за сегодня
    print('\n3️⃣ События deck_selected за сегодня:')
    try:
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_decks,
                COUNT(DISTINCT user_id) as unique_users,
                JSON_EXTRACT(metadata, '$.deck_name') as deck_name,
                COUNT(*) as deck_count
            FROM scenario_logs 
            WHERE DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            AND step = 'deck_selected'
            GROUP BY JSON_EXTRACT(metadata, '$.deck_name')
        """)
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                print(f'  Колода {row["deck_name"]}: {row["deck_count"]} раз')
        else:
            print('  ❌ Нет данных deck_selected (это ожидаемо для старой БД)')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    # 4. Проверяем v_decks_daily
    print('\n4️⃣ VIEW v_decks_daily за сегодня:')
    try:
        cursor = conn.execute("""
            SELECT * FROM v_decks_daily 
            WHERE d_local = DATE('now', '+3 hours')
        """)
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                print(f'  {dict(row)}')
        else:
            print('  ❌ VIEW пустой (это проблема!)')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    # 5. Проверяем воронку напрямую
    print('\n5️⃣ Воронка напрямую (card_drawn):')
    try:
        cursor = conn.execute("""
            SELECT 
                step,
                COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            AND scenario = 'card_of_day'
            AND step IN ('initial_resource_selected', 'request_type_selected', 'card_drawn', 'initial_response_provided', 'ai_reflection_choice', 'completed')
            GROUP BY step
            ORDER BY 
                CASE step
                    WHEN 'initial_resource_selected' THEN 1
                    WHEN 'request_type_selected' THEN 2
                    WHEN 'card_drawn' THEN 3
                    WHEN 'initial_response_provided' THEN 4
                    WHEN 'ai_reflection_choice' THEN 5
                    WHEN 'completed' THEN 6
                END
        """)
        rows = cursor.fetchall()
        for row in rows:
            print(f'  {row["step"]}: {row["count"]}')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    conn.close()

if __name__ == "__main__":
    debug_metrics_mismatch()
