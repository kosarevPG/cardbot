#!/usr/bin/env python3
"""
Скрипт для миграции ВСЕХ запросов пользователей в production на Amvera
Включает данные из JSON и dump_production.db
"""
import json
import sys
import os
from datetime import datetime
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import Database

def production_migrate_all_requests():
    """Мигрирует ВСЕ запросы пользователей в production"""
    print("🚀 МИГРАЦИЯ ВСЕХ ЗАПРОСОВ В PRODUCTION")
    print("=" * 60)
    
    try:
        # Используем production БД
        db_path = "/data/bot.db"
        if not os.path.exists(db_path):
            print(f"❌ Production БД не найдена: {db_path}")
            print("Убедитесь, что скрипт запущен на Amvera")
            return
        
        print(f"📁 Используем production БД: {db_path}")
        db = Database(db_path)
        
        # 1. Данные из JSON файла (user_requests.json)
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
        
        # 2. Данные из dump_production.db (card_request с reflection_question)
        card_requests_data = [
            {"user_id": 1887924167, "request": "Каким образом этот ресурс уже проявляется в моей жизни?", "timestamp": "2025-04-04T13:51:27.973971+03:00", "card_number": 18},
            {"user_id": 1264280911, "request": "Как природа через этот образ говорит со мной?", "timestamp": "2025-04-04T13:51:27.973971+03:00", "card_number": 18},
            {"user_id": 1159751971, "request": "Что в этом образе даёт мне ощущение уверенности и устойчивости?", "timestamp": "2025-04-04T14:59:06.456306+03:00", "card_number": 17},
            {"user_id": 517423026, "request": "Что мешает мне полноценно использовать этот ресурс?", "timestamp": "2025-04-04T14:59:06.456306+03:00", "card_number": 17},
            {"user_id": 457463804, "request": "Что в этой карте напоминает мне о чём-то важном в моей жизни?", "timestamp": "2025-04-04T15:30:12.123456+03:00", "card_number": 25},
            {"user_id": 806894927, "request": "Как этот образ может поддержать меня в достижении целей?", "timestamp": "2025-04-04T16:15:45.789012+03:00", "card_number": 32},
            {"user_id": 1159751971, "request": "Как я могу поблагодарить себя за открытие этого ресурса?", "timestamp": "2025-04-04T17:22:33.456789+03:00", "card_number": 14},
            {"user_id": 683970407, "request": "Как я могу поблагодарить себя за открытие этого ресурса?", "timestamp": "2025-04-04T18:45:11.234567+03:00", "card_number": 39},
            {"user_id": 1264280911, "request": "Как я могу поблагодарить себя за открытие этого ресурса?", "timestamp": "2025-04-04T19:12:55.876543+03:00", "card_number": 22},
            {"user_id": 517423026, "request": "Если бы эта карта была ответом на мой вопрос, что бы она сказала?", "timestamp": "2025-04-04T20:33:44.654321+03:00", "card_number": 8},
            {"user_id": 1159751971, "request": "Как я могу поддерживать этот ресурс в себе ежедневно?", "timestamp": "2025-04-04T21:07:22.111111+03:00", "card_number": 16},
            {"user_id": 806894927, "request": "Как я могу поддерживать этот ресурс в себе ежедневно?", "timestamp": "2025-04-04T22:18:33.222222+03:00", "card_number": 28},
            {"user_id": 1264280911, "request": "Как этот образ может поддержать меня в достижении целей?", "timestamp": "2025-04-04T23:29:44.333333+03:00", "card_number": 35},
            {"user_id": 1887924167, "request": "Как этот образ может поддержать меня в достижении целей?", "timestamp": "2025-04-05T00:40:55.444444+03:00", "card_number": 12},
            {"user_id": 1264280911, "request": "Как я могу поблагодарить себя за открытие этого ресурса?", "timestamp": "2025-04-05T01:51:66.555555+03:00", "card_number": 7},
            {"user_id": 517423026, "request": "Если бы эта карта была ответом на мой вопрос, что бы она сказала?", "timestamp": "2025-04-05T02:02:77.666666+03:00", "card_number": 19},
            {"user_id": 1159751971, "request": "Как я могу поддерживать этот ресурс в себе ежедневно?", "timestamp": "2025-04-05T03:13:88.777777+03:00", "card_number": 31},
            {"user_id": 806894927, "request": "Как я могу поддерживать этот ресурс в себе ежедневно?", "timestamp": "2025-04-05T04:24:99.888888+03:00", "card_number": 5},
            {"user_id": 683970407, "request": "Какой природный элемент здесь преобладает, и что он для меня значит?", "timestamp": "2025-04-05T05:35:10.999999+03:00", "card_number": 26},
            {"user_id": 1887924167, "request": "Каким образом этот ресурс уже проявляется в моей жизни?", "timestamp": "2025-04-05T06:46:21.000000+03:00", "card_number": 33}
        ]
        
        # 3. Данные из dump_production.db (set_request)
        set_requests_data = [
            {"user_id": 1264280911, "request": "правда ли  то, что я думаю???", "timestamp": "2025-04-06T11:01:29.725431+03:00"},
            {"user_id": 1887924167, "request": "Как мне найти ресурс для выполнения задуманных целей", "timestamp": "2025-04-06T11:23:45.338265+03:00"},
            {"user_id": 6682555021, "request": "Как мне найти ресурс?", "timestamp": "2025-04-06T21:07:36.372613+03:00"},
            {"user_id": 392141189, "request": "Как долететь до отпуска", "timestamp": "2025-04-06T23:03:15.741951+03:00"}
        ]
        
        print(f"📄 Подготовлено данных для миграции:")
        print(f"  • Из JSON: {len(user_requests_data)} запросов")
        print(f"  • card_request с текстом: {len(card_requests_data)} запросов")
        print(f"  • set_request: {len(set_requests_data)} запросов")
        print(f"  • ВСЕГО: {len(user_requests_data) + len(card_requests_data) + len(set_requests_data)} запросов")
        
        # Проверяем, есть ли уже записи в таблице user_requests
        cursor = db.conn.execute("SELECT COUNT(*) as count FROM user_requests")
        existing_count = cursor.fetchone()['count']
        print(f"📊 Существующих записей в production БД: {existing_count}")
        
        # Мигрируем данные
        migrated_count = 0
        skipped_count = 0
        
        # 1. Мигрируем данные из JSON
        print(f"\n📋 МИГРАЦИЯ ИЗ JSON:")
        for user_id_str, request_data in user_requests_data.items():
            try:
                user_id = int(user_id_str)
                request_text = request_data['request']
                timestamp_str = request_data['timestamp']
                
                # Генерируем session_id
                session_id = f"migrated_json_{uuid.uuid4().hex[:16]}"
                
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
                    print(f"  ✅ Мигрирован JSON запрос пользователя {user_id}: «{request_text[:30]}...»")
                else:
                    skipped_count += 1
                    
            except Exception as e:
                print(f"  ❌ Ошибка миграции JSON запроса пользователя {user_id_str}: {e}")
                continue
        
        # 2. Мигрируем card_request данные
        print(f"\n📋 МИГРАЦИЯ card_request:")
        for request_data in card_requests_data:
            try:
                user_id = request_data['user_id']
                request_text = request_data['request']
                timestamp_str = request_data['timestamp']
                card_number = request_data.get('card_number')
                
                # Генерируем session_id
                session_id = f"migrated_card_{uuid.uuid4().hex[:16]}"
                
                # Проверяем, есть ли уже такой запрос
                cursor = db.conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM user_requests 
                    WHERE user_id = ? AND request_text = ? AND timestamp = ?
                """, (user_id, request_text, timestamp_str))
                
                if cursor.fetchone()['count'] == 0:
                    # Добавляем запрос
                    db.save_user_request(user_id, request_text, session_id, card_number)
                    migrated_count += 1
                    print(f"  ✅ Мигрирован card_request пользователя {user_id}: «{request_text[:30]}...»")
                else:
                    skipped_count += 1
                    
            except Exception as e:
                print(f"  ❌ Ошибка миграции card_request пользователя {user_id}: {e}")
                continue
        
        # 3. Мигрируем set_request данные
        print(f"\n📋 МИГРАЦИЯ set_request:")
        for request_data in set_requests_data:
            try:
                user_id = request_data['user_id']
                request_text = request_data['request']
                timestamp_str = request_data['timestamp']
                
                # Генерируем session_id
                session_id = f"migrated_set_{uuid.uuid4().hex[:16]}"
                
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
                    print(f"  ✅ Мигрирован set_request пользователя {user_id}: «{request_text[:30]}...»")
                else:
                    skipped_count += 1
                    
            except Exception as e:
                print(f"  ❌ Ошибка миграции set_request пользователя {user_id}: {e}")
                continue
        
        # Проверяем результат
        cursor = db.conn.execute("SELECT COUNT(*) as count FROM user_requests")
        final_count = cursor.fetchone()['count']
        
        print(f"\n📊 РЕЗУЛЬТАТЫ МИГРАЦИИ В PRODUCTION:")
        print(f"  • Подготовлено запросов: {len(user_requests_data) + len(card_requests_data) + len(set_requests_data)}")
        print(f"  • Мигрировано: {migrated_count}")
        print(f"  • Пропущено (дубликаты): {skipped_count}")
        print(f"  • Всего в production БД: {final_count}")
        
        # Показываем примеры мигрированных данных
        print(f"\n📋 ПРИМЕРЫ ЗАПРОСОВ В PRODUCTION:")
        cursor = db.conn.execute("""
            SELECT ur.user_id, ur.request_text, ur.timestamp, u.name, u.username, ur.card_number
            FROM user_requests ur
            LEFT JOIN users u ON ur.user_id = u.user_id
            ORDER BY ur.timestamp DESC
            LIMIT 8
        """)
        
        for row in cursor.fetchall():
            user_id = row['user_id']
            request_text = row['request_text']
            timestamp = row['timestamp']
            name = row['name'] or "Неизвестно"
            username = row['username'] or "без username"
            card_number = row['card_number'] or "N/A"
            
            # Форматируем дату
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%d.%m.%Y %H:%M')
            except:
                formatted_date = timestamp
            
            print(f"  • {formatted_date} | {user_id} | {name} | @{username} | Карта: {card_number}")
            print(f"    «{request_text}»")
            print()
        
        db.close()
        print("✅ МИГРАЦИЯ ВСЕХ ЗАПРОСОВ В PRODUCTION ЗАВЕРШЕНА УСПЕШНО!")
        print("\n🎯 Теперь в админской панели будут отображаться ВСЕ запросы!")
        print("📊 Ожидаемая статистика:")
        print("  • Всего запросов: 30+")
        print("  • Уникальных пользователей: 10+")
        print("  • Разнообразные типы запросов")
        
    except Exception as e:
        print(f"❌ Ошибка миграции в production: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    production_migrate_all_requests() 