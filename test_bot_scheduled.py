import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.scheduler import MailingScheduler
from modules.post_management import PostManager
from database.db import Database
from datetime import datetime, timedelta
import pytz

async def test_bot_scheduled():
    print("=== ТЕСТ ОТЛОЖЕННЫХ ПОСТОВ ЧЕРЕЗ БОТА ===\n")
    
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
    
    # Создаем планировщик
    scheduler = MailingScheduler(post_manager, check_interval=10)  # Проверяем каждые 10 секунд
    
    print("Запускаем планировщик...")
    await scheduler.start()
    
    # Создаем тестовый пост
    post_id = post_manager.create_post(
        title="Тестовый отложенный пост через бота",
        content="<b>Тестовый отложенный пост через бота</b>\n\nЭто тестовое содержание для проверки отложенной отправки через планировщик.",
        created_by=6682555021
    )
    
    print(f"Создан пост с ID: {post_id}")
    
    # Создаем отложенную рассылку на 30 секунд вперед
    future_time = datetime.now() + timedelta(seconds=30)
    scheduled_at = future_time.strftime("%Y-%m-%d %H:%M")
    
    print(f"Запланированное время (Москва): {scheduled_at}")
    
    mailing_id = post_manager.create_mailing(
        post_id=post_id,
        title="Тестовый отложенный пост через бота",
        send_to_all=True,
        created_by=6682555021,
        scheduled_at=scheduled_at
    )
    
    print(f"Создана рассылка с ID: {mailing_id}")
    
    # Проверяем ожидающие рассылки
    pending = post_manager.db.get_pending_mailings()
    print(f"Ожидающих рассылок: {len(pending)}")
    for m in pending:
        print(f"ID: {m['id']}, Статус: {m['status']}, Запланировано: {m['scheduled_at']}")
    
    print("\nОжидаем 40 секунд для отправки...")
    await asyncio.sleep(40)
    
    print("Останавливаем планировщик...")
    await scheduler.stop()
    
    # Проверяем результат
    mailing = post_manager.get_mailing(mailing_id)
    if mailing:
        print(f"Финальный статус рассылки: {mailing['status']}")
    
    print("Планировщик остановлен.")
    db.close()

if __name__ == "__main__":
    asyncio.run(test_bot_scheduled()) 