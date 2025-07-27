import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.post_management import PostManager
from database.db import Database
from datetime import datetime, timedelta
import pytz

# Инициализируем компоненты
db = Database('database/dev.db')

# Создаем заглушку для бота и логгера
class MockBot:
    async def send_message(self, chat_id, text, **kwargs):
        print(f"📤 Отправлено сообщение пользователю {chat_id}: {text[:50]}...")
        return True

class MockLogger:
    def info(self, msg):
        print(f"ℹ️ {msg}")
    def error(self, msg):
        print(f"❌ {msg}")

# Создаем PostManager
post_manager = PostManager(db, MockBot(), MockLogger())

print("=== ТЕСТ СОЗДАНИЯ ОТЛОЖЕННОЙ РАССЫЛКИ ===\n")

# Создаем тестовый пост
post_id = post_manager.create_post(
    title="Тестовый отложенный пост 2",
    content="<b>Тестовый отложенный пост 2</b>\n\nЭто тестовое содержание для проверки отложенной отправки.",
    created_by=6682555021
)

print(f"Создан пост с ID: {post_id}")

# Создаем отложенную рассылку на 1 минуту вперед
future_time = datetime.now() + timedelta(minutes=1)
scheduled_at = future_time.strftime("%Y-%m-%d %H:%M")

print(f"Запланированное время (Москва): {scheduled_at}")

mailing_id = post_manager.create_mailing(
    post_id=post_id,
    title="Тестовый отложенный пост 2",
    send_to_all=True,
    created_by=6682555021,
    scheduled_at=scheduled_at
)

print(f"Создана рассылка с ID: {mailing_id}")

# Проверяем, что рассылка создалась
mailing = post_manager.get_mailing(mailing_id)
if mailing:
    print(f"Статус рассылки: {mailing['status']}")
    print(f"Запланированное время в БД: {mailing['scheduled_at']}")

# Проверяем ожидающие рассылки
pending = post_manager.db.get_pending_mailings()
print(f"\nОжидающих рассылок: {len(pending)}")
for m in pending:
    print(f"ID: {m['id']}, Статус: {m['status']}, Запланировано: {m['scheduled_at']}")

db.close() 