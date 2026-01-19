#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пересоздание VIEW с правильным форматом timestamp
"""

import sqlite3

db_path = "bot (7).db"

print(f"📁 База данных: {db_path}")
print()

sql_fix = """
-- Пересоздаем v_events с правильным форматом timestamp
DROP VIEW IF EXISTS v_events;
CREATE VIEW v_events AS
WITH tz AS (
    SELECT value AS offset FROM settings WHERE key='report_tz'
)
SELECT
    l.rowid AS event_id,
    l.user_id,
    l.scenario,
    l.step AS event,
    l.metadata,
    datetime(l.timestamp, (SELECT offset FROM tz)) AS ts_local,
    date(datetime(l.timestamp, (SELECT offset FROM tz))) AS d_local,
    json_extract(l.metadata, '$.session_id') AS session_id
FROM scenario_logs l
LEFT JOIN ignored_users i ON i.user_id = l.user_id
WHERE i.user_id IS NULL;

-- Пересоздаем зависимые VIEW
DROP VIEW IF EXISTS v_sessions;
CREATE VIEW v_sessions AS
SELECT 
    scenario,
    session_id,
    MIN(CASE WHEN event = 'scenario_started' THEN ts_local END) AS started_at,
    MIN(CASE WHEN event = 'scenario_started' THEN d_local END) AS started_date,
    MAX(CASE WHEN event = 'completed' THEN ts_local END) AS completed_at,
    CASE WHEN MAX(CASE WHEN event = 'completed' THEN 1 ELSE 0 END) > 0 
         THEN 1 ELSE 0 END AS is_completed,
    COUNT(*) AS total_events
FROM v_events
WHERE session_id IS NOT NULL
GROUP BY scenario, session_id;

DROP VIEW IF EXISTS v_dau_daily;
CREATE VIEW v_dau_daily AS
SELECT 
    d_local,
    COUNT(DISTINCT user_id) AS dau
FROM v_events
GROUP BY d_local
ORDER BY d_local DESC;

DROP VIEW IF EXISTS v_sessions_daily;
CREATE VIEW v_sessions_daily AS
SELECT 
    scenario,
    started_date AS d_local,
    COUNT(*) AS started,
    SUM(is_completed) AS completed,
    ROUND(100.0 * SUM(is_completed) / COUNT(*), 1) AS completion_rate
FROM v_sessions
GROUP BY scenario, started_date
ORDER BY started_date DESC;

DROP VIEW IF EXISTS v_decks_daily;
CREATE VIEW v_decks_daily AS
SELECT 
    d_local,
    json_extract(metadata, '$.deck') AS deck,
    COUNT(*) AS draws,
    COUNT(DISTINCT user_id) AS uniq_users
FROM v_events
WHERE event = 'card_drawn' AND json_extract(metadata, '$.deck') IS NOT NULL
GROUP BY d_local, deck
ORDER BY d_local DESC, draws DESC;
"""

try:
    conn = sqlite3.connect(db_path)
    conn.executescript(sql_fix)
    conn.commit()
    
    print("✅ VIEW пересозданы с правильным форматом timestamp!")
    print()
    
    # Тестируем
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("🧪 Тестирование v_dau_daily:")
    cursor.execute("""
        SELECT d_local, dau
        FROM v_dau_daily
        ORDER BY d_local DESC
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        print(f"  • {row['d_local']}: DAU = {row['dau']}")
    
    print()
    
    print("🧪 Тестирование v_sessions_daily:")
    cursor.execute("""
        SELECT d_local, scenario, started, completed, completion_rate
        FROM v_sessions_daily
        ORDER BY d_local DESC
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        print(f"  • {row['d_local']} | {row['scenario']}: {row['started']} запущено, {row['completed']} завершено ({row['completion_rate']:.1f}%)")
    
    conn.close()
    
    print()
    print("🎉 Готово! VIEW теперь работают корректно!")
    print()
    print("🚀 Теперь можно деплоить на прод!")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

