# FORCE RESTART 2025-08-24 - ИСПРАВЛЕНИЕ Any ИМПОРТА
# FORCE RESTART 2025-08-24 - ИСПРАВЛЕНИЕ ozon_stocks_detailed - теперь использует правильный метод
# Команды для работы с маркетплейсами
from aiogram import types, Dispatcher
import logging
import json
import html
from .marketplace_manager import MarketplaceManager, get_manager
from .google_sheets import test_google_sheets_connection, get_sheets_info, read_sheet_data
from modules.texts import get_personalized_text, MARKETPLACE_TEXTS

logger = logging.getLogger(__name__)

# Убираем dp - используем функцию регистрации

# Импортируем ADMIN_IDS из config для согласованности
try:
    from config import ADMIN_IDS
except ImportError:
    # Fallback если config недоступен
    ADMIN_IDS = []
    logger.warning("Не удалось импортировать ADMIN_IDS из config.py")

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return str(user_id) in ADMIN_IDS

async def cmd_wb_test(message: types.Message):
    """Тест подключения к WB API"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return

    await message.answer("🔄 Тестирую подключение к Wildberries API...")

    try:
        manager = get_manager()
        result = await manager.get_wb_warehouses()

        if result.get("success"):
            await message.answer("✅ Подключение к Wildberries API успешно! Склады получены.")
        else:
            await message.answer(f"❌ Ошибка подключения к Wildberries API: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Ошибка в команде wb_test: {e}", exc_info=True)
        await message.answer(f"❌ Произошла критическая ошибка: {str(e)}")

async def cmd_wb_stats(message: types.Message):
    """Статистика остатков WB"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return

    await message.answer("📊 Получаю остатки Wildberries...")

    try:
        manager = get_manager()

        warehouses_result = await manager.get_wb_warehouses()
        if not warehouses_result.get("success") or not warehouses_result.get("warehouses"):
            await message.answer(f"❌ Не удалось получить склады Wildberries: {warehouses_result.get('error')}")
            return

        # готовим barcodes один раз
        barcodes_res = await manager.get_wb_product_barcodes()
        if not barcodes_res.get("success"):
            await message.answer(f"❌ Не удалось получить артикулы: {barcodes_res.get('error')}")
            return
        barcodes = barcodes_res["barcodes"]

        total_positions = 0
        total_units = 0

        for wh in warehouses_result["warehouses"]:
            wid   = wh["id"]
            wname = wh["name"]
            stocks_res = await manager.get_wb_stocks(wid, barcodes)
            if not stocks_res.get("success"):
                continue
            items = stocks_res["stocks"].get("stocks", [])
            total_positions += len(items)
            total_units += sum(it.get("amount",0) for it in items)

        msg = (
            "📊 **Остатки Wildberries (все склады)**\n\n"
            f"Складов учтено: {len(warehouses_result['warehouses'])}\n"
            f"Позиции: {total_positions}\n"
            f"Всего единиц: {total_units}"
        )
        await message.answer(msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка в команде wb_stats: {e}", exc_info=True)
        await message.answer(f"❌ Произошла критическая ошибка: {str(e)}")

async def cmd_get_prices(message: types.Message):
    """Получение актуальных цен товаров"""
    if not is_admin(message.from_user.id):
        user_id = message.from_user.id
        text = get_personalized_text('errors.access_denied', MARKETPLACE_TEXTS, user_id, None)
        await message.reply(text)
        return
    
    try:
        user_id = message.from_user.id
        text = get_personalized_text('getting_prices', MARKETPLACE_TEXTS, user_id, None)
        await message.reply(text)
        
        manager = get_manager()
        result = await manager.update_prices_in_sheets()
        
        if result.get("success"):
            user_id = message.from_user.id
            text = get_personalized_text('prices_updated_success', MARKETPLACE_TEXTS, user_id, None).format(
                ozon_count=result.get('ozon_prices_count', 0),
                wb_count=result.get('wb_prices_count', 0)
            )
            await message.reply(text)

            # Дополнительно: показываем список товаров с ценами из Google Sheets.
            # Это самый надёжный источник (даже если API Ozon/WB не отдаёт цены).

            def _fmt_rub(val) -> str:
                try:
                    s = str(val).strip().replace("₽", "").replace(",", ".")
                    if not s:
                        return "н/д"
                    f = float(s)
                except Exception:
                    return "н/д"
                if f.is_integer():
                    return f"{int(f)} ₽"
                return f"{f:.2f} ₽"

            def _chunk_send(title: str, lines: list[str], max_chars: int = 3500) -> list[str]:
                """Собирает пачки текста под лимит Telegram (4096) и возвращает готовые сообщения."""
                if not lines:
                    return []
                chunks: list[str] = []
                cur = title + "\n"
                for line in lines:
                    if len(cur) + len(line) + 1 > max_chars:
                        chunks.append(cur.rstrip())
                        cur = title + "\n" + line + "\n"
                    else:
                        cur += line + "\n"
                if cur.strip():
                    chunks.append(cur.rstrip())
                return chunks

            sheet_data = None
            try:
                sheet_res = await manager.sheets_api.get_sheet_data(manager.spreadsheet_id, manager.sheet_name)
                sheet_data = sheet_res.get("data") if isinstance(sheet_res, dict) else None
            except Exception:
                sheet_data = None

            oz_lines: list[str] = []
            wb_lines: list[str] = []

            # Индексы колонок (0-based): A=0, C=2, D=3, P=15, Q=16
            if sheet_data and isinstance(sheet_data, list) and len(sheet_data) >= 2:
                for row in sheet_data[1:]:
                    if not isinstance(row, list):
                        continue
                    name = str((row[0] if len(row) > 0 else "") or "").strip()
                    nm_id = str((row[2] if len(row) > 2 else "") or "").strip()
                    offer_id = str((row[3] if len(row) > 3 else "") or "").strip()
                    wb_price_cell = (row[15] if len(row) > 15 else "") or ""
                    oz_price_cell = (row[16] if len(row) > 16 else "") or ""

                    title = name or offer_id or nm_id or "—"

                    if offer_id:
                        oz_lines.append(f"• {title} — {_fmt_rub(oz_price_cell)} (offer_id: {offer_id})")
                    if nm_id:
                        wb_lines.append(f"• {title} — {_fmt_rub(wb_price_cell)} (nm_id: {nm_id})")

            # Отправляем аккуратно, чтобы не превысить лимит сообщения
            if oz_lines:
                for msg_part in _chunk_send("🛒 Цены Ozon (из таблицы):", oz_lines[:200]):
                    await message.answer(msg_part)
            else:
                await message.answer("🛒 Цены Ozon: не удалось прочитать таблицу/нет строк с offer_id.")

            if wb_lines:
                for msg_part in _chunk_send("🛍️ Цены Wildberries (из таблицы):", wb_lines[:200]):
                    await message.answer(msg_part)
            else:
                await message.answer("🛍️ Цены Wildberries: не удалось прочитать таблицу/нет строк с nm_id.")
        else:
            user_id = message.from_user.id
            text = get_personalized_text('prices_update_error', MARKETPLACE_TEXTS, user_id, None).format(
                error=result.get('error', 'Неизвестная ошибка')
            )
            await message.reply(text)
            
    except Exception as e:
        logger.error(f"Ошибка в команде get_prices: {e}", exc_info=True)
        user_id = message.from_user.id
        text = get_personalized_text('prices_critical_error', MARKETPLACE_TEXTS, user_id, None)
        await message.reply(text)

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

**Цены товаров:**
• `/get_prices` - Получить актуальные цены всех товаров
• `/ozon_products_all` - Полный список всех товаров
• `/ozon_products_detailed` - Детальная информация о всех товарах
• `/ozon_stocks` - Остатки товаров (первые 5, с названиями)
• `/ozon_stocks_detailed` - Детальная информация об остатках по складам
• `/ozon_sync_all` - Синхронизация всех данных с Google таблицей
• `/ozon_sync_single OFFER_ID` - Синхронизация одного товара
• `/ozon_fill_by_id ID` - Автозаполнение товара по offer_id или product_id (название, остатки, цены)

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
    """Список товаров WB"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return

    await message.answer("📦 Получаю список артикулов Wildberries...")

    try:
        manager = get_manager()
        barcodes_result = await manager.get_wb_product_barcodes()

        if barcodes_result.get("success"):
            barcodes = barcodes_result.get("barcodes", [])
            if not barcodes:
                await message.answer("📭 Товары не найдены.")
                return

            response_text = f"✅ **Найдено артикулов: {len(barcodes)}**\n\n"
            response_text += "```\n" + "\n".join(barcodes[:20]) + "\n```"
            if len(barcodes) > 20:
                response_text += f"\n...и еще {len(barcodes) - 20}."

            await message.answer(response_text, parse_mode="Markdown")
        else:
            await message.answer(f"❌ Ошибка: {barcodes_result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Ошибка в команде wb_products: {e}", exc_info=True)
        await message.answer(f"❌ Произошла критическая ошибка: {str(e)}")

async def cmd_wb_stocks(message: types.Message):
    """Шорткат для остатков WB"""
    await cmd_wb_stats(message)

# ------------------ НОВАЯ КОМАНДА: /wb_sync_all ------------------
async def cmd_wb_sync_all(message: types.Message):
    """Синхронизирует остатки WB (total/FBO/FBS) в Google Sheet"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return

    await message.answer("🔄 Синхронизирую остатки Wildberries с таблицей…")

    try:
        mgr = get_manager()
        res = await mgr.sync_wb_stock_to_sheet()
        if res.get("success"):
            await message.answer(f"✅ Обновлены остатки для {res.get('updated',0)} товаров")
        else:
            await message.answer(f"❌ Ошибка: {res.get('error')}")
    except Exception as e:
        logger.exception("cmd_wb_sync_all error")
        await message.answer(f"❌ Критическая ошибка: {e}")
# ----------------------------------------------------------------

# ------------------ НОВАЯ КОМАНДА: /wb_warehouses ------------------
async def cmd_wb_get_warehouses(message: types.Message):
    """Возвращает список складов WB и их ID"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return

    await message.answer("🔍 Получаю список складов Wildberries...")

    try:
        manager = get_manager()
        result = await manager.get_wb_warehouses()

        if result.get("success"):
            warehouses = result.get("warehouses", [])
            if not warehouses:
                await message.answer("📭 Склады не найдены.")
                return

            response_text = "✅ **Ваши склады Wildberries:**\n\n"
            for wh in warehouses:
                wh_name = wh.get('name', 'Без имени')
                wh_id = wh.get('id', 'Нет ID')
                response_text += f"**Название:** {wh_name}\n**ID:** `{wh_id}`\n\n"

            await message.answer(response_text, parse_mode="Markdown")
        else:
            await message.answer(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")

    except Exception as e:
        logger.error(f"Ошибка в команде wb_get_warehouses: {e}")
        await message.answer(f"❌ Произошла критическая ошибка: {str(e)}")
# ------------------------------------------------------------------

# ---------- Временная команда: /wb_warehouses_json -----------------
async def cmd_wb_warehouses_json(message: types.Message):
    """Выводит сырой JSON списка складов WB (для диагностики)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет прав"); return

    mgr = get_manager()
    res = await mgr.get_wb_warehouses()
    await message.answer(f"```json\n{json.dumps(res, ensure_ascii=False, indent=2)[:3500]}\n```", parse_mode="Markdown")
# ------------------------------------------------------------------

async def cmd_ozon_test(message: types.Message):
    """Команда для тестирования подключения к Ozon API"""
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        await message.answer("🔄 Тестирую подключение к Ozon API...")
        
        manager = get_manager()
        
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
        
        manager = get_manager()
        
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
        
        manager = get_manager()
        
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
        
        manager = get_manager()
        
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
        
        manager = get_manager()
        
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
        
        manager = get_manager()
        
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
        
        manager = get_manager()
        
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
    """Команда для получения сводных остатков Ozon (total/FBO/FBS)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды."); return

    try:
        await message.answer("📊 Считаю остатки Ozon…")
        mgr = get_manager()
        res = await mgr.sync_ozon_data()
        if not res.get("success"):
            await message.answer(f"❌ Ошибка: {res.get('error')}"); return

        data = res["data"]
        total_total = sum(v["total_stock"] for v in data.values())
        total_fbo   = sum(v["fbo_stock"]   for v in data.values())
        total_fbs   = sum(v["fbs_stock"]   for v in data.values())

        msg = (
            f"📊 **Остатки Ozon**\n\n"
            f"Товаров: {len(data)}\n"
            f"• Общий остаток: {total_total}\n"
            f"• FBO: {total_fbo}\n"
            f"• FBS: {total_fbs}"
        )

        await message.answer(msg, parse_mode="Markdown")

    except Exception as e:
        logger.exception("cmd_ozon_stocks error")
        await message.answer(f"❌ Критическая ошибка: {e}")

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
        
        manager = get_manager()
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
        
        # TODO: Реализовать функцию sync_single_ozon_offer в marketplace_manager
        manager = get_manager()
        
        # Временно используем синхронизацию всех товаров
        result = await manager.sync_ozon_data()
        
        if result['success']:
            await message.answer(f"✅ Синхронизация завершена", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}", parse_mode="Markdown")
        
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
        
        manager = get_manager()
        
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
        
        manager = get_manager()
        
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

async def cmd_ozon_fill_by_id(message: types.Message):
    """
    Автозаполнение данных товара Ozon по offer_id или product_id.
    Команда: /ozon_fill_by_id <offer_id или product_id>
    
    Примеры:
    /ozon_fill_by_id KU-3-PVK
    /ozon_fill_by_id 2343897353
    """
    # Проверяем права администратора
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для выполнения этой команды. Требуются права администратора.")
        return
    
    try:
        # Получаем ID из сообщения
        command_parts = message.text.split(maxsplit=1)
        if len(command_parts) < 2:
            await message.answer(
                "❌ Укажите offer_id или product_id товара.\n\n"
                "Примеры:\n"
                "• /ozon_fill_by_id KU-3-PVK - по offer_id\n"
                "• /ozon_fill_by_id 2343897353 - по product_id"
            )
            return
        
        product_id = command_parts[1].strip()
        
        await message.answer(f"🔄 Получаю данные о товаре {product_id} из Ozon...")
        
        manager = get_manager()
        result = await manager.fill_ozon_product_by_id(product_id)
        
        if result.get("success"):
            offer_id = result.get("offer_id")
            product_name = result.get("name", "Без названия")
            stock = result.get("stock", 0)
            stock_fbo = result.get("stock_fbo", 0)
            stock_fbs = result.get("stock_fbs", 0)
            price = result.get("price")
            row = result.get("row")
            
            response = f"✅ **Товар успешно заполнен в таблице!**\n\n"
            response += f"📝 **Название:** {product_name}\n"
            response += f"🆔 **Offer ID:** {offer_id}\n"
            response += f"🆔 **Product ID:** {result.get('product_id')}\n"
            response += f"📊 **Остатки:**\n"
            response += f"   • Всего: {stock} шт.\n"
            response += f"   • FBO: {stock_fbo} шт.\n"
            response += f"   • FBS: {stock_fbs} шт.\n"
            if price:
                response += f"💰 **Цена:** {price} ₽\n"
            response += f"📍 **Строка в таблице:** {row}\n"
            
            await message.answer(response, parse_mode="Markdown")
        else:
            error = result.get("error", "Неизвестная ошибка")
            await message.answer(f"❌ Ошибка заполнения товара: {error}")
            
    except Exception as e:
        logger.error(f"Ошибка в команде ozon_fill_by_id: {e}", exc_info=True)
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
    dp.message.register(cmd_wb_get_warehouses, Command("wb_warehouses"))
    dp.message.register(cmd_wb_warehouses_json, Command("wb_warehouses_json"))
    # новая команда синхрон WB
    dp.message.register(cmd_wb_sync_all, Command("wb_sync_all"))
    
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
    dp.message.register(cmd_ozon_fill_by_id, Command("ozon_fill_by_id"))
    
    # Команды цен
    dp.message.register(cmd_get_prices, Command("get_prices"))
    
    # Команды Google Sheets
    dp.message.register(cmd_google_sheets_test, Command("sheets_test"))
    dp.message.register(cmd_google_sheets_info, Command("sheets_info"))
    dp.message.register(cmd_google_sheets_read, Command("sheets_read"))
    
    # Общие команды
    dp.message.register(cmd_marketplace_help, Command("marketplace_help"))
    
    logger.info("Обработчики команд маркетплейсов зарегистрированы")
