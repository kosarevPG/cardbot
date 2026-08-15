"""
Регрессионный тест отбора получателей рассылки по сегменту.

Запуск:  python tests/test_segment_recipients.py
Код возврата 0 — все проверки пройдены, 1 — есть падения.

Работает на временной базе, созданной с нуля, — боевые данные не нужны.

Что защищаем:
  * заблокировавшие бота не попадают в рассылку и не портят статистику доставки;
  * признак блокировки берётся из обоих журналов — рассылок и напоминаний;
  * время в этих журналах хранится в разных форматах ('2025-12-02 10:17:41' против
    '2026-08-08T19:00:39+03:00'), и сравнение на свежесть обязано это переживать;
  * побеждает самый свежий сигнал: разблокировавший бота возвращается в рассылку.
"""
import os
import sqlite3
import sys
import tempfile
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


class FakeDB:
    """Минимальная база с двумя журналами — только то, что читает проверяемый метод."""

    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.executescript("""
            CREATE TABLE mailing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, mailing_id INTEGER,
                user_id INTEGER, status TEXT, error_message TEXT, sent_at TEXT);
            CREATE TABLE actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                action TEXT, details TEXT, timestamp TEXT);
        """)

    def mailing(self, user_id, status, when, error=None):
        # Формат журнала рассылок: без 'T' и без часового пояса.
        self.conn.execute(
            "INSERT INTO mailing_logs (mailing_id, user_id, status, error_message, sent_at)"
            " VALUES (1, ?, ?, ?, ?)",
            (user_id, status, error, when.strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()

    def reminder(self, user_id, ok, when):
        # Формат журнала действий: ISO с 'T' и смещением часового пояса.
        details = ('{"kind": "morning", "status": "sent"}' if ok else
                   '{"kind": "morning", "status": "failed",'
                   ' "error": "Forbidden: bot was blocked by the user"}')
        self.conn.execute(
            "INSERT INTO actions (user_id, action, details, timestamp)"
            " VALUES (?, 'reminder_sent', ?, ?)",
            (user_id, details, when.strftime("%Y-%m-%dT%H:%M:%S.%f+03:00")))
        self.conn.commit()


def main():
    from database.db import Database

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = FakeDB(path)
        # Метод не трогает состояние объекта, поэтому проверяем реальный код
        # на подставной базе, не поднимая всю настоящую.
        db.get_unreachable_user_ids = Database.get_unreachable_user_ids.__get__(db)

        long_ago = datetime(2025, 12, 2, 10, 17, 41)
        yesterday = datetime.now() - timedelta(days=1)
        today = datetime.now()

        db.mailing(101, "sent", long_ago)                      # всё хорошо
        db.mailing(102, "blocked", long_ago, "Forbidden: bot was blocked by the user")
        db.mailing(103, "failed", long_ago, "Timed out")       # разовый сбой, не блокировка
        db.mailing(104, "sent", long_ago)                      # заблокирует позже
        db.mailing(105, "blocked", long_ago, "Forbidden: user is deactivated")
        db.reminder(105, ok=True, when=today)                  # аккаунт ожил
        db.reminder(104, ok=False, when=yesterday)             # свежая блокировка
        db.reminder(106, ok=False, when=yesterday)             # известен только по напоминаниям

        unreachable = db.get_unreachable_user_ids()

        print("Признак недоступности:")
        check("успешная доставка — доступен", 101 in unreachable, False)
        check("блокировка в рассылке — недоступен", 102 in unreachable, True)
        check("сетевой сбой блокировкой не считается", 103 in unreachable, False)
        check("блокировка видна только из напоминаний", 106 in unreachable, True)

        print("Побеждает самый свежий сигнал (форматы времени разные):")
        check("успех в рассылке, потом блокировка", 104 in unreachable, True)
        check("блокировка, потом успешное напоминание", 105 in unreachable, False)

        print("Отбор получателей сегмента:")
        members = [101, 102, 103, 104, 105, 106]
        recipients = [uid for uid in members if uid not in unreachable]
        check("в рассылку уходят только достижимые", recipients, [101, 103, 105])
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

    print()
    if failures:
        print(f"ПАДЕНИЙ: {len(failures)} — {', '.join(failures)}")
        return 1
    print("Все проверки пройдены.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
