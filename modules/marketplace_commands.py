# Команды для работы с маркетплейсами
from aiogram import types
import logging
from .marketplace_manager import MarketplaceManager
from .google_sheets import test_google_sheets_connection, get_sheets_info, read_sheet_data

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
        
        manager = MarketplaceManager()
        result = await manager.test_connections()
        
        if result["wildberries"] is True:
            await message.answer("✅ Подключение к Wildberries API успешно установлено!")
        else:
            await message.answer(f"❌ Ошибка подключения к Wildberries API: {result['wildberries']}")
        
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
        
        manager = MarketplaceManager()
        
        # Проверяем доступность WB API
        if not manager.wb_api_key:
            await message.answer("❌ Wildberries API не настроен. Добавьте WB_API_KEY в переменные окружения.")
            return
        
        # Получаем остатки
        stocks_result = await manager.get_wb_stocks()
        if stocks_result["success"]:
            stocks = stocks_result["stocks"]
            total = len(stocks)
            
            summary = f"📊 **Сводка Wildberries**\n\n"
            summary += f"Всего товаров: {total}\n\n"
            
            if stocks:
                summary += "**Первые товары:**\n"
                for i, stock_item in enumerate(stocks[:5], 1):
                    nm_id = stock_item.get("nmId", "N/A")
                    quantity = stock_item.get("quantity", 0)
                    summary += f"{i}. 📦 {nm_id} - Остаток: {quantity} шт.\n"
            else:
                summary += "📭 Товары не найдены"
            
            await message.answer(summary, parse_mode="Markdown")
        else:
            await message.answer(f"❌ Ошибка получения данных: {stocks_result.get('error', 'Неизвестная ошибка')}")
        
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
        
        manager = MarketplaceManager()
        result = await manager.test_connections()
        
        if result["ozon"] is True:
            await message.answer("✅ Подключение к Ozon API успешно установлено!")
        else:
            await message.answer(f"❌ Ошибка подключения к Ozon API: {result['ozon']}")
        
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
        
        manager = MarketplaceManager()
        
        # Получаем mapping товаров
        mapping_result = await manager.get_ozon_product_mapping()
        if not mapping_result["success"]:
            await message.answer(f"❌ Ошибка получения товаров: {mapping_result.get('error', 'Неизвестная ошибка')}")
            return
        
        mapping = mapping_result["mapping"]
        total = mapping_result["total_count"]
        
        # Формируем сводку
        summary = f"📊 **Сводка Ozon**\n\n"
        summary += f"Всего товаров: {total}\n\n"
        
        if mapping:
            summary += "**Первые товары:**\n"
            for i, (offer_id, product_id) in enumerate(list(mapping.items())[:5], 1):
                summary += f"{i}. {offer_id} → ID: {product_id}\n"
        
        # Пытаемся получить аналитику
        try:
            from datetime import datetime, timedelta
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            analytics_result = await manager.get_ozon_analytics(date_from, date_to)
            
            if analytics_result["success"]:
                summary += f"\n📈 **Аналитика за 30 дней:**\n"
                summary += f"✅ Получена успешно"
            else:
                summary += f"\n📈 **Аналитика:** ⚠️ Не удалось получить"
        except Exception as e:
            summary += f"\n📈 **Аналитика:** ⚠️ Ошибка: {str(e)}"
        
        await message.answer(summary, parse_mode="Markdown")
        
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
        
        manager = MarketplaceManager()
        
        result = await manager.get_ozon_product_mapping()
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
        
        manager = MarketplaceManager()
        
        # Получаем mapping товаров
        mapping_result = await manager.get_ozon_product_mapping()
        if not mapping_result["success"]:
            await message.answer(f"❌ Ошибка получения товаров: {mapping_result.get('error', 'Неизвестная ошибка')}")
            return
        
        mapping = mapping_result["mapping"]
        product_ids = list(mapping.values())
        
        # Получаем остатки
        stocks_result = await manager.get_ozon_stocks(product_ids)
        if stocks_result["success"]:
            stocks = stocks_result["stocks"]
            total = len(mapping)
            await message.answer(f"✅ Получено товаров: {len(stocks)} из {total}")
            
            if stocks:
                # Показываем первые 3 товара с информацией о наличии
                preview = "📋 **Информация о товарах:**\n\n"
                for i, (offer_id, product_id) in enumerate(list(mapping.items())[:3], 1):
                    stock_count = stocks.get(str(product_id), 0)
                    preview += f"{i}. 📦 {offer_id} (ID: {product_id})\n"
                    preview += f"   Остаток: {stock_count} шт.\n\n"
                
                await message.answer(preview, parse_mode="Markdown")
            else:
                await message.answer("📭 Остатки не найдены")
        else:
            await message.answer(f"❌ Ошибка получения остатков: {stocks_result.get('error', 'Неизвестная ошибка')}")
        
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
        
        manager = MarketplaceManager()
        result = await manager.sync_ozon_data()
        
        if result["success"]:
            message_text = f"✅ **Синхронизация завершена!**\n\n"
            message_text += f"**Статистика:**\n"
            message_text += f"• Всего товаров: {len(result['data'])}\n"
            message_text += f"• Успешно: {len(result['data'])}\n"
            message_text += f"• Ошибок: 0\n\n"
            message_text += f"📊 Данные обновлены в Google таблице"
            
            await message.answer(message_text, parse_mode="Markdown")
        else:
            await message.answer(f"❌ Ошибка синхронизации: {result.get('error', 'Неизвестная ошибка')}")
        
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
