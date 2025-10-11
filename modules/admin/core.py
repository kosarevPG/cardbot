"""
Ядро админской панели: основные обработчики и роутинг.
"""
import logging
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from database.db import Database
from modules.logging_service import LoggingService

logger = logging.getLogger(__name__)


def make_admin_handler(db: Database, logger_service: LoggingService):
    """Создает обработчик для команды /admin."""
    async def admin_handler(message: types.Message):
        user_id = message.from_user.id
        
        # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
        try:
            from config import ADMIN_IDS
            if str(user_id) not in ADMIN_IDS:
                logger.warning(f"BLOCKED: User {user_id} attempted to access admin panel via /admin")
                await message.answer("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.")
                return
        except ImportError as e:
            logger.error(f"CRITICAL: Failed to import ADMIN_IDS in admin handler: {e}")
            await message.answer("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ")
            return
        
        # Главное меню админки
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
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await logger_service.log_action(user_id, "admin_panel_opened", {})
    
    return admin_handler


def make_admin_callback_handler(db: Database, logger_service: LoggingService):
    """Создает обработчик для callback'ов админ-панели."""
    async def admin_callback_handler(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        
        # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
        try:
            from config import ADMIN_IDS
            if str(user_id) not in ADMIN_IDS:
                logger.warning(f"BLOCKED: User {user_id} attempted to access admin callback: {callback.data}")
                await callback.answer("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", show_alert=True)
                return
        except ImportError as e:
            logger.error(f"CRITICAL: Failed to import ADMIN_IDS in callback handler: {e}")
            await callback.answer("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", show_alert=True)
            return
        
        # Динамический импорт для избежания циклических зависимостей
        from modules.admin.dashboard import (
            show_admin_dashboard, show_admin_retention, show_admin_funnel,
            show_admin_value, show_admin_decks, show_admin_reflections, 
            show_admin_recent_reflections, show_admin_logs
        )
        from modules.admin.users import (
            show_admin_users, show_admin_users_list,
            show_admin_requests, show_admin_requests_full
        )
        from modules.admin.posts import (
            show_admin_posts, start_post_creation, show_posts_list,
            show_mailings_list, process_mailings_now
        )
        from modules.admin.marketplaces import show_admin_marketplaces
        
        action = callback.data
        
        # Роутинг callback'ов
        if action == "admin_dashboard":
            await show_admin_dashboard(callback.message, db, logger_service, user_id, 7)
        elif action.startswith("admin_dashboard_"):
            try:
                days = int(action.split("_")[-1])
                await show_admin_dashboard(callback.message, db, logger_service, user_id, days)
            except ValueError:
                await show_admin_dashboard(callback.message, db, logger_service, user_id, 7)
        
        elif action == "admin_retention":
            await show_admin_retention(callback.message, db, logger_service, user_id)
        
        elif action == "admin_funnel":
            await show_admin_funnel(callback.message, db, logger_service, user_id, 7)
        elif action.startswith("admin_funnel_"):
            try:
                days = int(action.split("_")[-1])
                await show_admin_funnel(callback.message, db, logger_service, user_id, days)
            except ValueError:
                await show_admin_funnel(callback.message, db, logger_service, user_id, 7)
        
        elif action == "admin_value":
            await show_admin_value(callback.message, db, logger_service, user_id, 7)
        elif action.startswith("admin_value_"):
            try:
                days = int(action.split("_")[-1])
                await show_admin_value(callback.message, db, logger_service, user_id, days)
            except ValueError:
                await show_admin_value(callback.message, db, logger_service, user_id, 7)
        
        elif action == "admin_decks":
            await show_admin_decks(callback.message, db, logger_service, user_id, 7)
        elif action.startswith("admin_decks_"):
            try:
                days = int(action.split("_")[-1])
                await show_admin_decks(callback.message, db, logger_service, user_id, days)
            except ValueError:
                await show_admin_decks(callback.message, db, logger_service, user_id, 7)
        
        elif action == "admin_reflections":
            await show_admin_reflections(callback.message, db, logger_service, user_id, 7)
        elif action.startswith("admin_reflections_"):
            try:
                days = int(action.split("_")[-1])
                await show_admin_reflections(callback.message, db, logger_service, user_id, days)
            except ValueError:
                await show_admin_reflections(callback.message, db, logger_service, user_id, 7)
        elif action.startswith("admin_recent_reflections_"):
            try:
                days = int(action.split("_")[-1])
                await show_admin_recent_reflections(callback.message, db, logger_service, user_id, days)
            except ValueError:
                await show_admin_recent_reflections(callback.message, db, logger_service, user_id, 7)
        elif action.startswith("admin_reflection_detail_"):
            try:
                user_reflection_id = int(action.split("_")[-1])
                # TODO: Реализовать show_reflection_detail
                await callback.answer("Функция в разработке", show_alert=True)
            except ValueError:
                await callback.answer("Ошибка: неверный ID рефлексии", show_alert=True)
        
        elif action == "admin_users":
            await show_admin_users(callback.message, db, logger_service, user_id)
        elif action == "admin_users_list":
            await show_admin_users_list(callback.message, db, logger_service, user_id)
        elif action.startswith("admin_users_page_"):
            try:
                page = int(action.split("_")[-1])
                await show_admin_users_list(callback.message, db, logger_service, user_id, page)
            except ValueError:
                await show_admin_users_list(callback.message, db, logger_service, user_id)
        
        elif action == "admin_requests":
            await show_admin_requests(callback.message, db, logger_service, user_id)
        elif action == "admin_requests_full":
            await show_admin_requests_full(callback.message, db, logger_service, user_id)
        
        elif action == "admin_logs":
            await show_admin_logs(callback.message, db, logger_service, user_id)
        
        elif action == "admin_posts":
            await show_admin_posts(callback.message, db, logger_service, user_id)
        elif action == "admin_create_post":
            await start_post_creation(callback.message, db, logger_service, user_id)
        elif action == "admin_list_posts":
            await show_posts_list(callback.message, db, logger_service, user_id)
        elif action == "admin_list_mailings":
            await show_mailings_list(callback.message, db, logger_service, user_id)
        elif action == "admin_process_mailings":
            await process_mailings_now(callback.message, db, logger_service, user_id)
        
        elif action == "admin_marketplaces":
            await show_admin_marketplaces(callback.message, db, logger_service, user_id)
        
        elif action == "admin_back" or action == "admin_main":
            await show_admin_main_menu(callback.message, db, logger_service, user_id)
        
        await callback.answer()
    
    return admin_callback_handler


async def show_admin_main_menu(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает главное меню админ-панели."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin main menu")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
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
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await logger_service.log_action(user_id, "admin_main_menu_viewed", {})
    except Exception as e:
        logger.error(f"Error showing admin main menu: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке меню администратора"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

