"""
Регрессионный тест дозвона напоминаний при сетевых сбоях.

Запуск:  python tests/test_reminder_retry.py
Код возврата 0 — все проверки пройдены, 1 — есть падения.

Воспроизводит реальный случай 11.08.2026: сеть контейнера лежала час
(10:00:31–11:01:51), и 47 напоминаний из 56 не ушли вообще. Повторов тогда не было,
человек просто оставался без напоминания, а в статистике это выглядело как провал.

Что защищаем:
  * временный сбой не теряет напоминание — оно уходит, когда сеть вернулась;
  * блокировка повторов не вызывает: человек не станет доступнее от второй попытки;
  * на одно напоминание приходится ровно одна запись в базе, иначе статистика
    доставки посчитает его несколько раз;
  * если сеть не вернулась за отведённое окно, неудача фиксируется явно;
  * повторы не выполняются подряд внутри одного прохода, иначе сбой у первых
    адресатов задерживал бы напоминания всем остальным.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aiogram.exceptions import TelegramNetworkError, TelegramForbiddenError  # noqa: E402

failures = []


def check(name, actual, expected):
    if actual == expected:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}: ожидалось {expected}, получено {actual}")
        failures.append(name)


class FakeBot:
    """Бот, который ведёт себя так, как ему велит сценарий теста."""

    def __init__(self):
        self.error = None          # что бросать на отправку
        self.delivered = []        # кому реально ушло

    async def send_message(self, user_id, text, **kwargs):
        if self.error is not None:
            raise self.error
        self.delivered.append(user_id)


class FakeDB:
    def __init__(self):
        self.actions = []
        self.card_available = True     # не вытянул ли человек карту сам

    def save_action(self, user_id, username, name, action, details, timestamp):
        self.actions.append({"user_id": user_id, "action": action, "details": details})

    def get_user(self, user_id):
        return {"name": "Тест"}

    def is_card_available(self, user_id, day):
        return self.card_available


def build_service():
    import modules.notification_service as ns

    async def fake_menu(user_id, db):
        return None

    ns.get_main_menu = fake_menu                      # клавиатура тут ни при чём
    bot, db = FakeBot(), FakeDB()
    return ns, ns.NotificationService(bot, db), bot, db


def logs_for(db, user_id):
    return [a["details"] for a in db.actions if a["user_id"] == user_id]


async def scenario_outage_then_recovery():
    """Сеть лежит полчаса, потом возвращается: напоминание должно дойти."""
    ns, svc, bot, db = build_service()
    t0 = datetime(2026, 8, 11, 11, 0)

    bot.error = TelegramNetworkError(method=None, message="Cannot connect to host")
    await svc._send_reminder(101, "morning", "текст", t0)

    check("во время сбоя запись не делается", logs_for(db, 101), [])
    check("напоминание встало в очередь", len(svc._pending), 1)

    for minute in range(1, 30):                       # сеть всё ещё лежит
        await svc._flush_pending(t0 + timedelta(minutes=minute))
    check("за время сбоя записей всё ещё нет", logs_for(db, 101), [])
    check("напоминание не потеряно", len(svc._pending), 1)

    bot.error = None                                  # сеть вернулась
    await svc._flush_pending(t0 + timedelta(minutes=30))

    check("напоминание доставлено", bot.delivered, [101])
    check("очередь опустела", len(svc._pending), 0)
    logs = logs_for(db, 101)
    check("ровно одна запись на напоминание", len(logs), 1)
    check("записан успех", logs[0]["status"], "sent")
    check("зафиксирована задержка", logs[0]["delayed_minutes"], 30)
    check("зафиксировано число попыток", logs[0]["attempts"] > 1, True)


async def scenario_permanent_error():
    """Заблокировавший бота: повторять нечего, фиксируем сразу."""
    ns, svc, bot, db = build_service()
    t0 = datetime(2026, 8, 11, 11, 0)

    bot.error = TelegramForbiddenError(method=None, message="Forbidden: bot was blocked by the user")
    await svc._send_reminder(102, "morning", "текст", t0)

    check("в очередь не попал", len(svc._pending), 0)
    logs = logs_for(db, 102)
    check("ровно одна запись", len(logs), 1)
    check("записана неудача", logs[0]["status"], "failed")
    check("причина сохранена", "Forbidden" in logs[0]["error"], True)


async def scenario_gives_up():
    """Сеть не вернулась за отведённое окно — неудачу надо признать явно."""
    ns, svc, bot, db = build_service()
    t0 = datetime(2026, 8, 11, 11, 0)

    bot.error = TelegramNetworkError(method=None, message="Cannot connect to host")
    await svc._send_reminder(103, "morning", "текст", t0)
    await svc._flush_pending(t0 + timedelta(minutes=ns.RETRY_WINDOW_MINUTES + 1))

    check("очередь очищена", len(svc._pending), 0)
    logs = logs_for(db, 103)
    check("ровно одна запись", len(logs), 1)
    check("записана неудача", logs[0]["status"], "failed")
    check("видно, сколько пытались", logs[0]["delayed_minutes"] > 0, True)


async def scenario_one_slow_does_not_block_others():
    """Сбой у первого адресата не должен задерживать остальных в той же пачке."""
    ns, svc, bot, db = build_service()
    t0 = datetime(2026, 8, 11, 11, 0)

    bot.error = TelegramNetworkError(method=None, message="Cannot connect to host")
    await svc._send_reminder(201, "morning", "текст", t0)
    bot.error = None
    await svc._send_reminder(202, "morning", "текст", t0)
    await svc._send_reminder(203, "morning", "текст", t0)

    check("остальные получили сразу", bot.delivered, [202, 203])
    check("сбойный ждёт своей очереди", len(svc._pending), 1)


async def scenario_no_duplicate_queue():
    """Один и тот же адресат не должен встать в очередь дважды за день."""
    ns, svc, bot, db = build_service()
    t0 = datetime(2026, 8, 11, 11, 0)

    bot.error = TelegramNetworkError(method=None, message="Cannot connect to host")
    await svc._send_reminder(301, "morning", "текст", t0)
    await svc._send_reminder(301, "morning", "текст", t0 + timedelta(seconds=30))
    check("в очереди одна запись", len(svc._pending), 1)

    await svc._send_reminder(301, "evening", "текст", t0)
    check("вечернее — отдельная запись", len(svc._pending), 2)


async def scenario_card_drawn_meanwhile():
    """Пока напоминание ждало сети, человек сам вытянул карту — звать его не надо."""
    ns, svc, bot, db = build_service()
    t0 = datetime(2026, 8, 11, 11, 0)

    bot.error = TelegramNetworkError(method=None, message="Cannot connect to host")
    await svc._send_reminder(401, "morning", "текст", t0)
    check("напоминание ждёт повтора", len(svc._pending), 1)

    db.card_available = False                         # карта вытянута вручную
    bot.error = None
    await svc._flush_pending(t0 + timedelta(minutes=15))

    check("запоздалое напоминание не ушло", bot.delivered, [])
    check("снято с очереди", len(svc._pending), 0)
    check("лишней записи в базе нет", logs_for(db, 401), [])


async def scenario_evening_ignores_card():
    """Вечернее напоминание к карте отношения не имеет — его снимать нельзя."""
    ns, svc, bot, db = build_service()
    t0 = datetime(2026, 8, 11, 21, 0)

    bot.error = TelegramNetworkError(method=None, message="Cannot connect to host")
    await svc._send_reminder(402, "evening", "текст", t0)
    db.card_available = False
    bot.error = None
    await svc._flush_pending(t0 + timedelta(minutes=5))

    check("вечернее доставлено", bot.delivered, [402])


def main():
    for name, scenario in (
        ("Сбой сети, затем восстановление:", scenario_outage_then_recovery),
        ("Постоянная ошибка (блокировка):", scenario_permanent_error),
        ("Сеть не вернулась за окно:", scenario_gives_up),
        ("Сбой одного не тормозит пачку:", scenario_one_slow_does_not_block_others),
        ("Защита от двойной постановки:", scenario_no_duplicate_queue),
        ("Карта вытянута, пока ждали сети:", scenario_card_drawn_meanwhile),
        ("Вечернее не зависит от карты:", scenario_evening_ignores_card),
    ):
        print(name)
        asyncio.run(scenario())

    print()
    if failures:
        print(f"ПАДЕНИЙ: {len(failures)} — {', '.join(failures)}")
        return 1
    print("Все проверки пройдены.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
