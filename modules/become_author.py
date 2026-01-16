# modules/become_author.py
import logging

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.db import Database

logger = logging.getLogger(__name__)


class AuthorTestStates(StatesGroup):
    answering = State()


# Минимальный каркас на 2 вопроса (без БД-схемы расширений).
# На Шаге 4 заменим на полный опросник.
QUESTIONS = [
    {
        "text": "Я хочу создать свой авторский продукт (МАК/Т-игра) в ближайшие 2–3 месяца.",
        "options": [
            ("Да", 2),
            ("Скорее да", 1),
            ("Скорее нет", 0),
            ("Нет", 0),
        ],
    },
    {
        "text": "Я готов(а) уделять этому минимум 2–3 часа в неделю.",
        "options": [
            ("Да", 2),
            ("Скорее да", 1),
            ("Скорее нет", 0),
            ("Нет", 0),
        ],
    },
]


def _progress(step: int) -> str:
    return f"Вопрос {step + 1}/{len(QUESTIONS)}"


def _build_question_kb(step: int) -> InlineKeyboardMarkup:
    q = QUESTIONS[step]
    rows = []
    for opt_text, opt_score in q["options"]:
        rows.append([
            InlineKeyboardButton(text=opt_text, callback_data=f"author_ans:{step}:{opt_score}"),
        ])
    rows.append([InlineKeyboardButton(text="Отмена", callback_data="author_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def start_author_test_flow(message: types.Message, state: FSMContext, db: Database) -> None:
    """Точка входа: если есть незавершённая сессия — предлагает продолжить/перезапустить."""
    user_id = message.from_user.id

    session = db.get_author_test_session(user_id)
    if session and session.get("status") == "in_progress" and int(session.get("current_step", 0)) > 0:
        total = len(QUESTIONS)
        step = int(session.get("current_step", 0))
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data="author_resume")],
            [InlineKeyboardButton(text="🔄 Начать заново", callback_data="author_restart")],
            [InlineKeyboardButton(text="Отмена", callback_data="author_cancel")],
        ])
        await message.answer(
            f"Вы не закончили прошлый тест (остановились на вопросе {min(step + 1, total)}/{total}). Продолжить?",
            reply_markup=kb,
        )
        return

    await _start_new_test(message, state, db)


async def _start_new_test(message: types.Message, state: FSMContext, db: Database) -> None:
    user_id = message.from_user.id
    db.reset_author_test(user_id)

    await state.clear()
    await state.set_state(AuthorTestStates.answering)
    await state.update_data(step=0, answers={}, score=0)
    await send_current_question(message, state)


async def _resume_test(message: types.Message, state: FSMContext, db: Database) -> None:
    user_id = message.from_user.id
    session = db.get_author_test_session(user_id)
    if not session or session.get("status") != "in_progress":
        await _start_new_test(message, state, db)
        return

    step = int(session.get("current_step", 0))
    answers = session.get("answers") or {}
    ready_total = int(session.get("ready_total", 0))

    await state.clear()
    await state.set_state(AuthorTestStates.answering)
    await state.update_data(step=step, answers=answers, score=ready_total)

    # Если уже за пределами вопросов — считаем завершенным
    if step >= len(QUESTIONS):
        await finish_author_test(message, state, db)
        return

    await send_current_question(message, state)


async def send_current_question(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    step = int(data.get("step", 0))

    if step >= len(QUESTIONS):
        # В обычном потоке завершение делает handle_author_callback
        return

    q = QUESTIONS[step]
    text = (
        "<b>Диагностика «Стать автором»</b>\n"
        + _progress(step)
        + "\n\n"
        + q["text"]
    )
    kb = _build_question_kb(step)

    try:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


async def handle_author_callback(callback: types.CallbackQuery, state: FSMContext, db: Database) -> str:
    """Обрабатывает callback-и теста.

    Возвращает статус: continue | finished | cancelled | ignored
    """

    if not callback.data:
        return "ignored"

    user_id = callback.from_user.id

    if callback.data == "author_cancel":
        await state.clear()
        await callback.answer("Ок, отменил(а).")
        return "cancelled"

    if callback.data == "author_restart":
        await callback.answer()
        await _start_new_test(callback.message, state, db)
        return "continue"

    if callback.data == "author_resume":
        await callback.answer()
        await _resume_test(callback.message, state, db)
        return "continue"

    if callback.data.startswith("author_ans:"):
        try:
            _, step_s, score_s = callback.data.split(":", 2)
            step = int(step_s)
            score = int(score_s)
        except Exception:
            await callback.answer("Не понял ответ, попробуйте ещё раз.", show_alert=True)
            return "ignored"

        data = await state.get_data()
        cur_step = int(data.get("step", 0))
        if step != cur_step:
            await callback.answer()
            return "ignored"

        answers = dict(data.get("answers", {}) or {})
        answers[str(step)] = score
        total = int(data.get("score", 0)) + score

        next_step = cur_step + 1

        # Сохраняем прогресс в БД (в этой версии складываем всё в ready_total)
        db.save_author_test_progress(
            user_id=user_id,
            step=next_step,
            answers=answers,
            fear_total=0,
            ready_total=total,
            flags=[],
        )

        await state.update_data(step=next_step, answers=answers, score=total)
        await callback.answer()

        if next_step >= len(QUESTIONS):
            await finish_author_test(callback.message, state, db)
            return "finished"

        await send_current_question(callback.message, state)
        return "continue"

    return "ignored"


async def finish_author_test(message: types.Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    score = int(data.get("score", 0))

    user_id = message.from_user.id if message.from_user else None
    if user_id is not None:
        db.complete_author_test(user_id, zone="DRAFT")

    await state.clear()

    text = (
        "<b>Спасибо! Черновик диагностики пройден.</b>\n\n"
        f"Суммарный балл (тестовый): <b>{score}</b>.\n"
        "Дальше по плану добавим полноценный опросник, зоны и сохранение прогресса."
    )
    await message.answer(text, parse_mode="HTML")
