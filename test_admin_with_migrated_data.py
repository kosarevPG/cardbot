#!/usr/bin/env python3
"""
Тестирование админской панели с мигрированными данными
"""
import sqlite3
import os
from datetime import datetime

def test_admin_panel():
    """Тестирует функциональность админской панели"""
    try:
        # Используем мигрированную БД
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print("🔍 Тестирование админской панели с мигрированными данными")
        print(f"📁 БД: {db_path}")
        
        # 1. Тестируем статистику запросов (как в show_admin_requests)
        print(f"\n📊 Статистика запросов (последние 7 дней):")
        
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_requests,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(LENGTH(request_text)) as avg_length,
                MIN(LENGTH(request_text)) as min_length,
                MAX(LENGTH(request_text)) as max_length
            FROM user_requests 
            WHERE timestamp >= datetime('now', '-7 days')
        """)
        
        stats = cursor.fetchone()
        print(f"  • Всего запросов: {stats['total_requests']}")
        print(f"  • Уникальных пользователей: {stats['unique_users']}")
        print(f"  • Средняя длина запроса: {stats['avg_length']:.1f} символов")
        print(f"  • Минимальная длина: {stats['min_length']} символов")
        print(f"  • Максимальная длина: {stats['max_length']} символов")
        
        # 2. Тестируем выборку запросов (как в show_admin_requests)
        print(f"\n📝 Последние запросы (как в админской панели):")
        
        cursor = conn.execute("""
            SELECT 
                ur.request_text,
                ur.timestamp,
                u.name,
                u.username,
                ur.user_id
            FROM user_requests ur 
            LEFT JOIN users u ON ur.user_id = u.user_id 
            ORDER BY ur.timestamp DESC 
            LIMIT 10
        """)
        
        requests = cursor.fetchall()
        for i, row in enumerate(requests, 1):
            name = row['name'] or "Неизвестный"
            username = f"@{row['username']}" if row['username'] else ""
            user_id = row['user_id']
            
            # Форматируем дату как в админской панели
            try:
                dt = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                formatted_date = dt.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = row['timestamp'][:16]
            
            # Обрезаем длинный текст
            request_text = row['request_text']
            if len(request_text) > 50:
                request_text = request_text[:50] + "..."
            
            print(f"  {i}. {formatted_date} | {name} {username} (ID: {user_id})")
            print(f"     💬 {request_text}")
        
        # 3. Тестируем полную выборку (как в show_admin_requests_full)
        print(f"\n📋 Полная выборка запросов (20 записей):")
        
        cursor = conn.execute("""
            SELECT 
                ur.request_text,
                ur.timestamp,
                u.name,
                u.username,
                ur.user_id,
                ur.card_number
            FROM user_requests ur 
            LEFT JOIN users u ON ur.user_id = u.user_id 
            ORDER BY ur.timestamp DESC 
            LIMIT 20
        """)
        
        full_requests = cursor.fetchall()
        for i, row in enumerate(full_requests, 1):
            name = row['name'] or "Неизвестный"
            username = f"@{row['username']}" if row['username'] else ""
            user_id = row['user_id']
            card_number = row['card_number'] or "N/A"
            
            # Форматируем дату
            try:
                dt = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                formatted_date = dt.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = row['timestamp'][:16]
            
            # Обрезаем длинный текст
            request_text = row['request_text']
            if len(request_text) > 60:
                request_text = request_text[:60] + "..."
            
            print(f"  {i}. {formatted_date} | {name} {username} (ID: {user_id}) | Карта: {card_number}")
            print(f"     💬 {request_text}")
        
        # 4. Тестируем статистику по пользователям
        print(f"\n👥 Статистика по пользователям:")
        
        cursor = conn.execute("""
            SELECT 
                u.name,
                u.username,
                ur.user_id,
                COUNT(*) as request_count
            FROM user_requests ur 
            LEFT JOIN users u ON ur.user_id = u.user_id 
            GROUP BY ur.user_id 
            ORDER BY request_count DESC 
            LIMIT 10
        """)
        
        user_stats = cursor.fetchall()
        for row in user_stats:
            name = row['name'] or "Неизвестный"
            username = f"@{row['username']}" if row['username'] else ""
            user_id = row['user_id']
            count = row['request_count']
            
            print(f"  • {name} {username} (ID: {user_id}): {count} запросов")
        
        conn.close()
        print(f"\n✅ Тестирование завершено успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    test_admin_panel() 