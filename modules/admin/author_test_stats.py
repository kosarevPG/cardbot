import logging
from aiogram import types
from aiogram.exceptions import TelegramBadRequest

from database.db import Database
from modules.logging_service import LoggingService

logger = logging.getLogger(__name__)


async def show_admin_author_test_stats(
    message: types.Message,
    db: Database,
    logger_service: LoggingService,
    user_id: int,
) -> None:
    """Показывает статистику по тесту «Стать автором» (совместимо с разными версиями db.get_author_test_stats)."""
    try:
        try:
            stats = db.get_author_test_stats(days=30, limit=10)  # новая версия
        except TypeError:
            stats = db.get_author_test_stats()  # старая/упрощённая версия
    except Exception as e:
        logger.error(f"Error getting author test stats: {e}", exc_info=True)
        stats = None

    if not isinstance(stats, dict):
        text = "❌ Не удалось получить статистику по тесту «Стать автором»."
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")],
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        return

    # Вариант A (расширенный): started_all/completed_all/zones_all/...
    if "started_all" in stats or "completed_all" in stats:
        zones = stats.get("zones_all") or {}
        text = (
            "📝 <b>ТЕСТ «СТАТЬ АВТОРОМ»</b>\n\n"
            f"• Начали (всего): <b>{stats.get('started_all', 0)}</b>\n"
            f"• В процессе: <b>{stats.get('in_progress_all', 0)}</b>\n"
            f"• Завершили (всего): <b>{stats.get('completed_all', 0)}</b>\n\n"
            f"• Начали за {stats.get('days', 30)} дней: <b>{stats.get('started_last_days', 0)}</b>\n"
            f"• Завершили за {stats.get('days', 30)} дней: <b>{stats.get('completed_last_days', 0)}</b>\n\n"
            "<b>Зоны (завершившие):</b>\n"
            f"• GREEN: <b>{zones.get('GREEN', 0)}</b>\n"
            f"• YELLOW: <b>{zones.get('YELLOW', 0)}</b>\n"
            f"• RED: <b>{zones.get('RED', 0)}</b>\n"
            f"• UNKNOWN: <b>{zones.get('UNKNOWN', 0)}</b>\n"
        )
    else:
        # Вариант B (упрощённый): started/completed/conversion/green/yellow/red
        text = (
            "📝 <b>ТЕСТ «СТАТЬ АВТОРОМ»</b>\n\n"
            f"• Начали: <b>{stats.get('started', 0)}</b>\n"
            f"• Завершили: <b>{stats.get('completed', 0)}</b>\n"
            f"• Конверсия: <b>{stats.get('conversion', 0)}%</b>\n\n"
            "<b>Зоны:</b>\n"
            f"• GREEN: <b>{stats.get('green', 0)}</b>\n"
            f"• YELLOW: <b>{stats.get('yellow', 0)}</b>\n"
            f"• RED: <b>{stats.get('red', 0)}</b>\n"
        )

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")],
    ])

    try:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML", disable_web_page_preview=True)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise

    try:
        await logger_service.log_action(user_id, "admin_author_test_stats_viewed", {})
    except Exception:
        pass

