import sqlite3
from datetime import datetime

# Подключаемся к базе данных
conn = sqlite3.connect('database/dev.db')
conn.row_factory = sqlite3.Row

print("=== ОТЛАДКА SQL ЗАПРОСА ===\n")

# Текущее время
cursor = conn.execute("SELECT datetime('now') as now, datetime('now', 'utc') as now_utc")
time_row = cursor.fetchone()
print(f"SQLite локальное: {time_row['now']}")
print(f"SQLite UTC: {time_row['now_utc']}")

# Проверяем все pending рассылки
cursor = conn.execute("""
    SELECT m.id, m.status, m.scheduled_at, p.title
    FROM mailings m
    JOIN posts p ON m.post_id = p.id
    WHERE m.status = 'pending'
    ORDER BY m.scheduled_at ASC
""")
all_pending = cursor.fetchall()

print(f"\nВсе pending рассылки: {len(all_pending)}")
for row in all_pending:
    print(f"ID: {row['id']}, Статус: {row['status']}, Запланировано: {row['scheduled_at']}, Заголовок: {row['title']}")

# Проверяем условие для каждой рассылки
print(f"\n=== ПРОВЕРКА УСЛОВИЙ ===")
for row in all_pending:
    scheduled = row['scheduled_at']
    if scheduled:
        # Проверяем условие scheduled_at <= datetime('now')
        cursor = conn.execute("""
            SELECT ? as scheduled, datetime('now') as now, 
                   ? <= datetime('now') as condition_result
        """, (scheduled, scheduled))
        result = cursor.fetchone()
        print(f"ID {row['id']}: {result['scheduled']} <= {result['now']} = {result['condition_result']}")

# Тестируем полный запрос get_pending_mailings
print(f"\n=== ТЕСТ ПОЛНОГО ЗАПРОСА ===")
cursor = conn.execute("""
    SELECT m.*, p.title as post_title, p.content as post_content, p.media_file_id
    FROM mailings m
    JOIN posts p ON m.post_id = p.id
    WHERE m.status = 'pending' 
    AND (m.scheduled_at IS NULL OR m.scheduled_at <= datetime('now'))
    ORDER BY m.created_at ASC
""")
results = cursor.fetchall()
print(f"Результат get_pending_mailings: {len(results)}")
for row in results:
    print(f"ID: {row['id']}, Статус: {row['status']}, Запланировано: {row['scheduled_at']}")

# Проверяем каждую часть запроса отдельно
print(f"\n=== ПРОВЕРКА ЧАСТЕЙ ЗАПРОСА ===")

# Только pending
cursor = conn.execute("""
    SELECT COUNT(*) as count
    FROM mailings m
    WHERE m.status = 'pending'
""")
result = cursor.fetchone()
print(f"Только pending: {result['count']}")

# Только условие времени
cursor = conn.execute("""
    SELECT COUNT(*) as count
    FROM mailings m
    WHERE m.scheduled_at IS NULL OR m.scheduled_at <= datetime('now')
""")
result = cursor.fetchone()
print(f"Только условие времени: {result['count']}")

# Оба условия
cursor = conn.execute("""
    SELECT COUNT(*) as count
    FROM mailings m
    WHERE m.status = 'pending' 
    AND (m.scheduled_at IS NULL OR m.scheduled_at <= datetime('now'))
""")
result = cursor.fetchone()
print(f"Оба условия: {result['count']}")

conn.close() 