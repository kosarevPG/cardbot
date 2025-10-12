"""
Админ модуль для просмотра логов обучения
"""
import logging
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from database.db import Database
from modules.logging_service import LoggingService
from modules.training_logger import TrainingLogger
from modules.texts import get_personalized_text, ERROR_TEXTS

logger = logging.getLogger(__name__)

async def show_admin_training_logs(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает меню логов обучения."""
    try:
        training_logger = TrainingLogger(db)
        
        # Получаем статистику за последние 7 дней
        stats = training_logger.get_training_stats(days=7)
        
        if not stats.get("success"):
            await message.edit_text("❌ Ошибка получения статистики обучения.", parse_mode="HTML")
            return
        
        # Формируем текст статистики
        text = "📚 <b>ЛОГИ ОБУЧЕНИЯ</b>\n\n"
        
        if stats.get("overall_stats"):
            text += "📊 <b>Статистика за 7 дней:</b>\n"
            
            current_training = None
            for stat in stats["overall_stats"]:
                training_type = stat["training_type"]
                step = stat["step"]
                count = stat["count"]
                unique_users = stat["unique_users"]
                
                if training_type != current_training:
                    text += f"\n🔹 <b>{training_type.replace('_', ' ').title()}:</b>\n"
                    current_training = training_type
                
                step_emoji = {
                    "started": "▶️",
                    "completed": "✅", 
                    "abandoned": "❌"
                }.get(step, "📝")
                
                step_name = {
                    "started": "Начали",
                    "completed": "Завершили",
                    "abandoned": "Бросили"
                }.get(step, step)
                
                text += f"{step_emoji} {step_name}: {count} раз ({unique_users} чел.)\n"
        else:
            text += "📝 За последние 7 дней обучение не проходил никто.\n"
        
        # Получаем последние пользователи
        recent_users = training_logger.get_training_users(limit=10)
        
        if recent_users:
            text += "\n👥 <b>Последние участники:</b>\n"
            for user in recent_users[:5]:  # Показываем только 5 последних
                # sqlite3.Row обращается как к словарю
                username = user["username"] if user["username"] else ""
                first_name = user["first_name"] if user["first_name"] else ""
                last_name = user["last_name"] if user["last_name"] else ""
                
                # Форматируем имя пользователя
                display_name = f"{first_name} {last_name}".strip()
                if username:
                    display_name += f" (@{username})"
                if not display_name:
                    display_name = f"ID: {user['user_id']}"
                
                step_emoji = {
                    "started": "▶️",
                    "completed": "✅",
                    "abandoned": "❌"
                }.get(user["step"], "📝")
                
                training_name = user["training_type"].replace("_", " ").title()
                text += f"{step_emoji} {display_name} - {training_name}\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📊 Детальная статистика", callback_data="admin_training_stats")],
            [types.InlineKeyboardButton(text="👥 Все участники", callback_data="admin_training_users")],
            [types.InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="admin_training_search")],
            [types.InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_training_settings")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_training_logs")],
            [types.InlineKeyboardButton(text="← Назад в Админ-панель", callback_data="admin_main")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await logger_service.log_action(user_id, "admin_training_logs_viewed", {})
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                logger.error(f"Error editing message in show_admin_training_logs: {e}", exc_info=True)
                text = get_personalized_text('admin.training_logs_load_error', ERROR_TEXTS, user_id, db)
                await message.answer(text)
                
    except Exception as e:
        logger.error(f"Error showing admin training logs: {e}", exc_info=True)
        text = get_personalized_text('admin.training_logs_critical_error', ERROR_TEXTS, user_id, db)
        await message.answer(text)

async def show_admin_training_stats(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает детальную статистику обучения."""
    try:
        training_logger = TrainingLogger(db)
        
        # Получаем статистику за разные периоды
        stats_7d = training_logger.get_training_stats(days=7)
        stats_30d = training_logger.get_training_stats(days=30)
        
        text = "📊 <b>ДЕТАЛЬНАЯ СТАТИСТИКА ОБУЧЕНИЯ</b>\n\n"
        
        # Статистика за 7 дней
        text += "📅 <b>За 7 дней:</b>\n"
        if stats_7d.get("overall_stats"):
            for stat in stats_7d["overall_stats"]:
                training_type = stat["training_type"].replace("_", " ").title()
                step = stat["step"]
                count = stat["count"]
                unique_users = stat["unique_users"]
                
                step_name = {
                    "started": "Начали",
                    "completed": "Завершили", 
                    "abandoned": "Бросили"
                }.get(step, step)
                
                text += f"• {training_type} - {step_name}: {count} ({unique_users} чел.)\n"
        else:
            text += "Нет данных\n"
        
        text += "\n📅 <b>За 30 дней:</b>\n"
        if stats_30d.get("overall_stats"):
            for stat in stats_30d["overall_stats"]:
                training_type = stat["training_type"].replace("_", " ").title()
                step = stat["step"]
                count = stat["count"]
                unique_users = stat["unique_users"]
                
                step_name = {
                    "started": "Начали",
                    "completed": "Завершили",
                    "abandoned": "Бросили"
                }.get(step, step)
                
                text += f"• {training_type} - {step_name}: {count} ({unique_users} чел.)\n"
        else:
            text += "Нет данных\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_training_stats")],
            [types.InlineKeyboardButton(text="← Назад к логам", callback_data="admin_training_logs")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await logger_service.log_action(user_id, "admin_training_stats_viewed", {})
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                logger.error(f"Error editing message in show_admin_training_stats: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Error showing admin training stats: {e}", exc_info=True)
        text = get_personalized_text('admin.training_stats_error', ERROR_TEXTS, user_id, db)
        await message.answer(text)

async def show_admin_training_users(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает список всех участников обучения."""
    try:
        training_logger = TrainingLogger(db)
        
        # Получаем всех пользователей
        users = training_logger.get_training_users(limit=50)
        
        text = "👥 <b>УЧАСТНИКИ ОБУЧЕНИЯ</b>\n\n"
        
        if users:
            for i, user in enumerate(users, 1):
                # sqlite3.Row обращается как к словарю
                username = user["username"] if user["username"] else ""
                first_name = user["first_name"] if user["first_name"] else ""
                last_name = user["last_name"] if user["last_name"] else ""
                user_id_display = user["user_id"]
                
                # Форматируем имя пользователя
                display_name = f"{first_name} {last_name}".strip()
                if username:
                    display_name += f" (@{username})"
                if not display_name:
                    display_name = f"ID: {user_id_display}"
                
                step_emoji = {
                    "started": "▶️",
                    "completed": "✅",
                    "abandoned": "❌"
                }.get(user["step"], "📝")
                
                training_name = user["training_type"].replace("_", " ").title()
                timestamp = user["timestamp"]
                
                text += f"{i}. {step_emoji} <b>{display_name}</b>\n"
                text += f"   📚 {training_name}\n"
                text += f"   🕒 {timestamp}\n\n"
                
                # Ограничиваем длину сообщения
                if len(text) > 3500:
                    text += f"... и еще {len(users) - i} участников"
                    break
        else:
            text += "📝 Пока никто не проходил обучение."
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_training_users")],
            [types.InlineKeyboardButton(text="← Назад к логам", callback_data="admin_training_logs")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await logger_service.log_action(user_id, "admin_training_users_viewed", {})
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                logger.error(f"Error editing message in show_admin_training_users: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"Error showing admin training users: {e}", exc_info=True)
        text = get_personalized_text('admin.training_users_error', ERROR_TEXTS, user_id, db)
        await message.answer(text)
