import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.scheduler import MailingScheduler
from modules.post_management import PostManager
from database.db import Database
from datetime import datetime, timedelta
import pytz

async def debug_scheduler():
    print("=== ОТЛАДКА ПЛАНИРОВЩИКА ===\n")
    
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
        def warning(self, msg):
            print(f"⚠️ {msg}")
    
    # Создаем PostManager
    post_manager = PostManager(db, MockBot(), MockLogger())
    
    # Создаем планировщик
    scheduler = MailingScheduler(post_manager, check_interval=5)  # Проверяем каждые 5 секунд
    
    print("Запускаем планировщик...")
    await scheduler.start()
    
    # Проверяем ожидающие рассылки каждые 5 секунд
    for i in range(12):  # 60 секунд
        print(f"\n--- Проверка {i+1} ---")
        
        # Проверяем ожидающие рассылки
        pending = post_manager.db.get_pending_mailings()
        print(f"Ожидающих рассылок: {len(pending)}")
        for m in pending:
            print(f"ID: {m['id']}, Статус: {m['status']}, Запланировано: {m['scheduled_at']}")
        
        # Принудительно обрабатываем рассылки
        result = await scheduler.process_mailings_now()
        print(f"Результат обработки: {result}")
        
        await asyncio.sleep(5)
    
    print("Останавливаем планировщик...")
    await scheduler.stop()
    
    print("Планировщик остановлен.")
    db.close()

if __name__ == "__main__":
    asyncio.run(debug_scheduler()) 