#!/usr/bin/env python3
"""
Скрипт для миграции запросов из dump_production.db
"""
import sqlite3
import json
import sys
import os
from datetime import datetime
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import Database

def migrate_from_dump():
    """Мигрирует запросы из dump_production.db"""
    print("🔄 МИГРАЦИЯ ИЗ DUMP_PRODUCTION.DB")
    print("=" * 50)
    
    try:
        # Подключаемся к dump_production.db
        dump_conn = sqlite3.connect('database/dump_production.db')
        dump_conn.row_factory = sqlite3.Row
        
        # Подключаемся к основной БД
        db = Database('database/dev.db')
        
        # Ищем записи с запросами в actions
        print("🔍 Поиск запросов в таблице actions...")
        
        # 1. Ищем card_request с reflection_question
        cursor = dump_conn.execute("""
            SELECT user_id, username, name, details, timestamp
            FROM actions 
            WHERE action = 'card_request' 
            AND details LIKE '%reflection_question%'
        """)
        
        card_requests = cursor.fetchall()
        print(f"📊 Найдено card_request с текстом: {len(card_requests)}")
        
        # 2. Ищем set_request
        cursor = dump_conn.execute("""
            SELECT user_id, username, name, details, timestamp
            FROM actions 
            WHERE action = 'set_request'
        """)
        
        set_requests = cursor.fetchall()
        print(f"📊 Найдено set_request: {len(set_requests)}")
        
        # Мигрируем card_request
        migrated_count = 0
        skipped_count = 0
        
        print(f"\n📋 МИГРАЦИЯ card_request:")
        for row in card_requests:
            try:
                user_id = row['user_id']
                details = row['details']
                timestamp = row['timestamp']
                
                # Парсим JSON
                details_data = json.loads(details)
                reflection_question = details_data.get('reflection_question', '')
                card_number = details_data.get('card_number')
                
                if reflection_question:
                    # Генерируем session_id
                    session_id = f"migrated_dump_{uuid.uuid4().hex[:16]}"
                    
                    # Проверяем, есть ли уже такой запрос
                    cursor = db.conn.execute("""
                        SELECT COUNT(*) as count 
                        FROM user_requests 
                        WHERE user_id = ? AND request_text = ? AND timestamp = ?
                    """, (user_id, reflection_question, timestamp))
                    
                    if cursor.fetchone()['count'] == 0:
                        # Добавляем запрос
                        db.save_user_request(user_id, reflection_question, session_id, card_number)
                        migrated_count += 1
                        print(f"  ✅ Мигрирован запрос пользователя {user_id}: «{reflection_question[:30]}...»")
                    else:
                        skipped_count += 1
                        
            except Exception as e:
                print(f"  ❌ Ошибка миграции card_request: {e}")
                continue
        
        # Мигрируем set_request
        print(f"\n📋 МИГРАЦИЯ set_request:")
        for row in set_requests:
            try:
                user_id = row['user_id']
                details = row['details']
                timestamp = row['timestamp']
                
                # Парсим JSON
                details_data = json.loads(details)
                request_text = details_data.get('request', '')
                
                if request_text:
                    # Генерируем session_id
                    session_id = f"migrated_dump_{uuid.uuid4().hex[:16]}"
                    
                    # Проверяем, есть ли уже такой запрос
                    cursor = db.conn.execute("""
                        SELECT COUNT(*) as count 
                        FROM user_requests 
                        WHERE user_id = ? AND request_text = ? AND timestamp = ?
                    """, (user_id, request_text, timestamp))
                    
                    if cursor.fetchone()['count'] == 0:
                        # Добавляем запрос
                        db.save_user_request(user_id, request_text, session_id)
                        migrated_count += 1
                        print(f"  ✅ Мигрирован запрос пользователя {user_id}: «{request_text[:30]}...»")
                    else:
                        skipped_count += 1
                        
            except Exception as e:
                print(f"  ❌ Ошибка миграции set_request: {e}")
                continue
        
        # Проверяем результат
        cursor = db.conn.execute("SELECT COUNT(*) as count FROM user_requests")
        final_count = cursor.fetchone()['count']
        
        print(f"\n📊 РЕЗУЛЬТАТЫ МИГРАЦИИ:")
        print(f"  • card_request с текстом: {len(card_requests)}")
        print(f"  • set_request: {len(set_requests)}")
        print(f"  • Мигрировано: {migrated_count}")
        print(f"  • Пропущено (дубликаты): {skipped_count}")
        print(f"  • Всего в БД после миграции: {final_count}")
        
        # Показываем примеры
        print(f"\n📋 ПРИМЕРЫ МИГРИРОВАННЫХ ЗАПРОСОВ:")
        cursor = db.conn.execute("""
            SELECT ur.user_id, ur.request_text, ur.timestamp, u.name, u.username
            FROM user_requests ur
            LEFT JOIN users u ON ur.user_id = u.user_id
            WHERE ur.session_id LIKE 'migrated_dump_%'
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
        
        dump_conn.close()
        db.close()
        print("✅ МИГРАЦИЯ ИЗ DUMP ЗАВЕРШЕНА УСПЕШНО!")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_from_dump() 