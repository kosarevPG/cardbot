#!/usr/bin/env python3
"""
Детальное сравнение логик сбора запросов
"""
import sqlite3
import json

def compare_logics():
    """Сравнивает нашу логику с предложенной"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🔍 Детальное сравнение логик")
        print(f"📁 БД: {db_path}")
        
        # 1. Проверяем, какие типы действий мы использовали
        print(f"\n📋 Наша логика - использованные типы действий:")
        
        # Проверяем, какие типы действий есть в user_requests
        cursor = conn.execute("""
            SELECT DISTINCT a.action, COUNT(*) as count
            FROM user_requests ur
            JOIN actions a ON ur.user_id = a.user_id 
                AND ur.request_text = json_extract(a.details, '$.request')
                AND ur.timestamp = a.timestamp
            GROUP BY a.action
            ORDER BY count DESC
        """)
        
        our_actions = cursor.fetchall()
        for row in our_actions:
            print(f"  • {row['action']}: {row['count']} записей")
        
        # 2. Проверяем предложенные типы действий
        print(f"\n📋 Предложенная логика - типы действий:")
        proposed_actions = [
            'typed_question_submitted',
            'initial_response_provided', 
            'set_request',
            'request_text_provided',
            'initial_response',
            'card_drawn_with_request'
        ]
        
        for action_type in proposed_actions:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM actions 
                WHERE action = ? AND json_extract(details, '$.request') IS NOT NULL
            """, (action_type,))
            count = cursor.fetchone()[0]
            print(f"  • {action_type}: {count} записей")
        
        # 3. Проверяем, что мы пропустили
        print(f"\n🔍 Что мы пропустили:")
        
        cursor = conn.execute("""
            SELECT action, COUNT(*) as count
            FROM actions 
            WHERE action IN (
                'typed_question_submitted',
                'initial_response_provided', 
                'set_request',
                'request_text_provided',
                'initial_response',
                'card_drawn_with_request'
            )
            AND json_extract(details, '$.request') IS NOT NULL
            AND json_extract(details, '$.request') != ''
            GROUP BY action
            ORDER BY count DESC
        """)
        
        proposed_total = cursor.fetchall()
        total_proposed = sum(row['count'] for row in proposed_total)
        print(f"  • Всего в предложенной логике: {total_proposed}")
        
        # 4. Проверяем, что у нас есть, но нет в предложенной
        print(f"\n🔍 Что у нас есть, но нет в предложенной логике:")
        
        cursor = conn.execute("""
            SELECT action, COUNT(*) as count
            FROM actions 
            WHERE action NOT IN (
                'typed_question_submitted',
                'initial_response_provided', 
                'set_request',
                'request_text_provided',
                'initial_response',
                'card_drawn_with_request'
            )
            AND json_extract(details, '$.request') IS NOT NULL
            AND json_extract(details, '$.request') != ''
            GROUP BY action
            ORDER BY count DESC
        """)
        
        our_extra = cursor.fetchall()
        for row in our_extra:
            print(f"  • {row['action']}: {row['count']} записей")
        
        # 5. Проверяем логику с card_flow_started
        print(f"\n🎯 Логика с card_flow_started:")
        
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
        
        card_matched = cursor.fetchone()[0]
        print(f"  • Запросы перед картами: {card_matched}")
        
        # 6. Показываем примеры запросов перед картами
        print(f"\n📝 Примеры запросов перед картами:")
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
            SELECT username, name, request_text, request_time, card_time
            FROM matched_requests
            WHERE rn = 1
            ORDER BY card_time DESC
            LIMIT 5
        """)
        
        card_examples = cursor.fetchall()
        for i, row in enumerate(card_examples, 1):
            name = row['name'] or "Неизвестный"
            username = f"@{row['username']}" if row['username'] else ""
            request_text = row['request_text'][:50] + "..." if len(row['request_text']) > 50 else row['request_text']
            print(f"  {i}. {name} {username}: {request_text}")
            print(f"     📅 Запрос: {row['request_time'][:16]} | Карта: {row['card_time'][:16]}")
        
        # 7. Рекомендации
        print(f"\n💡 Рекомендации:")
        print(f"  • Наша логика: {475} записей")
        print(f"  • Предложенная логика: {total_proposed} записей")
        print(f"  • Логика с картами: {card_matched} записей")
        
        if card_matched < total_proposed:
            print(f"  ⚠️ Логика с картами исключает {total_proposed - card_matched} запросов")
            print(f"     (запросы без последующего card_flow_started)")
        
        if total_proposed > 475:
            print(f"  ⚠️ Мы пропустили {total_proposed - 475} запросов")
            print(f"     (не все типы действий были учтены)")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    compare_logics() 