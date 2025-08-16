# код/test_post_system.py

import asyncio
import sqlite3
from datetime import datetime
import json
import os

# Импортируем наши модули
from database.db import Database
from modules.post_management import PostManager
from modules.scheduler import MailingScheduler

# Мок для бота и логгера
class MockBot:
    async def send_message(self, chat_id, text, **kwargs):
        print(f"Отправлено сообщение пользователю {chat_id}: {text[:50]}...")
        return True
    
    async def send_photo(self, chat_id, photo, caption=None, **kwargs):
        print(f"Отправлено фото пользователю {chat_id}: {caption[:50] if caption else 'Без подписи'}...")
        return True

class MockLogger:
    async def log_action(self, user_id, action, details):
        print(f"Лог: пользователь {user_id}, действие {action}, детали {details}")

async def test_post_system():
    """Тестирует систему постов."""
    print("🧪 Тестирование системы постов...")
    
    # Создаем временную БД
    db_path = "test_posts.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Инициализируем БД
    db = Database(path=db_path)
    
    # Создаем моки
    bot = MockBot()
    logger = MockLogger()
    
    # Создаем PostManager
    post_manager = PostManager(db, bot, logger)
    
    # Тест 1: Создание поста
    print("\n📝 Тест 1: Создание поста")
    post_id = post_manager.create_post(
        title="Тестовый пост",
        content="Это тестовый пост для проверки системы рассылок!",
        created_by=123456
    )
    print(f"✅ Пост создан с ID: {post_id}")
    
    # Тест 2: Получение поста
    print("\n📖 Тест 2: Получение поста")
    post = post_manager.get_post(post_id)
    print(f"✅ Пост получен: {post['title']}")
    
    # Тест 3: Создание рассылки всем пользователям
    print("\n📤 Тест 3: Создание рассылки всем пользователям")
    mailing_id = post_manager.create_mailing(
        post_id=post_id,
        title="Тестовая рассылка всем",
        send_to_all=True,
        created_by=123456
    )
    print(f"✅ Рассылка создана с ID: {mailing_id}")
    
    # Тест 4: Создание рассылки конкретным пользователям
    print("\n📤 Тест 4: Создание рассылки конкретным пользователям")
    mailing_id2 = post_manager.create_mailing(
        post_id=post_id,
        title="Тестовая рассылка конкретным",
        send_to_all=False,
        target_user_ids=[123456, 789012],
        created_by=123456
    )
    print(f"✅ Рассылка создана с ID: {mailing_id2}")
    
    # Тест 5: Создание запланированной рассылки
    print("\n📅 Тест 5: Создание запланированной рассылки")
    scheduled_time = "2024-12-31 23:59"
    mailing_id3 = post_manager.create_mailing(
        post_id=post_id,
        title="Запланированная рассылка",
        send_to_all=True,
        scheduled_at=scheduled_time,
        created_by=123456
    )
    print(f"✅ Запланированная рассылка создана с ID: {mailing_id3}")
    
    # Тест 6: Получение списка постов
    print("\n📋 Тест 6: Получение списка постов")
    posts = post_manager.get_all_posts()
    print(f"✅ Найдено постов: {len(posts)}")
    for post in posts:
        print(f"  - {post['title']} (ID: {post['id']})")
    
    # Тест 7: Получение списка рассылок
    print("\n📤 Тест 7: Получение списка рассылок")
    mailings = post_manager.get_all_mailings()
    print(f"✅ Найдено рассылок: {len(mailings)}")
    for mailing in mailings:
        print(f"  - {mailing['title']} (ID: {mailing['id']}, статус: {mailing['status']})")
    
    # Тест 8: Получение ожидающих рассылок
    print("\n⏳ Тест 8: Получение ожидающих рассылок")
    pending = post_manager.db.get_pending_mailings()
    print(f"✅ Ожидающих рассылок: {len(pending)}")
    
    # Тест 9: Форматирование превью
    print("\n📝 Тест 9: Форматирование превью")
    post_preview = post_manager.format_post_preview(post)
    print(f"✅ Превью поста: {post_preview}")
    
    mailing_preview = post_manager.format_mailing_preview(mailings[0])
    print(f"✅ Превью рассылки: {mailing_preview}")
    
    # Тест 10: Валидация данных
    print("\n✅ Тест 10: Валидация данных")
    post_validation = post_manager.validate_post_data("", "")
    print(f"Валидация пустого поста: {post_validation}")
    
    mailing_validation = post_manager.validate_mailing_data(False, [])
    print(f"Валидация рассылки без получателей: {mailing_validation}")
    
    # Тест 11: Создание Scheduler
    print("\n⏰ Тест 11: Создание планировщика")
    scheduler = MailingScheduler(post_manager, check_interval=5)
    print(f"✅ Планировщик создан, статус: {scheduler.get_status()}")
    
    # Тест 12: Обработка рассылок
    print("\n🔄 Тест 12: Обработка рассылок")
    result = await scheduler.process_mailings_now()
    print(f"✅ Результат обработки: {result}")
    
    # Очистка
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)
    
    print("\n🎉 Все тесты завершены успешно!")

if __name__ == "__main__":
    asyncio.run(test_post_system()) 