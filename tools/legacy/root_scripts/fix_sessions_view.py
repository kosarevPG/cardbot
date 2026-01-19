#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправление v_sessions для работы без события scenario_started
"""

import sqlite3

db_path = "bot (7).db"

print(f"📁 База данных: {db_path}")
print()

sql_fix = """
-- Исправляем v_sessions чтобы работало без scenario_started
DROP VIEW IF EXISTS v_sessions;
CREATE VIEW v_sessions AS
SELECT 
    scenario,
    session_id,
    -- Используем ПЕРВОЕ событие сессии (любое) для started_at/started_date
    MIN(ts_local) AS started_at,
    MIN(d_local) AS started_date,
    -- Используем событие 'completed' для completed_at
    MAX(CASE WHEN event = 'completed' THEN ts_local END) AS completed_at,
    -- Проверяем наличие события 'completed' для is_completed
    CASE WHEN MAX(CASE WHEN event = 'completed' THEN 1 ELSE 0 END) > 0 
         THEN 1 ELSE 0 END AS is_completed,
    COUNT(*) AS total_events
FROM v_events
WHERE session_id IS NOT NULL
GROUP BY scenario, session_id;

-- Пересоздаем v_sessions_daily
DROP VIEW IF EXISTS v_sessions_daily;
CREATE VIEW v_sessions_daily AS
SELECT 
    scenario,
    started_date AS d_local,
    COUNT(*) AS started,
    SUM(is_completed) AS completed,
    ROUND(100.0 * SUM(is_completed) / COUNT(*), 1) AS completion_rate
FROM v_sessions
WHERE started_date IS NOT NULL
GROUP BY scenario, started_date
ORDER BY started_date DESC;
"""

try:
    conn = sqlite3.connect(db_path)
    conn.executescript(sql_fix)
    conn.commit()
    
    print("✅ v_sessions исправлен!")
    print()
    
    # Тестируем
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("🧪 Тестирование v_sessions_daily:")
    cursor.execute("""
        SELECT d_local, scenario, started, completed, completion_rate
        FROM v_sessions_daily
        ORDER BY d_local DESC
        LIMIT 10
    """)
    
    for row in cursor.fetchall():
        print(f"  • {row['d_local']} | {row['scenario']}: {row['started']} запущено, {row['completed']} завершено ({row['completion_rate']:.1f}%)")
    
    print()
    
    # Тест за сегодня
    print("🧪 Сессии за сегодня:")
    cursor.execute("""
        SELECT scenario, started, completed, completion_rate
        FROM v_sessions_daily
        WHERE d_local = date('now', '+3 hours')
    """)
    
    today = cursor.fetchall()
    if today:
        for row in today:
            print(f"  • {row['scenario']}: {row['started']} запущено, {row['completed']} завершено ({row['completion_rate']:.1f}%)")
    else:
        print("  ℹ️  За сегодня нет сессий")
    
    print()
    
    # Общая статистика
    print("📊 ОБЩАЯ СТАТИСТИКА:")
    cursor.execute("""
        SELECT 
            SUM(started) as total_starts,
            SUM(completed) as total_completions
        FROM v_sessions_daily
        WHERE scenario = 'card_of_day'
    """)
    row = cursor.fetchone()
    print(f"  • Всего запущено: {row['total_starts']}")
    print(f"  • Всего завершено: {row['total_completions']}")
    if row['total_starts'] > 0:
        print(f"  • Общий Completion Rate: {(row['total_completions'] / row['total_starts'] * 100):.1f}%")
    
    conn.close()
    
    print()
    print("🎉 Готово! VIEW теперь работают БЕЗ события scenario_started!")
    print()
    print("✅ Метрики будут работать СЕЙЧАС с существующими данными")
    print("✅ После деплоя появится событие scenario_started и станет еще точнее")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

