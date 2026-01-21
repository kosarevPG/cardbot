# код/modules/decorators.py
"""
Декораторы для обработчиков бота.
"""

import logging
import functools
import asyncio
from typing import Callable, Any
from aiogram import types
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError
from aiohttp.client_exceptions import ClientConnectorError

logger = logging.getLogger(__name__)


def safe_handler(func: Callable) -> Callable:
    """
    Декоратор для безопасной обработки исключений в хендлерах.
    Логирует ошибки и предотвращает падение бота.
    Специальная обработка сетевых ошибок Telegram - не пытается отправлять сообщения при проблемах с сетью.
    
    Usage:
        @safe_handler
        async def my_handler(message: types.Message):
            # your code
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (TelegramNetworkError, ClientConnectorError) as e:
            # Сетевые ошибки - не пытаемся отправлять сообщения, только логируем
            logger.warning(
                f"Network error in handler {func.__name__}: {e}. "
                f"This is usually a temporary connectivity issue with Telegram API. "
                f"Handler will retry on next update."
            )
            # Не пытаемся отправлять сообщения при сетевых ошибках
            return None
        except TelegramAPIError as e:
            # Ошибки API Telegram (не сетевые) - логируем и пытаемся уведомить
            logger.error(f"Telegram API error in handler {func.__name__}: {e}", exc_info=True)
            # Пытаемся уведомить пользователя только если это не сетевой сбой
            try:
                for arg in args:
                    if isinstance(arg, types.Message):
                        await arg.answer("Произошла ошибка. Попробуйте позже или обратитесь к администратору.")
                        break
                    elif isinstance(arg, types.CallbackQuery):
                        await arg.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
                        break
            except Exception as notify_err:
                logger.error(f"Failed to notify user about Telegram API error: {notify_err}")
        except Exception as e:
            logger.error(f"Error in handler {func.__name__}: {e}", exc_info=True)
            # Пытаемся уведомить пользователя
            try:
                # Ищем Message или CallbackQuery в аргументах
                for arg in args:
                    if isinstance(arg, types.Message):
                        await arg.answer("Произошла ошибка. Попробуйте позже или обратитесь к администратору.")
                        break
                    elif isinstance(arg, types.CallbackQuery):
                        await arg.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)
                        break
            except Exception as notify_err:
                logger.error(f"Failed to notify user about error: {notify_err}")
    return wrapper


def log_handler_call(func: Callable) -> Callable:
    """
    Декоратор для логирования вызова обработчика.
    
    Usage:
        @log_handler_call
        async def my_handler(message: types.Message):
            # your code
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        handler_name = func.__name__
        # Пытаемся получить user_id для более информативного логирования
        user_id = None
        for arg in args:
            if isinstance(arg, (types.Message, types.CallbackQuery)):
                user_id = arg.from_user.id if arg.from_user else None
                break
        
        if user_id:
            logger.debug(f"Handler {handler_name} called by user {user_id}")
        else:
            logger.debug(f"Handler {handler_name} called")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Handler {handler_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Handler {handler_name} failed: {e}", exc_info=True)
            raise
    
    return wrapper


def with_user_data(db_key: str = 'db'):
    """
    Декоратор для автоматического получения user_data из БД и добавления в kwargs.
    
    Args:
        db_key: Ключ, по которому в kwargs находится объект Database
    
    Usage:
        @with_user_data(db_key='db')
        async def my_handler(message: types.Message, db, user_data):
            # user_data автоматически извлечен из БД
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Получаем db из kwargs
            db = kwargs.get(db_key)
            if not db:
                logger.warning(f"Database object not found in kwargs with key '{db_key}'")
                return await func(*args, **kwargs)
            
            # Получаем user_id из Message или CallbackQuery
            user_id = None
            for arg in args:
                if isinstance(arg, (types.Message, types.CallbackQuery)):
                    user_id = arg.from_user.id if arg.from_user else None
                    break
            
            if not user_id:
                logger.warning(f"Could not extract user_id in @with_user_data for {func.__name__}")
                return await func(*args, **kwargs)
            
            # Получаем user_data из БД
            try:
                user_data = db.get_user(user_id)
                kwargs['user_data'] = user_data
            except Exception as e:
                logger.error(f"Error getting user_data for user {user_id}: {e}")
                kwargs['user_data'] = None
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def answer_on_error(error_message: str = "Произошла ошибка. Попробуйте позже."):
    """
    Декоратор для автоматического ответа пользователю при ошибке.
    Специальная обработка сетевых ошибок Telegram - не пытается отправлять сообщения при проблемах с сетью.
    
    Args:
        error_message: Сообщение, которое будет отправлено при ошибке
    
    Usage:
        @answer_on_error("Что-то пошло не так!")
        async def my_handler(message: types.Message):
            # your code
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (TelegramNetworkError, ClientConnectorError) as e:
                # Сетевые ошибки - не пытаемся отправлять сообщения, только логируем
                logger.warning(
                    f"Network error in {func.__name__}: {e}. "
                    f"This is usually a temporary connectivity issue with Telegram API."
                )
                # Не пытаемся отправлять сообщения при сетевых ошибках
                return None
            except TelegramAPIError as e:
                # Ошибки API Telegram (не сетевые) - логируем и пытаемся уведомить
                logger.error(f"Telegram API error in {func.__name__}: {e}", exc_info=True)
                # Пытаемся отправить сообщение об ошибке только если это не сетевой сбой
                for arg in args:
                    if isinstance(arg, types.Message):
                        try:
                            await arg.answer(error_message)
                        except Exception:
                            pass
                        break
                    elif isinstance(arg, types.CallbackQuery):
                        try:
                            await arg.answer(error_message, show_alert=True)
                        except Exception:
                            pass
                        break
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                # Пытаемся отправить сообщение об ошибке
                for arg in args:
                    if isinstance(arg, types.Message):
                        try:
                            await arg.answer(error_message)
                        except Exception:
                            pass
                        break
                    elif isinstance(arg, types.CallbackQuery):
                        try:
                            await arg.answer(error_message, show_alert=True)
                        except Exception:
                            pass
                        break
        return wrapper
    return decorator

