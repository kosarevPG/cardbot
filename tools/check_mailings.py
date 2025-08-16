from database.db import Database
from datetime import datetime
import pytz

# Инициализируем базу данных
db = Database('database/dev.db')

print("=== ПРОВЕРКА ОТЛОЖЕННЫХ РАССЫЛОК ===\n")

# Получаем все рассылки
mailings = db.get_all_mailings(10)
print("Все рассылки:")
for m in mailings:
    print(f"ID: {m['id']}, Статус: {m['status']}, Запланировано: {m['scheduled_at']}, Заголовок: {m['post_title']}")

print("\n=== ОЖИДАЮЩИЕ РАССЫЛКИ ===")
pending = db.get_pending_mailings()
print(f"Найдено ожидающих рассылок: {len(pending)}")
for m in pending:
    print(f"ID: {m['id']}, Статус: {m['status']}, Запланировано: {m['scheduled_at']}, Заголовок: {m['post_title']}")

print("\n=== ТЕКУЩЕЕ ВРЕМЯ ===")
now_utc = datetime.now(pytz.UTC)
now_moscow = now_utc.astimezone(pytz.timezone('Europe/Moscow'))
print(f"UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Москва: {now_moscow.strftime('%Y-%m-%d %H:%M:%S')}")

db.close() 