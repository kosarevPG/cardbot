import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.scheduler import MailingScheduler
from modules.post_management import PostManager
from database.db import Database
from datetime import datetime
import pytz

async def test_scheduler():
    print("=== ТЕСТ ПЛАНИРОВЩИКА ===\n")
    
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
    scheduler = MailingScheduler(post_manager, check_interval=5)  # Проверяем каждые 5 секунд
    
    print("Запускаем планировщик...")
    await scheduler.start()
    
    print("Планировщик запущен. Ожидаем 10 секунд...")
    await asyncio.sleep(10)
    
    print("Останавливаем планировщик...")
    await scheduler.stop()
    
    print("Планировщик остановлен.")
    db.close()

if __name__ == "__main__":
    asyncio.run(test_scheduler()) 