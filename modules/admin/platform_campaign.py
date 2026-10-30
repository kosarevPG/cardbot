"""
Админский раздел кампании знакомства с платформой TopPsyGame.

Что здесь можно и чего нельзя:

* можно — посмотреть тексты всех экранов ровно в том виде, в каком их увидит
  пользователь; оценить аудиторию по сегментам с дедупликацией; прогнать
  dry-run и увидеть план касаний, ничего не отправив; отправить любой экран
  себе; включить или поставить на паузу автоматические касания; посмотреть
  отчёт по воронке;
* нельзя — запустить массовую отправку. Такой кнопки нет: первое касание
  делает сам человек через /platform или кнопку в меню, а серию получают
  только те, кто нажал «Да, присылайте».

Включение требует двух действий: кнопка «Включить» и подтверждение. Это
единственное место, откуда кампания вообще может начать отправлять.
"""
import logging

from aiogram import types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from database.db import Database
from modules.logging_service import LoggingService
from modules.platform_campaign import (
    FOLLOWUP_DELAYS, MAX_FOLLOWUPS, MAX_SEND_ATTEMPTS, PlatformCampaign, render,
)
from modules.texts.platform import (
    CAMPAIGN_ID, FOLLOWUP_SCREENS, PLATFORM_TEXTS, ROLE_EXPLORER,
    ROLE_FACILITATOR, platform_url,
)

logger = logging.getLogger(__name__)

# Человеческие названия групп аудитории для отчёта
GROUP_TITLES = {
    "asleep": "уснувшие постоянники",
    "oneshot": "разовые",
    "core": "ядро",
    "fresh": "присматриваются",
    "author_test": "прошли тест «Стать автором»",
}

# Порядок экранов в предпросмотре: ровно как их видит пользователь
PREVIEW_ORDER = (
    ("intro", "A. Первый экран"),
    ("facilitator", "B1. Ведущий"),
    ("explorer", "B2. Интересующийся"),
    ("consent_request", "Вопрос о согласии"),
    ("consent_granted", "C. Согласие получено"),
    ("declined", "C. Отказ"),
    ("stopped", "C. /platform_stop"),
    ("d2_facilitator", "D+2. Ведущий"),
    ("d2_explorer", "D+2. Интересующийся"),
    ("d5_facilitator", "D+5. Ведущий"),
    ("d5_explorer", "D+5. Интересующийся"),
)


def _is_admin(user_id: int) -> bool:
    try:
        from config import ADMIN_IDS
        return str(user_id) in ADMIN_IDS
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        return False


async def _show(message: types.Message, text: str, keyboard: types.InlineKeyboardMarkup):
    """Обновляет сообщение админки, не падая на «message is not modified»."""
    try:
        await message.edit_text(text[:4090], reply_markup=keyboard, parse_mode=ParseMode.HTML,
                                disable_web_page_preview=True)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


def _campaign(message: types.Message, db: Database, logger_service: LoggingService) -> PlatformCampaign:
    return PlatformCampaign(db, message.bot, logger_service)


def _menu_keyboard(enabled: bool) -> types.InlineKeyboardMarkup:
    switch = ([types.InlineKeyboardButton(text="⏸ Поставить на паузу",
                                          callback_data="admin_platform_pause")]
              if enabled else
              [types.InlineKeyboardButton(text="▶️ Включить касания",
                                          callback_data="admin_platform_enable")])
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📊 Отчёт по воронке", callback_data="admin_platform_report")],
        [types.InlineKeyboardButton(text="👥 Аудитория по сегментам", callback_data="admin_platform_audience")],
        [types.InlineKeyboardButton(text="👀 Предпросмотр текстов", callback_data="admin_platform_preview")],
        [types.InlineKeyboardButton(text="🧪 Dry-run касаний", callback_data="admin_platform_dryrun")],
        [types.InlineKeyboardButton(text="📨 Отправить себе первый экран", callback_data="admin_platform_test")],
        switch,
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main")],
    ])


def _back_keyboard() -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ К кампании", callback_data="admin_platform")],
    ])


async def show_admin_platform_campaign(message: types.Message, db: Database,
                                       logger_service: LoggingService, user_id: int):
    """Главный экран раздела: состояние выключателя и короткая сводка."""
    if not _is_admin(user_id):
        await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
        logger.warning(f"BLOCKED: User {user_id} attempted to access platform campaign admin")
        return

    try:
        enabled = db.is_platform_campaign_enabled(CAMPAIGN_ID)
        funnel = db.get_platform_campaign_funnel(CAMPAIGN_ID)
        steps = ", ".join(f"{sid.upper()}: {funnel['steps_sent'].get(sid, 0)}"
                          for sid, _ in FOLLOWUP_DELAYS) or "—"
        paused_until = db.get_platform_campaign_paused_until(CAMPAIGN_ID)
        pause_note = ""
        if paused_until:
            pause_note = (f"\n⏳ Пауза флуд-контроля Telegram до "
                          f"<code>{paused_until[:19]}</code>")

        text = f"""🃏 <b>КАМПАНИЯ: TOPPSYGAME</b>
<i>id кампании: <code>{CAMPAIGN_ID}</code></i>

{'▶️ Автоматические касания <b>ВКЛЮЧЕНЫ</b>' if enabled else '⏸ Автоматические касания <b>выключены</b>'}{pause_note}

<b>Как работает воронка</b>
• первое касание делает сам человек: /platform или кнопка в меню;
• серию получают только нажавшие «Да, присылайте»;
• касаний не больше {MAX_FOLLOWUPS}: D+{FOLLOWUP_DELAYS[0][1].days} и D+{FOLLOWUP_DELAYS[1][1].days} от согласия;
• массовой отправки в кампании нет — такой кнопки здесь не существует.

<b>Сейчас</b>
• вошли в воронку: <b>{funnel['total']}</b>
• выбрали ветку: ведущие <b>{funnel['facilitator']}</b>, интересующиеся <b>{funnel['explorer']}</b>
• «не интересно»: <b>{funnel['dismissed']}</b>
• дали согласие: <b>{funnel['consented']}</b>, из них активны: <b>{funnel['active']}</b>
• отписались: <b>{funnel['opted_out']}</b>
• доставлено касаний — {steps}
• пропущено: {funnel['skipped_total']}, с неудачей: {funnel['failed_total']}"""

        await _show(message, text, _menu_keyboard(enabled))
        await logger_service.log_action(user_id, "admin_platform_campaign_viewed",
                                        {"enabled": enabled})
    except Exception as e:
        logger.error(f"Error showing platform campaign admin: {e}", exc_info=True)
        await _show(message, "❌ Ошибка при загрузке раздела кампании", _back_keyboard())


async def show_platform_report(message: types.Message, db: Database,
                               logger_service: LoggingService, user_id: int):
    """Конверсия по шагам воронки + честная оговорка про измерение переходов."""
    if not _is_admin(user_id):
        await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН!", parse_mode="HTML")
        return

    try:
        f = db.get_platform_campaign_funnel(CAMPAIGN_ID)
        shown = f["total"] or 1

        def pct(n):
            return f"{100.0 * n / shown:.0f}%"

        chose = f["facilitator"] + f["explorer"]
        consent_base = chose or 1
        text = f"""📊 <b>ВОРОНКА КАМПАНИИ</b>

1️⃣ Увидели приглашение: <b>{f['total']}</b>
2️⃣ Выбрали ветку: <b>{chose}</b> ({pct(chose)})
   • ведущие: {f['facilitator']}
   • интересующиеся: {f['explorer']}
   • «не интересно»: {f['dismissed']} ({pct(f['dismissed'])})
3️⃣ Дали явное согласие на серию: <b>{f['consented']}</b> \
({100.0 * f['consented'] / consent_base:.0f}% от выбравших ветку)
4️⃣ Касания по исходам:
"""
        for step_id, delay in FOLLOWUP_DELAYS:
            sent = f['steps_sent'].get(step_id, 0)
            claimed = f['steps_claimed'].get(step_id, 0)
            skipped = f['steps_skipped'].get(step_id, 0)
            failed = f['steps_failed'].get(step_id, 0)
            pending = f['steps_pending'].get(step_id, 0)
            text += (f"   • D+{delay.days}: доставлено <b>{sent}</b>"
                     f" | пропущено {skipped} | неудач {failed}")
            if pending:
                text += f" | в работе {pending}"
            text += f" (занято шагов: {claimed})\n"

        text += f"""
🚪 Отписались: <b>{f['opted_out']}</b>
⚠️ Со сбоями отправки: <b>{f['failed']}</b>
✅ Подтверждённых конверсий: <b>{f['converted']}</b>

<b>Что эти числа значат</b>
• «Доставлено» — Telegram принял сообщение. Это доставка, не прочтение.
• «Занято шагов» — сколько шагов израсходовано. Шаг занимается до обращения к
  Telegram и остаётся занятым при пропуске и при неудаче, поэтому доставкой это
  число считать нельзя — для неё есть «доставлено».
• Нажатие кнопки-ссылки боту <b>не видно</b>: Telegram не присылает callback по
  URL-кнопкам. Кликов и посещений сайта здесь нет и не будет — переходы считаются
  по UTM-меткам на стороне платформы (MVP 2).
• Конверсии не угадываются по событиям бота: пока межпроектной атрибуции нет,
  здесь всегда 0."""

        await _show(message, text, _back_keyboard())
        await logger_service.log_action(user_id, "admin_platform_report_viewed", {})
    except Exception as e:
        logger.error(f"Error showing platform report: {e}", exc_info=True)
        await _show(message, "❌ Ошибка при расчёте воронки", _back_keyboard())


async def show_platform_audience(message: types.Message, db: Database,
                                 logger_service: LoggingService, user_id: int):
    """Оценка доступной аудитории по сегментам с дедупликацией пересечений."""
    if not _is_admin(user_id):
        await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН!", parse_mode="HTML")
        return

    try:
        data = _campaign(message, db, logger_service).estimate_audience()
        text = """👥 <b>АУДИТОРИЯ КАМПАНИИ</b>
<i>оценка потолка канала, а не список для отправки</i>

"""
        for row in data["groups"]:
            title = GROUP_TITLES.get(row["segment"], row["segment"])
            text += (f"• <b>{title}</b>: {row['total']}"
                     f" (без пересечений {row['unique']}, достижимы {row['reachable']})\n")

        text += f"""
<b>Итого уникальных:</b> {data['total']}
📬 Достижимы: <b>{data['reachable']}</b>
🚫 Заблокировали бота или удалили аккаунт: {data['blocked']}

<b>Уже в воронке</b>
• вошли: {data['entered']}
• дали согласие: {data['consented']}
• отписались: {data['opted_out']}

<b>Почему по этим спискам нельзя разослать</b>
Участие в боте — не согласие на рекламную рассылку. Согласий на такую рассылку в
базе нет, поэтому массовая первая отправка не предусмотрена: вход в воронку
добровольный — /platform и кнопка в главном меню."""

        await _show(message, text, _back_keyboard())
        await logger_service.log_action(user_id, "admin_platform_audience_viewed",
                                        {"reachable": data["reachable"]})
    except Exception as e:
        logger.error(f"Error estimating platform audience: {e}", exc_info=True)
        await _show(message, "❌ Ошибка при оценке аудитории", _back_keyboard())


async def show_platform_preview(message: types.Message, db: Database,
                                logger_service: LoggingService, user_id: int):
    """
    Предпросмотр всех текстов и кнопок. Сообщения длинные, поэтому отправляем их
    отдельными сообщениями в том же виде, в каком их получит пользователь.
    """
    if not _is_admin(user_id):
        await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН!", parse_mode="HTML")
        return

    try:
        await message.answer(
            "👀 <b>ПРЕДПРОСМОТР ТЕКСТОВ КАМПАНИИ</b>\n"
            "<i>ровно то, что увидит пользователь. Кнопки активны — не нажимай их здесь, "
            "кликом ты запишешь выбор себе.</i>",
            parse_mode=ParseMode.HTML)
        for screen_key, title in PREVIEW_ORDER:
            text, keyboard = render(screen_key)
            await message.answer(f"<b>— {title} —</b>\n\n{text}", reply_markup=keyboard,
                                 parse_mode=ParseMode.HTML, disable_web_page_preview=True)

        links = "\n".join(
            f"• <code>{PLATFORM_TEXTS[key].get('cta', {}).get('utm_content')}</code> → "
            f"{platform_url(PLATFORM_TEXTS[key]['cta']['utm_content'])}"
            for key, _ in PREVIEW_ORDER if PLATFORM_TEXTS[key].get("cta"))
        await message.answer(
            f"🔗 <b>Ссылки с UTM</b>\n{links}\n\n"
            "<i>Все ведут на корень приложения: остальные маршруты закрыты авторизацией, "
            "и глубокая ссылка после входа теряется. Шаг воронки различается через "
            "utm_content. Telegram ID и персональных данных в ссылках нет.</i>",
            parse_mode=ParseMode.HTML, disable_web_page_preview=True)

        await logger_service.log_action(user_id, "admin_platform_preview_viewed", {})
    except Exception as e:
        logger.error(f"Error showing platform preview: {e}", exc_info=True)
        await message.answer("❌ Ошибка при предпросмотре текстов")


async def run_platform_dry_run(message: types.Message, db: Database,
                               logger_service: LoggingService, user_id: int):
    """
    Dry-run: что ушло бы прямо сейчас. Ничего не отправляет и ничего не меняет в
    базе, поэтому работает и при выключенной кампании.
    """
    if not _is_admin(user_id):
        await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН!", parse_mode="HTML")
        return

    try:
        campaign = _campaign(message, db, logger_service)
        result = await campaign.process_due_followups(dry_run=True)
        planned = result.get("planned", [])

        text = f"""🧪 <b>DRY-RUN КАСАНИЙ</b>
<i>ничего не отправлено и не изменено</i>

Кампания сейчас: {'▶️ включена' if result['enabled'] else '⏸ выключена'}
Созрело к отправке: <b>{result['sent']}</b>
Пропустить: <b>{result['skipped']}</b>

"""
        if planned:
            text += "<b>План:</b>\n"
            for item in planned[:25]:
                step = str(item.get("step", "?")).upper()
                text += (f"• <code>{item['user_id']}</code> — {step}, "
                         f"{item.get('role', '?')}, {item.get('action')}\n")
            if len(planned) > 25:
                text += f"<i>…и ещё {len(planned) - 25}</i>\n"
        else:
            text += "<b>Отправлять сейчас нечего.</b>\n"

        text += ("\n<i>Причины пропуска: касание просрочено более чем на неделю, "
                 "человек недоступен или попытки исчерпаны "
                 f"(не больше {MAX_SEND_ATTEMPTS} на шаг).</i>")

        await _show(message, text, _back_keyboard())
        await logger_service.log_action(user_id, "admin_platform_dry_run",
                                        {"due": result["sent"], "skipped": result["skipped"]})
    except Exception as e:
        logger.error(f"Error running platform dry-run: {e}", exc_info=True)
        await _show(message, "❌ Ошибка при dry-run", _back_keyboard())


async def send_platform_test(message: types.Message, db: Database,
                             logger_service: LoggingService, user_id: int):
    """
    Тестовая отправка себе. Получатель — только сам администратор: user_id
    берётся из апдейта, выбрать чужой адрес здесь невозможно.
    """
    if not _is_admin(user_id):
        await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН!", parse_mode="HTML")
        return

    try:
        for screen_key in ("intro",
                           FOLLOWUP_SCREENS[("d2", ROLE_FACILITATOR)],
                           FOLLOWUP_SCREENS[("d5", ROLE_EXPLORER)]):
            text, keyboard = render(screen_key)
            await message.bot.send_message(user_id, text, reply_markup=keyboard,
                                           parse_mode=ParseMode.HTML,
                                           disable_web_page_preview=True)
        await message.answer(
            "📨 Отправил себе первый экран и по одному примеру касаний D+2 и D+5.\n"
            "<i>Это тестовая отправка: состояние кампании не изменилось, "
            "другим пользователям ничего не ушло.</i>",
            parse_mode=ParseMode.HTML)
        await logger_service.log_action(user_id, "admin_platform_test_send", {})
    except Exception as e:
        logger.error(f"Error sending platform test: {e}", exc_info=True)
        await message.answer("❌ Не удалось отправить тестовые сообщения")


async def ask_platform_enable(message: types.Message, db: Database,
                              logger_service: LoggingService, user_id: int):
    """Спрашивает подтверждение перед включением. Включение в один клик запрещено."""
    if not _is_admin(user_id):
        await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН!", parse_mode="HTML")
        return

    funnel = db.get_platform_campaign_funnel(CAMPAIGN_ID)
    campaign = _campaign(message, db, logger_service)
    result = await campaign.process_due_followups(dry_run=True)

    text = f"""▶️ <b>ВКЛЮЧИТЬ АВТОМАТИЧЕСКИЕ КАСАНИЯ?</b>

После включения планировщик начнёт отправлять D+2 и D+5 тем, кто дал явное
согласие. Сейчас таких людей: <b>{funnel['active']}</b>.
Созрело к отправке прямо сейчас: <b>{result['sent']}</b>.

Никому, кроме согласившихся, ничего не уйдёт. Отписавшиеся, заблокировавшие бота
и нажавшие «Не интересно» исключены. Выключить можно в любой момент — кампания
встанет на паузу сразу."""

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Да, включить",
                                    callback_data="admin_platform_enable_confirm")],
        [types.InlineKeyboardButton(text="⬅️ Отмена", callback_data="admin_platform")],
    ])
    await _show(message, text, keyboard)


async def set_platform_enabled(message: types.Message, db: Database,
                               logger_service: LoggingService, user_id: int, enabled: bool):
    """Включает кампанию (после подтверждения) или ставит её на паузу."""
    if not _is_admin(user_id):
        await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН!", parse_mode="HTML")
        return

    ok = db.set_platform_campaign_enabled(CAMPAIGN_ID, enabled, updated_by=user_id)
    logger.info(f"Platform campaign {'enabled' if enabled else 'paused'} by admin {user_id}: ok={ok}")
    await logger_service.log_action(
        user_id, "admin_platform_campaign_toggled", {"enabled": enabled, "ok": ok})
    await show_admin_platform_campaign(message, db, logger_service, user_id)


# Роутинг callback'ов раздела. Вынесен в таблицу, чтобы core.py не разрастался
# ещё одной лестницей if/elif.
async def route_platform_callback(action: str, message: types.Message, db: Database,
                                  logger_service: LoggingService, user_id: int) -> bool:
    """Обрабатывает admin_platform*-callback. False — действие не наше."""
    if action == "admin_platform":
        await show_admin_platform_campaign(message, db, logger_service, user_id)
    elif action == "admin_platform_report":
        await show_platform_report(message, db, logger_service, user_id)
    elif action == "admin_platform_audience":
        await show_platform_audience(message, db, logger_service, user_id)
    elif action == "admin_platform_preview":
        await show_platform_preview(message, db, logger_service, user_id)
    elif action == "admin_platform_dryrun":
        await run_platform_dry_run(message, db, logger_service, user_id)
    elif action == "admin_platform_test":
        await send_platform_test(message, db, logger_service, user_id)
    elif action == "admin_platform_enable":
        await ask_platform_enable(message, db, logger_service, user_id)
    elif action == "admin_platform_enable_confirm":
        await set_platform_enabled(message, db, logger_service, user_id, True)
    elif action == "admin_platform_pause":
        await set_platform_enabled(message, db, logger_service, user_id, False)
    else:
        return False
    return True
