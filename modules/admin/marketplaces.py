"""
Модуль управления маркетплейсами в админ-панели.
"""
import logging
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from database.db import Database
from modules.logging_service import LoggingService

logger = logging.getLogger(__name__)


async def show_admin_marketplaces(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает меню управления маркетплейсами."""
    
    # Проверяем права администратора
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("❌ У вас нет доступа к этой функции.", parse_mode="HTML")
            return
    except ImportError as e:
        logger.error(f"Failed to import ADMIN_IDS: {e}")
        await message.edit_text("❌ Ошибка проверки прав доступа.", parse_mode="HTML")
        return
    
    try:
        text = """🛍️ <b>УПРАВЛЕНИЕ МАРКЕТПЛЕЙСАМИ</b>

<b>Доступные маркетплейсы:</b>
• <b>Ozon</b> - Остатки, продажи, синхронизация
• <b>Wildberries</b> - Остатки, склады, синхронизация
• <b>Google Sheets</b> - Таблицы с данными

<b>Основные команды:</b>

<b>🔸 Ozon:</b>
• <code>/ozon_test</code> - Тест подключения
• <code>/ozon_products</code> - Список товаров (первые 5)
• <code>/ozon_products_all</code> - Полный список товаров
• <code>/ozon_stocks</code> - Остатки товаров
• <code>/ozon_stocks_detailed</code> - Детальная информация об остатках
• <code>/ozon_sync_all</code> - Синхронизация с Google Sheets

<b>🔸 Wildberries:</b>
• <code>/wb_test</code> - Тест подключения
• <code>/wb_products</code> - Список артикулов
• <code>/wb_stats</code> - Статистика остатков
• <code>/wb_warehouses</code> - Список складов
• <code>/wb_sync_all</code> - Синхронизация с Google Sheets

<b>🔸 Google Sheets:</b>
• <code>/sheets_test</code> - Тест подключения
• <code>/sheets_info SPREADSHEET_ID</code> - Информация о таблице
• <code>/sheets_read SPREADSHEET_ID [SHEET_NAME]</code> - Чтение данных

<i>💡 Все команды доступны только администраторам</i>"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_marketplaces")],
            [types.InlineKeyboardButton(text="← Назад в меню", callback_data="admin_main")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        
        await logger_service.log_action(user_id, "admin_marketplaces_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin marketplaces: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке меню маркетплейсов"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад в меню", callback_data="admin_main")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise


def show_admin_main_menu():
    """Возвращает главное меню админки."""
    text = """📊 <b>АДМИН ПАНЕЛЬ</b>

Выберите раздел для просмотра метрик:"""
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔍 Главный дашборд", callback_data="admin_dashboard")],
        [types.InlineKeyboardButton(text="📈 Метрики удержания", callback_data="admin_retention")],
        [types.InlineKeyboardButton(text="🔄 Воронка 'Карта дня'", callback_data="admin_funnel")],
        [types.InlineKeyboardButton(text="💎 Метрики ценности", callback_data="admin_value")],
        [types.InlineKeyboardButton(text="🃏 Статистика колод", callback_data="admin_decks")],
        [types.InlineKeyboardButton(text="🌙 Вечерняя рефлексия", callback_data="admin_reflections")],
        [types.InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [types.InlineKeyboardButton(text="📋 Детальные логи", callback_data="admin_logs")],
        [types.InlineKeyboardButton(text="📝 Управление постами", callback_data="admin_posts")],
        [types.InlineKeyboardButton(text="🛍️ Маркетплейсы", callback_data="admin_marketplaces")]
    ])
    
    return text, keyboard

