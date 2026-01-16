# modules/become_author.py
import logging

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


class AuthorTestStates(StatesGroup):
    answering = State()


# Минимальный каркас на 2 вопроса (без БД).
# На следующих шагах заменим на полный опросник + сохранение прогресса.
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


async def start_author_test(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AuthorTestStates.answering)
    await state.update_data(step=0, answers=[], score=0)
    await send_current_question(message, state)


async def send_current_question(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    step = int(data.get("step", 0))

    if step >= len(QUESTIONS):
        await finish_author_test(message, state)
        return

    q = QUESTIONS[step]
    text = (
        "<b>Диагностика «Стать автором»</b>\n"
        + _progress(step)
        + "\n\n"
        + q["text"]
    )

    kb_rows = []
    for opt_text, opt_score in q["options"]:
        kb_rows.append([
            InlineKeyboardButton(
                text=opt_text,
                callback_data=f"author_ans:{step}:{opt_score}",
            )
        ])
    kb_rows.append([InlineKeyboardButton(text="Отмена", callback_data="author_cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    try:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


async def handle_author_callback(callback: types.CallbackQuery, state: FSMContext) -> str:
    """Обрабатывает callback-и каркаса теста.

    Возвращает статус: continue | finished | cancelled | ignored
    """

    if not callback.data:
        return "ignored"

    if callback.data == "author_cancel":
        await state.clear()
        await callback.answer("Ок, отменил(а).")
        return "cancelled"

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

        answers = list(data.get("answers", []))
        answers.append({"step": step, "score": score})
        total = int(data.get("score", 0)) + score

        next_step = cur_step + 1
        await state.update_data(step=next_step, answers=answers, score=total)
        await callback.answer()

        if next_step >= len(QUESTIONS):
            await finish_author_test(callback.message, state)
            return "finished"

        await send_current_question(callback.message, state)
        return "continue"

    return "ignored"


async def finish_author_test(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    score = int(data.get("score", 0))
    await state.clear()

    text = (
        "<b>Спасибо! Черновик диагностики пройден.</b>\n\n"
        f"Суммарный балл (тестовый): <b>{score}</b>.\n"
        "Дальше по плану добавим полноценный опросник, зоны и сохранение прогресса."
    )
    await message.answer(text, parse_mode="HTML")
