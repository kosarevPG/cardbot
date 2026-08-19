# код/notification_service.py

import asyncio
from datetime import datetime, timedelta
try:
    from config_local import TIMEZONE
except ImportError:
    from config import TIMEZONE
import logging

from aiogram.exceptions import (
    TelegramNetworkError, TelegramRetryAfter, TelegramServerError,
)

# Импортируем функцию для получения меню
from modules.card_of_the_day import get_main_menu

# Сколько ещё пытаться достучаться после сетевого сбоя. 11.08.2026 сеть контейнера
# лежала час подряд (10:00:31–11:01:51) и унесла две пачки напоминаний целиком —
# 47 человек остались без него, потому что повторов не было вовсе.
RETRY_WINDOW_MINUTES = 60

# Потолок на одну отправку. Без него зависший запрос держит цикл минуту: ровно так
# 15.08.2026 обработка одного апдейта заняла 60 секунд. Напоминание не та вещь,
# ради которой стоит ждать так долго.
SEND_TIMEOUT_SECONDS = 20

# Насколько минут цикл готов догонять пропущенное, если проход затянулся. Дальше —
# уже не догон, а пачка несвоевременных напоминаний за прошедшее время.
CATCHUP_LIMIT_MINUTES = 5

# Отступ от начала минуты, чтобы не проснуться за мгновение до неё.
TICK_OFFSET_SECONDS = 0.5


def _is_temporary(error: Exception) -> bool:
    """
    Стоит ли повторять отправку. Сеть, таймаут, флуд-контроль и сбой на стороне
    Telegram — временные. Блокировка и удалённый аккаунт постоянны: повторять их
    бессмысленно, человек не станет доступнее от второй попытки.
    """
    return isinstance(error, (
        TelegramNetworkError, TelegramRetryAfter, TelegramServerError,
        asyncio.TimeoutError, ConnectionError, OSError,
    ))


class NotificationService:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        # Убрал basicConfig отсюда, лучше настраивать в main.py
        self.logger = logging.getLogger(__name__) # Используем именованный логгер
        # Напоминания, которые не ушли из-за сетевого сбоя и ждут повтора.
        # Ключ (user_id, вид, дата) не даёт поставить одно и то же напоминание
        # в очередь дважды. Живёт только в памяти: переживать перезапуск здесь
        # незачем, к моменту подъёма напоминание всё равно уже неактуально.
        self._pending = {}

    def _log_reminder(self, user_id: int, kind: str, ok: bool, error: str = None,
                      attempts: int = 1, delayed_minutes: int = 0):
        """
        Пишет итог отправки напоминания в actions.

        Раньше отправка фиксировалась только в файловый лог, поэтому по базе нельзя
        было понять, доходят ли напоминания вообще и как они влияют на возвраты —
        при том, что напоминание оказалось сильнейшим наблюдаемым фактором удержания.
        Пишем через db.save_action напрямую: logging_service.log_action на каждого
        адресата делал бы лишний запрос к Telegram API.

        Запись делается один раз, по итогу всех попыток, иначе одно напоминание
        считалось бы в статистике несколько раз.
        """
        try:
            details = {"kind": kind, "status": "sent" if ok else "failed"}
            if error:
                details["error"] = str(error)[:200]
            if attempts > 1:
                details["attempts"] = attempts
            if delayed_minutes:
                details["delayed_minutes"] = delayed_minutes
            self.db.save_action(
                user_id, "", "", "reminder_sent", details,
                datetime.now(TIMEZONE).isoformat(),
            )
        except Exception as e:
            self.logger.warning(f"Failed to log reminder for user {user_id}: {e}")

    async def _try_send(self, user_id: int, text: str):
        """Одна попытка отправки. Возвращает исключение или None при успехе."""
        try:
            await self.bot.send_message(
                user_id, text,
                reply_markup=await get_main_menu(user_id, self.db),
                request_timeout=SEND_TIMEOUT_SECONDS,
            )
            return None
        except Exception as e:
            return e

    async def _send_reminder(self, user_id: int, kind: str, text: str, now: datetime):
        """
        Отправляет напоминание. При временном сбое не теряет его, а ставит в очередь
        на повтор — следующие попытки сделает _flush_pending на очередных тиках цикла.
        Повторять здесь же, подряд, нельзя: во время сбоя это растянуло бы проход по
        пачке на минуты и сдвинуло бы напоминания остальным.
        """
        error = await self._try_send(user_id, text)
        if error is None:
            self.logger.info(f"{kind.capitalize()} reminder sent to user {user_id} at {now}")
            self._log_reminder(user_id, kind, True)
            return

        if _is_temporary(error):
            key = (user_id, kind, now.date())
            if key not in self._pending:
                self._pending[key] = {
                    "text": text, "attempts": 1, "since": now,
                    "deadline": now + timedelta(minutes=RETRY_WINDOW_MINUTES),
                    "error": error,
                }
                self.logger.warning(
                    f"{kind.capitalize()} reminder to user {user_id} deferred after network error: {error}")
            return

        self.logger.error(f"Failed to send {kind.upper()} reminder to user {user_id}: {error}")
        self._log_reminder(user_id, kind, False, error)

    async def _flush_pending(self, now: datetime):
        """
        Добивает напоминания, не ушедшие из-за сетевого сбоя: по одной попытке на
        каждом тике цикла, пока не выйдет отведённое окно. Отдав всё, что смогло,
        по остальным пишет в базу окончательную неудачу — чтобы сетевые потери были
        видны в статистике, а не растворялись молча.
        """
        for key, item in list(self._pending.items()):
            user_id, kind, day = key

            # Пока напоминание ждало сети, человек мог сам вытянуть карту. Звать его
            # за тем, что он уже сделал, не нужно — молча снимаем с очереди.
            if kind == "morning" and not self.db.is_card_available(user_id, day):
                self.logger.info(
                    f"Morning reminder to user {user_id} dropped: card already drawn")
                del self._pending[key]
                continue

            item["attempts"] += 1
            error = await self._try_send(user_id, item["text"])
            delayed = int((now - item["since"]).total_seconds() // 60)

            if error is None:
                self.logger.info(
                    f"{kind.capitalize()} reminder delivered to user {user_id} "
                    f"after {item['attempts']} attempts ({delayed} min late)")
                self._log_reminder(user_id, kind, True,
                                   attempts=item["attempts"], delayed_minutes=delayed)
                del self._pending[key]
                continue

            if not _is_temporary(error):
                # Сеть вернулась, но человек недоступен: блокировка или удалённый аккаунт.
                self.logger.error(f"Failed to send {kind.upper()} reminder to user {user_id}: {error}")
                self._log_reminder(user_id, kind, False, error,
                                   attempts=item["attempts"], delayed_minutes=delayed)
                del self._pending[key]
                continue

            item["error"] = error
            if now >= item["deadline"]:
                self.logger.error(
                    f"Giving up on {kind.upper()} reminder to user {user_id} "
                    f"after {item['attempts']} attempts over {delayed} min: {error}")
                self._log_reminder(user_id, kind, False, error,
                                   attempts=item["attempts"], delayed_minutes=delayed)
                del self._pending[key]

    async def _process_minute(self, moment: datetime):
        """
        Отправляет напоминания, назначенные на одну конкретную минуту.

        Имя запрашивается только у тех, кому действительно пора слать. Раньше оно
        бралось на каждого адресата каждую минуту — около восьмидесяти тысяч лишних
        запросов к базе в сутки, и именно они раскачивали цикл (см. check_reminders).
        """
        current_time_str = moment.strftime("%H:%M")
        today = moment.date()
        reminders_data = self.db.get_reminder_times() # {user_id: {'morning': t1, 'evening': t2}}

        for user_id, times in reminders_data.items():
            morning_time = times.get('morning')
            evening_time = times.get('evening')
            if morning_time != current_time_str and evening_time != current_time_str:
                continue

            name = (self.db.get_user(user_id) or {}).get("name", "")

            # Проверка утреннего напоминания (Карта Дня)
            if morning_time == current_time_str and self.db.is_card_available(user_id, today):
                text = f"{name}, привет! Пришло время вытянуть свою карту дня. ✨ Изменить настройки напоминаний: /remind, /remind_off" if name else "Привет! Пришло время вытянуть свою карту дня. ✨ Изменить настройки напоминаний: /remind, /remind_off"
                # Отправляем с клавиатурой, чтобы сразу можно было нажать
                await self._send_reminder(user_id, "morning", text, moment)

            # Проверка вечернего напоминания (Итог Дня)
            if evening_time == current_time_str:
                text = f"{name}, привет! Пришло время подвести итог дня 🌙" if name else "Привет! Пришло время подвести итог дня 🌙"
                # Отправляем с клавиатурой
                await self._send_reminder(user_id, "evening", text, moment)

    @staticmethod
    def _seconds_until_next_minute(now: datetime) -> float:
        """
        Сколько спать до начала следующей минуты. Считается от текущего времени, а не
        прибавлением 60 секунд к моменту пробуждения, поэтому время работы цикла в
        период не подмешивается и тик не уползает вперёд.
        """
        next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        return max(0.1, (next_minute - now).total_seconds() + TICK_OFFSET_SECONDS)

    def _minutes_to_process(self, last_processed, current):
        """
        Какие минуты обработать на этом тике. Обычно одна — текущая. Если предыдущий
        проход затянулся и минута успела смениться дважды, возвращаем и пропущенные:
        напоминание, назначенное на такую минуту, иначе исчезло бы бесследно.
        """
        if last_processed is None:
            return [current]
        if current <= last_processed:
            return []                      # проснулись в той же минуте, слать нечего

        gap = int((current - last_processed).total_seconds() // 60)
        if gap > CATCHUP_LIMIT_MINUTES:
            # Бот стоял долго. Догонять всё подряд нельзя: человек получил бы пачку
            # напоминаний за прошедшее время, и все не вовремя.
            self.logger.warning(
                f"Reminder loop resumed after {gap} min gap; skipping missed minutes")
            return [current]
        return [last_processed + timedelta(minutes=i) for i in range(1, gap + 1)]

    async def check_reminders(self):
        """
        Проверяет и отправляет утренние и вечерние напоминания.

        Цикл засыпает до начала следующей минуты, а не на фиксированные 60 секунд.
        Разница принципиальная: со сном на 60 секунд к периоду добавлялось время
        самой работы, тик медленно уползал вперёд и примерно раз в несколько часов
        перепрыгивал через минутную границу. Совпадение ищется по строке "%H:%M",
        поэтому перепрыгнутая минута для бота не существовала — назначенные на неё
        напоминания пропадали молча, без ошибки в логе. По замерам 18.08.2026 период
        составлял 60.58 с, а за сутки терялось около шести минут.
        """
        last_processed = None
        while True:
            try:
                now = datetime.now(TIMEZONE)

                # Сначала добиваем недоставленное с прошлых тиков, потом рассылаем новое.
                if self._pending:
                    await self._flush_pending(now)

                minutes = self._minutes_to_process(
                    last_processed, now.replace(second=0, microsecond=0))
                for moment in minutes:
                    await self._process_minute(moment)
                if minutes:
                    last_processed = minutes[-1]

            except Exception as loop_err:
                self.logger.error(f"Error in reminder check loop: {loop_err}", exc_info=True)
                # Ждем дольше в случае серьезной ошибки в цикле
                await asyncio.sleep(300) # Ждем 5 минут перед повторной попыткой
                continue # Переходим к следующей итерации цикла

            # Просыпаемся сразу после начала следующей минуты. Небольшой отступ нужен,
            # чтобы не проснуться за мгновение до неё и не потратить тик впустую.
            await asyncio.sleep(self._seconds_until_next_minute(datetime.now(TIMEZONE)))

    # ... (существующий метод send_broadcast) ...

    async def send_broadcast(self, broadcast_data):
        # Логируем входные данные
        logging.info(f"Starting broadcast with datetime: {broadcast_data['datetime']}, recipients: {broadcast_data['recipients']}")

        while True:
            now = datetime.now(TIMEZONE)
            logging.info(f"Current time: {now}, Target time: {broadcast_data['datetime']}")

            if now >= broadcast_data["datetime"]:
                recipients = self.db.get_all_users() if broadcast_data["recipients"] == "all" else broadcast_data["recipients"]
                for user_id in recipients:
                    name = self.db.get_user(user_id)["name"]
                    text = f"{name}, {broadcast_data['text']}" if name else broadcast_data["text"]
                    try:
                        await self.bot.send_message(user_id, text)
                        logging.info(f"Broadcast sent to user {user_id} at {now}")
                    except Exception as e:
                        logging.error(f"Failed to send broadcast to user {user_id}: {e}")
                break  # Выходим из цикла после отправки
            else:
                # Ждём до следующей проверки (например, 60 секунд)
                time_to_wait = (broadcast_data["datetime"] - now).total_seconds()
                wait_seconds = min(time_to_wait, 60)  # Ждём не больше 60 секунд за раз
                logging.info(f"Waiting {wait_seconds} seconds until broadcast time")
                await asyncio.sleep(wait_seconds)
