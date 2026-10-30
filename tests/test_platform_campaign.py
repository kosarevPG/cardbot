"""
Регрессионный тест воронки знакомства с платформой TopPsyGame.

Запуск:  python tests/test_platform_campaign.py
Код возврата 0 — все проверки пройдены, 1 — есть падения.

Работает на временной базе, созданной с нуля настоящим классом Database, —
боевые данные не нужны, Telegram не вызывается (бот подставной).

Что защищаем:
  * вход в воронку только по инициативе человека, участие в боте согласием не считается;
  * без явного согласия не уходит ни одного автоматического касания;
  * выключатель кампании по умолчанию выключен, и пока он выключен — тишина;
  * повторный клик по кнопке не плодит сообщений и не задваивает согласие;
  * повторный тик планировщика и перезапуск бота не дублируют касания;
  * больше двух касаний не бывает ни при каких обстоятельствах;
  * отказ, /platform_stop и блокировка бота прекращают кампанию;
  * повторный /platform не возвращает подписку без нового клика «Да, присылайте»;
  * временный сбой добивается повторами, постоянный — снимает человека с кампании;
  * просроченное касание не отправляется задним числом;
  * пересечения сегментов в оценке аудитории считаются один раз;
  * в ссылках нет Telegram ID и персональных данных.
"""
import asyncio
import os
import sys
import tempfile
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError  # noqa: E402

failures = []


def check(name, actual, expected):
    if actual == expected:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}: ожидалось {expected}, получено {actual}")
        failures.append(name)


# --------------------------------------------------------------------- подставные

class FakeBot:
    """Запоминает отправленное. error — что бросать вместо отправки."""

    def __init__(self):
        self.sent = []
        self.error = None
        self.attempts = 0            # считаем и неудачные попытки тоже

    async def send_message(self, chat_id, text, **kwargs):
        self.attempts += 1
        if self.error:
            raise self.error
        self.sent.append({"chat_id": chat_id, "text": text,
                          "markup": kwargs.get("reply_markup")})
        return FakeMessage(chat_id, self)


class FakeMessage:
    """Сообщение в чате: собирает ответы бота и снятия клавиатуры."""

    def __init__(self, user_id, bot, answers=None):
        self.bot = bot
        self.from_user = FakeUser(user_id)
        self.answers = answers if answers is not None else []
        self.keyboard_dropped = 0

    async def answer(self, text, **kwargs):
        self.answers.append({"text": text, "markup": kwargs.get("reply_markup")})
        return FakeMessage(self.from_user.id, self.bot, self.answers)

    async def edit_text(self, text, **kwargs):
        self.answers.append({"text": text, "markup": kwargs.get("reply_markup")})
        return self

    async def edit_reply_markup(self, reply_markup=None):
        self.keyboard_dropped += 1


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id
        self.username = f"user{user_id}"
        self.is_bot = False


class FakeCallback:
    def __init__(self, user_id, data, message):
        self.from_user = FakeUser(user_id)
        self.data = data
        self.message = message
        self.bot = message.bot
        self.answers = []

    async def answer(self, text=None, show_alert=False):
        self.answers.append(text)


class FakeLoggerService:
    """Пишет события в список вместо базы: тесту важен сам факт и детали."""

    def __init__(self):
        self.events = []

    async def log_action(self, user_id, action, details=None, username=None):
        self.events.append({"user_id": user_id, "action": action, "details": details or {}})


def events_of(logger_service, action_suffix):
    return [e for e in logger_service.events if e["action"].endswith(action_suffix)]


# ------------------------------------------------------------------- окружение

def make_env(path):
    """Настоящая база + настоящая воронка на подставных боте и логгере."""
    from database.db import Database
    from modules.platform_campaign import PlatformCampaign

    db = Database(path=path)
    bot, logs = FakeBot(), FakeLoggerService()
    return db, bot, logs, PlatformCampaign(db, bot, logs)


def add_user(db, user_id, name="Тест"):
    db.conn.execute("INSERT OR IGNORE INTO users (user_id, name, username) VALUES (?, ?, ?)",
                    (user_id, name, f"user{user_id}"))
    db.conn.commit()


async def enter_funnel(campaign, user_id, role_callback, consent=True):
    """Проводит человека по воронке так, как это делают кнопки в Telegram."""
    bot = campaign.bot
    message = FakeMessage(user_id, bot)
    await campaign.show_intro(message, user_id, "command")

    callback = FakeCallback(user_id, role_callback, message)
    await campaign.handle_callback(callback)

    if consent:
        from modules.texts.platform import CB_CONSENT_YES
        await campaign.handle_callback(FakeCallback(user_id, CB_CONSENT_YES, message))
    return message


def set_consent_at(db, user_id, when, campaign_id="platform_launch"):
    """Сдвигает момент согласия в прошлое, чтобы касание созрело."""
    db.update_platform_campaign_state(user_id, campaign_id, consent_at=when.isoformat())


# --------------------------------------------------------------------- сценарии

async def scenario_opt_in_flow(path):
    """Прохождение воронки: приглашение → ветка → явное согласие."""
    from modules.texts.platform import CB_ROLE_FACILITATOR

    db, bot, logs, campaign = make_env(path)
    add_user(db, 101)

    message = await enter_funnel(campaign, 101, CB_ROLE_FACILITATOR)
    state = campaign.state(101)

    print("Вход в воронку:")
    # Четыре сообщения: приглашение, ответ по роли, вопрос о согласии, подтверждение
    check("показаны все четыре шага знакомства", len(message.answers), 4)
    check("ветка записана", state["role"], "facilitator")
    check("согласие записано", bool(state["consent_at"]), True)
    check("отказа нет", state["opted_out_at"], None)
    check("ни одного касания не отправлено", bot.sent, [])
    check("событие интереса записано", len(events_of(logs, "interest_selected")), 1)
    check("событие согласия записано", len(events_of(logs, "consent_granted")), 1)
    check("CTA помечен как показанный, а не нажатый",
          events_of(logs, "cta_offered")[0]["details"]["step"], "intro")
    db.close()


async def scenario_kill_switch(path):
    """Пока администратор не включил кампанию, планировщик молчит."""
    from modules.texts.platform import CB_ROLE_EXPLORER

    db, bot, logs, campaign = make_env(path)
    add_user(db, 102)
    await enter_funnel(campaign, 102, CB_ROLE_EXPLORER)
    set_consent_at(db, 102, datetime.now() - timedelta(days=3))

    print("Выключатель кампании:")
    check("по умолчанию выключено", db.is_platform_campaign_enabled("platform_launch"), False)
    result = await campaign.process_due_followups()
    check("тик при выключенной кампании ничего не делает", result.get("reason"), "disabled")
    check("ничего не отправлено", bot.sent, [])

    # dry-run должен работать и до включения: админ обязан видеть план заранее.
    dry = await campaign.process_due_followups(dry_run=True)
    check("dry-run видит созревшее касание", dry["sent"], 1)
    check("dry-run ничего не отправил", bot.sent, [])
    check("dry-run не занял шаг", campaign.state(102)["sent_step_ids"], [])
    db.close()


async def scenario_no_consent(path):
    """Без явного согласия не уходит ничего, даже при включённой кампании."""
    from modules.texts.platform import CB_CONSENT_NO, CB_ROLE_FACILITATOR

    db, bot, logs, campaign = make_env(path)
    db.set_platform_campaign_enabled("platform_launch", True, updated_by=1)

    # Выбрал ветку, но согласие не дал вообще
    add_user(db, 201)
    await enter_funnel(campaign, 201, CB_ROLE_FACILITATOR, consent=False)

    # Выбрал ветку и ответил «Нет, спасибо»
    add_user(db, 202)
    message = await enter_funnel(campaign, 202, CB_ROLE_FACILITATOR, consent=False)
    await campaign.handle_callback(FakeCallback(202, CB_CONSENT_NO, message))

    # «Не интересно» на первом экране
    from modules.texts.platform import CB_DISMISS
    add_user(db, 203)
    msg3 = FakeMessage(203, bot)
    await campaign.show_intro(msg3, 203, "main_menu")
    await campaign.handle_callback(FakeCallback(203, CB_DISMISS, msg3))

    result = await campaign.process_due_followups(now=datetime.now() + timedelta(days=30))

    print("Отсутствие согласия:")
    check("интерес без согласия касаний не даёт", campaign.state(201)["consent_at"], None)
    check("«Нет, спасибо» записан как отказ", campaign.state(202)["opted_out_reason"], "declined")
    check("«Не интересно» записано как отказ", campaign.state(203)["opted_out_reason"], "dismissed")
    check("планировщик никого не нашёл", result["sent"], 0)
    check("ничего не отправлено", bot.sent, [])
    db.close()


async def scenario_repeat_callbacks(path):
    """Повторные нажатия: ни лишних сообщений, ни задвоенного согласия."""
    from modules.texts.platform import (
        CB_CONSENT_YES, CB_DISMISS, CB_ROLE_FACILITATOR,
    )

    db, bot, logs, campaign = make_env(path)
    add_user(db, 301)

    message = FakeMessage(301, bot)
    await campaign.show_intro(message, 301, "command")
    answers_after_intro = len(message.answers)

    first = await campaign.handle_callback(FakeCallback(301, CB_ROLE_FACILITATOR, message))
    after_first = len(message.answers)
    second = await campaign.handle_callback(FakeCallback(301, CB_ROLE_FACILITATOR, message))
    after_second = len(message.answers)

    consent_1 = await campaign.handle_callback(FakeCallback(301, CB_CONSENT_YES, message))
    consent_at = campaign.state(301)["consent_at"]
    consent_2 = await campaign.handle_callback(FakeCallback(301, CB_CONSENT_YES, message))

    print("Повторный callback:")
    check("первый клик по ветке обработан", first, "role_selected")
    check("первый клик добавил два сообщения", after_first - answers_after_intro, 2)
    check("второй клик распознан как повтор", second, "already_chosen")
    check("второй клик не добавил сообщений", after_second, after_first)
    check("согласие записано один раз", (consent_1, consent_2), ("consented", "already_consented"))
    check("отметка согласия не переписана", campaign.state(301)["consent_at"], consent_at)
    check("событие согласия одно", len(events_of(logs, "consent_granted")), 1)

    # Повторное «Не интересно» тоже не плодит отказов
    add_user(db, 302)
    msg = FakeMessage(302, bot)
    await campaign.show_intro(msg, 302, "command")
    d1 = await campaign.handle_callback(FakeCallback(302, CB_DISMISS, msg))
    opted_at = campaign.state(302)["opted_out_at"]
    d2 = await campaign.handle_callback(FakeCallback(302, CB_DISMISS, msg))
    check("повторное «Не интересно» распознано", (d1, d2), ("dismissed", "already_dismissed"))
    check("дата отказа не переписана", campaign.state(302)["opted_out_at"], opted_at)
    db.close()


async def scenario_followups_and_restart(path):
    """D+2 и D+5 по одному разу: повторный тик и перезапуск бота дублей не дают."""
    from modules.texts.platform import CB_ROLE_FACILITATOR

    db, bot, logs, campaign = make_env(path)
    db.set_platform_campaign_enabled("platform_launch", True, updated_by=1)
    add_user(db, 401)
    await enter_funnel(campaign, 401, CB_ROLE_FACILITATOR)

    consent_moment = datetime.now() - timedelta(days=2, hours=1)
    set_consent_at(db, 401, consent_moment)

    print("Касания D+2 и D+5:")
    # Раньше срока не уходит
    early = await campaign.process_due_followups(now=consent_moment + timedelta(days=1))
    check("до срока ничего не уходит", early["sent"], 0)

    first = await campaign.process_due_followups()
    check("D+2 отправлено", first["sent"], 1)
    check("отправлен текст про начало сессии", "Как начать сессию" in bot.sent[0]["text"], True)

    # Повторный тик в ту же минуту
    again = await campaign.process_due_followups()
    check("повторный тик дубля не даёт", again["sent"], 0)
    check("отправка по-прежнему одна", len(bot.sent), 1)

    # Перезапуск бота: новое соединение с базой и новый объект кампании
    db.close()
    db2, bot2, logs2, campaign2 = make_env(path)
    after_restart = await campaign2.process_due_followups()
    check("после рестарта D+2 не повторяется", after_restart["sent"], 0)
    check("после рестарта ничего не отправлено", bot2.sent, [])

    # Срок D+5
    d5 = await campaign2.process_due_followups(now=consent_moment + timedelta(days=5, minutes=1))
    check("D+5 отправлено", d5["sent"], 1)
    check("отправлено последнее касание", "знакомство завершаем" in bot2.sent[0]["text"], True)
    check("шагов ровно два", campaign2.state(401)["sent_step_ids"], ["d2", "d5"])

    # Третьего касания не существует даже через месяц
    extra = await campaign2.process_due_followups(now=consent_moment + timedelta(days=40))
    check("третьего касания нет", extra["sent"], 0)
    check("всего отправок за кампанию", len(bot2.sent), 1)
    check("событий доставки ровно два по кампании",
          len(events_of(logs, "followup_sent")) + len(events_of(logs2, "followup_sent")), 2)
    db2.close()


async def scenario_opt_out_stops_series(path):
    """Отписка посреди серии: второе касание уже не уходит."""
    from modules.texts.platform import CB_OPT_OUT, CB_ROLE_EXPLORER

    db, bot, logs, campaign = make_env(path)
    db.set_platform_campaign_enabled("platform_launch", True, updated_by=1)
    add_user(db, 501)
    message = await enter_funnel(campaign, 501, CB_ROLE_EXPLORER)
    consent_moment = datetime.now() - timedelta(days=2, hours=1)
    set_consent_at(db, 501, consent_moment)

    await campaign.process_due_followups()
    sent_after_d2 = len(bot.sent)

    # Нажал «Больше не присылать» под касанием
    await campaign.handle_callback(FakeCallback(501, CB_OPT_OUT, message))
    d5 = await campaign.process_due_followups(now=consent_moment + timedelta(days=6))

    print("Отписка кнопкой:")
    check("D+2 успел уйти", sent_after_d2, 1)
    check("отказ записан", campaign.state(501)["opted_out_reason"], "button")
    check("D+5 не уходит", d5["sent"], 0)
    check("больше ничего не отправлено", len(bot.sent), 1)

    # /platform_stop — то же самое, но командой
    add_user(db, 502)
    await enter_funnel(campaign, 502, CB_ROLE_EXPLORER)
    set_consent_at(db, 502, datetime.now() - timedelta(days=3))
    stop_message = FakeMessage(502, bot)
    await campaign.stop(stop_message, 502)
    after_stop = await campaign.process_due_followups()

    print("Команда /platform_stop:")
    check("отказ записан как команда", campaign.state(502)["opted_out_reason"], "command")
    check("подтверждение отправлено", "отключена" in stop_message.answers[-1]["text"], True)
    check("касания прекращены", after_stop["sent"], 0)
    db.close()


async def scenario_platform_after_optout(path):
    """
    /platform после отказа открывает экран знакомства, но подписку не возвращает:
    для этого нужен новый явный клик «Да, присылайте». Уже отправленные касания
    при этом не повторяются.
    """
    from modules.texts.platform import CB_CONSENT_YES, CB_ROLE_FACILITATOR

    db, bot, logs, campaign = make_env(path)
    db.set_platform_campaign_enabled("platform_launch", True, updated_by=1)
    add_user(db, 601)
    await enter_funnel(campaign, 601, CB_ROLE_FACILITATOR)
    consent_moment = datetime.now() - timedelta(days=2, hours=1)
    set_consent_at(db, 601, consent_moment)
    await campaign.process_due_followups()            # ушло D+2

    stop_msg = FakeMessage(601, bot)
    await campaign.stop(stop_msg, 601)

    # Повторный /platform
    again = FakeMessage(601, bot)
    await campaign.show_intro(again, 601, "command")
    state_after_platform = campaign.state(601)

    print("/platform после отказа:")
    check("экран знакомства показан", len(again.answers), 1)
    check("отказ остался в силе", bool(state_after_platform["opted_out_at"]), True)
    check("касания не возобновились",
          (await campaign.process_due_followups(now=consent_moment + timedelta(days=6)))["sent"], 0)

    # Новый явный клик: выбор ветки снова предлагает согласие, и только клик
    # «Да, присылайте» возвращает человека в серию.
    role_again = await campaign.handle_callback(FakeCallback(601, CB_ROLE_FACILITATOR, again))
    consent_again = await campaign.handle_callback(FakeCallback(601, CB_CONSENT_YES, again))
    state_after_consent = campaign.state(601)

    # Серия пересчитывается от НОВОГО согласия: касания привязаны к моменту
    # подтверждения, а не к первому сообщению.
    new_consent = datetime.fromisoformat(state_after_consent["consent_at"])
    resumed = await campaign.process_due_followups(
        now=new_consent + timedelta(days=5, minutes=1))

    check("после отказа ветку можно выбрать заново", role_again, "role_selected")
    check("повторное согласие распознано как возврат", consent_again, "resumed")
    check("новый клик снял отказ", state_after_consent["opted_out_at"], None)
    check("отправленный ранее шаг сохранён", "d2" in state_after_consent["sent_step_ids"], True)
    check("после возобновления уходит только D+5", resumed["sent"], 1)
    check("повторной серии нет", campaign.state(601)["sent_step_ids"], ["d2", "d5"])
    check("D+2 второй раз не уходит",
          sum(1 for m in bot.sent if "Как начать сессию" in m["text"]), 1)
    db.close()


async def scenario_retry_temporary_error(path):
    """Сетевой сбой: касание добивается повторами, но не бесконечно."""
    from modules.platform_campaign import MAX_SEND_ATTEMPTS
    from modules.texts.platform import CB_ROLE_FACILITATOR

    db, bot, logs, campaign = make_env(path)
    db.set_platform_campaign_enabled("platform_launch", True, updated_by=1)
    add_user(db, 701)
    await enter_funnel(campaign, 701, CB_ROLE_FACILITATOR)
    now = datetime.now()
    set_consent_at(db, 701, now - timedelta(days=2, hours=1))

    bot.error = TelegramNetworkError(method=None, message="Cannot connect to host")
    first = await campaign.process_due_followups(now=now)
    state = campaign.state(701)

    print("Временный сбой:")
    check("попытка отложена", first["deferred"], 1)
    check("шаг занят, чтобы рестарт его не повторил", state["sent_step_ids"], ["d2"])
    check("счётчик попыток в базе", state["retry_state"]["d2"]["attempts"], 1)
    check("ошибка записана", "Cannot connect" in (state["last_error"] or ""), True)
    check("неудача ещё не финальная", len(events_of(logs, "followup_failed")), 0)

    # Сеть вернулась — следующий тик добивает
    bot.error = None
    second = await campaign.process_due_followups(now=now + timedelta(minutes=5))
    check("повтор доставил касание", second["sent"], 1)
    check("отправка одна", len(bot.sent), 1)
    check("повторы сняты с очереди", campaign.state(701)["retry_state"], {})

    # Сбой, который не кончается: попытки ограничены
    add_user(db, 702)
    await enter_funnel(campaign, 702, CB_ROLE_FACILITATOR)
    set_consent_at(db, 702, now - timedelta(days=2, hours=1))
    bot.error = TelegramNetworkError(method=None, message="Cannot connect to host")
    bot.attempts = 0
    for i in range(6):
        await campaign.process_due_followups(now=now + timedelta(minutes=5 * i))
    final = campaign.state(702)

    check("попыток на шаг не больше потолка", bot.attempts, MAX_SEND_ATTEMPTS)
    check("после потолка зафиксирована неудача", len(events_of(logs, "followup_failed")), 1)
    check("повторы сняты", final["retry_state"], {})
    check("шаг остался занятым", final["sent_step_ids"], ["d2"])
    db.close()


async def scenario_blocked_user(path):
    """Блокировка бота прекращает кампанию и не считается сбоем доставки."""
    from modules.texts.platform import CB_ROLE_EXPLORER

    db, bot, logs, campaign = make_env(path)
    db.set_platform_campaign_enabled("platform_launch", True, updated_by=1)
    add_user(db, 801)
    await enter_funnel(campaign, 801, CB_ROLE_EXPLORER)
    now = datetime.now()
    set_consent_at(db, 801, now - timedelta(days=2, hours=1))

    bot.error = TelegramForbiddenError(method=None, message="Forbidden: bot was blocked by the user")
    result = await campaign.process_due_followups(now=now)
    state = campaign.state(801)

    print("Блокировка бота:")
    check("отправка признана неудачной", result["failed"], 1)
    check("повторов не планируется", state["retry_state"], {})
    check("человек снят с кампании", state["opted_out_reason"], "blocked")

    bot.error = None
    rest = await campaign.process_due_followups(now=now + timedelta(days=4))
    check("D+5 заблокировавшему не уходит", rest["sent"], 0)

    # Тот, кто уже известен как заблокировавший, в проход не попадает вовсе
    add_user(db, 802)
    await enter_funnel(campaign, 802, CB_ROLE_EXPLORER)
    set_consent_at(db, 802, now - timedelta(days=2, hours=1))
    db.conn.execute(
        "INSERT INTO mailing_logs (mailing_id, user_id, status, error_message, sent_at)"
        " VALUES (1, 802, 'blocked', 'Forbidden: bot was blocked by the user', ?)",
        (now.strftime("%Y-%m-%d %H:%M:%S"),))
    db.conn.commit()
    skipped = await campaign.process_due_followups(now=now)
    check("известный недоступным пропущен без отправки", skipped["skipped"], 1)
    check("ему ничего не отправлено", bot.sent, [])
    check("и он снят с кампании", campaign.state(802)["opted_out_reason"], "blocked")
    db.close()


async def scenario_stale_step(path):
    """Долгий простой бота: просроченное касание не уходит задним числом."""
    from modules.texts.platform import CB_ROLE_FACILITATOR

    db, bot, logs, campaign = make_env(path)
    db.set_platform_campaign_enabled("platform_launch", True, updated_by=1)
    add_user(db, 901)
    await enter_funnel(campaign, 901, CB_ROLE_FACILITATOR)
    # Согласие было месяц назад: оба касания давно просрочены
    set_consent_at(db, 901, datetime.now() - timedelta(days=30))

    result = await campaign.process_due_followups()
    state = campaign.state(901)

    print("Просроченные касания:")
    check("ничего не отправлено", bot.sent, [])
    check("оба шага помечены пропущенными", result["skipped"], 2)
    check("шаги заняты, чтобы не выстрелить позже", state["sent_step_ids"], ["d2", "d5"])
    check("пропуск зафиксирован в аналитике",
          events_of(logs, "followup_skipped")[0]["details"]["reason"], "stale")
    db.close()


async def scenario_audience_dedup(path):
    """Пересечения сегментов в оценке аудитории считаются один раз."""
    db, bot, logs, campaign = make_env(path)

    now = datetime.now()
    # Пользователь 1001 — ядро «Карты дня» И прошёл тест автора: пересечение
    for user_id, days_with_card in ((1001, 3), (1002, 1)):
        add_user(db, user_id)
        for day in range(days_with_card):
            db.conn.execute(
                "INSERT INTO scenario_logs (user_id, scenario, step, timestamp)"
                " VALUES (?, 'card_of_day', 'card_drawn', ?)",
                (user_id, (now - timedelta(days=day)).isoformat()))
        db.conn.execute(
            "INSERT INTO actions (user_id, username, name, action, details, timestamp)"
            " VALUES (?, '', '', 'card_drawn', '{}', ?)", (user_id, now.isoformat()))
    add_user(db, 1003)
    for user_id in (1001, 1003):
        db.conn.execute(
            "INSERT OR REPLACE INTO author_test_sessions_new (user_id, status, completed_at)"
            " VALUES (?, 'completed', ?)", (user_id, now.isoformat()))
    db.conn.commit()

    from modules.admin.user_segments import get_author_test_candidates
    candidates = get_author_test_candidates(db)
    data = campaign.estimate_audience()
    by_segment = {row["segment"]: row for row in data["groups"]}

    print("Оценка аудитории:")
    check("кандидаты по тесту автора найдены", candidates, [1001, 1003])
    check("в тесте автора двое", by_segment["author_test"]["total"], 2)
    check("пересечение с сегментами снято", by_segment["author_test"]["unique"], 1)
    check("всего уникальных трое", data["total"], 3)
    check("сумма уникальных равна итогу",
          sum(r["unique"] for r in data["groups"]), data["total"])
    db.close()


async def scenario_admin_screens(path):
    """
    Админские экраны собираются и ничего не отправляют пользователям.
    Текста много, и ошибка форматирования не должна выясняться в бою.
    """
    import config
    from modules.admin.platform_campaign import route_platform_callback
    from modules.texts.platform import CB_ROLE_FACILITATOR

    db, bot, logs, campaign = make_env(path)
    add_user(db, 1101)
    await enter_funnel(campaign, 1101, CB_ROLE_FACILITATOR)
    set_consent_at(db, 1101, datetime.now() - timedelta(days=3))

    admin_id = 9001
    original_admins = config.ADMIN_IDS
    config.ADMIN_IDS = [str(admin_id)]
    try:
        print("Админские экраны:")
        for action in ("admin_platform", "admin_platform_report", "admin_platform_audience",
                       "admin_platform_preview", "admin_platform_dryrun",
                       "admin_platform_test", "admin_platform_enable"):
            message = FakeMessage(admin_id, bot)
            handled = await route_platform_callback(action, message, db, logs, admin_id)
            check(f"{action} отработал", handled and bool(message.answers), True)

        check("незнакомый callback не наш",
              await route_platform_callback("admin_platform_nope", FakeMessage(admin_id, bot),
                                            db, logs, admin_id), False)

        # Тестовая отправка ушла только самому админу
        check("тестовые сообщения ушли только админу",
              {m["chat_id"] for m in bot.sent}, {admin_id})

        # Включение требует подтверждения: экран «Включить» ничего не включает
        check("кнопка «Включить» сама не включает",
              db.is_platform_campaign_enabled("platform_launch"), False)
        await route_platform_callback("admin_platform_enable_confirm",
                                      FakeMessage(admin_id, bot), db, logs, admin_id)
        check("подтверждение включает кампанию",
              db.is_platform_campaign_enabled("platform_launch"), True)
        await route_platform_callback("admin_platform_pause",
                                      FakeMessage(admin_id, bot), db, logs, admin_id)
        check("пауза выключает кампанию",
              db.is_platform_campaign_enabled("platform_launch"), False)

        # Не админ не должен увидеть ничего
        outsider = FakeMessage(5555, bot)
        await route_platform_callback("admin_platform_report", outsider, db, logs, 5555)
        check("посторонний получает отказ",
              "ДОСТУП ЗАПРЕЩЕН" in outsider.answers[-1]["text"], True)
    finally:
        config.ADMIN_IDS = original_admins
    db.close()


def scenario_links_have_no_personal_data():
    """В ссылках только UTM-метки: ни Telegram ID, ни имён."""
    from modules.texts.platform import (
        PLATFORM_TEXTS, PLATFORM_URL, UTM_CONTENTS, platform_url,
    )

    print("Ссылки и UTM:")
    for content in UTM_CONTENTS:
        url = platform_url(content)
        check(f"ссылка {content} ведёт на платформу", url.startswith(PLATFORM_URL), True)
        check(f"ссылка {content} несёт только метки",
              sorted(part.split("=")[0] for part in url.split("?")[1].split("&")),
              ["utm_campaign", "utm_content", "utm_medium", "utm_source"])

    bad = None
    try:
        platform_url("user_12345")
    except ValueError:
        bad = "rejected"
    check("произвольная метка отклоняется", bad, "rejected")

    # Ни один экран не ссылается на промежуточные адреса (например, GitHub)
    hosts = {PLATFORM_TEXTS[k]["cta"]["utm_content"] for k in PLATFORM_TEXTS
             if PLATFORM_TEXTS[k].get("cta")}
    check("все CTA используют согласованные метки", hosts <= set(UTM_CONTENTS), True)


# ------------------------------------------------------------------------- запуск

async def run_all():
    scenarios = [
        scenario_opt_in_flow,
        scenario_kill_switch,
        scenario_no_consent,
        scenario_repeat_callbacks,
        scenario_followups_and_restart,
        scenario_opt_out_stops_series,
        scenario_platform_after_optout,
        scenario_retry_temporary_error,
        scenario_blocked_user,
        scenario_stale_step,
        scenario_audience_dedup,
        scenario_admin_screens,
    ]
    for scenario in scenarios:
        # Каждому сценарию — своя база: состояние кампании не должно протекать
        # между проверками.
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "bot.db")
        await scenario(path)
        print()

    scenario_links_have_no_personal_data()
    print()


def main():
    asyncio.run(run_all())
    if failures:
        print(f"ПАДЕНИЙ: {len(failures)} — {', '.join(failures)}")
        return 1
    print("Все проверки пройдены.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
