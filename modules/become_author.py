import json
import logging
from datetime import datetime
from typing import Any

from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

from database.db import Database
from modules.card_of_the_day import get_main_menu

try:
    from config_local import ADMIN_IDS, TIMEZONE
except ImportError:
    from config import ADMIN_IDS, TIMEZONE

logger = logging.getLogger(__name__)


class AuthorTestStates(StatesGroup):
    answering = State()


# --- Вопросы ---
# Часть 1 — 17 вопросов (0–3) → fear_total
PART_1_QUESTIONS: list[str] = [
    "Я сомневаюсь, что моего опыта достаточно, чтобы создавать МАК-карт или Т-игру",
    "Мне кажется, что мои идеи не уникальны",
    "Я боюсь, что клиенты или коллеги не воспримут мой продукт всерьёз",
    "Я боюсь, что продукт не будут покупать",
    "Мне сложно поставить цену на авторский продукт",
    "Я переживаю, что вложу силы и не получу отдачи",
    "Я боюсь продавать и получать отказы",
    "Я не понимаю, как продвигать авторский продукт",
    "Мне страшно выходить в публичность со своей идеей",
    "Я часто обесцениваю себя и свои идеи",
    "Я боюсь критики и негативной обратной связи",
    "Я откладываю запуск, потому что хочу сделать «идеально»",
    "Мне кажется, что у меня нет времени на создание продукта",
    "Я боюсь выгореть в процессе",
    "Мне сложно структурировать процесс работы",
    "Мне кажется, что рынок переполнен",
    "Я часто сравниваю себя с другими авторами",
]

# Часть 2 — 8 вопросов (варианты с баллами) → ready_total (+ флаги просто для аналитики)
PART_2_QUESTIONS: list[dict[str, Any]] = [
    {
        "text": "Я понимаю, что наставник не делает продукт за меня",
        "options": [
            ("Да", 2, None),
            ("Скорее да", 2, None),
            ("Скорее нет", 0, "flag_q18_no"),
            ("Нет", 0, "flag_q18_no"),
        ],
    },
    {
        "text": "Я готов(а) самостоятельно выполнять задания, даже если сложно",
        "options": [
            ("Да", 2, None),
            ("Скорее да", 2, None),
            ("Скорее нет", 1, None),
            ("Нет", 0, None),
        ],
    },
    {
        "text": "Если что-то не получается, я:",
        "options": [
            ("Ищу решение", 2, None),
            ("Обращаюсь за обратной связью", 2, None),
            ("Теряю мотивацию", 1, None),
            ("Останавливаюсь", 0, "flag_stop"),
        ],
    },
    {
        "text": "Обычно, когда я покупаю обучение:",
        "options": [
            ("Дохожу до конца", 2, None),
            ("Делаю частично", 1, None),
            ("Бросаю на середине", 0, "flag_q21_drop"),
        ],
    },
    {
        "text": "За последний год я:",
        "options": [
            ("Запускал(а) продукт или проект", 2, None),
            ("Начинал(а), но не завершил(а)", 1, None),
            ("Только думал(а), но не делал(а)", 0, None),
        ],
    },
    {
        "text": "Если результат не приходит быстро, я:",
        "options": [
            ("Продолжаю работать", 2, None),
            ("Сомневаюсь", 1, None),
            ("Сдаюсь", 0, None),
        ],
    },
    {
        "text": "Я понимаю, что МАК-карты и Т-игры — это:",
        "options": [
            ("Авторский метод и ответственность", 2, None),
            ("Инструмент, который нужно тестировать", 2, None),
            ("Просто формат для продажи", 0, None),
            ("Пока не до конца понимаю", 1, None),
        ],
    },
    {
        "text": "Я хочу быть:",
        "options": [
            ("Автором своего метода", 2, None),
            ("Повторить чужую модель", 0, "flag_q25_try"),
            ("Просто попробовать", 0, "flag_q25_try"),
        ],
    },
]

TOTAL_QUESTIONS = len(PART_1_QUESTIONS) + len(PART_2_QUESTIONS)


def _progress(step: int) -> str:
    return f"Вопрос {step + 1}/{TOTAL_QUESTIONS}"


def _now_iso() -> str:
    try:
        # TIMEZONE может быть pytz timezone
        return datetime.now(TIMEZONE).isoformat() if TIMEZONE else datetime.now().isoformat()
    except Exception:
        return datetime.now().isoformat()


def _build_scale_kb(step: int) -> InlineKeyboardMarkup:
    # 0–3 в одной строке + отмена
    rows = [[
        InlineKeyboardButton(text="0", callback_data=f"author_ans:{step}:0"),
        InlineKeyboardButton(text="1", callback_data=f"author_ans:{step}:1"),
        InlineKeyboardButton(text="2", callback_data=f"author_ans:{step}:2"),
        InlineKeyboardButton(text="3", callback_data=f"author_ans:{step}:3"),
    ]]
    rows.append([InlineKeyboardButton(text="Отмена", callback_data="author_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_options_kb(step: int) -> InlineKeyboardMarkup:
    idx = step - len(PART_1_QUESTIONS)
    q = PART_2_QUESTIONS[idx]
    rows = []
    for opt_idx, (opt_text, _opt_score, _opt_flag) in enumerate(q["options"]):
        # ВАЖНО: callback_data у Telegram ограничен 64 байтами.
        # Поэтому не кладем туда текст ответа — только индексы.
        rows.append([
            InlineKeyboardButton(
                text=opt_text,
                callback_data=f"author_p2:{step}:{opt_idx}",
            )
        ])
    rows.append([InlineKeyboardButton(text="Отмена", callback_data="author_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _zone_from_ready(ready_total: int) -> str:
    if 12 <= ready_total <= 16:
        return "GREEN"
    if 7 <= ready_total <= 11:
        return "YELLOW"
    return "RED"


def _session_has_progress(session: dict | None) -> bool:
    if not session:
        return False
    for key in ("current_step", "last_question"):
        try:
            if int(session.get(key, 0)) > 0:
                return True
        except Exception:
            pass
    answers = session.get("answers") or {}
    return bool(answers)

def _step_from_session(session: dict | None) -> int:
    """Возвращает номер следующего вопроса (0-based) максимально устойчиво к разным схемам БД."""
    if not session:
        return 0

    for key in ("current_step", "last_question"):
        try:
            v = int(session.get(key, 0) or 0)
            if v > 0:
                return v
        except Exception:
            pass

    # Фолбек: если current_step не сохраняется (старая схема), вычисляем по answers
    answers = session.get("answers") or {}
    if isinstance(answers, dict) and answers:
        try:
            max_k = max(int(k) for k in answers.keys())
            return max_k + 1
        except Exception:
            return 0
    return 0


async def start_author_test_flow(message: types.Message, state: FSMContext, db: Database) -> None:
    """Точка входа: если есть незавершённая сессия — предлагает продолжить/перезапустить."""
    user_id = message.from_user.id
    session = db.get_author_test_session(user_id)

    if session and session.get("status") == "in_progress" and _session_has_progress(session):
        step = _step_from_session(session)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data="author_resume")],
            [InlineKeyboardButton(text="🔄 Начать заново", callback_data="author_restart")],
            [InlineKeyboardButton(text="Отмена", callback_data="author_cancel")],
        ])
        await message.answer(
            f"Вы не закончили прошлый тест (остановились на вопросе {min(step + 1, TOTAL_QUESTIONS)}/{TOTAL_QUESTIONS}). Продолжить?",
            reply_markup=kb,
        )
        return

    await _start_new_test(message, state, db)


async def _start_new_test(message: types.Message, state: FSMContext, db: Database) -> None:
    user_id = message.from_user.id
    db.reset_author_test(user_id)

    await state.clear()
    await state.set_state(AuthorTestStates.answering)
    await state.update_data(
        step=0,
        fear_total=0,
        ready_total=0,
        flags=[],
        answers={},
    )
    await send_current_question(message, state)


async def _resume_test(message: types.Message, state: FSMContext, db: Database) -> None:
    user_id = message.from_user.id
    session = db.get_author_test_session(user_id)
    if not session or session.get("status") != "in_progress":
        await _start_new_test(message, state, db)
        return

    step = _step_from_session(session)
    answers = session.get("answers") or {}
    fear_total = int(session.get("fear_total", 0) or 0)
    ready_total = int(session.get("ready_total", 0) or 0)
    flags = session.get("flags") or []

    await state.clear()
    await state.set_state(AuthorTestStates.answering)
    await state.update_data(
        step=step,
        answers=answers,
        fear_total=fear_total,
        ready_total=ready_total,
        flags=flags,
    )

    if step >= TOTAL_QUESTIONS:
        await finish_author_test(message, state, db)
        return

    await send_current_question(message, state)


async def send_current_question(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    step = int(data.get("step", 0))
    if step >= TOTAL_QUESTIONS:
        return

    if step < len(PART_1_QUESTIONS):
        q_text = PART_1_QUESTIONS[step]
        text = (
            "<b>Диагностика «Стать автором»</b>\n"
            f"📊 <b>Часть 1. Блоки и страхи</b>\n"
            f"{_progress(step)}\n\n"
            f"<b>{q_text}</b>\n\n"
            "0 — совсем не про меня\n"
            "1 — немного\n"
            "2 — да, мешает\n"
            "3 — сильно мешает"
        )
        kb = _build_scale_kb(step)
    else:
        idx = step - len(PART_1_QUESTIONS)
        q = PART_2_QUESTIONS[idx]
        text = (
            "<b>Диагностика «Стать автором»</b>\n"
            f"🚀 <b>Часть 2. Готовность</b>\n"
            f"{_progress(step)}\n\n"
            f"<b>{q['text']}</b>"
        )
        kb = _build_options_kb(step)

    # Диагностика: в проде ловили BUTTON_DATA_INVALID при переходе ~19→20.
    # Логируем только рядом с проблемным местом, чтобы не засорять логи.
    if step in (17, 18, 19, 20):
        try:
            btn_debug = []
            for row in kb.inline_keyboard:
                for b in row:
                    cd = b.callback_data or ""
                    btn_debug.append((b.text, cd, len(cd.encode("utf-8"))))
            logger.info(f"[author_test] step={step} kb_buttons={btn_debug}")
        except Exception:
            logger.exception("[author_test] failed to build debug info for keyboard")

    try:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except TelegramBadRequest as e:
        # Защита от падений при некорректном callback_data (лимит 64 байта, и т.п.)
        if "BUTTON_DATA_INVALID" in str(e):
            logger.error("BUTTON_DATA_INVALID while sending question keyboard; sending without keyboard", exc_info=True)
            try:
                await message.edit_text(text, parse_mode="HTML")
            except Exception:
                await message.answer(text, parse_mode="HTML")
            return
        # не наша ошибка — пробуем fallback
        try:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await message.answer(text, parse_mode="HTML")
    except Exception:
        try:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "BUTTON_DATA_INVALID" in str(e):
                logger.error("BUTTON_DATA_INVALID while sending question keyboard (answer); sending without keyboard", exc_info=True)
                await message.answer(text, parse_mode="HTML")
            else:
                raise


async def handle_author_callback(callback: types.CallbackQuery, state: FSMContext, db: Database) -> str:
    """Возвращает статус: continue | finished | cancelled | ignored"""
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
        parts = callback.data.split(":", 5)
        # author_ans:step:score[:flag:answer_json]
        try:
            step = int(parts[1])
            score = int(parts[2])
        except Exception:
            await callback.answer("Не понял ответ, попробуйте ещё раз.", show_alert=True)
            return "ignored"

        flag = None
        answer_text = str(score)
        if len(parts) >= 4:
            flag_raw = parts[3]
            flag = None if flag_raw in ("-", "None", "") else flag_raw
        if len(parts) >= 5:
            try:
                answer_text = json.loads(parts[4])
            except Exception:
                # fallback
                answer_text = answer_text

        data = await state.get_data()
        cur_step = int(data.get("step", 0))
        if step != cur_step:
            await callback.answer()
            return "ignored"

        fear_total = int(data.get("fear_total", 0))
        ready_total = int(data.get("ready_total", 0))
        flags = list(data.get("flags", []) or [])
        answers = dict(data.get("answers", {}) or {})

        # агрегируем
        if step < len(PART_1_QUESTIONS):
            fear_total += score
        else:
            ready_total += score
        if flag and flag not in flags:
            flags.append(flag)
        answers[str(step)] = {"score": score, "text": answer_text, "flag": flag}

        next_step = cur_step + 1

        # Сохраняем прогресс (сейчас используем существующий API db.save_author_test_progress)
        db.save_author_test_progress(
            user_id=user_id,
            step=next_step,
            answers=answers,
            fear_total=fear_total,
            ready_total=ready_total,
            flags=flags,
        )

        await state.update_data(
            step=next_step,
            answers=answers,
            fear_total=fear_total,
            ready_total=ready_total,
            flags=flags,
        )
        await callback.answer()

        if next_step >= TOTAL_QUESTIONS:
            await finish_author_test(callback.message, state, db)
            return "finished"

        await send_current_question(callback.message, state)
        return "continue"

    if callback.data.startswith("author_p2:"):
        try:
            _, step_s, opt_s = callback.data.split(":", 2)
            step = int(step_s)
            opt_idx = int(opt_s)
        except Exception:
            await callback.answer("Не понял ответ, попробуйте ещё раз.", show_alert=True)
            return "ignored"

        data = await state.get_data()
        cur_step = int(data.get("step", 0))
        if step != cur_step:
            await callback.answer()
            return "ignored"

        # lookup option
        q2_idx = step - len(PART_1_QUESTIONS)
        if q2_idx < 0 or q2_idx >= len(PART_2_QUESTIONS):
            await callback.answer()
            return "ignored"

        options = PART_2_QUESTIONS[q2_idx]["options"]
        if opt_idx < 0 or opt_idx >= len(options):
            await callback.answer()
            return "ignored"

        opt_text, score, flag = options[opt_idx]

        fear_total = int(data.get("fear_total", 0))
        ready_total = int(data.get("ready_total", 0)) + int(score)
        flags = list(data.get("flags", []) or [])
        if flag and flag not in flags:
            flags.append(flag)
        answers = dict(data.get("answers", {}) or {})
        answers[str(step)] = {"score": int(score), "text": opt_text, "flag": flag}

        next_step = cur_step + 1
        db.save_author_test_progress(
            user_id=callback.from_user.id,
            step=next_step,
            answers=answers,
            fear_total=fear_total,
            ready_total=ready_total,
            flags=flags,
        )

        await state.update_data(
            step=next_step,
            answers=answers,
            fear_total=fear_total,
            ready_total=ready_total,
            flags=flags,
        )
        await callback.answer()

        if next_step >= TOTAL_QUESTIONS:
            await finish_author_test(callback.message, state, db)
            return "finished"

        await send_current_question(callback.message, state)
        return "continue"

    if callback.data == "author_placeholder":
        await callback.answer("Материалы пока готовятся. Следите за обновлениями!", show_alert=True)
        return "ignored"

    return "ignored"


async def _notify_admins_green(
    bot: Bot,
    user_id: int,
    username: str | None,
    full_name: str | None,
    ready_total: int,
    fear_total: int,
    zone: str,
) -> None:
    if zone != "GREEN":
        return
    text = (
        "🚨 <b>Новый кандидат в авторы (GREEN)</b>\n\n"
        f"👤 <b>Пользователь:</b> {full_name or '-'}"
        + (f" (@{username})" if username else "")
        + "\n"
        f"ID: <code>{user_id}</code>\n"
        f"📊 <b>Баллы:</b> Ready: <b>{ready_total}</b>/16, Fear: <b>{fear_total}</b>\n"
        f"🎯 <b>Зона:</b> {zone}\n\n"
        "Нужно связаться."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать пользователю", url=f"tg://user?id={user_id}")],
    ])
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")


async def finish_author_test(message: types.Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    fear_total = int(data.get("fear_total", 0))
    ready_total = int(data.get("ready_total", 0))
    flags = list(data.get("flags", []) or [])

    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        await state.clear()
        return

    zone = _zone_from_ready(ready_total)

    # фиксируем результат в БД
    db.complete_author_test(user_id, zone=zone)
    await state.clear()

    if zone == "GREEN":
        result_text = (
            "🟢 <b>Поздравляю, вы – будущий автор!</b>\n\n"
            "По результатам диагностики вы попали в <b>зелёную зону</b>. Это означает, что:\n"
            "• Есть не только идея, но и готовность действовать.\n"
            "• Вы умеете брать ответственность за продукт.\n"
            "• У вас реальные шансы довести дело до результата.\n\n"
            "<b>Что дальше:</b>\n"
            "Ожидайте сообщения от администратора — мы продолжим общение."
        )
        await message.answer(result_text, parse_mode="HTML")
        try:
            await _notify_admins_green(
                bot=message.bot,
                user_id=user_id,
                username=getattr(message.from_user, "username", None),
                full_name=getattr(message.from_user, "full_name", None),
                ready_total=ready_total,
                fear_total=fear_total,
                zone=zone,
            )
        except Exception:
            logger.exception("Failed to notify admins about GREEN author candidate")
    elif zone == "YELLOW":
        result_text = (
            "🟡 <b>Вам нужно ещё немного времени!</b>\n\n"
            "По результатам диагностики я вижу: у вас есть потенциал, но сейчас есть факторы, "
            "которые могут помешать вам дойти до результата.\n\n"
            "Я рекомендую сначала пройти подготовительный этап, укрепить действия и уверенность."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌱 Подготовительный материал (скоро)", callback_data="author_placeholder")],
        ])
        await message.answer(result_text, reply_markup=kb, parse_mode="HTML")
    else:
        result_text = (
            "🔴 <b>Пока не время…</b>\n\n"
            "Благодарю вас за прохождение диагностики. По результатам теста сейчас наставничество "
            "будет для вас преждевременным.\n\n"
            "Я оставляю для вас доступ к материалам, которые помогут укрепить позицию."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Открытые материалы (скоро)", callback_data="author_placeholder")],
        ])
        await message.answer(result_text, reply_markup=kb, parse_mode="HTML")

    # меню
    await message.answer("Выбери действие:", reply_markup=await get_main_menu(user_id, db))
