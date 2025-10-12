#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматическая миграция при старте бота.
Добавить в main.py перед запуском polling.
"""

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

def apply_metrics_migration(db_path: str = 'data/bot.db'):
    """
    Применяет SQL миграцию для создания VIEW инфраструктуры.
    Безопасно для повторного запуска (использует IF NOT EXISTS).
    """
    
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
    
    -- 2.1. Таблица логов обучения
    CREATE TABLE IF NOT EXISTS training_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        training_type TEXT NOT NULL,  -- 'card_conversation' или другой тип обучения
        step TEXT NOT NULL,           -- 'started', 'completed', 'abandoned'
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        details TEXT,                 -- JSON с дополнительными данными
        session_id TEXT              -- ID сессии для группировки
    );
    
    -- Индексы для быстрого поиска логов обучения
    CREATE INDEX IF NOT EXISTS idx_training_logs_user_id ON training_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_training_logs_training_type ON training_logs(training_type);
    CREATE INDEX IF NOT EXISTS idx_training_logs_step ON training_logs(step);
    CREATE INDEX IF NOT EXISTS idx_training_logs_timestamp ON training_logs(timestamp);
    CREATE INDEX IF NOT EXISTS idx_training_logs_session_id ON training_logs(session_id);
    
    -- Добавляем настройки
    INSERT OR REPLACE INTO settings (key, value, description) VALUES 
        ('report_tz', '+03:00', 'Часовой пояс для отчетов (МСК)'),
        ('training_logs_enabled', 'true', 'Включить логирование обучения'),
        ('training_exclude_admins', 'true', 'Исключить админов из логов обучения');
    
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
        -- Используем ПЕРВОЕ событие сессии (любое) для started_at/started_date
        -- Это работает как со старыми данными (без scenario_started), так и с новыми
        MIN(ts_local) AS started_at,
        MIN(d_local) AS started_date,
        MAX(CASE WHEN event = 'completed' THEN ts_local END) AS completed_at,
        CASE WHEN MAX(CASE WHEN event = 'completed' THEN 1 ELSE 0 END) > 0 
             THEN 1 ELSE 0 END AS is_completed,
        COUNT(*) AS total_events,
        COUNT(*) AS step_count  -- Количество шагов в сессии
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
    WHERE started_date IS NOT NULL
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
        
        logger.info("✅ Metrics infrastructure migration applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to apply metrics migration: {e}", exc_info=True)
        return False

# Использование в main.py:
# if __name__ == "__main__":
#     # ... инициализация db, logging_service и т.д. ...
#     
#     # Применяем миграцию при старте
#     logger.info("🔄 Applying database migrations...")
#     apply_metrics_migration(db_path='data/bot.db')
#     
#     # Запускаем бота
#     asyncio.run(main())

