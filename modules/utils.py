# код/modules/utils.py
"""
Вспомогательные функции общего назначения.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def get_user_name(user_data: Optional[Dict[str, Any]], default: str = "Друг") -> str:
    """
    Получает имя пользователя из user_data с fallback на default.
    
    Args:
        user_data: Словарь с данными пользователя
        default: Значение по умолчанию, если имя не найдено
        
    Returns:
        str: Имя пользователя или default
    """
    if not user_data:
        return default
    
    name = user_data.get("name", default)
    if isinstance(name, str):
        name = name.strip()
        return name if name else default
    return default


def safe_get_user_id(event) -> Optional[int]:
    """
    Безопасно извлекает user_id из события (Message или CallbackQuery).
    
    Args:
        event: Message или CallbackQuery объект
        
    Returns:
        int | None: user_id или None
    """
    try:
        if hasattr(event, 'from_user') and event.from_user:
            return event.from_user.id
        return None
    except Exception as e:
        logger.error(f"Error getting user_id from event: {e}")
        return None


def safe_get_username(event) -> str:
    """
    Безопасно извлекает username из события (Message или CallbackQuery).
    
    Args:
        event: Message или CallbackQuery объект
        
    Returns:
        str: username или пустая строка
    """
    try:
        if hasattr(event, 'from_user') and event.from_user:
            return event.from_user.username or ""
        return ""
    except Exception as e:
        logger.error(f"Error getting username from event: {e}")
        return ""


def format_time_msk(dt: Optional[datetime]) -> str:
    """
    Форматирует datetime в строку вида "ДД.ММ.ГГГГ ЧЧ:ММ МСК".
    
    Args:
        dt: datetime объект
        
    Returns:
        str: Отформатированная строка или "н/д"
    """
    if not dt:
        return "н/д"
    
    try:
        return dt.strftime("%d.%m.%Y %H:%M МСК")
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        return "н/д"


def validate_time_format(time_str: str) -> bool:
    """
    Проверяет, соответствует ли строка формату времени ЧЧ:ММ.
    
    Args:
        time_str: Строка для проверки
        
    Returns:
        bool: True, если формат корректен
    """
    if not time_str or not isinstance(time_str, str):
        return False
    
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        return False
    
    try:
        hours, minutes = int(parts[0]), int(parts[1])
        return 0 <= hours <= 23 and 0 <= minutes <= 59
    except (ValueError, TypeError):
        return False


def truncate_text(text: str, max_length: int = 4000, suffix: str = "...") -> str:
    """
    Обрезает текст до максимальной длины, добавляя suffix.
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста
        
    Returns:
        str: Обрезанный текст
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_user_display(user_id: int, username: Optional[str], name: Optional[str]) -> str:
    """
    Форматирует информацию о пользователе в виде "ID | @username | name".
    
    Args:
        user_id: ID пользователя
        username: Никнейм (с @ или без)
        name: Имя пользователя
        
    Returns:
        str: Отформатированная строка
    """
    # Форматируем username
    if username:
        username = username.strip()
        if username and not username.startswith("@"):
            username = f"@{username}"
    else:
        username = "—"
    
    # Форматируем name
    name = name.strip() if name else "—"
    
    return f"<code>{user_id}</code> | {username} | {name}"


def safe_int(value: Any, default: int = 0) -> int:
    """
    Безопасно преобразует значение в int.
    
    Args:
        value: Значение для преобразования
        default: Значение по умолчанию
        
    Returns:
        int: Преобразованное значение или default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

