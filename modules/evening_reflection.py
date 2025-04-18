import logging
from datetime import datetime
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram import F, Router # Используем Router для удобства

# Локальные импорты (или относительные, если структура позволяет)
# Важно: Убедись, что UserState импортируется ПЕРЕД его использованием здесь
from modules.user_management import UserState
from database.db import Database # Укажи правильный путь к твоему классу Database
from modules.logging_service import LoggingService # Укажи правильный путь
from config import TIMEZONE
# Импортируем функцию для получения главного меню, чтобы показать его в конце
from modules.card_of_the_day import get_main_menu

logger = logging.getLogger(__name__)

# Создаем Router для этого модуля
reflection_router = Router()

# --- Состояния для Вечерней Рефлексии ---
# Они должны быть определены в UserState в user_management.py
# Здесь мы их используем для фильтров

# --- Тексты сообщений ---
MSG_INTRO = "Давай мягко завершим этот день. Это займёт всего пару минут 🌙"
ASK_GOOD_MOMENTS = "Что сегодня было хорошего? Что подарило тебе радость, тепло или вдохновение?"
ASK_GRATITUDE = "За что сегодня ты испытываешь благодарность?"
ASK_HARD_MOMENTS = "Были ли моменты, которые были непростыми? Что вызвало напряжение или усталость?"
MSG_CONCLUSION = "Спасибо, что уделил(а) себе это внимание. Ты молодец.\nПусть ночь будет спокойной, а утро — новым началом ✨"
MSG_INPUT_ERROR = "Пожалуйста, опиши свои мысли текстом."

# --- Хендлеры ---

async def start_evening_reflection(message: types.Message, state: FSMContext, db: Database, logger_service: LoggingService):
    """Начало флоу 'Итог дня'."""
    user_id = message.from_user.id
    await logger_service.log_action(user_id, "evening_reflection_started")
    await message.answer(MSG_INTRO)
    await message.answer(ASK_GOOD_MOMENTS)
    await state.set_state(UserState.waiting_for_good_moments)

@reflection_router.message(StateFilter(UserState.waiting_for_good_moments))
async def process_good_moments(message: types.Message, state: FSMContext, db: Database, logger_service: LoggingService):
    """Обработка ответа на вопрос о хороших моментах."""
    user_id = message.from_user.id
    answer = message.text.strip()
    if not answer:
        await message.reply(MSG_INPUT_ERROR)
        return

    await state.update_data(good_moments=answer)
    await logger_service.log_action(user_id, "evening_reflection_good_provided", {"length": len(answer)})
    await message.answer(ASK_GRATITUDE)
    await state.set_state(UserState.waiting_for_gratitude)

@reflection_router.message(StateFilter(UserState.waiting_for_gratitude))
async def process_gratitude(message: types.Message, state: FSMContext, db: Database, logger_service: LoggingService):
    """Обработка ответа на вопрос о благодарности."""
    user_id = message.from_user.id
    answer = message.text.strip()
    if not answer:
        await message.reply(MSG_INPUT_ERROR)
        return

    await state.update_data(gratitude=answer)
    await logger_service.log_action(user_id, "evening_reflection_gratitude_provided", {"length": len(answer)})
    await message.answer(ASK_HARD_MOMENTS)
    await state.set_state(UserState.waiting_for_hard_moments)

@reflection_router.message(StateFilter(UserState.waiting_for_hard_moments))
async def process_hard_moments(message: types.Message, state: FSMContext, db: Database, logger_service: LoggingService):
    """Обработка ответа на вопрос о непростых моментах и завершение."""
    user_id = message.from_user.id
    hard_moments_answer = message.text.strip()
    if not hard_moments_answer:
        await message.reply(MSG_INPUT_ERROR)
        return

    await state.update_data(hard_moments=hard_moments_answer)
    await logger_service.log_action(user_id, "evening_reflection_hard_provided", {"length": len(hard_moments_answer)})

    # Сохранение данных в БД
    data = await state.get_data()
    good_moments = data.get("good_moments")
    gratitude = data.get("gratitude")
    # hard_moments_answer уже есть

    try:
        today_str = datetime.now(TIMEZONE).strftime('%Y-%m-%d')
        created_at_iso = datetime.now(TIMEZONE).isoformat()
        await db.save_evening_reflection(
            user_id=user_id,
            date=today_str,
            good_moments=good_moments,
            gratitude=gratitude,
            hard_moments=hard_moments_answer,
            created_at=created_at_iso
        )
        await logger_service.log_action(user_id, "evening_reflection_saved_to_db")
    except Exception as e:
        logger.error(f"Failed to save evening reflection for user {user_id}: {e}", exc_info=True)
        await message.answer("Ой, не получилось сохранить твою рефлексию. Но спасибо, что поделился(ась)!")
        # Не показываем главное меню, чтобы не сбивать пользователя, если он захочет попробовать снова

    # Завершение
    await message.answer(MSG_CONCLUSION, reply_markup=await get_main_menu(user_id, db))
    await state.clear()
