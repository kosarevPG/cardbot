#!/usr/bin/env python3
"""
Финальное сравнение логик сбора запросов
"""
import sqlite3
import json

def final_comparison():
    """Финальное сравнение логик"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🎯 Финальное сравнение логик")
        print(f"📁 БД: {db_path}")
        
        # 1. Наша логика
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        our_total = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(DISTINCT user_id) FROM user_requests")
        our_users = cursor.fetchone()[0]
        
        print(f"\n📊 Наша логика (user_requests):")
        print(f"  • Всего запросов: {our_total}")
        print(f"  • Уникальных пользователей: {our_users}")
        
        # 2. Предложенная логика
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
        
        proposed_total = cursor.fetchone()[0]
        
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
            SELECT COUNT(DISTINCT user_id) as count
            FROM extracted_requests
        """)
        
        proposed_users = cursor.fetchone()[0]
        
        print(f"\n📊 Предложенная логика:")
        print(f"  • Всего запросов: {proposed_total}")
        print(f"  • Уникальных пользователей: {proposed_users}")
        
        # 3. Логика с картами
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
        
        card_total = cursor.fetchone()[0]
        
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
            SELECT COUNT(DISTINCT user_id) as count
            FROM matched_requests
            WHERE rn = 1
        """)
        
        card_users = cursor.fetchone()[0]
        
        print(f"\n📊 Логика с картами:")
        print(f"  • Запросы перед картами: {card_total}")
        print(f"  • Уникальных пользователей: {card_users}")
        
        # 4. Сравнение
        print(f"\n📈 Сравнение:")
        print(f"  • Наша логика vs Предложенная: {our_total} vs {proposed_total} ({our_total - proposed_total:+d})")
        print(f"  • Наша логика vs Карты: {our_total} vs {card_total} ({our_total - card_total:+d})")
        print(f"  • Предложенная vs Карты: {proposed_total} vs {card_total} ({proposed_total - card_total:+d})")
        
        # 5. Что у нас есть дополнительно
        print(f"\n🔍 Что у нас есть дополнительно:")
        
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
        
        extra_actions = cursor.fetchall()
        if extra_actions:
            for row in extra_actions:
                print(f"  • {row['action']}: {row['count']} записей")
        else:
            print(f"  • Дополнительных типов действий нет")
        
        # 6. Топ пользователей
        print(f"\n🏆 Топ-5 пользователей по количеству запросов:")
        cursor = conn.execute("""
            SELECT ur.user_id, u.name, u.username, COUNT(*) as request_count
            FROM user_requests ur 
            LEFT JOIN users u ON ur.user_id = u.user_id 
            GROUP BY ur.user_id 
            ORDER BY request_count DESC 
            LIMIT 5
        """)
        
        top_users = cursor.fetchall()
        for i, row in enumerate(top_users, 1):
            name = row['name'] or "Неизвестный"
            username = f"@{row['username']}" if row['username'] else ""
            print(f"  {i}. {name} {username} (ID: {row['user_id']}) - {row['request_count']} запросов")
        
        # 7. Итоговая рекомендация
        print(f"\n💡 Итоговая рекомендация:")
        if our_total >= proposed_total:
            print(f"  ✅ Наша логика более полная - собрали {our_total} запросов")
            print(f"     (включая дополнительные типы действий)")
        else:
            print(f"  ⚠️ Предложенная логика более полная - {proposed_total} запросов")
        
        if card_total < our_total:
            print(f"  📊 Логика с картами исключает {our_total - card_total} запросов")
            print(f"     (запросы без последующего card_flow_started)")
        
        print(f"  🎯 Рекомендуем использовать нашу логику для максимальной полноты данных")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    final_comparison() 