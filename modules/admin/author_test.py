import logging
from aiogram import types
from aiogram.exceptions import TelegramBadRequest

from database.db import Database
from modules.logging_service import LoggingService

logger = logging.getLogger(__name__)


def _fmt_user_line(row: dict, *, prefix: str) -> str:
    user_id = row.get("user_id")
    name = row.get("name") or "—"
    username = row.get("username") or ""
    uname = f"@{username}" if username else "—"
    extra = ""
    if prefix == "started":
        step = row.get("current_step")
        if step is not None:
            extra = f" (шаг {step})"
    if prefix == "completed":
        zone = row.get("zone") or "—"
        ready = row.get("ready_total")
        fear = row.get("fear_total")
        parts = [f"зона={zone}"]
        if ready is not None:
            parts.append(f"ready={ready}")
        if fear is not None:
            parts.append(f"fear={fear}")
        extra = " (" + ", ".join(parts) + ")"
    return f"• <code>{user_id}</code> | {uname} | {name}{extra}"


async def show_admin_author_test(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, days: int = 30) -> None:
    """Экран статистики по тесту «Стать автором»."""
    try:
        stats = db.get_author_test_stats(days=days, limit=10)
    except Exception as e:
        logger.error(f"Error getting author test stats: {e}", exc_info=True)
        stats = None

    if not stats:
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

    zones = stats.get("zones_all") or {}
    recent_started = stats.get("recent_started") or []
    recent_completed = stats.get("recent_completed") or []

    lines = []
    lines.append("📝 <b>ТЕСТ «СТАТЬ АВТОРОМ»</b>\n")
    lines.append(f"Период: последние <b>{stats.get('days')}</b> дней\n")

    lines.append("<b>Итого (все время):</b>")
    lines.append(f"• Начали: <b>{stats.get('started_all', 0)}</b>")
    lines.append(f"• В процессе: <b>{stats.get('in_progress_all', 0)}</b>")
    lines.append(f"• Завершили: <b>{stats.get('completed_all', 0)}</b>\n")

    lines.append(f"<b>За последние {stats.get('days')} дней:</b>")
    lines.append(f"• Начали: <b>{stats.get('started_last_days', 0)}</b>")
    lines.append(f"• Завершили: <b>{stats.get('completed_last_days', 0)}</b>\n")

    lines.append("<b>Зоны (завершившие):</b>")
    lines.append(
        f"• GREEN: <b>{zones.get('GREEN', 0)}</b> | "
        f"YELLOW: <b>{zones.get('YELLOW', 0)}</b> | "
        f"RED: <b>{zones.get('RED', 0)}</b> | "
        f"UNKNOWN: <b>{zones.get('UNKNOWN', 0)}</b>\n"
    )

    lines.append("<b>Последние в процессе:</b>")
    if recent_started:
        lines.extend([_fmt_user_line(r, prefix="started") for r in recent_started[:10]])
    else:
        lines.append("• —")
    lines.append("")

    lines.append("<b>Последние завершившие:</b>")
    if recent_completed:
        lines.extend([_fmt_user_line(r, prefix="completed") for r in recent_completed[:10]])
    else:
        lines.append("• —")

    text = "\n".join(lines)

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="7 дней", callback_data="admin_author_test_7"),
            types.InlineKeyboardButton(text="30 дней", callback_data="admin_author_test_30"),
            types.InlineKeyboardButton(text="90 дней", callback_data="admin_author_test_90"),
        ],
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")],
    ])

    try:
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML", disable_web_page_preview=True)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise

    try:
        await logger_service.log_action(user_id, "admin_author_test_viewed", {"days": int(stats.get("days", days))})
    except Exception:
        pass

