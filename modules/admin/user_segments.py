"""
Отчёт по сегментам пользователей: кто составляет ядро, кто уснул, кого реактивировать.

Обычный список пользователей отвечает на вопрос «кто есть в базе», но не на вопрос
«на ком держится продукт». Здесь пользователи разбиты по глубине и свежести
использования «Карты дня», плюс показана концентрация: какая доля активности
приходится на одного самого активного человека.
"""
import logging
from aiogram import types
from aiogram.exceptions import TelegramBadRequest

from database.db import Database
from modules.logging_service import LoggingService

try:
    from config_local import NO_LOGS_USERS
except ImportError:
    from config import NO_LOGS_USERS

logger = logging.getLogger(__name__)

# Пользователь считается «живым», если что-то делал за столько дней
ACTIVE_WINDOW_DAYS = 30
# Со скольких разных дней использования человек считается вернувшимся, а не разовым
REGULAR_MIN_DAYS = 2
# Со скольких — ядром
CORE_MIN_DAYS = 3


def _excluded_sql(db: Database) -> str:
    """Условие исключения служебных аккаунтов. Берём объединение ignored_users и конфига."""
    ids = set(NO_LOGS_USERS or [])
    try:
        ids |= {row[0] for row in db.conn.execute("SELECT user_id FROM ignored_users")}
    except Exception as e:
        logger.warning(f"Не удалось прочитать ignored_users: {e}")
    return f"({','.join(str(int(i)) for i in ids)})" if ids else "(0)"


def get_user_segments(db: Database) -> dict:
    """Считает сегменты пользователей по активности в сценарии «Карта дня»."""
    excluded = _excluded_sql(db)

    # Профиль каждого пользователя: сколько разных дней тянул карту,
    # сколько всего карт, когда был последний раз, доходил ли до полного разбора.
    rows = db.conn.execute(f"""
        SELECT
            u.user_id,
            COALESCE(c.days, 0)        AS days,
            COALESCE(c.cards, 0)       AS cards,
            c.last_card                AS last_card,
            COALESCE(d.deep, 0)        AS deep,
            a.last_seen                AS last_seen,
            julianday('now') - julianday(a.last_seen) AS days_ago
        FROM users u
        LEFT JOIN (
            SELECT user_id, COUNT(DISTINCT date(timestamp)) days,
                   COUNT(*) cards, MAX(timestamp) last_card
            FROM scenario_logs
            WHERE scenario = 'card_of_day' AND step = 'card_drawn'
            GROUP BY user_id
        ) c ON c.user_id = u.user_id
        LEFT JOIN (
            SELECT user_id, COUNT(*) deep FROM scenario_logs
            WHERE scenario = 'card_of_day' AND step = 'completed'
            GROUP BY user_id
        ) d ON d.user_id = u.user_id
        LEFT JOIN (
            SELECT user_id, MAX(timestamp) last_seen FROM actions GROUP BY user_id
        ) a ON a.user_id = u.user_id
        WHERE u.user_id NOT IN {excluded}
    """).fetchall()

    seg = {"core": [], "fresh": [], "asleep": [], "oneshot": [], "no_card": []}
    deep_users = 0
    for r in rows:
        days, days_ago, deep = r["days"], r["days_ago"], r["deep"]
        if deep:
            deep_users += 1
        recent = days_ago is not None and days_ago <= ACTIVE_WINDOW_DAYS

        if days == 0:
            seg["no_card"].append(r)
        elif recent and days >= CORE_MIN_DAYS:
            seg["core"].append(r)
        elif recent:
            seg["fresh"].append(r)
        elif days >= REGULAR_MIN_DAYS:
            seg["asleep"].append(r)
        else:
            seg["oneshot"].append(r)

    # Концентрация активности за 30 дней
    conc = db.conn.execute(f"""
        SELECT user_id, COUNT(*) n FROM scenario_logs
        WHERE scenario = 'card_of_day' AND step = 'card_drawn'
          AND user_id NOT IN {excluded}
          AND timestamp >= datetime('now', '-30 days')
        GROUP BY user_id ORDER BY n DESC
    """).fetchall()
    total_cards = sum(r["n"] for r in conc)

    return {
        "segments": seg,
        "total": len(rows),
        "deep_users": deep_users,
        "cards_30d": total_cards,
        "actives_30d": len(conc),
        "top1_share": (100.0 * conc[0]["n"] / total_cards) if total_cards else 0,
        "top5_share": (100.0 * sum(r["n"] for r in conc[:5]) / total_cards) if total_cards else 0,
        "top_users": conc[:5],
    }


def _fmt_user(db: Database, row) -> str:
    """Строка одного пользователя: имя/username, сколько дней и когда был последний раз."""
    data = db.get_user(row["user_id"]) or {}
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip()
    who = f"@{username}" if username else (name or str(row["user_id"]))
    ago = row["days_ago"]
    ago_str = "сегодня" if ago is not None and ago < 1 else (f"{int(ago)} дн. назад" if ago is not None else "нет данных")
    return f"  • {who} — {row['days']} дн., {row['cards']} карт, {ago_str}"


async def show_admin_user_segments(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает разбивку пользователей по сегментам."""
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access user segments")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return

    try:
        s = get_user_segments(db)
        seg = s["segments"]
        total = s["total"] or 1

        def pct(n):
            return f"{100.0 * n / total:.0f}%"

        core = sorted(seg["core"], key=lambda r: r["cards"], reverse=True)
        asleep = sorted(seg["asleep"], key=lambda r: r["cards"], reverse=True)

        text = f"""👥 <b>СЕГМЕНТЫ ПОЛЬЗОВАТЕЛЕЙ</b>
Всего в базе (без служебных): <b>{s['total']}</b>

🔥 <b>Ядро</b> — {len(seg['core'])} ({pct(len(seg['core']))})
<i>активны за {ACTIVE_WINDOW_DAYS} дн., карта в {CORE_MIN_DAYS}+ разных дней</i>
"""
        text += "\n".join(_fmt_user(db, r) for r in core[:8]) or "  —"

        text += f"""

🌱 <b>Присматриваются</b> — {len(seg['fresh'])} ({pct(len(seg['fresh']))})
<i>активны недавно, но пока 1–2 дня с картой</i>

😴 <b>Уснувшие постоянники</b> — {len(seg['asleep'])} ({pct(len(seg['asleep']))})
<i>возвращались {REGULAR_MIN_DAYS}+ дней, молчат более {ACTIVE_WINDOW_DAYS} дн. — главная аудитория для реактивации</i>
"""
        text += "\n".join(_fmt_user(db, r) for r in asleep[:8]) or "  —"

        text += f"""

👋 <b>Разовые</b> — {len(seg['oneshot'])} ({pct(len(seg['oneshot']))})
<i>вытянули карту в один день и не вернулись</i>

💤 <b>Без карты</b> — {len(seg['no_card'])} ({pct(len(seg['no_card']))})
<i>дошли до бота, но ни одной карты не вытянули</i>

🤖 <b>Глубина:</b> {s['deep_users']} чел. хотя бы раз прошли полный разбор с ИИ

⚠️ <b>Концентрация за 30 дней</b>
• Карт вытянуто: {s['cards_30d']} — людьми: {s['actives_30d']}
• Доля самого активного: <b>{s['top1_share']:.0f}%</b>
• Доля топ-5: {s['top5_share']:.0f}%"""

        if s["top1_share"] >= 50:
            text += "\n\n<i>Активность держится на одном человеке — на таких числах любые\nизменения метрик будут шумом, а не эффектом.</i>"

        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_user_segments")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])

        try:
            await message.edit_text(text[:4090], reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_user_segments_viewed", {})

    except Exception as e:
        logger.error(f"Error showing user segments: {e}", exc_info=True)
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])
        try:
            await message.edit_text("❌ Ошибка при расчёте сегментов", reply_markup=keyboard)
        except TelegramBadRequest:
            pass
