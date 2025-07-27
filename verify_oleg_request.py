#!/usr/bin/env python3
"""
Проверка записей Олега в user_requests
"""
import sqlite3
from datetime import datetime

def verify_oleg_request():
    """Проверяет записи Олега в user_requests"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🔍 Проверяем записи Олега (1740579634)")
        print(f"📁 БД: {db_path}")
        
        # Ищем записи Олега
        cursor = conn.execute("""
            SELECT ur.*, u.name, u.username
            FROM user_requests ur 
            LEFT JOIN users u ON ur.user_id = u.user_id 
            WHERE ur.user_id = 1740579634
            ORDER BY ur.timestamp DESC
        """)
        
        oleg_requests = cursor.fetchall()
        
        if oleg_requests:
            print(f"\n✅ Найдено {len(oleg_requests)} записей Олега:")
            for i, row in enumerate(oleg_requests, 1):
                name = row['name'] or "Неизвестный"
                username = f"@{row['username']}" if row['username'] else ""
                
                # Форматируем дату
                try:
                    dt = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                    formatted_date = dt.strftime("%d.%m.%Y %H:%M:%S")
                except:
                    formatted_date = row['timestamp']
                
                print(f"\n  {i}. ID: {row['id']}")
                print(f"     👤 {name} {username} (ID: {row['user_id']})")
                print(f"     📅 {formatted_date}")
                print(f"     💬 {row['request_text']}")
                print(f"     🆔 Session: {row['session_id']}")
                print(f"     🃏 Card: {row['card_number']}")
        else:
            print(f"\n❌ Записей Олега не найдено")
        
        # Проверяем общую статистику
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        total_requests = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(DISTINCT user_id) FROM user_requests")
        unique_users = cursor.fetchone()[0]
        
        print(f"\n📊 Общая статистика:")
        print(f"  • Всего запросов: {total_requests}")
        print(f"  • Уникальных пользователей: {unique_users}")
        
        # Показываем топ-5 пользователей по количеству запросов
        cursor = conn.execute("""
            SELECT ur.user_id, u.name, u.username, COUNT(*) as request_count
            FROM user_requests ur 
            LEFT JOIN users u ON ur.user_id = u.user_id 
            GROUP BY ur.user_id 
            ORDER BY request_count DESC 
            LIMIT 5
        """)
        
        top_users = cursor.fetchall()
        print(f"\n🏆 Топ-5 пользователей по количеству запросов:")
        for i, row in enumerate(top_users, 1):
            name = row['name'] or "Неизвестный"
            username = f"@{row['username']}" if row['username'] else ""
            print(f"  {i}. {name} {username} (ID: {row['user_id']}) - {row['request_count']} запросов")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    verify_oleg_request() 