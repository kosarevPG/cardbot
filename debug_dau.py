#!/usr/bin/env python3
from config_local import NO_LOGS_USERS
from database.db import Database

print("=== ОТЛАДКА DAU МЕТРИК ===")
print(f"NO_LOGS_USERS: {NO_LOGS_USERS}")
print(f"6682555021 in NO_LOGS_USERS: {6682555021 in NO_LOGS_USERS}")

# Инициализируем БД
db = Database('database/dev.db')

# Проверяем DAU без исключений
print("\n=== DAU БЕЗ ИСКЛЮЧЕНИЙ ===")
cursor = db.conn.execute("""
    SELECT 
        DATE(started_at) as date,
        COUNT(DISTINCT user_id) as dau
    FROM user_scenarios 
    WHERE started_at >= datetime('now', '-7 days')
    GROUP BY DATE(started_at)
    ORDER BY date DESC
""")
daily_data = [dict(row) for row in cursor.fetchall()]
print(f"Всего записей: {len(daily_data)}")
for row in daily_data:
    print(f"  {row['date']}: {row['dau']}")

# Проверяем DAU с исключениями
print("\n=== DAU С ИСКЛЮЧЕНИЯМИ ===")
excluded_users = NO_LOGS_USERS
excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
print(f"excluded_condition: {excluded_condition}")
print(f"params: {list(excluded_users)}")

cursor = db.conn.execute(f"""
    SELECT 
        DATE(started_at) as date,
        COUNT(DISTINCT user_id) as dau
    FROM user_scenarios 
    WHERE started_at >= datetime('now', '-7 days')
    {excluded_condition}
    GROUP BY DATE(started_at)
    ORDER BY date DESC
""", list(excluded_users) if excluded_users else [])

daily_data = [dict(row) for row in cursor.fetchall()]
print(f"Всего записей после исключения: {len(daily_data)}")
for row in daily_data:
    print(f"  {row['date']}: {row['dau']}")

# Проверяем все записи в user_scenarios
print("\n=== ВСЕ ЗАПИСИ В USER_SCENARIOS ===")
cursor = db.conn.execute("""
    SELECT user_id, DATE(started_at) as date, scenario
    FROM user_scenarios 
    WHERE started_at >= datetime('now', '-7 days')
    ORDER BY started_at DESC
""")
all_records = cursor.fetchall()
print(f"Всего записей: {len(all_records)}")
for record in all_records:
    print(f"  User {record['user_id']}: {record['date']} - {record['scenario']}")

# Проверяем конкретно пользователя 171507422
print("\n=== ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ 171507422 ===")
cursor = db.conn.execute("""
    SELECT user_id, DATE(started_at) as date, scenario
    FROM user_scenarios 
    WHERE user_id = 171507422
    AND started_at >= datetime('now', '-7 days')
    ORDER BY started_at DESC
""")
user_171507422_records = cursor.fetchall()
print(f"Записей для 171507422: {len(user_171507422_records)}")
for record in user_171507422_records:
    print(f"  User {record['user_id']}: {record['date']} - {record['scenario']}")

# Проверяем SQL запрос вручную
print("\n=== РУЧНАЯ ПРОВЕРКА SQL ===")
excluded_users = NO_LOGS_USERS
excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""

# Выводим полный SQL запрос
sql_query = f"""
    SELECT 
        DATE(started_at) as date,
        COUNT(DISTINCT user_id) as dau
    FROM user_scenarios 
    WHERE started_at >= datetime('now', '-7 days')
    {excluded_condition}
    GROUP BY DATE(started_at)
    ORDER BY date DESC
"""
print(f"SQL запрос: {sql_query}")
print(f"Параметры: {list(excluded_users)}")

# Проверяем каждый пользователь отдельно
print("\n=== ПРОВЕРКА КАЖДОГО ПОЛЬЗОВАТЕЛЯ ===")
for user_id in [6682555021, 171507422]:
    print(f"\nПользователь {user_id}:")
    print(f"  В NO_LOGS_USERS: {user_id in NO_LOGS_USERS}")
    
    cursor = db.conn.execute("""
        SELECT COUNT(*) as count
        FROM user_scenarios 
        WHERE user_id = ?
        AND started_at >= datetime('now', '-7 days')
    """, (user_id,))
    count = cursor.fetchone()['count']
    print(f"  Записей в БД: {count}")

db.close() 