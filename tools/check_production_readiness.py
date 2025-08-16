#!/usr/bin/env python3
"""
Проверка готовности к продакшн деплою
"""

import sqlite3
import os
import sys

DB_PATH = "database/dev.db"

def check_production_readiness():
    """Проверяет готовность к деплою в продакшн"""
    
    print("ПРОВЕРКА ГОТОВНОСТИ К ПРОДАКШН ДЕПЛОЮ")
    print("=" * 60)
    
    # Проверка 1: База данных
    print("\n1. ПРОВЕРКА БАЗЫ ДАННЫХ")
    if not os.path.exists(DB_PATH):
        print("База данных не найдена")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Проверяем таблицу scenario_logs
        cursor = conn.execute("SELECT COUNT(*) as count FROM scenario_logs")
        total_logs = cursor.fetchone()['count']
        print(f"Записей в scenario_logs: {total_logs}")
        
        if total_logs == 0:
            print("Внимание: Нет данных в scenario_logs")
        
    except Exception as e:
        print(f"Ошибка при проверке БД: {e}")
        return False
    
    # Проверка 2: Воронка за разные периоды
    print("\n2. ПРОВЕРКА ВОРОНКИ ПО ПЕРИОДАМ")
    
    periods = [1, 7, 30]
    funnel_works = True
    
    for days in periods:
        try:
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
            print(f"Ошибка при проверке периода {days} дней: {e}")
            funnel_works = False
    
    # Проверка 3: Все шаги воронки
    print("\n3. ПРОВЕРКА ВСЕХ ШАГОВ ВОРОНКИ")
    
    expected_steps = [
        'started',
        'initial_resource_selected', 
        'request_type_selected',
        'card_drawn',
        'initial_response_provided',
        'ai_reflection_choice',
        'completed'
    ]
    
    for step in expected_steps:
        try:
            cursor = conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = ?
                AND timestamp >= datetime('now', '-30 days')
            """, (step,))
            count = cursor.fetchone()['count']
            status = "OK" if count > 0 else "WARN"
            print(f"  {status} {step}: {count}")
            
        except Exception as e:
            print(f"  ERROR {step}: ошибка - {e}")
            funnel_works = False
    
    # Проверка 4: Критические файлы
    print("\n4. ПРОВЕРКА КРИТИЧЕСКИХ ФАЙЛОВ")
    
    critical_files = [
        'main.py',
        'database/db.py',
        'modules/card_of_the_day.py'
    ]
    
    files_ok = True
    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"OK {file_path}")
        else:
            print(f"ERROR {file_path} - НЕ НАЙДЕН")
            files_ok = False
    
    # Проверка 5: Новые файлы анализа
    print("\n5. ПРОВЕРКА ФАЙЛОВ АНАЛИЗА")
    
    analysis_files = [
        'analyze_funnel_steps.py',
        'analyze_user_dropoffs.py',
        'check_funnel_30_days.py',
        'test_funnel_periods.py'
    ]
    
    for file_path in analysis_files:
        if os.path.exists(file_path):
            print(f"OK {file_path}")
        else:
            print(f"WARN {file_path} - не найден (опциональный)")
    
    # Итоговая оценка
    print("\nИТОГОВАЯ ОЦЕНКА ГОТОВНОСТИ")
    print("=" * 60)
    
    if funnel_works and files_ok:
        print("ГОТОВ К ДЕПЛОЮ В ПРОДАКШН")
        print("\nЧТО ДЕПЛОИТЬ:")
        print("  • main.py")
        print("  • database/db.py") 
        print("  • modules/card_of_the_day.py")
        print("\nЧТО ПРОВЕРИТЬ ПОСЛЕ ДЕПЛОЯ:")
        print("  • Воронка в админке")
        print("  • Переключение периодов")
        print("  • Корректность данных")
        return True
    else:
        print("НЕ ГОТОВ К ДЕПЛОЮ")
        if not funnel_works:
            print("  • Проблемы с воронкой")
        if not files_ok:
            print("  • Отсутствуют критические файлы")
        return False
    
    conn.close()
    
    # Итоговая оценка
    print("\nИТОГОВАЯ ОЦЕНКА ГОТОВНОСТИ")
    print("=" * 60)
    
    if funnel_works and files_ok:
        print("ГОТОВ К ДЕПЛОЮ В ПРОДАКШН")
        print("\nЧТО ДЕПЛОИТЬ:")
        print("  • main.py")
        print("  • database/db.py") 
        print("  • modules/card_of_the_day.py")
        print("\nЧТО ПРОВЕРИТЬ ПОСЛЕ ДЕПЛОЯ:")
        print("  • Воронка в админке")
        print("  • Переключение периодов")
        print("  • Корректность данных")
        return True
    else:
        print("НЕ ГОТОВ К ДЕПЛОЮ")
        if not funnel_works:
            print("  • Проблемы с воронкой")
        if not files_ok:
            print("  • Отсутствуют критические файлы")
        return False

if __name__ == "__main__":
    success = check_production_readiness()
    sys.exit(0 if success else 1) 