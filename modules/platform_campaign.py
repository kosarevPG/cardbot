# код/modules/platform_campaign.py
"""
Воронка знакомства с платформой TopPsyGame: короткий opt-in, а не серия рассылок.

Что здесь важно по устройству:

* Первый контакт всегда инициирует человек — команда /platform или кнопка в
  главном меню. Массовой первой отправки в этом модуле нет вовсе: участие в боте
  не является согласием на рекламную рассылку, а подтверждённых согласий на такую
  рассылку в базе нет.
* Автоматические касания (D+2 и D+5) уходят ТОЛЬКО тем, кто нажал «Да,
  присылайте», и только когда администратор отдельно включил их в админке.
  По умолчанию выключатель стоит в положении «выключено»: ни миграция, ни старт
  бота ничего не отправляют.
* Защита от дублей после рестарта лежит в базе, а не в памяти: шаг «занимается»
  (db.claim_platform_campaign_step) до обращения к Telegram. Поднявшийся заново
  процесс видит шаг занятым и повторно его не отправляет.
* Больше двух касаний не уйдёт ни при каких обстоятельствах: шагов всего два, и
  каждый можно занять один раз за всю кампанию.

Тексты, подписи кнопок, UTM-метки и названия событий — в modules/texts/platform.py.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

from modules.texts.platform import (
    CAMPAIGN_ID, CB_CONSENT_NO, CB_CONSENT_YES, CB_DISMISS, CB_OPT_OUT,
    FOLLOWUP_SCREENS, PLATFORM_EVENTS, PLATFORM_TEXTS, ROLE_BY_CALLBACK,
    ROLE_EXPLORER, ROLE_FACILITATOR, ROLE_SCREENS, platform_url,
)
from modules.utils import (
    is_certainly_not_delivered, is_temporary_error, is_user_unreachable_error,
)

try:
    from config_local import TIMEZONE
except ImportError:
    from config import TIMEZONE

logger = logging.getLogger(__name__)

# Шаги серии: идентификатор -> отсрочка от МОМЕНТА СОГЛАСИЯ (не от первого
# сообщения). Порядок значим: тик планировщика идёт по нему сверху вниз.
FOLLOWUP_DELAYS = (
    ("d2", timedelta(days=2)),
    ("d5", timedelta(days=5)),
)

# Жёсткий потолок на количество касаний. Шагов ровно столько, сколько обещано
# пользователю в тексте согласия.
MAX_FOLLOWUPS = len(FOLLOWUP_DELAYS)

# Насколько касание может опоздать и всё ещё иметь смысл. Если бот стоял дольше,
# «подсказка на второй день» через три недели выглядит как спам, а не как помощь:
# такой шаг занимаем и помечаем пропущенным, но не отправляем.
STEP_STALE_AFTER = timedelta(days=7)

# Сколько всего попыток отправки допустимо на один шаг, включая первую. Счётчик
# живёт в базе, поэтому рестарт его не обнуляет.
MAX_SEND_ATTEMPTS = 3

# Сколько ещё пытаться после сбоя. Дальше — окончательная неудача.
RETRY_WINDOW = timedelta(minutes=60)

# Потолок ОБРАЩЕНИЙ к Telegram за один тик, а не успешных отправок: считать
# только успехи означало бы, что на серии сетевых ошибок проход долбит API
# сколько угодно раз. Кампания не должна соперничать с продуктовыми
# уведомлениями за лимиты Telegram API (30 сообщений в секунду на бота).
MAX_SEND_ATTEMPTS_PER_TICK = 20

# Запас к паузе флуд-контроля: Telegram называет минимальное время ожидания,
# и просыпаться ровно на этой секунде смысла нет.
FLOOD_WAIT_MARGIN = timedelta(seconds=5)

# Пауза между отправками — как в рассылке постов.
SEND_PAUSE_SECONDS = 0.05

# Потолок на одну отправку, чтобы зависший запрос не держал тик.
SEND_TIMEOUT_SECONDS = 20


def _parse_ts(value):
    """Читает отметку времени из базы. Наивную дату дополняет таймзоной бота."""
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value))
        except ValueError:
            logger.warning(f"Не удалось разобрать отметку времени кампании: {value!r}")
            return None
    if dt.tzinfo is None and TIMEZONE is not None:
        dt = TIMEZONE.localize(dt) if hasattr(TIMEZONE, "localize") else dt.replace(tzinfo=TIMEZONE)
    return dt


def _now():
    return datetime.now(TIMEZONE) if TIMEZONE else datetime.now()


def _aware(dt: datetime) -> datetime:
    """
    Дополняет наивную дату таймзоной бота. Отметки в базе хранятся со смещением,
    и сравнение с наивным «сейчас» иначе падает — а падать проходу планировщика
    из-за формата даты нельзя.
    """
    if dt.tzinfo is not None or TIMEZONE is None:
        return dt
    return TIMEZONE.localize(dt) if hasattr(TIMEZONE, "localize") else dt.replace(tzinfo=TIMEZONE)


def build_keyboard(screen: dict) -> types.InlineKeyboardMarkup | None:
    """
    Собирает клавиатуру экрана: сначала кнопка-ссылка (если есть), затем
    callback-кнопки. Разметка берётся из описания экрана, поэтому правка текстов
    не требует правок здесь.
    """
    rows = []
    cta = screen.get("cta")
    if cta:
        rows.append([types.InlineKeyboardButton(
            text=cta["text"], url=platform_url(cta["utm_content"]))])
    for button in screen.get("buttons", []):
        rows.append([types.InlineKeyboardButton(
            text=button["text"], callback_data=button["callback"])])
    return types.InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def render(screen_key: str) -> tuple[str, types.InlineKeyboardMarkup | None]:
    """Текст и клавиатура экрана по его ключу."""
    screen = PLATFORM_TEXTS[screen_key]
    return screen["text"], build_keyboard(screen)


class PlatformCampaign:
    """
    Состояние воронки и отправка касаний. Класс без собственного состояния в
    памяти: всё, что должно пережить рестарт, лежит в базе.
    """

    def __init__(self, db, bot, logger_service, campaign_id: str = CAMPAIGN_ID):
        self.db = db
        self.bot = bot
        self.logger_service = logger_service
        self.campaign_id = campaign_id

    # ------------------------------------------------------------------ служебное

    async def _log(self, user_id: int, event_key: str, details: dict = None):
        """Пишет событие воронки в actions. Схема событий — в texts/platform.py."""
        try:
            await self.logger_service.log_action(
                user_id, PLATFORM_EVENTS[event_key],
                {"campaign_id": self.campaign_id, **(details or {})})
        except Exception as e:
            logger.warning(f"Failed to log platform event {event_key} for {user_id}: {e}")

    def _update(self, user_id: int, **fields):
        fields.setdefault("last_event_at", _now().isoformat())
        return self.db.update_platform_campaign_state(user_id, self.campaign_id, **fields)

    def state(self, user_id: int) -> dict | None:
        return self.db.get_platform_campaign_state(user_id, self.campaign_id)

    @staticmethod
    async def _drop_keyboard(message: types.Message):
        """
        Снимает inline-кнопки с показанного сообщения: после сделанного выбора
        нажать ту же кнопку второй раз уже нельзя. Защита в коде всё равно есть —
        старое сообщение может остаться открытым на другом устройстве.
        """
        try:
            await message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        except Exception as e:
            logger.debug(f"Не удалось снять клавиатуру: {e}")

    async def _answer(self, message: types.Message, screen_key: str):
        text, keyboard = render(screen_key)
        await message.answer(text, reply_markup=keyboard,
                             parse_mode=ParseMode.HTML, disable_web_page_preview=True)

    # ------------------------------------------------------- пользовательские шаги

    async def show_intro(self, message: types.Message, user_id: int, source: str):
        """
        Первый экран. Вызывается только по инициативе человека: /platform или
        кнопка в меню. Ни согласия, ни отказа не меняет — о согласии спрашивают
        отдельной кнопкой дальше по сценарию.
        """
        state = self.db.ensure_platform_campaign_state(user_id, self.campaign_id)
        if not state.get("first_shown_at"):
            self._update(user_id, first_shown_at=_now().isoformat())
        else:
            self._update(user_id)

        await self._answer(message, "intro")
        await self._log(user_id, "INVITE_SHOWN", {"source": source})

    async def stop(self, message: types.Message, user_id: int):
        """Команда /platform_stop: отписка от серии."""
        self.db.ensure_platform_campaign_state(user_id, self.campaign_id)
        await self._opt_out(user_id, "command")
        await self._answer(message, "stopped")

    async def _opt_out(self, user_id: int, reason: str):
        """
        Фиксирует отказ. Повторный отказ не перезаписывает первую отметку:
        в отчёте важна дата, когда человек ушёл, а не дата последнего клика.
        """
        state = self.state(user_id) or {}
        if not state.get("opted_out_at"):
            self._update(user_id, opted_out_at=_now().isoformat(), opted_out_reason=reason)
        await self._log(user_id, "OPTED_OUT", {"reason": reason})

    async def handle_callback(self, callback: types.CallbackQuery) -> str:
        """
        Обрабатывает кнопки воронки. Возвращает короткий код результата — он нужен
        тестам и логам, пользователю результат виден по сообщениям.

        Повторное нажатие любой кнопки безопасно: ветка, согласие и отказ
        записываются один раз, второй клик лишних сообщений не рождает.
        """
        user_id = callback.from_user.id
        data = callback.data
        self.db.ensure_platform_campaign_state(user_id, self.campaign_id)
        state = self.state(user_id) or {}

        if data in ROLE_BY_CALLBACK:
            return await self._handle_role(callback, state, ROLE_BY_CALLBACK[data])
        if data == CB_DISMISS:
            return await self._handle_dismiss(callback, state)
        if data == CB_CONSENT_YES:
            return await self._handle_consent(callback, state)
        if data == CB_CONSENT_NO:
            return await self._handle_consent_declined(callback, state)
        if data == CB_OPT_OUT:
            return await self._handle_opt_out_button(callback, state)

        logger.warning(f"Неизвестный callback кампании: {data}")
        await callback.answer("Это действие сейчас недоступно.", show_alert=True)
        return "unknown"

    async def _handle_role(self, callback, state, role) -> str:
        if state.get("interest") == role and not state.get("opted_out_at"):
            # Та же ветка уже выбрана: это второй клик по одному сообщению
            # (двойное нажатие или открытое на другом устройстве). Повтор
            # сообщений не плодим.
            #
            # Отписавшихся эта отсечка не касается: человек заново открыл
            # /platform и нажал кнопку, то есть хочет пройти знакомство снова.
            # Иначе у него не осталось бы способа вернуться — а вернуться он
            # вправе, нужен только новый явный клик «Да, присылайте».
            await self._drop_keyboard(callback.message)
            await callback.answer("Выбор уже сохранён.")
            return "already_chosen"

        # Другая ветка — человек передумал. Это законно: /platform открывает
        # экран знакомства и после отказа, и выбор ветки сам по себе подпиской
        # не является, о согласии спрашивают отдельно.
        user_id = callback.from_user.id
        self._update(user_id, role=role, interest=role)
        await self._drop_keyboard(callback.message)
        await callback.answer()

        screen_key = ROLE_SCREENS[role]
        await self._answer(callback.message, screen_key)
        await self._log(user_id, "INTEREST_SELECTED", {"role": role})
        await self._log(user_id, "CTA_OFFERED", {
            "role": role, "step": "intro",
            "utm_content": PLATFORM_TEXTS[screen_key]["cta"]["utm_content"],
        })

        if state.get("consent_at") and not state.get("opted_out_at"):
            # Человек уже в серии — спрашивать согласие второй раз не нужно.
            return "role_selected"

        # Согласие спрашиваем ОТДЕЛЬНЫМ сообщением: интерес к платформе не должен
        # по пути превращаться в подписку на серию.
        await self._answer(callback.message, "consent_request")
        return "role_selected"

    async def _handle_dismiss(self, callback, state) -> str:
        user_id = callback.from_user.id
        if state.get("interest") == "dismissed":
            await self._drop_keyboard(callback.message)
            await callback.answer("Хорошо, больше не напоминаем.")
            return "already_dismissed"

        self._update(user_id, interest="dismissed")
        await self._drop_keyboard(callback.message)
        await callback.answer()
        await self._log(user_id, "DISMISSED", {})
        await self._opt_out(user_id, "dismissed")
        await self._answer(callback.message, "declined")
        return "dismissed"

    async def _handle_consent(self, callback, state) -> str:
        user_id = callback.from_user.id
        if state.get("consent_at") and not state.get("opted_out_at"):
            # Согласие уже действует: это повторный клик по тому же сообщению.
            await self._drop_keyboard(callback.message)
            await callback.answer("Согласие уже сохранено.")
            return "already_consented"

        resumed = bool(state.get("opted_out_at"))

        role = state.get("role")
        if role not in (ROLE_FACILITATOR, ROLE_EXPLORER):
            # Согласие без выбранной ветки отправлять нечем: текст касания зависит
            # от роли. Такое возможно только на очень старом сообщении.
            await callback.answer("Сначала выбери, что тебе ближе — через /platform.",
                                  show_alert=True)
            return "no_role"

        # Новое явное согласие снимает прежний отказ — именно за этим в тексте
        # оговорено, что /platform сам подписку не возвращает, нужен клик.
        # Уже отправленные шаги при этом сохраняются: повторной серии не будет.
        self._update(user_id, consent_at=_now().isoformat(),
                     opted_out_at=None, opted_out_reason=None)
        await self._drop_keyboard(callback.message)
        await callback.answer()
        await self._log(user_id, "CONSENT_GRANTED", {"role": role, "resumed": resumed})
        await self._answer(callback.message, "consent_granted")
        return "resumed" if resumed else "consented"

    async def _handle_consent_declined(self, callback, state) -> str:
        user_id = callback.from_user.id
        already = bool(state.get("opted_out_at")) and not state.get("consent_at")
        await self._drop_keyboard(callback.message)
        await callback.answer()
        if already:
            return "already_declined"

        await self._log(user_id, "CONSENT_DECLINED", {"role": state.get("role")})
        await self._opt_out(user_id, "declined")
        await self._answer(callback.message, "declined")
        return "declined"

    async def _handle_opt_out_button(self, callback, state) -> str:
        user_id = callback.from_user.id
        await self._drop_keyboard(callback.message)
        await callback.answer()
        if state.get("opted_out_at"):
            return "already_opted_out"

        await self._opt_out(user_id, "button")
        await self._answer(callback.message, "declined")
        return "opted_out"

    # ----------------------------------------------------------------- планировщик

    def due_steps(self, state: dict, now: datetime) -> list[dict]:
        """
        Какие касания для этого человека созрели к моменту now и в каком виде:
        'send' — отправить, 'retry' — добить после временного сбоя,
        'stale' — просрочено, отправлять поздно.

        Чистая функция от состояния: ею пользуются и тик планировщика, и dry-run,
        поэтому админ видит ровно то, что уйдёт.
        """
        consent_at = _parse_ts(state.get("consent_at"))
        if not consent_at or state.get("opted_out_at") or state.get("converted_at"):
            return []
        now = _aware(now)

        sent = set(state.get("sent_step_ids") or [])
        retries = state.get("retry_state") or {}
        plan = []
        for step_id, delay in FOLLOWUP_DELAYS:
            due_at = consent_at + delay
            if now < due_at:
                break                     # шаги упорядочены: дальше только позже
            if step_id in sent:
                # Шаг занят. Отправлять его заново нельзя — кроме случая, когда
                # отправка сорвалась по временной причине и попытки не исчерпаны.
                retry = retries.get(step_id)
                if not retry:
                    continue
                attempts = retry.get("attempts", 0)
                first_failed = _parse_ts(retry.get("first_failed_at")) or now
                if attempts < MAX_SEND_ATTEMPTS and now - first_failed <= RETRY_WINDOW:
                    plan.append({"step": step_id, "due_at": due_at,
                                 "action": "retry", "attempts": attempts})
                else:
                    plan.append({"step": step_id, "due_at": due_at, "action": "give_up",
                                 "attempts": attempts, "error": retry.get("error")})
                continue
            action = "stale" if now - due_at > STEP_STALE_AFTER else "send"
            plan.append({"step": step_id, "due_at": due_at, "action": action, "attempts": 0})
        return plan

    async def process_due_followups(self, now: datetime = None, dry_run: bool = False) -> dict:
        """
        Один проход по согласившимся. Вызывается планировщиком и кнопкой dry-run
        в админке.

        dry_run ничего не отправляет и ничего не меняет в базе — только
        возвращает план. Поэтому выключатель кампании его не блокирует: админ
        должен видеть план и до запуска.
        """
        now = _aware(now) if now else _now()
        paused_until = _parse_ts(self.db.get_platform_campaign_paused_until(self.campaign_id))
        result = {
            "enabled": bool(self.db.is_platform_campaign_enabled(self.campaign_id)),
            "dry_run": dry_run, "sent": 0, "failed": 0, "deferred": 0,
            "skipped": 0, "attempts": 0, "planned": [],
            "paused_until": paused_until.isoformat() if paused_until else None,
        }
        if not dry_run and not result["enabled"]:
            # Выключатель — это пауза всей кампании, а не ошибка.
            result["reason"] = "disabled"
            return result

        if not dry_run and paused_until and now < paused_until:
            # Флуд-контроль Telegram назвал время ожидания, и оно может быть
            # больше интервала тика. Пока срок не вышел, к API не обращаемся.
            result["reason"] = "flood_wait"
            result["flood_wait"] = int((paused_until - now).total_seconds())
            return result

        participants = self.db.get_platform_campaign_participants(self.campaign_id)
        if not participants:
            return result

        # Заблокировавшие бота считаются один раз на проход: запрос тяжёлый.
        unreachable = self.db.get_unreachable_user_ids()

        for state in participants:
            if result["attempts"] >= MAX_SEND_ATTEMPTS_PER_TICK:
                result["throttled"] = True
                break

            user_id = state["user_id"]
            role = state.get("role")
            plan = self.due_steps(state, now)
            if not plan:
                continue

            if role not in (ROLE_FACILITATOR, ROLE_EXPLORER):
                # Текст касания зависит от роли; без роли отправлять нечего.
                logger.warning(f"Platform campaign: user {user_id} consented without role")
                result["skipped"] += len(plan)
                continue

            if user_id in unreachable:
                # Человек заблокировал бота или удалил аккаунт — кампания для него
                # закончена, в статистику доставки его сбои не пишем.
                result["skipped"] += len(plan)
                result["planned"].append({"user_id": user_id, "step": plan[0]["step"],
                                          "action": "unreachable"})
                if not dry_run:
                    await self._log(user_id, "FOLLOWUP_SKIPPED",
                                    {"step": plan[0]["step"], "reason": "unreachable"})
                    await self._opt_out(user_id, "blocked")
                continue

            for item in plan:
                if dry_run:
                    result["planned"].append({"user_id": user_id, "role": role, **item})
                    if item["action"] in ("send", "retry"):
                        result["sent"] += 1          # «уйдёт, если включить»
                    else:
                        result["skipped"] += 1
                    continue

                if result["attempts"] >= MAX_SEND_ATTEMPTS_PER_TICK:
                    result["throttled"] = True
                    break

                outcome = await self._process_step(user_id, role, item, now, result)
                result[outcome] = result.get(outcome, 0) + 1
                if result.get("flood_wait"):
                    # Telegram попросил подождать: на этом тике больше не шлём.
                    break

            if result.get("flood_wait"):
                break

        return result

    async def _process_step(self, user_id: int, role: str, item: dict, now: datetime,
                            result: dict = None) -> str:
        """
        Обрабатывает одно созревшее касание. Возвращает sent/failed/deferred/skipped.
        В result (итоги тика) отмечает флуд-контроль, чтобы вызывающий остановил проход.
        """
        result = result if result is not None else {}
        step_id = item["step"]
        action = item["action"]

        if action == "stale":
            # Занимаем шаг, чтобы он не выстрелил позже, и фиксируем пропуск.
            if self.db.claim_platform_campaign_step(user_id, self.campaign_id, step_id):
                self._record_step_result(user_id, step_id, self.db.PLATFORM_STEP_SKIPPED,
                                         reason="stale")
                await self._log(user_id, "FOLLOWUP_SKIPPED", {
                    "step": step_id, "reason": "stale",
                    "overdue_days": (now - item["due_at"]).days,
                })
            return "skipped"

        if action == "give_up":
            await self._finalize_failure(user_id, step_id, item.get("error"),
                                         item.get("attempts", 0))
            return "failed"

        if action == "send":
            # Занятие шага перечитывает согласие в своей транзакции, поэтому
            # отписка, прилетевшая во время прохода, здесь уже видна.
            if not self.db.claim_platform_campaign_step(user_id, self.campaign_id, step_id):
                return "skipped"

        attempts = item.get("attempts", 0) + 1
        result["attempts"] = result.get("attempts", 0) + 1
        outcome, error = await self._send_step(user_id, role, step_id)

        if outcome == "ineligible":
            # Человек отписался между планированием и отправкой. Шаг остаётся
            # занятым: возвращать его в очередь нельзя, он больше не нужен.
            result["attempts"] -= 1               # до Telegram дело не дошло
            self._record_step_result(user_id, step_id, self.db.PLATFORM_STEP_SKIPPED,
                                     reason="opted_out")
            await self._log(user_id, "FOLLOWUP_SKIPPED",
                            {"step": step_id, "reason": "opted_out"})
            return "skipped"

        if error is None:
            self._clear_retry(user_id, step_id)
            self._record_step_result(user_id, step_id, self.db.PLATFORM_STEP_SENT,
                                     attempts=attempts)
            await self._log(user_id, "FOLLOWUP_SENT", {
                "step": step_id, "role": role, "attempts": attempts,
                # Подтверждён приём Telegram'ом. Ни прочтение, ни переход по
                # ссылке этим не подтверждаются: нажатие URL-кнопки боту не видно.
                "delivery": "telegram_accepted",
            })
            await asyncio.sleep(SEND_PAUSE_SECONDS)
            return "sent"

        if is_user_unreachable_error(error):
            self._record_error(user_id, step_id, error, attempts, retryable=False)
            self._record_step_result(user_id, step_id, self.db.PLATFORM_STEP_FAILED,
                                     attempts=attempts, reason="unreachable", error=error)
            await self._log(user_id, "FOLLOWUP_FAILED", {
                "step": step_id, "role": role, "attempts": attempts,
                "error": str(error)[:200], "reason": "unreachable",
            })
            await self._opt_out(user_id, "blocked")
            return "failed"

        if isinstance(error, TelegramRetryAfter):
            # Лимит Telegram на бота. Ждать внутри тика нельзя — это задержало бы
            # весь проход; запоминаем срок в базе и выходим. Сообщение отклонено
            # лимитом, то есть точно не доставлено, — повтор безопасен.
            wait = getattr(error, "retry_after", None) or 0
            until = now + timedelta(seconds=wait) + FLOOD_WAIT_MARGIN
            self.db.set_platform_campaign_paused_until(self.campaign_id, until.isoformat())
            result["flood_wait"] = wait
            result["paused_until"] = until.isoformat()
            self._record_error(user_id, step_id, error, attempts, retryable=True)
            self._record_step_result(user_id, step_id, self.db.PLATFORM_STEP_DEFERRED,
                                     attempts=attempts, reason="flood_wait", error=error)
            return "deferred"

        # Повторяем только то, что точно не было доставлено. Таймаут ответа,
        # обрыв на середине и 5xx от этого отличаются: Telegram мог принять
        # сообщение и потерять ответ, и повтор тогда даст человеку второе
        # одинаковое письмо. Для маркетинговой серии потеря безопаснее дубля,
        # поэтому неопределённую доставку считаем окончательной неудачей.
        if (is_certainly_not_delivered(error) and is_temporary_error(error)
                and attempts < MAX_SEND_ATTEMPTS):
            self._record_error(user_id, step_id, error, attempts, retryable=True)
            self._record_step_result(user_id, step_id, self.db.PLATFORM_STEP_DEFERRED,
                                     attempts=attempts, reason="not_delivered", error=error)
            logger.warning(f"Platform follow-up {step_id} to user {user_id} deferred: {error}")
            return "deferred"

        reason = "attempts_exhausted" if is_certainly_not_delivered(error) else "delivery_unknown"
        await self._finalize_failure(user_id, step_id, error, attempts, reason)
        return "failed"

    async def _send_step(self, user_id: int, role: str, step_id: str):
        """
        Одна попытка отправки касания. Возвращает ("sent"|"failed"|"ineligible", ошибку).

        Согласие перечитывается здесь, непосредственно перед обращением к
        Telegram, и между проверкой и отправкой нет ни одного await: отписка,
        сделанная во время прохода, успевает сработать.
        """
        if not self.db.platform_campaign_consent_is_live(user_id, self.campaign_id):
            logger.info(f"Platform follow-up {step_id} to user {user_id} cancelled: consent withdrawn")
            return "ineligible", None

        text, keyboard = render(FOLLOWUP_SCREENS[(step_id, role)])
        try:
            await self.bot.send_message(
                user_id, text, reply_markup=keyboard, parse_mode=ParseMode.HTML,
                disable_web_page_preview=True, request_timeout=SEND_TIMEOUT_SECONDS)
            return "sent", None
        except TelegramRetryAfter as e:
            logger.warning(f"Platform campaign hit flood control, retry after {e.retry_after}s")
            return "failed", e
        except Exception as e:
            return "failed", e

    async def _finalize_failure(self, user_id: int, step_id: str, error, attempts: int,
                                reason: str = "attempts_exhausted"):
        """Окончательная неудача: попытки исчерпаны или доставка неопределённа."""
        logger.error(f"Giving up on platform follow-up {step_id} to user {user_id} "
                     f"after {attempts} attempts ({reason}): {error}")
        self._record_error(user_id, step_id, error, attempts, retryable=False)
        self._record_step_result(user_id, step_id, self.db.PLATFORM_STEP_FAILED,
                                 attempts=attempts, reason=reason, error=error)
        await self._log(user_id, "FOLLOWUP_FAILED", {
            "step": step_id, "attempts": attempts, "reason": reason,
            "error": str(error)[:200],
        })

    def _record_step_result(self, user_id: int, step_id: str, status: str,
                            attempts: int = None, reason: str = None, error=None):
        """
        Пишет исход шага. Нужен потому, что «шаг занят» и «сообщение доставлено» —
        разные вещи: занятым шаг становится до обращения к Telegram и остаётся им
        при пропуске и при неудаче. Без отдельной записи исхода отчёт считал бы
        доставкой любой занятый шаг.
        """
        state = self.state(user_id) or {}
        results = dict(state.get("step_results") or {})
        entry = {"status": status, "at": _now().isoformat()}
        if attempts is not None:
            entry["attempts"] = attempts
        if reason:
            entry["reason"] = reason
        if error is not None:
            entry["error"] = str(error)[:200]
        results[step_id] = entry
        self._update(user_id, step_results=results)

    def _record_error(self, user_id: int, step_id: str, error, attempts: int, retryable: bool):
        """
        Пишет ошибку отправки в состояние. Счётчик попыток живёт в базе, поэтому
        рестарт не даёт шагу лишних попыток.
        """
        state = self.state(user_id) or {}
        retries = dict(state.get("retry_state") or {})
        if retryable:
            entry = dict(retries.get(step_id) or {})
            entry["attempts"] = attempts
            entry["error"] = str(error)[:200]
            entry.setdefault("first_failed_at", _now().isoformat())
            retries[step_id] = entry
        else:
            retries.pop(step_id, None)
        self._update(user_id, retry_state=retries,
                     last_error=f"{step_id}: {str(error)[:200]}",
                     last_error_at=_now().isoformat())

    def _clear_retry(self, user_id: int, step_id: str):
        state = self.state(user_id) or {}
        retries = dict(state.get("retry_state") or {})
        if step_id in retries:
            retries.pop(step_id, None)
            self._update(user_id, retry_state=retries)
        else:
            self._update(user_id)

    # -------------------------------------------------------------------- аудитория

    def estimate_audience(self) -> dict:
        """
        Сколько людей вообще можно позвать в воронку — для оценки канала, а не для
        отправки. Сегменты берём из готового отчёта по «Карте дня», кандидатов по
        тесту «Стать автором» — из его таблицы, пересечения дедуплицируем.

        Отправлять по этим спискам нельзя: согласия на рекламную рассылку у этих
        людей нет. Числа нужны, чтобы понимать потолок канала при добровольном
        входе через /platform.
        """
        from modules.admin.user_segments import (
            SENDABLE_SEGMENTS, get_author_test_candidates, get_user_segments,
        )

        segments = get_user_segments(self.db)["segments"]
        unreachable = self.db.get_unreachable_user_ids()

        groups = {name: {r["user_id"] for r in segments.get(name, [])}
                  for name in SENDABLE_SEGMENTS}
        groups["author_test"] = set(get_author_test_candidates(self.db))

        seen: set[int] = set()
        rows = []
        for name in list(SENDABLE_SEGMENTS) + ["author_test"]:
            ids = groups[name]
            unique = ids - seen            # дедупликация: человек считается один раз
            seen |= ids
            rows.append({
                "segment": name,
                "total": len(ids),
                "unique": len(unique),
                "reachable": len({uid for uid in unique if uid not in unreachable}),
            })

        reachable_total = {uid for uid in seen if uid not in unreachable}
        funnel = self.db.get_platform_campaign_funnel(self.campaign_id)
        return {
            "groups": rows,
            "total": len(seen),
            "reachable": len(reachable_total),
            "blocked": len(seen) - len(reachable_total),
            "entered": funnel["total"],
            "consented": funnel["consented"],
            "opted_out": funnel["opted_out"],
        }


# ------------------------------------------------------------------- обработчики

def make_platform_handler(db, logger_service, source: str = "command"):
    """
    Команда /platform и кнопка главного меню. Состояния FSM не трогает: экран
    знакомства самостоятелен и не должен ломать «Карту дня» или тест автора.
    """
    async def handler(message: types.Message):
        campaign = PlatformCampaign(db, message.bot, logger_service)
        try:
            await campaign.show_intro(message, message.from_user.id, source)
        except Exception as e:
            logger.error(f"Error showing platform intro: {e}", exc_info=True)
            await message.answer("Не получилось открыть знакомство с платформой. Попробуй позже.")
    return handler


def make_platform_stop_handler(db, logger_service):
    """Команда /platform_stop."""
    async def handler(message: types.Message):
        campaign = PlatformCampaign(db, message.bot, logger_service)
        try:
            await campaign.stop(message, message.from_user.id)
        except Exception as e:
            logger.error(f"Error stopping platform campaign: {e}", exc_info=True)
            await message.answer("Не получилось отключить рассылку. Напиши, пожалуйста, ещё раз: /platform_stop")
    return handler


def make_platform_callback_handler(db, logger_service):
    """Кнопки воронки (callback_data с префиксом platform_)."""
    async def handler(callback: types.CallbackQuery):
        campaign = PlatformCampaign(db, callback.bot, logger_service)
        try:
            await campaign.handle_callback(callback)
        except Exception as e:
            logger.error(f"Error handling platform callback {callback.data}: {e}", exc_info=True)
            try:
                await callback.answer("Что-то сломалось, попробуй позже.", show_alert=True)
            except Exception:
                pass
    return handler
