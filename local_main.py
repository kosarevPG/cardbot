#!/usr/bin/env python3
"""
Локальный запуск Telegram бота
Используется при недоступности Amvera
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(str(Path(__file__).parent))

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Устанавливаем уровень DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Импортируем локальный конфиг
try:
    from local_config import *
    logger.info("✅ Локальный конфиг загружен успешно")
except ImportError as e:
    logger.error(f"❌ Ошибка загрузки локального конфига: {e}")
    sys.exit(1)

# Проверяем обязательные настройки
if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    logger.error("❌ BOT_TOKEN не настроен! Укажите токен в local_config.py или .env файле")
    sys.exit(1)

# Импортируем aiogram
try:
    from aiogram import Bot, Dispatcher, types
    from aiogram.filters import Command
    from aiogram.types import Message
    logger.info("✅ aiogram импортирован успешно")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта aiogram: {e}")
    logger.info("💡 Установите: pip install aiogram>=3.0.0")
    sys.exit(1)

# Импортируем модули бота
try:
    from modules.marketplace_commands import cmd_ozon_sync_all
    from modules.card_of_the_day import cmd_card_of_the_day
    from modules.evening_reflection import cmd_evening_reflection
    from modules.notification_service import NotificationService
    from modules.scheduler import MailingScheduler, ReflectionAnalysisScheduler
    logger.info("✅ Модули бота импортированы успешно")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта модулей: {e}")
    sys.exit(1)

# Создаем экземпляры бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Регистрируем команды
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    await message.answer(
        "🌟 **Привет! Я бот карт дня и синхронизации Ozon!**\n\n"
        "📋 **Доступные команды:**\n"
        "• /start - это сообщение\n"
        "• /card - карта дня\n"
        "• /evening - вечерняя рефлексия\n"
        "• /ozon_sync_all - синхронизация Ozon с Google таблицей\n\n"
        "🚀 **Бот запущен локально** (Amvera недоступен)"
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    await message.answer(
        "📚 **Справка по командам:**\n\n"
        "🎴 **/card** - показывает карту дня для медитации и размышлений\n\n"
        "🌙 **/evening** - запускает вечернюю рефлексию дня\n\n"
        "🛒 **/ozon_sync_all** - синхронизирует данные Ozon с Google таблицей\n"
        "⚠️ Требует права администратора\n\n"
        "🔧 **Техническая информация:**\n"
        "• Бот запущен локально\n"
        "• Версия: Локальная (Amvera недоступен)\n"
        "• Статус: Работает"
    )

# Регистрируем основные команды
dp.message.register(cmd_card_of_the_day, Command("card"))
dp.message.register(cmd_evening_reflection, Command("evening"))
dp.message.register(cmd_ozon_sync_all, Command("ozon_sync_all"))

# Обработчик ошибок
@dp.errors()
async def errors_handler(update: types.Update, exception: Exception):
    """Обработчик ошибок"""
    logger.error(f"❌ Ошибка в боте: {exception}")
    try:
        if update.message:
            await update.message.answer(
                "❌ Произошла ошибка при обработке команды. Попробуйте позже или обратитесь к администратору."
            )
    except Exception as e:
        logger.error(f"❌ Не удалось отправить сообщение об ошибке: {e}")

async def main():
    """Главная функция запуска бота"""
    logger.info("🚀 Запускаю локальный Telegram бот...")
    
    try:
        # Проверяем подключение к Telegram
        me = await bot.get_me()
        logger.info(f"✅ Бот подключен: @{me.username} (ID: {me.id})")
        
        # Запускаем бота
        logger.info("🔄 Бот запущен и готов к работе!")
        logger.info("💡 Для остановки нажмите Ctrl+C")
        
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка запуска бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Создаем необходимые директории
        os.makedirs("data", exist_ok=True)
        os.makedirs("database", exist_ok=True)
        
        # Запускаем бота
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        sys.exit(1)
