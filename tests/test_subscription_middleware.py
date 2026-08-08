"""
Регрессионный тест порядка проверок в SubscriptionMiddleware.

Запуск:  python tests/test_subscription_middleware.py
Код возврата 0 — все проверки пройдены, 1 — есть падения.

Дополнительного тестового стека не требует: только стандартная библиотека и aiogram,
который и так в зависимостях. Класс берётся из живого main.py разбором AST, поэтому
проверяется реальный код, а не его копия, — импортировать main.py целиком нельзя,
он на импорте создаёт Bot и подключается к базе.

Что защищаем:
  * подписка не турникет — при любой ошибке пользователь проходит дальше (fail-open);
  * обращение к Telegram не чаще раза в сутки на человека;
  * на callback'ах к Telegram не ходим вовсе и НЕ отмечаем проверку сделанной,
    иначе нажатие кнопки «съест» приглашение для следующего сообщения.
"""
import ast
import asyncio
import io
import logging
import os
import sys
from datetime import datetime, date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aiogram import types  # noqa: E402

logging.disable(logging.CRITICAL)

SRC = io.open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
CLS = next(
    n for n in ast.parse(SRC).body
    if isinstance(n, ast.ClassDef) and n.name == "SubscriptionMiddleware"
)

state = {"api_calls": 0, "invites": 0, "handler_calls": 0, "status": "left", "raise": False}


class FakeBot:
    async def get_chat_member(self, chat_id, user_id):
        state["api_calls"] += 1
        if state["raise"]:
            raise RuntimeError("network down")
        return type("S", (), {"status": state["status"]})()


class FakeDB:
    def __init__(self, completed=True):
        self.completed = completed

    def has_completed_scenario_first_time(self, uid, scenario):
        return self.completed

    def get_user(self, uid):
        return {"name": "Катя", "username": "kate"}

    def save_action(self, *args):
        pass


class QuietLogger:
    def warning(self, *a, **k): pass
    def error(self, *a, **k): pass
    def info(self, *a, **k): pass


async def fake_answer(self, text, **kwargs):
    state["invites"] += 1


async def handler(event, data):
    state["handler_calls"] += 1
    return "handled"


def build():
    """Собирает middleware из исходника main.py с подменёнными зависимостями."""
    ns = {
        "types": types,
        "ADMIN_IDS": ["999"],
        "logger": QuietLogger(),
        "datetime": datetime,
        "date": date,
        "TIMEZONE": None,
        "bot": FakeBot(),
        "CHANNEL_ID": "@ch",
    }
    exec(ast.get_source_segment(SRC, CLS), ns)
    mw = ns["SubscriptionMiddleware"]()
    mw._checked_on.clear()
    return mw


USER = types.User(id=1, is_bot=False, first_name="T", username="t")
ADMIN = types.User(id=999, is_bot=False, first_name="A")
CHAT = types.Chat(id=1, type="private")


def msg(user=USER):
    return types.Message(message_id=1, date=datetime.now(), chat=CHAT, from_user=user)


def cb(user=USER):
    return types.CallbackQuery(id="1", from_user=user, chat_instance="ci", data="x")


def reset(**kwargs):
    state.update({"api_calls": 0, "invites": 0, "handler_calls": 0, "status": "left", "raise": False})
    state.update(kwargs)


def check(label, condition, detail):
    print(f'  [{"OK  " if condition else "FAIL"}] {label}: {detail}')
    return condition


async def run_all():
    types.Message.answer = fake_answer
    ok = True

    reset()
    mw = build()
    for _ in range(5):
        await mw(handler, cb(), {"db": FakeDB()})
    ok &= check("callback ×5 — Telegram не дёргаем",
                state["api_calls"] == 0 and state["handler_calls"] == 5,
                f'api={state["api_calls"]} handler={state["handler_calls"]}')

    reset()
    mw = build()
    for _ in range(5):
        await mw(handler, msg(), {"db": FakeDB()})
    ok &= check("message ×5 за день — максимум 1 запрос",
                state["api_calls"] == 1 and state["invites"] == 1,
                f'api={state["api_calls"]} invites={state["invites"]}')

    reset(raise_=True)
    state["raise"] = True
    mw = build()
    for _ in range(4):
        await mw(handler, msg(), {"db": FakeDB()})
    ok &= check("сетевая ошибка — fail-open, 1 попытка в день",
                state["api_calls"] == 1 and state["handler_calls"] == 4,
                f'api={state["api_calls"]} handler={state["handler_calls"]}')

    reset(status="left")
    mw = build()
    for _ in range(3):
        await mw(handler, msg(), {"db": FakeDB()})
    ok &= check("неподписанный — приглашение раз в сутки",
                state["invites"] == 1, f'invites={state["invites"]}')

    reset(status="member")
    mw = build()
    for _ in range(3):
        await mw(handler, msg(), {"db": FakeDB()})
    ok &= check("подписанный — приглашения нет",
                state["invites"] == 0 and state["api_calls"] == 1,
                f'invites={state["invites"]} api={state["api_calls"]}')

    reset(status="left")
    mw = build()
    for _ in range(10):
        await mw(handler, cb(), {"db": FakeDB()})
    await mw(handler, msg(), {"db": FakeDB()})
    ok &= check("callback'и не съедают приглашение",
                state["invites"] == 1 and state["api_calls"] == 1,
                f'после 10 callback\'ов message получил invites={state["invites"]}')

    reset()
    mw = build()
    await mw(handler, msg(ADMIN), {"db": FakeDB()})
    ok &= check("админ — без запросов",
                state["api_calls"] == 0 and state["handler_calls"] == 1,
                f'api={state["api_calls"]}')

    reset()
    mw = build()
    await mw(handler, msg(), {"db": FakeDB(completed=False)})
    ok &= check("не завершал card_of_day — без запросов",
                state["api_calls"] == 0 and state["handler_calls"] == 1,
                f'api={state["api_calls"]}')

    reset(status="left")
    mw = build()
    await mw(handler, msg(), {"db": FakeDB()})
    mw._checked_on[1] = date.today() - timedelta(days=1)
    await mw(handler, msg(), {"db": FakeDB()})
    ok &= check("новый день — проверка повторяется",
                state["api_calls"] == 2, f'api={state["api_calls"]}')

    print("\nИТОГ:", "все проверки пройдены" if ok else "ЕСТЬ ПАДЕНИЯ")
    return ok


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(run_all()) else 1)
