"""
Декораторы для админской панели.
Содержит общие проверки и утилиты для админских функций.
"""
import logging
from functools import wraps
from aiogram import types

logger = logging.getLogger(__name__)


def admin_required(func):
    """
    Декоратор для проверки прав администратора.
    Применяется к async функциям, которые принимают message/callback и user_id.
    """
    @wraps(func)
    async def wrapper(message_or_callback, db, logger_service, user_id, *args, **kwargs):
        # Проверяем права администратора
        try:
            from config import ADMIN_IDS
            if str(user_id) not in ADMIN_IDS:
                error_text = "🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора."
                logger.warning(f"BLOCKED: User {user_id} attempted to access admin function: {func.__name__}")
                
                # Определяем тип объекта и отправляем соответствующее сообщение
                if isinstance(message_or_callback, types.CallbackQuery):
                    await message_or_callback.message.edit_text(error_text, parse_mode="HTML")
                else:
                    await message_or_callback.answer(error_text)
                return
        except ImportError as e:
            error_text = "🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ"
            logger.error(f"CRITICAL: Failed to import ADMIN_IDS in {func.__name__}: {e}")
            
            if isinstance(message_or_callback, types.CallbackQuery):
                await message_or_callback.message.edit_text(error_text, parse_mode="HTML")
            else:
                await message_or_callback.answer(error_text)
            return
        
        # Вызываем оригинальную функцию
        return await func(message_or_callback, db, logger_service, user_id, *args, **kwargs)
    
    return wrapper


def safe_edit_message(parse_mode="HTML"):
    """
    Декоратор для безопасного редактирования сообщений.
    Обрабатывает ошибку "message is not modified".
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from aiogram.exceptions import TelegramBadRequest
            try:
                return await func(*args, **kwargs)
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
                # Игнорируем ошибку, если сообщение не изменилось
                logger.debug(f"Message not modified in {func.__name__}, ignoring error")
        return wrapper
    return decorator


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

