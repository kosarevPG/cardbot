import sqlite3
from datetime import datetime

# Подключаемся к базе данных
conn = sqlite3.connect('database/dev.db')
conn.row_factory = sqlite3.Row

print("=== ПРОВЕРКА БАЗЫ ДАННЫХ ===\n")

# Проверяем таблицу mailings
cursor = conn.execute("SELECT * FROM mailings ORDER BY id DESC LIMIT 5")
mailings = cursor.fetchall()

print("Последние 5 рассылок:")
for row in mailings:
    print(f"ID: {row['id']}, Статус: {row['status']}, Запланировано: {row['scheduled_at']}, Создано: {row['created_at']}")

print("\n=== ПРОВЕРКА ОЖИДАЮЩИХ РАССЫЛОК ===")
cursor = conn.execute("""
    SELECT m.*, p.title as post_title 
    FROM mailings m 
    JOIN posts p ON m.post_id = p.id 
    WHERE m.status = 'pending'
""")
pending = cursor.fetchall()

print(f"Найдено ожидающих рассылок: {len(pending)}")
for row in pending:
    print(f"ID: {row['id']}, Статус: {row['status']}, Запланировано: {row['scheduled_at']}, Заголовок: {row['post_title']}")

print("\n=== ТЕКУЩЕЕ ВРЕМЯ В БАЗЕ ===")
cursor = conn.execute("SELECT datetime('now') as now, datetime('now', 'utc') as now_utc")
time_row = cursor.fetchone()
print(f"Локальное время: {time_row['now']}")
print(f"UTC время: {time_row['now_utc']}")

conn.close() 