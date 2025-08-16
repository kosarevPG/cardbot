#!/usr/bin/env python3
"""
Скрипт для миграции запросов пользователей из JSON в SQLite БД
"""
import json
import sys
import os
from datetime import datetime
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import Database

def migrate_user_requests():
    """Мигрирует запросы пользователей из JSON в SQLite"""
    print("🔄 МИГРАЦИЯ ЗАПРОСОВ ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 50)
    
    try:
        # Загружаем данные из JSON
        json_file = "data/user_requests.json"
        if not os.path.exists(json_file):
            print(f"❌ Файл {json_file} не найден")
            return
        
        with open(json_file, 'r', encoding='utf-8') as f:
            user_requests = json.load(f)
        
        print(f"📄 Загружено {len(user_requests)} запросов из JSON")
        
        # Подключаемся к БД
        db = Database('database/dev.db')
        
        # Проверяем, есть ли уже записи в таблице user_requests
        cursor = db.conn.execute("SELECT COUNT(*) as count FROM user_requests")
        existing_count = cursor.fetchone()['count']
        print(f"📊 Существующих записей в БД: {existing_count}")
        
        # Мигрируем данные
        migrated_count = 0
        skipped_count = 0
        
        for user_id_str, request_data in user_requests.items():
            try:
                user_id = int(user_id_str)
                request_text = request_data['request']
                timestamp_str = request_data['timestamp']
                
                # Генерируем session_id для старых запросов
                session_id = f"migrated_{uuid.uuid4().hex[:16]}"
                
                # Проверяем, есть ли уже такой запрос
                cursor = db.conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM user_requests 
                    WHERE user_id = ? AND request_text = ? AND timestamp = ?
                """, (user_id, request_text, timestamp_str))
                
                if cursor.fetchone()['count'] == 0:
                    # Добавляем запрос
                    db.save_user_request(user_id, request_text, session_id)
                    migrated_count += 1
                    print(f"  ✅ Мигрирован запрос пользователя {user_id}: «{request_text[:30]}...»")
                else:
                    skipped_count += 1
                    print(f"  ⏭️ Пропущен дубликат для пользователя {user_id}")
                    
            except Exception as e:
                print(f"  ❌ Ошибка миграции запроса пользователя {user_id_str}: {e}")
                continue
        
        # Проверяем результат
        cursor = db.conn.execute("SELECT COUNT(*) as count FROM user_requests")
        final_count = cursor.fetchone()['count']
        
        print(f"\n📊 РЕЗУЛЬТАТЫ МИГРАЦИИ:")
        print(f"  • Загружено из JSON: {len(user_requests)}")
        print(f"  • Мигрировано: {migrated_count}")
        print(f"  • Пропущено (дубликаты): {skipped_count}")
        print(f"  • Всего в БД после миграции: {final_count}")
        
        # Показываем примеры мигрированных данных
        print(f"\n📋 ПРИМЕРЫ МИГРИРОВАННЫХ ЗАПРОСОВ:")
        cursor = db.conn.execute("""
            SELECT ur.user_id, ur.request_text, ur.timestamp, u.name, u.username
            FROM user_requests ur
            LEFT JOIN users u ON ur.user_id = u.user_id
            ORDER BY ur.timestamp DESC
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            user_id = row['user_id']
            request_text = row['request_text']
            timestamp = row['timestamp']
            name = row['name'] or "Неизвестно"
            username = row['username'] or "без username"
            
            # Форматируем дату
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%d.%m.%Y %H:%M')
            except:
                formatted_date = timestamp
            
            print(f"  • {formatted_date} | {user_id} | {name} | @{username}")
            print(f"    «{request_text}»")
            print()
        
        db.close()
        print("✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_user_requests() 