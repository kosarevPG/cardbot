#!/usr/bin/env python3
"""
Проверка пропущенных типов запросов в actions
"""
import sqlite3
import json
import os

def check_missing_requests():
    """Проверяет пропущенные типы запросов"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print("🔍 Проверка пропущенных типов запросов")
        print(f"📁 БД: {db_path}")
        
        # Проверяем все типы действий с 'request' в details
        action_types = [
            'typed_question_submitted',
            'initial_response_provided', 
            'set_request',
            'request_text_provided',
            'initial_response',
            'card_drawn_with_request'
        ]
        
        for action_type in action_types:
            print(f"\n📝 Проверяем {action_type}:")
            
            cursor = conn.execute("""
                SELECT user_id, details, timestamp 
                FROM actions 
                WHERE action = ? 
                AND details LIKE '%request%'
                ORDER BY timestamp DESC
            """, (action_type,))
            
            records = cursor.fetchall()
            print(f"  🔍 Найдено {len(records)} записей")
            
            if records:
                print(f"  📋 Примеры записей:")
                for i, row in enumerate(records[:3], 1):  # Показываем первые 3
                    try:
                        details = json.loads(row['details'])
                        print(f"    {i}. User ID: {row['user_id']}")
                        print(f"       Timestamp: {row['timestamp']}")
                        print(f"       Details: {details}")
                        print()
                    except Exception as e:
                        print(f"    {i}. User ID: {row['user_id']}")
                        print(f"       Timestamp: {row['timestamp']}")
                        print(f"       Raw details: {row['details']}")
                        print(f"       Error parsing: {e}")
                        print()
        
        # Также проверим общий запрос
        print(f"\n🔍 Общий поиск всех записей с 'request' в details:")
        cursor = conn.execute("""
            SELECT action, COUNT(*) as count 
            FROM actions 
            WHERE details LIKE '%request%'
            GROUP BY action 
            ORDER BY count DESC
        """)
        
        all_request_actions = cursor.fetchall()
        print(f"  📊 Статистика по типам действий:")
        for row in all_request_actions:
            print(f"    • {row['action']}: {row['count']} записей")
        
        # Проверим, что уже мигрировано
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        migrated_count = cursor.fetchone()[0]
        print(f"\n📊 Уже мигрировано в user_requests: {migrated_count} записей")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")

if __name__ == "__main__":
    check_missing_requests() 