#!/usr/bin/env python3
"""
Скрипт для миграции запросов пользователей в production на Amvera
"""
import json
import sys
import os
from datetime import datetime
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import Database

def production_migrate_requests():
    """Мигрирует запросы пользователей в production"""
    print("🚀 МИГРАЦИЯ ЗАПРОСОВ В PRODUCTION")
    print("=" * 50)
    
    try:
        # Используем production БД
        db_path = "/data/bot.db"
        if not os.path.exists(db_path):
            print(f"❌ Production БД не найдена: {db_path}")
            print("Убедитесь, что скрипт запущен на Amvera")
            return
        
        print(f"📁 Используем production БД: {db_path}")
        db = Database(db_path)
        
        # Данные для миграции (из JSON файла)
        user_requests_data = {
            "6682555021": {
                "request": "Как мне найти ресурс?",
                "timestamp": "2025-04-06T21:07:36.372613+03:00"
            },
            "7494824111": {
                "request": "Не хочу писать",
                "timestamp": "2025-04-06T01:55:39.558176+03:00"
            },
            "7426810672": {
                "request": "Тест",
                "timestamp": "2025-04-06T13:21:31.142476+03:00"
            },
            "392141189": {
                "request": "Как долететь до отпуска",
                "timestamp": "2025-04-06T23:03:15.741951+03:00"
            },
            "1264280911": {
                "request": "правда ли  то, что я думаю???",
                "timestamp": "2025-04-06T11:01:29.725431+03:00"
            },
            "1887924167": {
                "request": "Как мне найти ресурс для выполнения задуманных целей",
                "timestamp": "2025-04-06T11:23:45.338265+03:00"
            },
            "171507422": {
                "request": "Тестовый запрос",
                "timestamp": "2025-04-06T16:53:08.063653+03:00"
            }
        }
        
        print(f"📄 Подготовлено {len(user_requests_data)} запросов для миграции")
        
        # Проверяем, есть ли уже записи в таблице user_requests
        cursor = db.conn.execute("SELECT COUNT(*) as count FROM user_requests")
        existing_count = cursor.fetchone()['count']
        print(f"📊 Существующих записей в production БД: {existing_count}")
        
        # Мигрируем данные
        migrated_count = 0
        skipped_count = 0
        
        for user_id_str, request_data in user_requests_data.items():
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
        
        print(f"\n📊 РЕЗУЛЬТАТЫ МИГРАЦИИ В PRODUCTION:")
        print(f"  • Подготовлено запросов: {len(user_requests_data)}")
        print(f"  • Мигрировано: {migrated_count}")
        print(f"  • Пропущено (дубликаты): {skipped_count}")
        print(f"  • Всего в production БД: {final_count}")
        
        # Показываем примеры мигрированных данных
        print(f"\n📋 ПРИМЕРЫ ЗАПРОСОВ В PRODUCTION:")
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
        print("✅ МИГРАЦИЯ В PRODUCTION ЗАВЕРШЕНА УСПЕШНО!")
        print("\n🎯 Теперь в админской панели будут отображаться все запросы!")
        
    except Exception as e:
        print(f"❌ Ошибка миграции в production: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    production_migrate_requests() 