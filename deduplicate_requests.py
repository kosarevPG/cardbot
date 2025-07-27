#!/usr/bin/env python3
"""
Дедубликация запросов в user_requests
Оставляет только уникальные пары пользователь-запрос
"""
import sqlite3
import os
from datetime import datetime

def deduplicate_requests():
    """Удаляет дубликаты запросов, оставляя только уникальные пары пользователь-запрос"""
    try:
        db_path = "database/bot (20).db"
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        print(f"🧹 Дедубликация запросов в user_requests")
        print(f"📁 БД: {db_path}")
        
        # Проверяем текущее количество записей
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        total_before = cursor.fetchone()[0]
        print(f"📊 Записей до дедубликации: {total_before}")
        
        # Находим дубликаты
        print(f"\n🔍 Анализируем дубликаты...")
        cursor = conn.execute("""
            SELECT user_id, request_text, COUNT(*) as count
            FROM user_requests 
            GROUP BY user_id, request_text 
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)
        
        duplicates = cursor.fetchall()
        print(f"📋 Найдено {len(duplicates)} групп дубликатов:")
        
        total_duplicates = 0
        for row in duplicates:
            count = row['count']
            total_duplicates += count - 1  # -1 потому что одну запись оставляем
            print(f"  • User {row['user_id']}: '{row['request_text'][:50]}...' - {count} дубликатов")
        
        print(f"📊 Всего дубликатов для удаления: {total_duplicates}")
        
        if total_duplicates == 0:
            print("✅ Дубликатов не найдено!")
            return True
        
        # Создаем временную таблицу с уникальными записями
        print(f"\n🔄 Создаем временную таблицу с уникальными записями...")
        
        # Сначала создаем временную таблицу
        conn.execute("""
            CREATE TABLE user_requests_temp AS
            SELECT MIN(id) as id, user_id, request_text, MIN(timestamp) as timestamp, 
                   MIN(session_id) as session_id, MIN(card_number) as card_number
            FROM user_requests 
            GROUP BY user_id, request_text
        """)
        
        # Проверяем количество записей в временной таблице
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests_temp")
        unique_count = cursor.fetchone()[0]
        print(f"📊 Уникальных записей: {unique_count}")
        
        # Удаляем старую таблицу и переименовываем временную
        print(f"🔄 Заменяем таблицу...")
        conn.execute("DROP TABLE user_requests")
        conn.execute("ALTER TABLE user_requests_temp RENAME TO user_requests")
        
        # Восстанавливаем индексы
        print(f"🔧 Восстанавливаем индексы...")
        conn.execute("CREATE INDEX idx_user_requests_user_id ON user_requests(user_id)")
        conn.execute("CREATE INDEX idx_user_requests_timestamp ON user_requests(timestamp)")
        conn.execute("CREATE INDEX idx_user_requests_session_id ON user_requests(session_id)")
        
        # Сохраняем изменения
        conn.commit()
        
        # Проверяем результат
        cursor = conn.execute("SELECT COUNT(*) FROM user_requests")
        total_after = cursor.fetchone()[0]
        
        print(f"\n🎉 Дедубликация завершена!")
        print(f"📊 Записей до дедубликации: {total_before}")
        print(f"📊 Записей после дедубликации: {total_after}")
        print(f"🗑️ Удалено дубликатов: {total_before - total_after}")
        
        # Показываем примеры уникальных запросов
        cursor = conn.execute("""
            SELECT ur.request_text, ur.timestamp, u.name, u.username, ur.user_id
            FROM user_requests ur 
            LEFT JOIN users u ON ur.user_id = u.user_id 
            ORDER BY ur.timestamp DESC 
            LIMIT 10
        """)
        
        examples = cursor.fetchall()
        if examples:
            print(f"\n📝 Примеры уникальных запросов:")
            for i, row in enumerate(examples, 1):
                name = row['name'] or "Неизвестный"
                username = f"@{row['username']}" if row['username'] else ""
                user_id = row['user_id']
                
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
                
                print(f"  {i}. {formatted_date} | {name} {username} (ID: {user_id})")
                print(f"     💬 {request_text}")
        
        # Проверяем, что дубликатов больше нет
        cursor = conn.execute("""
            SELECT user_id, request_text, COUNT(*) as count
            FROM user_requests 
            GROUP BY user_id, request_text 
            HAVING COUNT(*) > 1
        """)
        
        remaining_duplicates = cursor.fetchall()
        if remaining_duplicates:
            print(f"\n⚠️ ВНИМАНИЕ: Остались дубликаты:")
            for row in remaining_duplicates:
                print(f"  • User {row['user_id']}: '{row['request_text'][:50]}...' - {row['count']} записей")
        else:
            print(f"\n✅ Дубликатов больше нет!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при дедубликации: {e}")
        return False

if __name__ == "__main__":
    success = deduplicate_requests()
    if success:
        print("\n✅ Дедубликация успешно завершена!")
    else:
        print("\n❌ Дедубликация завершилась с ошибками!") 