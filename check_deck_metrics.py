#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def check_deck_metrics():
    """Проверяет метрики колод."""
    db_path = "bot (8).db"
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return
    
    print(f"📁 База данных: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print('\n=== ПРОВЕРКА v_decks_daily ===')
    try:
        cursor = conn.execute('SELECT * FROM v_decks_daily LIMIT 5')
        rows = cursor.fetchall()
        if rows:
            print('✅ VIEW существует, записи:')
            for row in rows:
                print(f'  {dict(row)}')
        else:
            print('❌ VIEW пустой')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    print('\n=== ПРОВЕРКА scenario_logs для колод ===')
    try:
        cursor = conn.execute("""
            SELECT 
                JSON_EXTRACT(metadata, '$.deck_name') as deck_name,
                COUNT(*) as count
            FROM scenario_logs 
            WHERE step = 'deck_selected' 
            AND DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            GROUP BY deck_name
        """)
        rows = cursor.fetchall()
        if rows:
            print('✅ Данные по колодам в scenario_logs:')
            for row in rows:
                print(f'  {dict(row)}')
        else:
            print('❌ Нет данных по колодам за сегодня')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    print('\n=== ПРОВЕРКА всех deck_selected за последние дни ===')
    try:
        cursor = conn.execute("""
            SELECT 
                DATE(timestamp, '+3 hours') as date,
                JSON_EXTRACT(metadata, '$.deck_name') as deck_name,
                COUNT(*) as count
            FROM scenario_logs 
            WHERE step = 'deck_selected' 
            AND DATE(timestamp, '+3 hours') >= DATE('now', '+3 hours', '-7 days')
            GROUP BY DATE(timestamp, '+3 hours'), deck_name
            ORDER BY date DESC
        """)
        rows = cursor.fetchall()
        if rows:
            print('✅ Данные по колодам за последние 7 дней:')
            for row in rows:
                print(f'  {dict(row)}')
        else:
            print('❌ Нет данных по колодам за последние 7 дней')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    print('\n=== ПРОВЕРКА card_drawn ===')
    try:
        cursor = conn.execute("""
            SELECT 
                DATE(timestamp, '+3 hours') as date,
                COUNT(*) as count
            FROM scenario_logs 
            WHERE step = 'card_drawn' 
            AND DATE(timestamp, '+3 hours') >= DATE('now', '+3 hours', '-7 days')
            GROUP BY DATE(timestamp, '+3 hours')
            ORDER BY date DESC
        """)
        rows = cursor.fetchall()
        if rows:
            print('✅ Данные по вытянутым картам:')
            for row in rows:
                print(f'  {dict(row)}')
        else:
            print('❌ Нет данных по вытянутым картам')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
    
    conn.close()

if __name__ == "__main__":
    check_deck_metrics()
