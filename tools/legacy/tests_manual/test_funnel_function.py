#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def test_funnel_function():
    """Тестирует функцию get_card_funnel_metrics напрямую."""
    db_path = "bot (10).db"
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return
    
    print(f"📁 База данных: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print('\n=== ТЕСТ ФУНКЦИИ get_card_funnel_metrics ===')
    
    # Тестируем с include_excluded_users=False (по умолчанию)
    print('\n1️⃣ Тест с include_excluded_users=False (должен использовать v_events):')
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
        
        print(f"  Шаги из v_events: {step_counts}")
        
        # Базовый шаг для расчета процентов
        base_count = step_counts.get('scenario_started', 0)
        if base_count == 0:
            base_count = step_counts.get('initial_resource_selected', 0)
        
        print(f"  Базовый шаг (initial_resource_selected): {base_count}")
        
        # Извлекаем конкретные шаги
        step1 = step_counts.get('scenario_started', step_counts.get('initial_resource_selected', 0))
        step2 = step_counts.get('initial_resource_selected', 0)
        step3 = step_counts.get('request_type_selected', 0)
        step4 = step_counts.get('card_drawn', 0)
        step5 = step_counts.get('initial_response_provided', 0)
        step6 = step_counts.get('ai_reflection_choice', 0)
        step7 = step_counts.get('completed', 0)
        
        print(f"  Step 1 (scenario_started): {step1}")
        print(f"  Step 2 (initial_resource_selected): {step2}")
        print(f"  Step 3 (request_type_selected): {step3}")
        print(f"  Step 4 (card_drawn): {step4}")
        print(f"  Step 5 (initial_response_provided): {step5}")
        print(f"  Step 6 (ai_reflection_choice): {step6}")
        print(f"  Step 7 (completed): {step7}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тестируем с include_excluded_users=True
    print('\n2️⃣ Тест с include_excluded_users=True (должен использовать scenario_logs):')
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
        
        print(f"  Шаги из scenario_logs: {step_counts}")
        
        # Базовый шаг для расчета процентов
        base_count = step_counts.get('scenario_started', 0)
        if base_count == 0:
            base_count = step_counts.get('initial_resource_selected', 0)
        
        print(f"  Базовый шаг (initial_resource_selected): {base_count}")
        
        # Извлекаем конкретные шаги
        step1 = step_counts.get('scenario_started', step_counts.get('initial_resource_selected', 0))
        step2 = step_counts.get('initial_resource_selected', 0)
        step3 = step_counts.get('request_type_selected', 0)
        step4 = step_counts.get('card_drawn', 0)
        step5 = step_counts.get('initial_response_provided', 0)
        step6 = step_counts.get('ai_reflection_choice', 0)
        step7 = step_counts.get('completed', 0)
        
        print(f"  Step 1 (scenario_started): {step1}")
        print(f"  Step 2 (initial_resource_selected): {step2}")
        print(f"  Step 3 (request_type_selected): {step3}")
        print(f"  Step 4 (card_drawn): {step4}")
        print(f"  Step 5 (initial_response_provided): {step5}")
        print(f"  Step 6 (ai_reflection_choice): {step6}")
        print(f"  Step 7 (completed): {step7}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    conn.close()

if __name__ == "__main__":
    test_funnel_function()

