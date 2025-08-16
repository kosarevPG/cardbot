#!/usr/bin/env python3
"""
Скрипт для анализа запросов пользователей в dump_production.db
"""
import sqlite3
import sys
import os
from datetime import datetime

def check_dump_requests():
    """Анализирует запросы пользователей в dump_production.db"""
    print("🔍 АНАЛИЗ ЗАПРОСОВ В DUMP_PRODUCTION.DB")
    print("=" * 50)
    
    try:
        db_path = "database/dump_production.db"
        if not os.path.exists(db_path):
            print(f"❌ Файл {db_path} не найден")
            return
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Проверяем таблицу user_requests
        print("📊 АНАЛИЗ ТАБЛИЦЫ user_requests:")
        print("-" * 40)
        
        # Количество записей
        cursor = conn.execute("SELECT COUNT(*) as count FROM user_requests")
        count = cursor.fetchone()['count']
        print(f"📈 Всего запросов: {count}")
        
        if count > 0:
            # Структура таблицы
            cursor = conn.execute("PRAGMA table_info(user_requests)")
            columns = cursor.fetchall()
            print(f"📝 Столбцы:")
            for col in columns:
                print(f"  • {col['name']} ({col['type']})")
            
            # Уникальные пользователи
            cursor = conn.execute("SELECT COUNT(DISTINCT user_id) as unique_users FROM user_requests")
            unique_users = cursor.fetchone()['unique_users']
            print(f"👥 Уникальных пользователей: {unique_users}")
            
            # Статистика по датам
            cursor = conn.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as requests_count
                FROM user_requests 
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
                LIMIT 5
            """)
            dates = cursor.fetchall()
            print(f"📅 Запросы по датам:")
            for row in dates:
                print(f"  • {row['date']}: {row['requests_count']} запросов")
            
            # Примеры запросов
            print(f"\n📋 ПРИМЕРЫ ЗАПРОСОВ:")
            cursor = conn.execute("""
                SELECT user_id, request_text, timestamp, session_id, card_number
                FROM user_requests 
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            
            for i, row in enumerate(cursor.fetchall(), 1):
                user_id = row['user_id']
                request_text = row['request_text']
                timestamp = row['timestamp']
                session_id = row['session_id']
                card_number = row['card_number']
                
                # Форматируем дату
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_date = timestamp
                
                print(f"\n🔸 ЗАПРОС #{i}")
                print(f"   📅 Дата: {formatted_date}")
                print(f"   👤 Пользователь: {user_id}")
                print(f"   🎴 Карта: {card_number}")
                print(f"   🔗 Session: {session_id}")
                print(f"   💬 Запрос: «{request_text}»")
                print(f"   {'─' * 50}")
            
            # Статистика по длине запросов
            cursor = conn.execute("""
                SELECT 
                    AVG(LENGTH(request_text)) as avg_length,
                    MIN(LENGTH(request_text)) as min_length,
                    MAX(LENGTH(request_text)) as max_length
                FROM user_requests
            """)
            stats = cursor.fetchone()
            print(f"\n📊 СТАТИСТИКА ПО ДЛИНЕ:")
            print(f"  • Средняя длина: {stats['avg_length']:.1f} символов")
            print(f"  • Минимум: {stats['min_length']} символов")
            print(f"  • Максимум: {stats['max_length']} символов")
            
        else:
            print("❌ В таблице user_requests нет данных")
        
        conn.close()
        print(f"\n✅ АНАЛИЗ ЗАВЕРШЕН")
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_dump_requests() 