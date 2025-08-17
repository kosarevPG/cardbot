# Команды для работы с маркетплейсами
from aiogram import types
import logging
from .wb_api import test_wb_connection, get_wb_summary
from .ozon_api import test_ozon_connection, get_ozon_summary

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

**Ozon:**
• `/ozon_test` - Тест подключения к Ozon API
• `/ozon_stats` - Статистика продаж и заказов
• `/ozon_products` - Список товаров
• `/ozon_stocks` - Остатки товаров

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

async def cmd_ozon_test(message: types.Message):
    """Команда для тестирования подключения к Ozon API"""
    try:
        await message.answer("🔄 Тестирую подключение к Ozon API...")
        
        result = await test_ozon_connection()
        await message.answer(result)
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_test: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_stats(message: types.Message):
    """Команда для получения статистики Ozon"""
    try:
        await message.answer("📊 Получаю статистику Ozon...")
        
        result = await get_ozon_summary()
        await message.answer(result, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_stats: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_products(message: types.Message):
    """Команда для получения списка товаров Ozon"""
    try:
        await message.answer("📦 Получаю список товаров Ozon...")
        
        from modules.ozon_api import get_ozon_products
        
        result = await get_ozon_products()
        if result["success"]:
            data = result["data"]
            if isinstance(data, dict) and "result" in data:
                items = data["result"].get("items", [])
                total = data["result"].get("total", 0)
                await message.answer(f"✅ Получено товаров: {len(items)} из {total}")
                
                if items:
                    # Показываем первые 3 товара
                    preview = "📋 **Первые товары:**\n\n"
                    for i, item in enumerate(items[:3], 1):
                        offer_id = item.get("offer_id", "N/A")
                        product_id = item.get("product_id", "N/A")
                        archived = "📦" if not item.get("archived") else "🗄️"
                        preview += f"{i}. {archived} {offer_id} (ID: {product_id})\n"
                    
                    await message.answer(preview, parse_mode="Markdown")
                else:
                    await message.answer("📭 Товары не найдены")
            else:
                await message.answer("❌ Неожиданный формат данных")
        else:
            await message.answer(f"❌ Ошибка получения товаров: {result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_products: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_stocks(message: types.Message):
    """Команда для получения остатков Ozon"""
    try:
        await message.answer("📊 Получаю остатки товаров Ozon...")
        
        from modules.ozon_api import get_ozon_stocks
        
        result = await get_ozon_stocks()
        if result["success"]:
            data = result["data"]
            if isinstance(data, dict) and "result" in data:
                items = data["result"].get("items", [])
                total = data["result"].get("total", 0)
                await message.answer(f"✅ Получено товаров: {len(items)} из {total}")
                
                if items:
                    # Показываем первые 3 товара с информацией о наличии
                    preview = "📋 **Информация о товарах:**\n\n"
                    for i, item in enumerate(items[:3], 1):
                        offer_id = item.get("offer_id", "N/A")
                        product_id = item.get("product_id", "N/A")
                        has_fbo = "✅" if item.get("has_fbo_stocks") else "❌"
                        has_fbs = "✅" if item.get("has_fbs_stocks") else "❌"
                        archived = "🗄️" if item.get("archived") else "📦"
                        preview += f"{i}. {archived} {offer_id} (ID: {product_id})\n"
                        preview += f"   FBO склады: {has_fbo} | FBS склады: {has_fbs}\n\n"
                    
                    await message.answer(preview, parse_mode="Markdown")
                else:
                    await message.answer("📭 Товары не найдены")
            else:
                await message.answer("❌ Неожиданный формат данных")
        else:
            await message.answer(f"❌ Ошибка получения товаров: {result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_stocks: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

def register_marketplace_handlers(dp):
    """Регистрирует обработчики команд маркетплейсов"""
    
    # Импортируем фильтры для aiogram 3.x
    from aiogram.filters import Command
    
    # Основные команды
    dp.message.register(cmd_wb_test, Command("wb_test"))
    dp.message.register(cmd_wb_stats, Command("wb_stats"))
    dp.message.register(cmd_wb_products, Command("wb_products"))
    dp.message.register(cmd_wb_stocks, Command("wb_stocks"))
    
    # Команды Ozon
    dp.message.register(cmd_ozon_test, Command("ozon_test"))
    dp.message.register(cmd_ozon_stats, Command("ozon_stats"))
    dp.message.register(cmd_ozon_products, Command("ozon_products"))
    dp.message.register(cmd_ozon_stocks, Command("ozon_stocks"))
    
    # Общие команды
    dp.message.register(cmd_marketplace_help, Command("marketplace_help"))
    
    logger.info("Обработчики команд маркетплейсов зарегистрированы")
