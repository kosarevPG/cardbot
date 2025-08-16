import sqlite3
from datetime import datetime
import pytz

# Подключаемся к базе данных
conn = sqlite3.connect('database/dev.db')
conn.row_factory = sqlite3.Row

print("=== ПРОВЕРКА ВРЕМЕНИ ===\n")

# Текущее время
now = datetime.now()
now_utc = datetime.now(pytz.UTC)
moscow_tz = pytz.timezone('Europe/Moscow')
now_moscow = now_utc.astimezone(moscow_tz)

print(f"Локальное время: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"UTC время: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Московское время: {now_moscow.strftime('%Y-%m-%d %H:%M:%S')}")

# Время в SQLite
cursor = conn.execute("SELECT datetime('now') as now, datetime('now', 'utc') as now_utc")
time_row = cursor.fetchone()
print(f"\nSQLite локальное: {time_row['now']}")
print(f"SQLite UTC: {time_row['now_utc']}")

# Проверяем рассылки
cursor = conn.execute("""
    SELECT m.id, m.status, m.scheduled_at, p.title
    FROM mailings m
    JOIN posts p ON m.post_id = p.id
    WHERE m.status = 'pending'
    ORDER BY m.scheduled_at ASC
""")
mailings = cursor.fetchall()

print(f"\n=== ОТЛОЖЕННЫЕ РАССЫЛКИ ===")
for row in mailings:
    print(f"ID: {row['id']}, Статус: {row['status']}, Запланировано: {row['scheduled_at']}, Заголовок: {row['title']}")

# Проверяем условие для каждой рассылки
print(f"\n=== ПРОВЕРКА УСЛОВИЙ ===")
for row in mailings:
    scheduled = row['scheduled_at']
    if scheduled:
        # Сравниваем с UTC временем SQLite
        condition = f"scheduled_at <= datetime('now')"
        cursor = conn.execute(f"SELECT {condition} as result")
        result = cursor.fetchone()
        print(f"ID {row['id']}: {scheduled} <= {time_row['now']} = {result['result']}")

conn.close() 