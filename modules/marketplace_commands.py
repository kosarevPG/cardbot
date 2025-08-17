# Команды для работы с маркетплейсами
from aiogram import types
import logging
from .wb_api import test_wb_connection, get_wb_summary

logger = logging.getLogger(__name__)

async def cmd_wb_test(message: types.Message):
    """Команда для тестирования подключения к WB API"""
    try:
        await message.answer("🔄 Тестирую подключение к Wildberries API...")
        
        result = await test_wb_connection()
        await message.answer(result)
        
    except Exception as e:
        logger.error(f"Ошибка в команде wb_test: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_wb_stats(message: types.Message):
    """Команда для получения статистики WB"""
    try:
        await message.answer("📊 Получаю статистику Wildberries...")
        
        result = await get_wb_summary()
        await message.answer(result, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде wb_stats: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_marketplace_help(message: types.Message):
    """Справка по командам маркетплейсов"""
    help_text = """
🛍️ **Команды для работы с маркетплейсами:**

**Wildberries:**
• `/wb_test` - Тест подключения к WB API
• `/wb_stats` - Статистика продаж и заказов
• `/wb_products` - Список товаров
• `/wb_stocks` - Остатки товаров

**Ozon (скоро):**
• `/ozon_test` - Тест подключения к Ozon API
• `/ozon_stats` - Статистика продаж

**Общие:**
• `/marketplace_help` - Эта справка

---
💡 *Для использования команд нужны настроенные API ключи в Amvera*
    """
    
    await message.answer(help_text, parse_mode="Markdown")

async def cmd_wb_products(message: types.Message):
    """Команда для получения списка товаров WB"""
    try:
        await message.answer("📦 Получаю список товаров Wildberries...")
        
        # Здесь будет вызов API для получения товаров
        await message.answer("🔄 Функция в разработке...")
        
    except Exception as e:
        logger.error(f"Ошибка в команде wb_products: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_wb_stocks(message: types.Message):
    """Команда для получения остатков WB"""
    try:
        await message.answer("📊 Получаю остатки товаров Wildberries...")
        
        # Здесь будет вызов API для получения остатков
        await message.answer("🔄 Функция в разработке...")
        
    except Exception as e:
        logger.error(f"Ошибка в команде wb_stocks: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

def register_marketplace_handlers(dp):
    """Регистрирует обработчики команд маркетплейсов"""
    
    # Основные команды
    dp.message.register(cmd_wb_test, commands=["wb_test"])
    dp.message.register(cmd_wb_stats, commands=["wb_stats"])
    dp.message.register(cmd_wb_products, commands=["wb_products"])
    dp.message.register(cmd_wb_stocks, commands=["wb_stocks"])
    dp.message.register(cmd_marketplace_help, commands=["marketplace_help"])
    
    logger.info("Обработчики команд маркетплейсов зарегистрированы")
