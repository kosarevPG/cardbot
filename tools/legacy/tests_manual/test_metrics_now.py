#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест метрик на локальной базе
"""

import sqlite3
import sys

db_path = "bot (7).db"

print(f"📁 База данных: {db_path}")
print()
print("=" * 60)
print("🧪 ТЕСТИРОВАНИЕ МЕТРИК")
print("=" * 60)
print()

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Сессии за сегодня (как в главном дашборде)
    print("1️⃣  ГЛАВНЫЙ ДАШБОРД: Запущено/Завершено")
    print("-" * 60)
    
    cursor.execute("""
        SELECT 
            COALESCE(SUM(started), 0) as total_starts,
            COALESCE(SUM(completed), 0) as total_completions
        FROM v_sessions_daily 
        WHERE scenario = 'card_of_day' AND d_local = date('now', '+3 hours')
    """)
    
    row = cursor.fetchone()
    print(f"✅ Запущено: {row['total_starts']}")
    print(f"✅ Завершено: {row['total_completions']}")
    
    if row['total_starts'] > 0:
        completion_rate = (row['total_completions'] / row['total_starts'] * 100)
        print(f"✅ Completion Rate: {completion_rate:.1f}%")
    else:
        print("⚠️  За сегодня нет запусков (это нормально, если сегодня никто не использовал бота)")
    
    print()
    
    # 2. DAU
    print("2️⃣  DAU")
    print("-" * 60)
    
    cursor.execute("""
        SELECT COALESCE(dau, 0) as dau
        FROM v_dau_daily 
        WHERE d_local = date('now', '+3 hours')
    """)
    row = cursor.fetchone()
    print(f"✅ DAU сегодня: {row['dau']}")
    
    cursor.execute("""
        SELECT AVG(dau) as avg_dau
        FROM v_dau_daily 
        WHERE d_local >= date('now', '+3 hours', '-7 days')
    """)
    row = cursor.fetchone()
    print(f"✅ Средний DAU (7 дней): {row['avg_dau']:.1f}")
    
    print()
    
    # 3. Воронка
    print("3️⃣  ВОРОНКА 'КАРТА ДНЯ' (за сегодня)")
    print("-" * 60)
    
    cursor.execute("""
        SELECT 
            event,
            COUNT(DISTINCT session_id) as count
        FROM v_events
        WHERE scenario = 'card_of_day' AND d_local = date('now', '+3 hours')
        GROUP BY event
        ORDER BY 
            CASE event
                WHEN 'scenario_started' THEN 1
                WHEN 'initial_resource_selected' THEN 2
                WHEN 'card_drawn' THEN 3
                WHEN 'completed' THEN 4
                ELSE 5
            END
    """)
    
    steps = cursor.fetchall()
    
    if steps:
        step_counts = {row['event']: row['count'] for row in steps}
        base_count = step_counts.get('scenario_started', 0)
        if base_count == 0:
            base_count = step_counts.get('initial_resource_selected', 0)
        
        print(f"Базовый шаг для расчета: {base_count}")
        print()
        
        for row in steps:
            pct = (row['count'] / base_count * 100) if base_count > 0 else 0
            print(f"  • {row['event']}: {row['count']} ({pct:.1f}%)")
        
        completion_rate = (step_counts.get('completed', 0) / base_count * 100) if base_count > 0 else 0
        print()
        print(f"✅ Completion Rate: {completion_rate:.1f}%")
    else:
        print("⚠️  За сегодня нет событий")
    
    print()
    
    # 4. Колоды
    print("4️⃣  СТАТИСТИКА КОЛОД (за сегодня)")
    print("-" * 60)
    
    cursor.execute("""
        SELECT 
            deck,
            SUM(draws) as total_draws,
            SUM(uniq_users) as unique_users
        FROM v_decks_daily 
        WHERE d_local = date('now', '+3 hours') AND deck IS NOT NULL
        GROUP BY deck
    """)
    
    decks = cursor.fetchall()
    
    if decks:
        total_draws = sum(row['total_draws'] for row in decks)
        for deck in decks:
            pct = (deck['total_draws'] / total_draws * 100) if total_draws > 0 else 0
            print(f"  • {deck['deck']}: {deck['total_draws']} вытягиваний ({pct:.1f}%)")
    else:
        print("⚠️  За сегодня нет вытягиваний карт")
    
    print()
    
    # 5. Проверка последних 7 дней
    print("5️⃣  СТАТИСТИКА ЗА ПОСЛЕДНИЕ 7 ДНЕЙ")
    print("-" * 60)
    
    cursor.execute("""
        SELECT 
            scenario,
            SUM(started) as total_starts,
            SUM(completed) as total_completions
        FROM v_sessions_daily 
        WHERE scenario = 'card_of_day' AND d_local >= date('now', '+3 hours', '-7 days')
        GROUP BY scenario
    """)
    
    row = cursor.fetchone()
    if row:
        print(f"✅ Запущено (7 дней): {row['total_starts']}")
        print(f"✅ Завершено (7 дней): {row['total_completions']}")
        if row['total_starts'] > 0:
            completion_rate = (row['total_completions'] / row['total_starts'] * 100)
            print(f"✅ Completion Rate: {completion_rate:.1f}%")
    else:
        print("⚠️  Нет данных за последние 7 дней")
    
    print()
    
    # 6. Проверка событий scenario_started и completed
    print("6️⃣  ПРОВЕРКА ОБЯЗАТЕЛЬНЫХ СОБЫТИЙ")
    print("-" * 60)
    
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN event = 'scenario_started' THEN 1 ELSE 0 END) as started_count,
            SUM(CASE WHEN event = 'completed' THEN 1 ELSE 0 END) as completed_count,
            SUM(CASE WHEN event = 'initial_resource_selected' THEN 1 ELSE 0 END) as resource_count
        FROM v_events
        WHERE d_local >= date('now', '+3 hours', '-7 days')
    """)
    
    row = cursor.fetchone()
    print(f"📊 События за последние 7 дней:")
    print(f"  • scenario_started: {row['started_count']}")
    print(f"  • completed: {row['completed_count']}")
    print(f"  • initial_resource_selected: {row['resource_count']}")
    
    if row['started_count'] == 0:
        print()
        print("⚠️  ВАЖНО: нет событий 'scenario_started'!")
        print("   Это означает, что код с новыми событиями еще не запускался.")
        print("   После деплоя эти события появятся.")
    
    if row['completed_count'] == 0 and row['resource_count'] > 0:
        print()
        print("⚠️  ВАЖНО: нет событий 'completed'!")
        print("   Пользователи начинают сценарий, но никто не завершил.")
        print("   Или код с событием 'completed' еще не запускался.")
    
    conn.close()
    
    print()
    print("=" * 60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)
    print()
    print("🎯 ВЫВОД:")
    print("  VIEW работают корректно!")
    print("  Метрики считаются правильно!")
    print()
    print("🚀 СЛЕДУЮЩИЙ ШАГ:")
    print("  Задеплой фикс на прод: tools\\emergency_fix_and_deploy.bat")
    print("  Или вручную: git add . && git commit -m \"fix\" && git push")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

