"""
Регрессионный тест расписания цикла напоминаний.

Запуск:  python tests/test_reminder_schedule.py
Код возврата 0 — все проверки пройдены, 1 — есть падения.

Закрывает баг, найденный по логам Amvera 18.08.2026: цикл спал фиксированные
60 секунд ПОСЛЕ работы, поэтому к периоду добавлялось время самой работы. Замеренный
период — 60.58 с. Тик медленно уползал вперёд и раз в несколько часов перепрыгивал
через минутную границу, а совпадение ищется по строке "%H:%M" — значит перепрыгнутой
минуты для бота не существовало. Назначенные на неё напоминания пропадали молча,
без единой ошибки в логе. За сутки так терялось около шести минут.

Что защищаем:
  * пропущенная минута обрабатывается следом, а не теряется;
  * пробуждение внутри уже обработанной минуты не рассылает ничего повторно;
  * после долгого простоя догон не превращается в пачку несвоевременных напоминаний;
  * имя запрашивается только у тех, кому реально пора слать: раньше цикл дёргал базу
    на каждого адресата каждую минуту, и именно это раскачивало период.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

failures = []


def check(name, actual, expected):
    if actual == expected:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}: ожидалось {expected}, получено {actual}")
        failures.append(name)


class FakeBot:
    def __init__(self):
        self.delivered = []

    async def send_message(self, user_id, text, **kwargs):
        self.delivered.append(user_id)


class FakeDB:
    """Полсотни адресатов, из них лишь у одного напоминание на проверяемую минуту."""

    def __init__(self, times):
        self.times = times
        self.get_user_calls = 0

    def get_reminder_times(self):
        return self.times

    def get_user(self, user_id):
        self.get_user_calls += 1
        return {"name": "Тест"}

    def is_card_available(self, user_id, day):
        return True

    def save_action(self, *args):
        pass


def build(times):
    import modules.notification_service as ns

    async def fake_menu(user_id, db):
        return None

    ns.get_main_menu = fake_menu
    bot, db = FakeBot(), FakeDB(times)
    return ns, ns.NotificationService(bot, db), bot, db


def minute(h, m):
    return datetime(2026, 8, 19, h, m)


def scenario_sleep_alignment():
    """Сон считается до границы минуты, а не фиксированные 60 секунд."""
    ns, svc, bot, db = build({})
    off = ns.TICK_OFFSET_SECONDS

    check("проснулись в начале минуты — спим почти всю её",
          round(svc._seconds_until_next_minute(datetime(2026, 8, 19, 11, 0, 0)), 2),
          round(60 + off, 2))

    check("работа заняла 25 с — спим остаток, а не ещё минуту",
          round(svc._seconds_until_next_minute(datetime(2026, 8, 19, 11, 0, 25)), 2),
          round(35 + off, 2))

    # Главное: период не накапливается. Каждый следующий тик считается от часов,
    # поэтому сколько бы ни заняла работа, просыпаемся в начале очередной минуты.
    # Порядок как в цикле: сначала работа, потом сон до границы следующей минуты.
    now = datetime(2026, 8, 19, 11, 0, 0) + timedelta(seconds=off)
    starts = []
    for _ in range(60):
        starts.append(now)
        now = now + timedelta(seconds=12.7)                       # работа заняла 12.7 с
        now = now + timedelta(seconds=svc._seconds_until_next_minute(now))
    span = (starts[-1] - starts[0]).total_seconds()
    check("за 60 тиков ровно 59 минут, дрейфа нет", round(span, 1), 59 * 60.0)
    check("все тики в разных минутах", len({s.strftime("%H:%M") for s in starts}), 60)


def scenario_minute_selection():
    ns, svc, bot, db = build({})
    limit = ns.CATCHUP_LIMIT_MINUTES

    check("первый запуск — только текущая минута",
          svc._minutes_to_process(None, minute(11, 0)), [minute(11, 0)])

    check("обычный ход — следующая минута",
          svc._minutes_to_process(minute(11, 0), minute(11, 1)), [minute(11, 1)])

    check("минута перепрыгнута — обрабатываем обе",
          svc._minutes_to_process(minute(10, 59), minute(11, 1)),
          [minute(11, 0), minute(11, 1)])

    check("проснулись в той же минуте — не шлём повторно",
          svc._minutes_to_process(minute(11, 0), minute(11, 0)), [])

    check("часы сдвинулись назад — ничего не шлём",
          svc._minutes_to_process(minute(11, 5), minute(11, 2)), [])

    check("догон на границе допустимого",
          len(svc._minutes_to_process(minute(11, 0), minute(11, 0) + timedelta(minutes=limit))),
          limit)

    check("после долгого простоя догон не делается",
          svc._minutes_to_process(minute(11, 0), minute(11, 0) + timedelta(minutes=limit + 1)),
          [minute(11, 0) + timedelta(minutes=limit + 1)])


async def scenario_skipped_minute_still_sends():
    """Напоминание, назначенное на перепрыгнутую минуту, всё равно уходит."""
    ns, svc, bot, db = build({777: {"morning": "11:00", "evening": None}})

    for moment in svc._minutes_to_process(minute(10, 59), minute(11, 1)):
        await svc._process_minute(moment)

    check("напоминание на пропущенную минуту доставлено", bot.delivered, [777])


async def scenario_no_pointless_db_calls():
    """Цикл не должен ходить в базу за именем каждого адресата каждую минуту."""
    times = {uid: {"morning": "11:00", "evening": None} for uid in range(1, 51)}
    times[42] = {"morning": "09:30", "evening": None}     # единственный на 09:30
    ns, svc, bot, db = build(times)

    await svc._process_minute(minute(9, 30))

    check("имя запрошено только у адресата минуты", db.get_user_calls, 1)
    check("отправлено только ему", bot.delivered, [42])


def main():
    print("Выравнивание сна по минуте:")
    scenario_sleep_alignment()
    print("Выбор минут для обработки:")
    scenario_minute_selection()
    print("Пропущенная минута:")
    asyncio.run(scenario_skipped_minute_still_sends())
    print("Лишние запросы к базе:")
    asyncio.run(scenario_no_pointless_db_calls())

    print()
    if failures:
        print(f"ПАДЕНИЙ: {len(failures)} — {', '.join(failures)}")
        return 1
    print("Все проверки пройдены.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
