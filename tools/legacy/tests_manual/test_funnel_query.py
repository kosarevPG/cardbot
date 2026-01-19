#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def test_funnel_query():
    """Тестирует запрос функции get_card_funnel_metrics."""
    db_path = "bot (10).db"
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return
    
    print(f"📁 База данных: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print('\n=== ТЕСТ ЗАПРОСА ФУНКЦИИ ===')
    
    # Тест с v_events (как должно быть по умолчанию)
    print('\n1️⃣ Тест с v_events (include_excluded_users=False):')
    try:
        cursor = conn.execute("""
            SELECT 
                event,
                COUNT(DISTINCT session_id) as count
            FROM v_events
            WHERE scenario = 'card_of_day' AND d_local = date('now', '+3 hours')
            GROUP BY event
        """)
        
        step_counts = {}
        for row in cursor.fetchall():
            step_counts[row['event']] = row['count']
        
        print(f"  Результат: {step_counts}")
        
        # Проверяем ключевые шаги
        initial_resource = step_counts.get('initial_resource_selected', 0)
        card_drawn = step_counts.get('card_drawn', 0)
        completed = step_counts.get('completed', 0)
        
        print(f"  initial_resource_selected: {initial_resource}")
        print(f"  card_drawn: {card_drawn}")
        print(f"  completed: {completed}")
        
    except Exception as e:
        print(f"❌ Ошибка в запросе v_events: {e}")
    
    # Тест с scenario_logs (как происходит сейчас)
    print('\n2️⃣ Тест с scenario_logs (include_excluded_users=True):')
    try:
        cursor = conn.execute("""
            SELECT 
                step,
                COUNT(DISTINCT JSON_EXTRACT(metadata, '$.session_id')) as count
            FROM scenario_logs
            WHERE scenario = 'card_of_day' AND DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            GROUP BY step
        """)
        
        step_counts = {}
        for row in cursor.fetchall():
            step_counts[row['step']] = row['count']
        
        print(f"  Результат: {step_counts}")
        
        # Проверяем ключевые шаги
        initial_resource = step_counts.get('initial_resource_selected', 0)
        card_drawn = step_counts.get('card_drawn', 0)
        completed = step_counts.get('completed', 0)
        
        print(f"  initial_resource_selected: {initial_resource}")
        print(f"  card_drawn: {card_drawn}")
        print(f"  completed: {completed}")
        
    except Exception as e:
        print(f"❌ Ошибка в запросе scenario_logs: {e}")
    
    # Тест с scenario_logs БЕЗ админов (как должно быть)
    print('\n3️⃣ Тест с scenario_logs БЕЗ админов:')
    try:
        cursor = conn.execute("""
            SELECT 
                step,
                COUNT(DISTINCT JSON_EXTRACT(metadata, '$.session_id')) as count
            FROM scenario_logs
            WHERE scenario = 'card_of_day' 
            AND DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')
            AND user_id NOT IN (SELECT user_id FROM ignored_users)
            GROUP BY step
        """)
        
        step_counts = {}
        for row in cursor.fetchall():
            step_counts[row['step']] = row['count']
        
        print(f"  Результат: {step_counts}")
        
        # Проверяем ключевые шаги
        initial_resource = step_counts.get('initial_resource_selected', 0)
        card_drawn = step_counts.get('card_drawn', 0)
        completed = step_counts.get('completed', 0)
        
        print(f"  initial_resource_selected: {initial_resource}")
        print(f"  card_drawn: {card_drawn}")
        print(f"  completed: {completed}")
        
    except Exception as e:
        print(f"❌ Ошибка в запросе scenario_logs без админов: {e}")
    
    conn.close()

if __name__ == "__main__":
    test_funnel_query()

