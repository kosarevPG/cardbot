#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест метрик
"""

import sqlite3

db_path = "bot (7).db"

print(f"📁 База данных: {db_path}")
print()

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Проверяем какие даты есть в v_dau_daily
    print("📅 Даты в v_dau_daily:")
    cursor.execute("""
        SELECT d_local, dau
        FROM v_dau_daily
        ORDER BY d_local DESC
        LIMIT 10
    """)
    dates = cursor.fetchall()
    if dates:
        for d in dates:
            print(f"  • {d['d_local']}: DAU = {d['dau']}")
    else:
        print("  ⚠️  Нет данных")
    
    print()
    
    # Проверяем сессии по дням
    print("📅 Сессии по дням:")
    cursor.execute("""
        SELECT d_local, scenario, started, completed, completion_rate
        FROM v_sessions_daily
        ORDER BY d_local DESC
        LIMIT 10
    """)
    sessions = cursor.fetchall()
    if sessions:
        for s in sessions:
            print(f"  • {s['d_local']} | {s['scenario']}: {s['started']} запущено, {s['completed']} завершено ({s['completion_rate']:.1f}%)")
    else:
        print("  ⚠️  Нет данных")
    
    print()
    
    # Проверяем, когда была последняя активность
    print("📊 Последняя активность:")
    cursor.execute("""
        SELECT d_local, COUNT(*) as events
        FROM v_events
        GROUP BY d_local
        ORDER BY d_local DESC
        LIMIT 5
    """)
    activity = cursor.fetchall()
    if activity:
        for a in activity:
            print(f"  • {a['d_local']}: {a['events']} событий")
    else:
        print("  ⚠️  Нет событий")
    
    print()
    
    # Проверяем наличие scenario_started и completed
    print("📊 Обязательные события (всего за все время):")
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN event = 'scenario_started' THEN 1 ELSE 0 END) as started_count,
            SUM(CASE WHEN event = 'completed' THEN 1 ELSE 0 END) as completed_count,
            SUM(CASE WHEN event = 'initial_resource_selected' THEN 1 ELSE 0 END) as resource_count
        FROM v_events
    """)
    row = cursor.fetchone()
    print(f"  • scenario_started: {row['started_count']}")
    print(f"  • completed: {row['completed_count']}")
    print(f"  • initial_resource_selected: {row['resource_count']}")
    
    print()
    
    # Проверяем сырые данные из scenario_logs
    print("📊 Сырые данные (scenario_logs) за последний день активности:")
    cursor.execute("""
        SELECT 
            step,
            COUNT(*) as count
        FROM scenario_logs
        WHERE scenario = 'card_of_day'
        GROUP BY step
        ORDER BY count DESC
        LIMIT 10
    """)
    raw_steps = cursor.fetchall()
    if raw_steps:
        for step in raw_steps:
            print(f"  • {step['step']}: {step['count']}")
    else:
        print("  ⚠️  Нет данных")
    
    print()
    
    # Проверяем session_id в metadata
    print("📊 Session_id в metadata:")
    cursor.execute("""
        SELECT 
            COUNT(*) as total_logs,
            SUM(CASE WHEN json_extract(metadata, '$.session_id') IS NOT NULL THEN 1 ELSE 0 END) as with_session,
            SUM(CASE WHEN json_extract(metadata, '$.session_id') IS NULL THEN 1 ELSE 0 END) as without_session
        FROM scenario_logs
        WHERE scenario = 'card_of_day'
    """)
    row = cursor.fetchone()
    print(f"  • Всего логов: {row['total_logs']}")
    print(f"  • С session_id: {row['with_session']}")
    print(f"  • Без session_id: {row['without_session']}")
    
    if row['without_session'] > 0 and row['with_session'] == 0:
        print()
        print("  ⚠️  ПРОБЛЕМА: НЕТ session_id в metadata!")
        print("     Это значит, что код с session_id еще не запускался.")
        print("     v_sessions будет пустым, потому что он группирует по session_id.")
    
    print()
    
    # Итоговый диагноз
    print("=" * 60)
    print("🎯 ДИАГНОЗ:")
    print("=" * 60)
    
    if row['started_count'] == 0:
        print("❌ Событие 'scenario_started' НЕ ЛОГИРУЕТСЯ")
        print("   Это новое событие, которое мы только что добавили.")
        print("   После деплоя оно появится.")
    else:
        print("✅ Событие 'scenario_started' логируется")
    
    if row['completed_count'] == 0:
        print("❌ Событие 'completed' НЕ ЛОГИРУЕТСЯ")
        print("   Это новое событие, которое мы только что добавили.")
        print("   После деплоя оно появится.")
    else:
        print("✅ Событие 'completed' логируется")
    
    if row['without_session'] > 0 and row['with_session'] == 0:
        print("❌ session_id НЕ СОХРАНЯЕТСЯ в metadata")
        print("   v_sessions будет пустым без session_id.")
    else:
        print("✅ session_id сохраняется в metadata")
    
    print()
    print("🚀 РЕШЕНИЕ:")
    print("   Задеплой обновленный код - новые события начнут логироваться!")
    print("   VIEW уже готовы и будут работать сразу после первых новых событий.")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

