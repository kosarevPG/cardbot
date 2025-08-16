#!/usr/bin/env python3
"""
Анализ логики сбора текстовых запросов пользователей
"""
import sqlite3
import json
from datetime import datetime

def analyze_request_logic():
    """Анализирует логику сбора запросов"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🔍 Анализ логики сбора запросов")
        print(f"📁 БД: {db_path}")
        
        # 1. Проверяем, что у нас есть в user_requests
        print(f"\n📊 Текущее содержимое user_requests:")
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        total_requests = cursor.fetchone()[0]
        print(f"  • Всего записей: {total_requests}")
        
        cursor = conn.execute("SELECT COUNT(DISTINCT user_id) FROM user_requests")
        unique_users = cursor.fetchone()[0]
        print(f"  • Уникальных пользователей: {unique_users}")
        
        # 2. Проверяем источники запросов в actions
        print(f"\n🔍 Анализ источников в таблице actions:")
        
        # Находим все типы действий с запросами
        cursor = conn.execute("""
            SELECT action, COUNT(*) as count
            FROM actions 
            WHERE details LIKE '%request%' OR details LIKE '%response%'
            GROUP BY action
            ORDER BY count DESC
        """)
        
        action_types = cursor.fetchall()
        print(f"  • Типы действий с запросами/ответами:")
        for row in action_types:
            print(f"    - {row['action']}: {row['count']} записей")
        
        # 3. Проверяем предложенную логику - находим card_flow_started
        print(f"\n🎯 Проверяем предложенную логику:")
        
        cursor = conn.execute("""
            SELECT COUNT(*) FROM actions WHERE action = 'card_flow_started'
        """)
        card_starts = cursor.fetchone()[0]
        print(f"  • Записей card_flow_started: {card_starts}")
        
        # 4. Проверяем предложенные типы действий
        proposed_actions = [
            'typed_question_submitted',
            'initial_response_provided', 
            'set_request',
            'request_text_provided',
            'initial_response',
            'card_drawn_with_request'
        ]
        
        print(f"\n📋 Проверяем предложенные типы действий:")
        for action_type in proposed_actions:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM actions WHERE action = ?
            """, (action_type,))
            count = cursor.fetchone()[0]
            print(f"  • {action_type}: {count} записей")
        
        # 5. Выполняем предложенный запрос
        print(f"\n🔍 Выполняем предложенный запрос:")
        
        cursor = conn.execute("""
            WITH relevant_actions AS (
                SELECT 
                    user_id,
                    username,
                    name,
                    action,
                    details,
                    timestamp
                FROM actions
                WHERE 
                    details LIKE '%request%' AND
                    action IN (
                        'typed_question_submitted',
                        'initial_response_provided',
                        'set_request',
                        'request_text_provided',
                        'initial_response',
                        'card_drawn_with_request'
                    )
            ),
            extracted_requests AS (
                SELECT
                    user_id,
                    username,
                    name,
                    json_extract(details, '$.request') AS request_text,
                    timestamp
                FROM relevant_actions
                WHERE json_extract(details, '$.request') IS NOT NULL
            )
            SELECT COUNT(*) as count
            FROM extracted_requests
        """)
        
        proposed_count = cursor.fetchone()[0]
        print(f"  • Предложенная логика находит: {proposed_count} записей")
        
        # 6. Сравниваем с нашей логикой
        print(f"\n📊 Сравнение логик:")
        print(f"  • Наша логика (user_requests): {total_requests} записей")
        print(f"  • Предложенная логика: {proposed_count} записей")
        
        # 7. Проверяем вторую часть предложенной логики
        print(f"\n🎯 Проверяем логику сопоставления с card_flow_started:")
        
        cursor = conn.execute("""
            WITH card_starts AS (
                SELECT 
                    id AS card_action_id,
                    user_id,
                    timestamp AS card_time
                FROM actions
                WHERE action = 'card_flow_started'
            ),
            text_requests AS (
                SELECT 
                    id AS request_action_id,
                    user_id,
                    username,
                    name,
                    action,
                    json_extract(details, '$.request') AS request_text,
                    timestamp AS request_time
                FROM actions
                WHERE 
                    action IN (
                        'typed_question_submitted',
                        'initial_response_provided',
                        'set_request',
                        'request_text_provided',
                        'initial_response',
                        'card_drawn_with_request'
                    )
                    AND json_extract(details, '$.request') IS NOT NULL
                    AND json_extract(details, '$.request') != ''
            ),
            matched_requests AS (
                SELECT 
                    c.user_id,
                    r.username,
                    r.name,
                    r.request_text,
                    r.request_time,
                    c.card_time,
                    ROW_NUMBER() OVER (PARTITION BY c.card_action_id ORDER BY r.request_time DESC) AS rn
                FROM card_starts c
                JOIN text_requests r
                  ON c.user_id = r.user_id
                 AND r.request_time < c.card_time
            )
            SELECT COUNT(*) as count
            FROM matched_requests
            WHERE rn = 1
        """)
        
        matched_count = cursor.fetchone()[0]
        print(f"  • Запросы перед картами: {matched_count} записей")
        
        # 8. Показываем примеры из нашей логики
        print(f"\n📝 Примеры из нашей логики (user_requests):")
        cursor = conn.execute("""
            SELECT ur.request_text, ur.timestamp, u.name, u.username, ur.user_id
            FROM user_requests ur 
            LEFT JOIN users u ON ur.user_id = u.user_id 
            ORDER BY ur.timestamp DESC 
            LIMIT 5
        """)
        
        examples = cursor.fetchall()
        for i, row in enumerate(examples, 1):
            name = row['name'] or "Неизвестный"
            username = f"@{row['username']}" if row['username'] else ""
            request_text = row['request_text'][:50] + "..." if len(row['request_text']) > 50 else row['request_text']
            print(f"  {i}. {name} {username}: {request_text}")
        
        # 9. Показываем примеры из предложенной логики
        print(f"\n📝 Примеры из предложенной логики:")
        cursor = conn.execute("""
            WITH relevant_actions AS (
                SELECT 
                    user_id,
                    username,
                    name,
                    action,
                    details,
                    timestamp
                FROM actions
                WHERE 
                    details LIKE '%request%' AND
                    action IN (
                        'typed_question_submitted',
                        'initial_response_provided',
                        'set_request',
                        'request_text_provided',
                        'initial_response',
                        'card_drawn_with_request'
                    )
            ),
            extracted_requests AS (
                SELECT
                    user_id,
                    username,
                    name,
                    json_extract(details, '$.request') AS request_text,
                    timestamp
                FROM relevant_actions
                WHERE json_extract(details, '$.request') IS NOT NULL
            )
            SELECT username, name, request_text, timestamp
            FROM extracted_requests
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        
        proposed_examples = cursor.fetchall()
        for i, row in enumerate(proposed_examples, 1):
            name = row['name'] or "Неизвестный"
            username = f"@{row['username']}" if row['username'] else ""
            request_text = row['request_text'][:50] + "..." if len(row['request_text']) > 50 else row['request_text']
            print(f"  {i}. {name} {username}: {request_text}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    analyze_request_logic() 