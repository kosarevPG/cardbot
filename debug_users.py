#!/usr/bin/env python3
from config_local import NO_LOGS_USERS
from database.db import Database

print("=== ОТЛАДКА СТАТИСТИКИ ПОЛЬЗОВАТЕЛЕЙ ===")
print(f"NO_LOGS_USERS: {NO_LOGS_USERS}")

# Инициализируем БД
db = Database('database/dev.db')

# Получаем всех пользователей
all_users = db.get_all_users()
print(f"\nВсего пользователей в БД: {len(all_users)}")
for user_id in all_users:
    print(f"  User {user_id}")

# Исключаем админские ID
excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
filtered_users = [uid for uid in all_users if uid not in excluded_users]
print(f"\nПосле исключения админских ID: {len(filtered_users)}")
for user_id in filtered_users:
    print(f"  User {user_id}")

# Проверяем активных пользователей
excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""

cursor = db.conn.execute(f"""
    SELECT COUNT(DISTINCT user_id) as active_users
    FROM user_scenarios 
    WHERE started_at >= datetime('now', '-7 days')
    {excluded_condition}
""", list(excluded_users) if excluded_users else [])

active_users = cursor.fetchone()['active_users']
print(f"\nАктивных пользователей за 7 дней: {active_users}")

# Проверяем процент активности
activity_pct = (active_users/len(filtered_users)*100) if len(filtered_users) > 0 else 0
print(f"Процент активности: {activity_pct:.1f}%")

db.close() 