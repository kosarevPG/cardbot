# FORCE RESTART 2025-08-24 - ИСПРАВЛЕНИЕ Any ИМПОРТА
# FORCE RESTART 2025-08-24 - ИСПРАВЛЕНИЕ ozon_stocks_detailed - теперь использует правильный метод
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
• `/ozon_debug` - Детальная диагностика Ozon API
• `/ozon_simple_test` - Простой тест получения товаров
• `/ozon_stats` - Статистика продаж и заказов
• `/ozon_products` - Список товаров (первые 5, расширенная информация)
• `/ozon_products_all` - Полный список всех товаров
• `/ozon_products_detailed` - Детальная информация о всех товарах
• `/ozon_stocks` - Остатки товаров (первые 5, с названиями)
• `/ozon_stocks_detailed` - Детальная информация об остатках по складам
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
        
        # Показываем статус конфигурации
        status = manager.get_status()
        ozon_status = status["ozon"]
        
        config_info = f"📋 **Конфигурация Ozon API:**\n\n"
        config_info += f"🔑 API ключ: {'✅ Настроен' if ozon_status['api_key'] else '❌ НЕ настроен'}\n"
        config_info += f"🆔 Client ID: {'✅ Настроен' if ozon_status['client_id'] else '❌ НЕ настроен'}\n"
        config_info += f"⚙️ Общий статус: {'✅ Настроен' if ozon_status['configured'] else '❌ НЕ настроен'}\n\n"
        
        if ozon_status['configured']:
            # Тестируем подключение
            result = await manager.test_connections()
            
            if result["ozon"] is True:
                config_info += "🔄 **Тест подключения:** ✅ Успешно!\n\n"
                config_info += "💡 API ключи корректны, но возможно проблема с правами доступа к эндпоинту `/v3/product/list`"
            else:
                config_info += f"🔄 **Тест подключения:** ❌ Ошибка: {result['ozon']}\n\n"
                config_info += "💡 Проверьте правильность API ключей в переменных окружения Amvera"
        else:
            config_info += "⚠️ **Проблема:** API ключи не настроены в переменных окружения\n\n"
            config_info += "💡 Добавьте в Amvera:\n"
            config_info += "• `OZON_API_KEY`\n"
            config_info += "• `OZON_CLIENT_ID`"
        
        await message.answer(config_info, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_test: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_debug(message: types.Message):
    """Команда для детальной диагностики Ozon API"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("🔍 Запускаю детальную диагностику Ozon API...")
        
        manager = MarketplaceManager()
        
        # Проверяем переменные окружения
        import os
        ozon_api_key = os.getenv("OZON_API_KEY", "")
        ozon_client_id = os.getenv("OZON_CLIENT_ID", "")
        
        debug_info = f"🔍 **Детальная диагностика Ozon API**\n\n"
        
        # Информация о переменных окружения
        debug_info += f"📋 **Переменные окружения:**\n"
        debug_info += f"🔑 OZON_API_KEY: {'***' + ozon_api_key[-8:] if ozon_api_key else '❌ НЕ УСТАНОВЛЕНА'}\n"
        debug_info += f"🆔 OZON_CLIENT_ID: {'***' + ozon_client_id[-8:] if ozon_client_id else '❌ НЕ УСТАНОВЛЕНА'}\n\n"
        
        # Информация о конфигурации менеджера
        status = manager.get_status()
        ozon_status = status["ozon"]
        
        debug_info += f"⚙️ **Конфигурация менеджера:**\n"
        debug_info += f"🔑 API ключ: {'✅ Загружен' if ozon_status['api_key'] else '❌ НЕ загружен'}\n"
        debug_info += f"🆔 Client ID: {'✅ Загружен' if ozon_status['client_id'] else '❌ НЕ загружен'}\n"
        debug_info += f"🌐 Base URL: {manager.ozon_base_url}\n"
        debug_info += f"🔗 Эндпоинт product_list: {manager.ozon_endpoints['product_list']}\n\n"
        
        if ozon_status['configured']:
            # Пытаемся получить товары с детальным логированием
            debug_info += f"🔄 **Тестируем API запрос...**\n"
            
            try:
                result = await manager.get_ozon_product_mapping(page_size=1)
                
                if result["success"]:
                    mapping = result["mapping"]
                    total = result["total_count"]
                    debug_info += f"✅ **API запрос успешен!**\n"
                    debug_info += f"📦 Получено товаров: {len(mapping)} из {total}\n"
                    
                    if mapping:
                        debug_info += f"🔍 **Пример товара:**\n"
                        for offer_id, product_id in list(mapping.items())[:1]:
                            debug_info += f"   • offer_id: {offer_id} - product_id: {product_id}\n"
                    else:
                        debug_info += f"⚠️ **Проблема:** API вернул 0 товаров\n"
                        debug_info += f"💡 Возможные причины:\n"
                        debug_info += f"   • Нет товаров в каталоге\n"
                        debug_info += f"   • Недостаточно прав для доступа к эндпоинту\n"
                        debug_info += f"   • Товары скрыты/архивированы\n"
                else:
                    debug_info += f"❌ **API запрос не удался:**\n"
                    debug_info += f"   Ошибка: {result.get('error', 'Неизвестная ошибка')}\n"
                    if 'details' in result:
                        debug_info += f"   Детали: {result['details']}\n"
                    
            except Exception as e:
                debug_info += f"❌ **Ошибка при тестировании API:**\n"
                debug_info += f"   {str(e)}\n"
        else:
            debug_info += f"⚠️ **API не настроен** - пропускаем тестирование\n"
        
        await message.answer(debug_info, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_debug: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_simple_test(message: types.Message):
    """Команда для простого тестирования получения списка товаров Ozon"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("🔍 Тестирую простое получение списка товаров...")
        
        manager = MarketplaceManager()
        
        # Проверяем простое получение товаров из /v3/product/list
        try:
            result = await manager.get_ozon_products_simple(page_size=1)
            
            test_info = f"🔍 **Простой тест /v3/product/list**\n\n"
            
            if result["success"]:
                products = result["products"]
                total = result["total_count"]
                test_info += f"✅ **API запрос успешен!**\n"
                test_info += f"📦 Получено товаров: {len(products)}\n"
                test_info += f"📊 Общее количество: {total}\n\n"
                
                if products:
                    test_info += f"🔍 **Первый товар:**\n"
                    first_product = products[0]
                    test_info += f"   • offer_id: {first_product.get('offer_id', 'НЕТ')}\n"
                    test_info += f"   • product_id: {first_product.get('product_id', 'НЕТ')}\n"
                    test_info += f"   • archived: {first_product.get('archived', 'НЕТ')}\n"
                    test_info += f"   • has_fbo_stocks: {first_product.get('has_fbo_stocks', 'НЕТ')}\n"
                    test_info += f"   • has_fbs_stocks: {first_product.get('has_fbs_stocks', 'НЕТ')}\n"
                    test_info += f"   • is_discounted: {first_product.get('is_discounted', 'НЕТ')}\n"
                else:
                    test_info += f"⚠️ **Проблема:** API вернул 0 товаров\n"
                    test_info += f"💡 **Возможные причины:**\n"
                    test_info += f"   • У вас нет товаров в каталоге Ozon\n"
                    test_info += f"   • Все товары архивированы\n"
                    test_info += f"   • Недостаточно прав API\n"
            else:
                test_info += f"❌ **API запрос не удался:**\n"
                test_info += f"   Ошибка: {result.get('error', 'Неизвестная ошибка')}\n"
                if 'details' in result:
                    test_info += f"   Детали: {result['details']}\n"
                    
        except Exception as e:
            test_info = f"❌ **Ошибка при тестировании:**\n"
            test_info += f"   {str(e)}\n"
        
        await message.answer(test_info, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_simple_test: {e}")
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
                summary += f"{i}. {offer_id} - ID: {product_id}\n"
        
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
                # Показываем первые 5 товаров с расширенной информацией
                preview = "📋 **Первые товары (расширенная информация):**\n\n"
                
                # Получаем детальную информацию о продуктах
                product_ids = list(mapping.values())
                detailed_result = await manager.get_ozon_products_detailed(product_ids)
                
                if detailed_result["success"]:
                    products = detailed_result["products"]
                    
                    for i, (offer_id, product_id) in enumerate(list(mapping.items())[:5], 1):
                        product_info = products.get(str(product_id), {})
                        
                        # Статус продукта
                        archived = "🗄️" if product_info.get("archived") else "📦"
                        fbo_status = "✅" if product_info.get("has_fbo_stocks") else "❌"
                        fbs_status = "✅" if product_info.get("has_fbs_stocks") else "❌"
                        discount = "🏷️" if product_info.get("is_discounted") else ""
                        
                        # Получаем название продукта
                        product_name = product_info.get("name", "Без названия")
                        
                        preview += f"{i}. {archived} **{offer_id}** (ID: {product_id})\n"
                        preview += f"   📝 **{product_name}**\n"
                        preview += f"   📊 FBO: {fbo_status} | FBS: {fbs_status} {discount}\n"
                        
                        # Информация о размерах
                        quants = product_info.get("quants", [])
                        if quants:
                            preview += f"   📏 Размеры: {len(quants)} шт.\n"
                        
                        preview += "\n"
                else:
                    # Fallback к базовой информации
                    for i, (offer_id, product_id) in enumerate(list(mapping.items())[:5], 1):
                        preview += f"{i}. 📦 {offer_id} (ID: {product_id})\n"
                
                # Добавляем информацию о пагинации
                if len(mapping) > 5:
                    preview += f"📄 Показано: 5 из {len(mapping)} товаров"
                    preview += f"\n💡 Используйте `/ozon_products_all` для полного списка"
                    preview += f"\n💡 Используйте `/ozon_products_detailed` для детальной информации"
                
                await message.answer(preview, parse_mode="Markdown")
            else:
                await message.answer("📭 Товары не найдены")
        else:
            await message.answer(f"❌ Ошибка получения товаров: {result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_products: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_products_all(message: types.Message):
    """Команда для получения полного списка товаров Ozon"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("📦 Получаю полный список товаров Ozon...")
        
        manager = MarketplaceManager()
        
        result = await manager.get_ozon_product_mapping()
        if result["success"]:
            mapping = result["mapping"]
            total = result["total_count"]
            
            if mapping:
                # Показываем все товары
                full_list = f"📋 **Полный список товаров Ozon**\n\n"
                full_list += f"Всего товаров: {total}\n\n"
                
                # Получаем детальную информацию для названий
                product_ids = list(mapping.values())
                detailed_result = await manager.get_ozon_products_detailed(product_ids)
                
                if detailed_result["success"]:
                    products = detailed_result["products"]
                    
                    for i, (offer_id, product_id) in enumerate(mapping.items(), 1):
                        product_info = products.get(str(product_id), {})
                        product_name = product_info.get("name", "Без названия")
                        full_list += f"{i:2d}. 📦 {offer_id} (ID: {product_id})\n"
                        full_list += f"      �� {product_name}\n"
                else:
                    # Fallback к базовой информации
                    for i, (offer_id, product_id) in enumerate(mapping.items(), 1):
                        full_list += f"{i:2d}. 📦 {offer_id} (ID: {product_id})\n"
                
                # Разбиваем на части, если сообщение слишком длинное
                if len(full_list) > 4000:  # Telegram лимит ~4096 символов
                    parts = []
                    current_part = ""
                    current_count = 0
                    
                    for i, (offer_id, product_id) in enumerate(mapping.items(), 1):
                        line = f"{i:2d}. 📦 {offer_id} (ID: {product_id})\n"
                        
                        if len(current_part) + len(line) > 3500:
                            parts.append(f"📋 **Товары Ozon (часть {len(parts) + 1})**\n\n{current_part}")
                            current_part = line
                            current_count = 1
                        else:
                            current_part += line
                            current_count += 1
                    
                    # Добавляем последнюю часть
                    if current_part:
                        parts.append(f"📋 **Товары Ozon (часть {len(parts) + 1})**\n\n{current_part}")
                    
                    # Отправляем части
                    for i, part in enumerate(parts):
                        if i == 0:
                            await message.answer(f"✅ Получено товаров: {total}\n\n{part}", parse_mode="Markdown")
                        else:
                            await message.answer(part, parse_mode="Markdown")
                else:
                    await message.answer(f"✅ Получено товаров: {total}\n\n{full_list}", parse_mode="Markdown")
            else:
                await message.answer("📭 Товары не найдены")
        else:
            await message.answer(f"❌ Ошибка получения товаров: {result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_products_all: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_products_detailed(message: types.Message):
    """Команда для получения детальной информации о всех товарах Ozon"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("📦 Получаю детальную информацию о всех товарах Ozon...")
        
        manager = MarketplaceManager()
        
        result = await manager.get_ozon_product_mapping()
        if result["success"]:
            mapping = result["mapping"]
            total = result["total_count"]
            
            if mapping:
                # Получаем детальную информацию
                product_ids = list(mapping.values())
                detailed_result = await manager.get_ozon_products_detailed(product_ids)
                
                if detailed_result["success"]:
                    products = detailed_result["products"]
                    
                    # Формируем детальный отчет
                    detailed_report = f"📋 **Детальная информация о товарах Ozon**\n\n"
                    detailed_report += f"Всего товаров: {total}\n\n"
                    
                    # Статистика по статусам
                    archived_count = sum(1 for p in products.values() if p.get("archived"))
                    fbo_count = sum(1 for p in products.values() if p.get("has_fbo_stocks"))
                    fbs_count = sum(1 for p in products.values() if p.get("has_fbs_stocks"))
                    discounted_count = sum(1 for p in products.values() if p.get("is_discounted"))
                    
                    detailed_report += f"📊 **Статистика:**\n"
                    detailed_report += f"• Архивных: {archived_count}\n"
                    detailed_report += f"• С FBO остатками: {fbo_count}\n"
                    detailed_report += f"• С FBS остатками: {fbs_count}\n"
                    detailed_report += f"• Со скидками: {discounted_count}\n\n"
                    
                    # Детальная информация по каждому товару
                    for i, (offer_id, product_id) in enumerate(mapping.items(), 1):
                        product_info = products.get(str(product_id), {})
                        
                        # Статус продукта
                        archived = "🗄️ АРХИВ" if product_info.get("archived") else "📦 АКТИВЕН"
                        fbo_status = "✅ ЕСТЬ" if product_info.get("has_fbo_stocks") else "❌ НЕТ"
                        fbs_status = "✅ ЕСТЬ" if product_info.get("has_fbs_stocks") else "❌ НЕТ"
                        discount = "🏷️ СКИДКА" if product_info.get("is_discounted") else ""
                        
                        # Получаем название продукта
                        product_name = product_info.get("name", "Без названия")
                        
                        detailed_report += f"**{i:2d}. {offer_id}** (ID: {product_id})\n"
                        detailed_report += f"   📝 **{product_name}**\n"
                        detailed_report += f"   📊 Статус: {archived}\n"
                        detailed_report += f"   🏪 FBO склады: {fbo_status}\n"
                        detailed_report += f"   🏪 FBS склады: {fbs_status}\n"
                        
                        if discount:
                            detailed_report += f"   {discount}\n"
                        
                        # Информация о размерах
                        quants = product_info.get("quants", [])
                        if quants:
                            detailed_report += f"   📏 Размеры ({len(quants)} шт.):\n"
                            for quant in quants[:3]:  # Показываем первые 3 размера
                                quant_code = quant.get("quant_code", "N/A")
                                quant_size = quant.get("quant_size", 0)
                                detailed_report += f"      • {quant_code}: {quant_size}\n"
                            
                            if len(quants) > 3:
                                detailed_report += f"      ... и еще {len(quants) - 3} размеров\n"
                        
                        detailed_report += "\n"
                    
                    # Разбиваем на части, если сообщение слишком длинное
                    if len(detailed_report) > 4000:
                        parts = []
                        current_part = ""
                        
                        lines = detailed_report.split('\n')
                        for line in lines:
                            if len(current_part) + len(line) + 1 > 3500:
                                parts.append(current_part.strip())
                                current_part = line + '\n'
                            else:
                                current_part += line + '\n'
                        
                        if current_part:
                            parts.append(current_part.strip())
                        
                        # Отправляем части
                        for i, part in enumerate(parts):
                            if i == 0:
                                await message.answer(f"✅ Получено товаров: {total}\n\n{part}", parse_mode="Markdown")
                            else:
                                await message.answer(f"📋 **Товары Ozon (часть {i + 1})**\n\n{part}", parse_mode="Markdown")
                    else:
                        await message.answer(f"✅ Получено товаров: {total}\n\n{detailed_report}", parse_mode="Markdown")
                else:
                    await message.answer(f"❌ Ошибка получения детальной информации: {detailed_result.get('error', 'Неизвестная ошибка')}")
            else:
                await message.answer("📭 Товары не найдены")
        else:
            await message.answer(f"❌ Ошибка получения товаров: {result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_products_detailed: {e}")
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
        logger.info(f"Результат получения остатков: {stocks_result}")
        
        if stocks_result["success"]:
            stocks = stocks_result["stocks"]
            total = len(mapping)
            logger.info(f"Получено остатков для {len(stocks)} товаров из {total}")
            await message.answer(f"✅ Получено товаров: {len(stocks)} из {total}")
            
            if stocks:
                # Показываем первые 5 товаров с информацией о наличии
                preview = "📋 **Информация о товарах:**\n\n"
                # Получаем детальную информацию для названий
                product_ids = list(mapping.values())
                detailed_result = await manager.get_ozon_products_detailed(product_ids)
                
                if detailed_result["success"]:
                    products = detailed_result["products"]
                    
                    for i, (offer_id, product_id) in enumerate(list(mapping.items())[:5], 1):
                        stock_info = stocks.get(str(product_id), {})
                        product_info = products.get(str(product_id), {})
                        product_name = product_info.get("name", "Без названия")
                        
                        # Получаем информацию об остатках
                        if isinstance(stock_info, dict):
                            total_stock = stock_info.get("total", 0)
                            warehouses = stock_info.get("warehouses", [])
                            
                            preview += f"{i}. 📦 {offer_id} (ID: {product_id})\n"
                            preview += f"   📝 {product_name}\n"
                            preview += f"   📊 **Общий остаток: {total_stock} шт.**\n"
                            
                            # Детальная информация по складам
                            if warehouses:
                                preview += f"   🏪 **По складам:**\n"
                                for warehouse in warehouses[:3]:  # Показываем первые 3 склада
                                    preview += f"      • {warehouse['name']}: {warehouse['stock']} шт. (резерв: {warehouse['reserved']})\n"
                                
                                if len(warehouses) > 3:
                                    preview += f"      ... и еще {len(warehouses) - 3} складов\n"
                            else:
                                preview += f"   🏪 **Склады:** Нет данных\n"
                        else:
                            # Fallback для старого формата
                            stock_count = stock_info if isinstance(stock_info, (int, str)) else 0
                            preview += f"{i}. 📦 {offer_id} (ID: {product_id})\n"
                            preview += f"   📝 {product_name}\n"
                            preview += f"   📊 Остаток: {stock_count} шт.\n"
                        
                        preview += "\n"
                else:
                    # Fallback к базовой информации
                    for i, (offer_id, product_id) in enumerate(list(mapping.items())[:5], 1):
                        stock_info = stocks.get(str(product_id), {})
                        
                        # Получаем информацию об остатках
                        if isinstance(stock_info, dict):
                            total_stock = stock_info.get("total", 0)
                            preview += f"{i}. 📦 {offer_id} (ID: {product_id})\n"
                            preview += f"   📊 Остаток: {total_stock} шт.\n\n"
                        else:
                            # Fallback для старого формата
                            stock_count = stock_info if isinstance(stock_info, (int, str)) else 0
                            preview += f"{i}. 📦 {offer_id} (ID: {product_id})\n"
                            preview += f"   📊 Остаток: {stock_count} шт.\n\n"
                
                # Добавляем информацию о пагинации
                if len(mapping) > 5:
                    preview += f"📄 Показано: 5 из {len(mapping)} товаров"
                    preview += f"\n💡 Используйте `/ozon_stocks_all` для полного списка"
                
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

async def cmd_ozon_stocks_detailed(message: types.Message):
    """Команда для получения детальной информации об остатках Ozon по складам"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("📊 Получаю детальную информацию об остатках товаров Ozon...")
        
        manager = MarketplaceManager()
        
        # Получаем mapping товаров
        mapping_result = await manager.get_ozon_product_mapping()
        if not mapping_result["success"]:
            await message.answer(f"❌ Ошибка получения товаров: {mapping_result.get('error', 'Неизвестная ошибка')}")
            return
        
        mapping = mapping_result["mapping"]
        product_ids = list(mapping.values())
        
        # Получаем остатки через offer_id (правильный метод)
        offer_ids = list(mapping.keys())
        stocks_result = await manager.get_ozon_stocks_by_offer(offer_ids)
        
        if stocks_result["success"]:
            stocks = stocks_result["stocks"]
            total = len(mapping)
            logger.info(f"Результат получения остатков: {stocks_result}")
            logger.info(f"stocks={stocks}")
            
            await message.answer(f"✅ Получено товаров: {len(stocks)} из {total}")
            
            if stocks and isinstance(stocks, dict):
                # Получаем детальную информацию для названий
                detailed_result = await manager.get_ozon_products_detailed(product_ids)
                
                if detailed_result["success"]:
                    products = detailed_result["products"]
                    
                    # --- Читаем названия из таблицы (колонка B) один раз ---
                    try:
                        sheet_rows = await manager.sheets_api.read_data(
                            manager.spreadsheet_id,
                            f"{manager.sheet_name}!B:D"  # B=Название, D=offer_id
                        )
                        sheet_name_by_offer = {
                            row[2]: row[0] for row in sheet_rows if len(row) >= 3 and row[2]
                        }
                    except Exception as e:
                        logger.warning(f"Не удалось прочитать названия из таблицы: {e}")
                        sheet_name_by_offer = {}
                    
                    # Формируем детальный отчет по остаткам
                    detailed_report = f"📋 **Детальная информация об остатках Ozon**\n\n"
                    detailed_report += f"Всего товаров: {total}\n\n"
                    
                    # Статистика по остаткам
                    total_stock_sum = 0
                    products_with_stock = 0
                    products_without_stock = 0
                    
                    for offer_id in mapping.keys():
                        stock_info = stocks.get(offer_id, {})
                        if isinstance(stock_info, dict):
                            total_stock = stock_info.get("total", 0)
                            total_stock_sum += total_stock
                            if total_stock > 0:
                                products_with_stock += 1
                            else:
                                products_without_stock += 1
                    
                    detailed_report += f"📊 **Статистика остатков:**\n"
                    detailed_report += f"• Общий остаток: {total_stock_sum} шт.\n"
                    detailed_report += f"• Товаров с остатками: {products_with_stock}\n"
                    detailed_report += f"• Товаров без остатков: {products_without_stock}\n\n"
                    
                    # Детальная информация по каждому товару
                    for i, (offer_id, product_id) in enumerate(mapping.items(), 1):
                        stock_info = stocks.get(offer_id, {})  # Используем offer_id
                        product_info = products.get(str(product_id), {})
                        product_name = product_info.get("name", "Без названия")
                        if product_name == "Без названия":
                            product_name = sheet_name_by_offer.get(offer_id, "Без названия")
                        
                        detailed_report += f"**{i:2d}. {offer_id}** (ID: {product_id})\n"
                        detailed_report += f"   📝 {product_name}\n"
                        
                        # Информация об остатках
                        if isinstance(stock_info, dict):
                            total_stock = stock_info.get("total", 0)
                            warehouses = stock_info.get("warehouses", [])
                            
                            detailed_report += f"   📊 **Общий остаток: {total_stock} шт.**\n"
                            
                            if warehouses:
                                detailed_report += f"   🏪 **По складам:**\n"
                                for warehouse in warehouses:
                                    detailed_report += f"      • {warehouse['name']}: {warehouse['stock']} шт. (резерв: {warehouse['reserved']})\n"
                            else:
                                detailed_report += f"   🏪 **Склады:** Нет данных\n"
                        else:
                            # Fallback для старого формата
                            stock_count = stock_info if isinstance(stock_info, (int, str)) else 0
                            detailed_report += f"   📊 **Остаток: {stock_count} шт.**\n"
                        
                        detailed_report += "\n"
                    
                    # Разбиваем на части, если сообщение слишком длинное
                    if len(detailed_report) > 4000:
                        parts = []
                        current_part = ""
                        
                        lines = detailed_report.split('\n')
                        for line in lines:
                            if len(current_part) + len(line) + 1 > 3500:
                                parts.append(current_part.strip())
                                current_part = line + '\n'
                            else:
                                current_part += line + '\n'
                        
                        if current_part:
                            parts.append(current_part.strip())
                        
                        # Отправляем части
                        for i, part in enumerate(parts):
                            if i == 0:
                                await message.answer(f"✅ Получено товаров: {total}\n\n{part}", parse_mode="Markdown")
                            else:
                                await message.answer(f"📋 **Остатки Ozon (часть {i + 1})**\n\n{part}", parse_mode="Markdown")
                    else:
                        await message.answer(f"✅ Получено товаров: {total}\n\n{detailed_report}", parse_mode="Markdown")
                else:
                    await message.answer(f"❌ Ошибка получения детальной информации: {detailed_result.get('error', 'Неизвестная ошибка')}")
            else:
                logger.warning(f"stocks не является словарем или пустой: {type(stocks)} = {stocks}")
                await message.answer("📭 Остатки не найдены")
        else:
            await message.answer(f"❌ Ошибка получения остатков: {stocks_result.get('error', 'Неизвестная ошибка')}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_stocks_detailed: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)}")

async def cmd_ozon_debug_stocks(message: types.Message):
    """Команда для детальной диагностики проблемы с остатками Ozon"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("🔍 Запускаю детальную диагностику остатков Ozon...")
        
        manager = MarketplaceManager()
        
        # Шаг 1: Получаем список товаров
        result = await manager.get_ozon_product_mapping()
        if not result["success"]:
            await message.answer(f"❌ Ошибка получения товаров: {result.get('error')}")
            return
        
        mapping = result["mapping"]
        total = result["total_count"]
        
        if not mapping:
            await message.answer("📭 Товары не найдены")
            return
        
        # Шаг 2: Анализируем каждый товар отдельно
        debug_info = f"🔍 **Детальная диагностика остатков Ozon**\n\n"
        debug_info += f"📊 Всего товаров: {total}\n\n"
        
        for i, (offer_id, product_id) in enumerate(list(mapping.items())[:3], 1):  # Анализируем первые 3
            debug_info += f"**{i}. Товар {offer_id} (ID: {product_id})**\n"
            
            # Тестируем запрос остатков для одного товара
            try:
                # Пробуем разные варианты фильтров
                test_payloads = [
                    {
                        "cursor": "",
                        "filter": {
                            "product_id": [product_id],
                            "visibility": "ALL"
                        },
                        "limit": 100
                    },
                    {
                        "cursor": "",
                        "filter": {
                            "product_id": [product_id]
                        },
                        "limit": 100
                    },
                    {
                        "cursor": "",
                        "filter": {
                            "offer_id": [offer_id],
                            "visibility": "ALL"
                        },
                        "limit": 100
                    }
                ]
                
                for j, payload in enumerate(test_payloads, 1):
                    debug_info += f"   🔬 Тест {j}: {payload}\n"
                    
                    # Здесь можно добавить реальный API вызов для тестирования
                    # Пока просто показываем payload
                
                debug_info += "\n"
                
            except Exception as e:
                debug_info += f"   ❌ Ошибка анализа: {e}\n\n"
        
        debug_info += "💡 **Рекомендации:**\n"
        debug_info += "• Проверьте права доступа к API остатков\n"
        debug_info += "• Убедитесь, что товары имеют остатки на складах\n"
        debug_info += "• Попробуйте использовать offer_id вместо product_id\n"
        
        await message.answer(debug_info, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_debug_stocks: {e}")
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
    dp.message.register(cmd_ozon_debug, Command("ozon_debug"))
    dp.message.register(cmd_ozon_simple_test, Command("ozon_simple_test"))
    dp.message.register(cmd_ozon_stats, Command("ozon_stats"))
    dp.message.register(cmd_ozon_products, Command("ozon_products"))
    dp.message.register(cmd_ozon_products_all, Command("ozon_products_all"))
    dp.message.register(cmd_ozon_products_detailed, Command("ozon_products_detailed"))
    dp.message.register(cmd_ozon_stocks, Command("ozon_stocks"))
    dp.message.register(cmd_ozon_stocks_detailed, Command("ozon_stocks_detailed"))
    dp.message.register(cmd_ozon_sync_all, Command("ozon_sync_all"))
    dp.message.register(cmd_ozon_sync_single, Command("ozon_sync_single"))
    dp.message.register(cmd_ozon_debug_stocks, Command("ozon_debug_stocks"))
    
    # Команды Google Sheets
    dp.message.register(cmd_google_sheets_test, Command("sheets_test"))
    dp.message.register(cmd_google_sheets_info, Command("sheets_info"))
    dp.message.register(cmd_google_sheets_read, Command("sheets_read"))
    
    # Общие команды
    dp.message.register(cmd_marketplace_help, Command("marketplace_help"))
    
    logger.info("Обработчики команд маркетплейсов зарегистрированы")
