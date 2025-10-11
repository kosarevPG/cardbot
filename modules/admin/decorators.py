"""
Декораторы и утилиты для админской панели.
"""
import logging
from functools import wraps
from aiogram import types
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


async def check_admin_rights(user_id: int) -> bool:
    """
    Проверяет права администратора для пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        bool: True если пользователь админ, False иначе
    """
    try:
        from config import ADMIN_IDS
        return str(user_id) in ADMIN_IDS
    except ImportError:
        logger.error("Failed to import ADMIN_IDS")
        return False


async def safe_message_edit(message: types.Message, text: str, reply_markup=None, parse_mode="HTML"):
    """
    Безопасное редактирование сообщения с обработкой ошибки "message is not modified".
    
    Args:
        message: Сообщение для редактирования
        text: Новый текст
        reply_markup: Клавиатура (опционально)
        parse_mode: Режим парсинга (по умолчанию HTML)
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
        # Игнорируем ошибку, если сообщение не изменилось
        logger.debug("Message not modified, ignoring error")


def admin_required_message(func):
    """
    Декоратор для проверки прав администратора (для обработчиков сообщений).
    """
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        user_id = message.from_user.id
        
        try:
            from config import ADMIN_IDS
            if str(user_id) not in ADMIN_IDS:
                logger.warning(f"BLOCKED: User {user_id} attempted to access admin function: {func.__name__}")
                await message.answer("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.")
                return
        except ImportError as e:
            logger.error(f"CRITICAL: Failed to import ADMIN_IDS in {func.__name__}: {e}")
            await message.answer("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ")
            return
        
        return await func(message, *args, **kwargs)
    
    return wrapper


def admin_required_callback(func):
    """
    Декоратор для проверки прав администратора (для callback'ов).
    """
    @wraps(func)
    async def wrapper(callback: types.CallbackQuery, *args, **kwargs):
        user_id = callback.from_user.id
        
        try:
            from config import ADMIN_IDS
            if str(user_id) not in ADMIN_IDS:
                logger.warning(f"BLOCKED: User {user_id} attempted to access admin callback: {func.__name__}")
                await callback.answer("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", show_alert=True)
                return
        except ImportError as e:
            logger.error(f"CRITICAL: Failed to import ADMIN_IDS in {func.__name__}: {e}")
            await callback.answer("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", show_alert=True)
            return
        
        return await func(callback, *args, **kwargs)
    
    return wrapper

