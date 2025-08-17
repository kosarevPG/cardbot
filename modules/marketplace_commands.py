# Команды для работы с маркетплейсами
from aiogram import types
import logging
from .wb_api import test_wb_connection, get_wb_summary
from .ozon_api import test_ozon_connection, get_ozon_summary
from .google_sheets import test_google_sheets_connection, get_sheets_info, read_sheet_data
from .ozon_sync import sync_ozon_data, sync_single_ozon_offer

# ID администраторов (замените на ваши)
ADMIN_IDS = [6682555021]  # ID пользователя для доступа к командам маркетплейсов

logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

async def cmd_wb_test(message: types.Message):
    """Команда для тестирования подключения к WB API"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("🔄 Тестирую подключение к Wildberries API...")
        
        result = await test_wb_connection()
        await message.answer(result)
        
    except Exception as e:
        logger.error(f"Ошибка в команде wb_test: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_wb_stats(message: types.Message):
    """Команда для получения статистики WB"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
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
• `/ozon_sync_all` - Синхронизация всех данных с Google таблицей
• `/ozon_sync_single OFFER_ID` - Синхронизация одного товара

**Google Sheets:**
• `/sheets_test` - Тест подключения к Google Sheets API
• `/sheets_info SPREADSHEET_ID` - Информация о таблице
• `/sheets_read SPREADSHEET_ID [SHEET_NAME]` - Чтение данных

**Общие:**
• `/marketplace_help` - Эта справка

---
🔒 *Все команды доступны только администраторам*
💡 *Для использования команд нужны настроенные API ключи в Amvera*
📊 *Для Google Sheets нужен сервисный аккаунт*
    """
    
    await message.answer(help_text, parse_mode="Markdown")

async def cmd_wb_products(message: types.Message):
    """Команда для получения списка товаров WB"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("📦 Получаю список товаров Wildberries...")
        
        # Здесь будет вызов API для получения товаров
        await message.answer("🔄 Функция в разработке...")
        
    except Exception as e:
        logger.error(f"Ошибка в команде wb_products: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_wb_stocks(message: types.Message):
    """Команда для получения остатков WB"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("📊 Получаю остатки товаров Wildberries...")
        
        # Здесь будет вызов API для получения остатков
        await message.answer("🔄 Функция в разработке...")
        
    except Exception as e:
        logger.error(f"Ошибка в команде wb_stocks: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_test(message: types.Message):
    """Команда для тестирования подключения к Ozon API"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("🔄 Тестирую подключение к Ozon API...")
        
        result = await test_ozon_connection()
        await message.answer(result)
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_test: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_stats(message: types.Message):
    """Команда для получения статистики Ozon"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("📊 Получаю статистику Ozon...")
        
        result = await get_ozon_summary()
        await message.answer(result, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_stats: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_products(message: types.Message):
    """Команда для получения списка товаров Ozon"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("📦 Получаю список товаров Ozon...")
        
        from modules.ozon_api import get_ozon_products
        
        result = await get_ozon_products()
        if result["success"]:
            mapping = result["mapping"]
            total = result["total_count"]
            await message.answer(f"✅ Получено товаров: {len(mapping)} из {total}")
            
            if mapping:
                # Показываем первые 3 товара
                preview = "📋 **Первые товары:**\n\n"
                for i, (offer_id, product_id) in enumerate(list(mapping.items())[:3], 1):
                    preview += f"{i}. 📦 {offer_id} (ID: {product_id})\n"
                
                await message.answer(preview, parse_mode="Markdown")
            else:
                await message.answer("📭 Товары не найдены")
        else:
            await message.answer(f"❌ Ошибка получения товаров: {result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_products: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_stocks(message: types.Message):
    """Команда для получения остатков Ozon"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
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

async def cmd_google_sheets_test(message: types.Message):
    """Команда для тестирования подключения к Google Sheets API"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("🔄 Тестирую подключение к Google Sheets API...")
        
        result = await test_google_sheets_connection()
        await message.answer(result)
        
    except Exception as e:
        logger.error(f"Ошибка в команде google_sheets_test: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_google_sheets_info(message: types.Message):
    """Команда для получения информации о Google таблице"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        # Парсим команду: /sheets_info SPREADSHEET_ID
        command_parts = message.text.split()
        if len(command_parts) < 2:
            await message.answer("❌ Укажите ID таблицы: `/sheets_info SPREADSHEET_ID`")
            return
        
        spreadsheet_id = command_parts[1]
        await message.answer(f"📊 Получаю информацию о таблице {spreadsheet_id}...")
        
        result = await get_sheets_info(spreadsheet_id)
        if result["success"]:
            info = result
            response = f"📋 **Информация о таблице:**\n\n"
            response += f"**Название:** {info['spreadsheet_title']}\n"
            response += f"**ID:** `{info['spreadsheet_id']}`\n"
            response += f"**Количество листов:** {info['sheets_count']}\n\n"
            
            if info['sheets']:
                response += "**Листы:**\n"
                for i, sheet in enumerate(info['sheets'][:5], 1):  # Показываем первые 5
                    response += f"{i}. {sheet['title']} ({sheet['row_count']}×{sheet['col_count']})\n"
                
                if len(info['sheets']) > 5:
                    response += f"\n... и еще {len(info['sheets']) - 5} листов"
            
            await message.answer(response, parse_mode="Markdown")
        else:
            await message.answer(f"❌ Ошибка получения информации: {result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде google_sheets_info: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_google_sheets_read(message: types.Message):
    """Команда для чтения данных из Google таблицы"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        # Парсим команду: /sheets_read SPREADSHEET_ID [SHEET_NAME]
        command_parts = message.text.split()
        if len(command_parts) < 2:
            await message.answer("❌ Укажите ID таблицы: `/sheets_read SPREADSHEET_ID [SHEET_NAME]`")
            return
        
        spreadsheet_id = command_parts[1]
        sheet_name = command_parts[2] if len(command_parts) > 2 else None
        
        await message.answer(f"📖 Читаю данные из таблицы {spreadsheet_id}...")
        
        result = await read_sheet_data(spreadsheet_id, sheet_name)
        if result["success"]:
            data = result["data"]
            response = f"📊 **Данные из таблицы:**\n\n"
            response += f"**Таблица:** {result['spreadsheet_title']}\n"
            response += f"**Лист:** {result['sheet_name']}\n"
            response += f"**Размер:** {result['rows']}×{result['columns']}\n\n"
            
            if data and len(data) > 0:
                # Показываем первые 5 строк
                response += "**Первые строки:**\n"
                for i, row in enumerate(data[:5], 1):
                    row_text = " | ".join(str(cell) for cell in row[:5])  # Первые 5 ячеек
                    if len(row) > 5:
                        row_text += " ..."
                    response += f"{i}. {row_text}\n"
                
                if len(data) > 5:
                    response += f"\n... и еще {len(data) - 5} строк"
            else:
                response += "📭 Данные не найдены"
            
            await message.answer(response, parse_mode="Markdown")
        else:
            await message.answer(f"❌ Ошибка чтения данных: {result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде google_sheets_read: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_sync_all(message: types.Message):
    """Команда для синхронизации всех данных Ozon с Google таблицей"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("🔄 Начинаю синхронизацию всех данных Ozon с Google таблицей...\n\n⚠️ Это может занять несколько минут.")
        
        result = await sync_ozon_data()
        await message.answer(result, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_sync_all: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_sync_single(message: types.Message):
    """Команда для синхронизации одного offer_id Ozon с Google таблицей"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        # Парсим команду: /ozon_sync_single OFFER_ID
        command_parts = message.text.split()
        if len(command_parts) < 2:
            await message.answer("❌ Укажите offer_id: `/ozon_sync_single OFFER_ID`")
            return
        
        offer_id = command_parts[1]
        await message.answer(f"🔄 Синхронизирую данные для {offer_id}...")
        
        result = await sync_single_ozon_offer(offer_id)
        await message.answer(result, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_sync_single: {e}")
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
    dp.message.register(cmd_ozon_sync_all, Command("ozon_sync_all"))
    dp.message.register(cmd_ozon_sync_single, Command("ozon_sync_single"))
    
    # Команды Google Sheets
    dp.message.register(cmd_google_sheets_test, Command("sheets_test"))
    dp.message.register(cmd_google_sheets_info, Command("sheets_info"))
    dp.message.register(cmd_google_sheets_read, Command("sheets_read"))
    
    # Общие команды
    dp.message.register(cmd_marketplace_help, Command("marketplace_help"))
    
    logger.info("Обработчики команд маркетплейсов зарегистрированы")
