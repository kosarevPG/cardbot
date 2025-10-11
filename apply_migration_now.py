#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Применение миграции к bot (7).db
"""

import sqlite3
import os

db_path = "bot (7).db"

if not os.path.exists(db_path):
    print(f"❌ База данных не найдена: {db_path}")
    exit(1)

print(f"📁 База данных: {db_path}")
print()

sql_migration = """
-- ============================================================================
-- СИСТЕМА МЕТРИК: ИНФРАСТРУКТУРА (AUTO MIGRATION)
-- ============================================================================

-- 1. Таблица исключенных пользователей (админы)
CREATE TABLE IF NOT EXISTS ignored_users (
    user_id INTEGER PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Добавляем админов
INSERT OR IGNORE INTO ignored_users(user_id) VALUES 
    (171507422),   -- KosarevPG
    (6682555021);  -- Admin

-- 2. Таблица настроек
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Добавляем часовой пояс
INSERT OR REPLACE INTO settings (key, value, description) VALUES 
    ('report_tz', '+03:00', 'Часовой пояс для отчетов (МСК)');

-- 3. VIEW базовых событий (с фильтрацией админов)
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

-- 4. VIEW сессий
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

-- 5. VIEW DAU по дням
DROP VIEW IF EXISTS v_dau_daily;
CREATE VIEW v_dau_daily AS
SELECT 
    d_local,
    COUNT(DISTINCT user_id) AS dau
FROM v_events
GROUP BY d_local
ORDER BY d_local DESC;

-- 6. VIEW статистики сессий по дням
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

-- 7. VIEW статистики колод по дням
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

-- 8. Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_scenario_logs_timestamp ON scenario_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_scenario_logs_user_scenario ON scenario_logs(user_id, scenario);
CREATE INDEX IF NOT EXISTS idx_scenario_logs_step ON scenario_logs(step);
"""

try:
    conn = sqlite3.connect(db_path)
    conn.executescript(sql_migration)
    conn.commit()
    conn.close()
    
    print("✅ Миграция применена успешно!")
    print()
    print("🧪 Тестируем VIEW...")
    print()
    
    # Проверка VIEW
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'v_%'")
    views = cursor.fetchall()
    
    print(f"📊 Создано VIEW: {len(views)}")
    for view in views:
        print(f"  ✅ {view['name']}")
    
    print()
    
    # Тест v_sessions_daily за сегодня
    cursor.execute("""
        SELECT scenario, started, completed, completion_rate
        FROM v_sessions_daily
        WHERE d_local = date('now', '+3 hours')
    """)
    sessions_today = cursor.fetchall()
    
    print("📊 Сессии за сегодня:")
    if sessions_today:
        for s in sessions_today:
            print(f"  • {s['scenario']}: запущено {s['started']}, завершено {s['completed']} ({s['completion_rate']:.1f}%)")
    else:
        print("  ℹ️  Нет сессий за сегодня")
    
    print()
    
    # Тест DAU
    cursor.execute("""
        SELECT dau FROM v_dau_daily
        WHERE d_local = date('now', '+3 hours')
    """)
    dau_today = cursor.fetchone()
    
    if dau_today:
        print(f"📊 DAU сегодня: {dau_today['dau']}")
    else:
        print("📊 DAU сегодня: 0")
    
    conn.close()
    
    print()
    print("🎉 Готово! VIEW работают корректно!")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

