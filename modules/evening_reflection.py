# код/evening_reflection.py 0

import logging
from datetime import datetime
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram import F, Router # Используем Router для удобства

# Локальные импорты
from modules.user_management import UserState
from database.db import Database
from modules.logging_service import LoggingService
try:
    from config_local import TIMEZONE
except ImportError:
    from config import TIMEZONE
# --- НОВЫЙ ИМПОРТ ---
from modules.ai_service import get_reflection_summary_and_card_synergy, get_empathetic_response # Импортируем новую функцию
# --- КОНЕЦ НОВОГО ИМПОРТА ---
from modules.card_of_the_day import get_main_menu

logger = logging.getLogger(__name__)

# Создаем Router для этого модуля
# (Оставляем его, если он используется для других обработчиков, например, callback_query,
#  или если планируется его использовать в будущем. Если нет - можно удалить)
reflection_router = Router()

# --- Тексты сообщений ---
MSG_INTRO = "Привет! 🌙 Давай вместе подведём итоги твоего дня. Это займёт всего 2-3 минуты, но поможет лучше понять себя и свои чувства.\n\n💡 Отвечай своими словами, как тебе удобно. Даже короткий ответ будет ценным!"
ASK_GOOD_MOMENTS = "Начнём с приятного! ✨ Что сегодня принесло тебе радость, вдохновение или просто хорошее настроение? Расскажи своими словами.\n\n💡 Например: 'встреча с подругой', 'успешно завершила проект', 'выпила вкусный кофе'"
ASK_GRATITUDE = "Отлично! 🙏 А за что ты сегодня чувствуешь благодарность? Может быть, за поддержку близких, за маленькие радости или за то, что справилась с чем-то сложным?\n\n💡 Например: 'за помощь коллег', 'за солнечную погоду', 'за то, что не сдалась'"
ASK_HARD_MOMENTS = "Спасибо за честность! 💪 А теперь расскажи о том, что сегодня было непростым. Какие моменты вызвали напряжение, усталость или другие сложные чувства?\n\n💡 Например: 'сложный разговор с начальником', 'устала от рутины', 'чувствую тревогу'"
MSG_CONCLUSION = "Спасибо, что поделилась своими мыслями! 🌟 Ты молодец, что находишь время для самоанализа. Пусть ночь будет спокойной, а завтра принесёт новые возможности ✨"
MSG_INPUT_ERROR = "Пожалуйста, опиши своими словами, что ты чувствуешь. Даже короткий ответ поможет мне лучше понять тебя.\n\n💡 Например: 'чувствую усталость', 'было много дел', 'встретила интересного человека'"
MSG_AI_SUMMARY_PREFIX = "✨ Вот что я поняла о твоём дне:\n\n" # Префикс для AI резюме
MSG_AI_SUMMARY_FAIL = "К сожалению, не удалось сгенерировать AI-итог, но твои размышления очень ценны! Спасибо, что поделилась ими."

# --- Хендлеры ---

# Эта функция будет вызываться из main.py, зарегистрированная напрямую на dp
async def start_evening_reflection(message: types.Message, state: FSMContext, db: Database, logger_service: LoggingService):
    """Начало флоу 'Итог дня'."""
    user_id = message.from_user.id
    
    # Начинаем сценарий "Вечерняя рефлексия"
    session_id = db.start_user_scenario(user_id, 'evening_reflection')
    db.log_scenario_step(user_id, 'evening_reflection', 'started', {
        'session_id': session_id,
        'today': datetime.now(TIMEZONE).date().isoformat()
    })
    
    # Сохраняем session_id в состоянии
    await state.update_data(session_id=session_id)
    
    await logger_service.log_action(user_id, "evening_reflection_started")
    await message.answer(MSG_INTRO)
    await message.answer(ASK_GOOD_MOMENTS)
    await state.set_state(UserState.waiting_for_good_moments)

# УБРАН ДЕКОРАТОР @reflection_router.message(...)
# Эта функция будет вызываться из main.py, зарегистрированная напрямую на dp
async def process_good_moments(message: types.Message, state: FSMContext, db: Database, logger_service: LoggingService):
    """Обработка ответа на вопрос о хороших моментах."""
    user_id = message.from_user.id
    answer = message.text.strip()
    if not answer:
        await message.reply(MSG_INPUT_ERROR)
        return

    await state.update_data(good_moments=answer)
    
    # Логируем ответ на вопрос о хороших моментах
    fsm_data = await state.get_data()
    session_id = fsm_data.get("session_id", "unknown")
    db.log_scenario_step(user_id, 'evening_reflection', 'good_moments_provided', {
        'session_id': session_id,
        'answer_length': len(answer)
    })
    
    await logger_service.log_action(user_id, "evening_reflection_good_provided", {"length": len(answer)})
    await message.answer(ASK_GRATITUDE)
    await state.set_state(UserState.waiting_for_gratitude)

# УБРАН ДЕКОРАТОР @reflection_router.message(...)
# Эта функция будет вызываться из main.py, зарегистрированная напрямую на dp
async def process_gratitude(message: types.Message, state: FSMContext, db: Database, logger_service: LoggingService):
    """Обработка ответа на вопрос о благодарности."""
    user_id = message.from_user.id
    answer = message.text.strip()
    if not answer:
        await message.reply(MSG_INPUT_ERROR)
        return

    await state.update_data(gratitude=answer)
    
    # Логируем ответ на вопрос о благодарности
    fsm_data = await state.get_data()
    session_id = fsm_data.get("session_id", "unknown")
    db.log_scenario_step(user_id, 'evening_reflection', 'gratitude_provided', {
        'session_id': session_id,
        'answer_length': len(answer)
    })
    
    await logger_service.log_action(user_id, "evening_reflection_gratitude_provided", {"length": len(answer)})
    await message.answer(ASK_HARD_MOMENTS)
    await state.set_state(UserState.waiting_for_hard_moments)

# УБРАН ДЕКОРАТОР @reflection_router.message(...)
# Эта функция будет вызываться из main.py, зарегистрированная напрямую на dp
async def process_hard_moments(message: types.Message, state: FSMContext, db: Database, logger_service: LoggingService):
    """Обработка ответа на вопрос о непростых моментах, генерация AI-резюме и завершение."""
    user_id = message.from_user.id
    hard_moments_answer = message.text.strip()
    if not hard_moments_answer:
        await message.reply(MSG_INPUT_ERROR)
        return

    await state.update_data(hard_moments=hard_moments_answer)
    
    # Логируем ответ на вопрос о непростых моментах
    fsm_data = await state.get_data()
    session_id = fsm_data.get("session_id", "unknown")
    db.log_scenario_step(user_id, 'evening_reflection', 'hard_moments_provided', {
        'session_id': session_id,
        'answer_length': len(hard_moments_answer)
    })
    
    await logger_service.log_action(user_id, "evening_reflection_hard_provided", {"length": len(hard_moments_answer)})

    # --- НОВЫЙ КОД: Эмпатичный отклик ИИ ---
    try:
        # Показываем "печатает..." пока генерируется эмпатичный отклик
        await message.bot.send_chat_action(user_id, 'typing')
        empathetic_response = await get_empathetic_response(hard_moments_answer)
        
        if empathetic_response:
            await message.answer(empathetic_response)
            await logger_service.log_action(user_id, "evening_reflection_empathetic_response_sent")
        else:
            # Fallback сообщение если ИИ не сгенерировал ответ
            await message.answer("Очень сочувствую, что ты переживаешь это. Твои чувства важны и понятны.")
            await logger_service.log_action(user_id, "evening_reflection_empathetic_response_failed", {"reason": "AI service returned None"})
            
    except Exception as empathetic_err:
        logger.error(f"Error during empathetic response generation for user {user_id}: {empathetic_err}", exc_info=True)
        # Fallback сообщение в случае ошибки
        fallback_messages = [
            "Очень сочувствую, что ты переживаешь это. Твои чувства важны и понятны.",
            "Спасибо, что поделилась этим со мной. Я слышу тебя и понимаю.",
            "Понимаю, что это непростой момент. Ты не одна, и твои переживания валидны.",
            "Спасибо за доверие. Твои чувства заслуживают внимания и понимания."
        ]
        import random
        fallback_message = random.choice(fallback_messages)
        await message.answer(fallback_message)
        await logger_service.log_action(user_id, "evening_reflection_empathetic_response_failed", {"reason": str(empathetic_err)})
    # --- КОНЕЦ НОВОГО КОДА ---

    # --- НАЧАЛО ИНТЕГРАЦИИ AI ---
    data = await state.get_data()
    ai_summary_text = None # Инициализируем переменную для резюме
    
    try:
        # Показываем "печатает..." пока генерируется резюме
        await message.bot.send_chat_action(user_id, 'typing') # <--- Индикатор "печатает..."
        # Карты не имеют названий/значений, поэтому всегда используем обычное резюме без карты
        ai_summary_text = await get_reflection_summary_and_card_synergy(user_id, data, db, None, None)

        if ai_summary_text:
            await message.answer(f"{MSG_AI_SUMMARY_PREFIX}<i>{ai_summary_text}</i>", parse_mode="HTML") # Добавлен parse_mode HTML
            await logger_service.log_action(user_id, "evening_reflection_summary_sent")
        else:
            # Если AI вернул None или пустую строку (из-за непредвиденной ошибки в ai_service)
            fallback_messages = [
                "К сожалению, не удалось сгенерировать AI-итог, но твои размышления очень ценны! Спасибо, что поделилась ими.",
                "Не получилось создать AI-резюме, но главное — это твои мысли и чувства. Они бесценны! ✨",
                "AI-итог не сгенерировался, но твои ответы показывают глубину самоанализа. Это прекрасно! 🌟"
            ]
            import random
            fallback_message = random.choice(fallback_messages)
            await message.answer(fallback_message)
            await logger_service.log_action(user_id, "evening_reflection_summary_failed", {"reason": "AI service returned None"})

    except Exception as ai_err:
        logger.error(f"Error during AI reflection summary generation for user {user_id}: {ai_err}", exc_info=True)
        fallback_messages = [
            "К сожалению, не удалось сгенерировать AI-итог, но твои размышления очень ценны! Спасибо, что поделилась ими.",
            "Не получилось создать AI-резюме, но главное — это твои мысли и чувства. Они бесценны! ✨",
            "AI-итог не сгенерировался, но твои ответы показывают глубину самоанализа. Это прекрасно! 🌟"
        ]
        import random
        fallback_message = random.choice(fallback_messages)
        await message.answer(fallback_message, parse_mode="HTML") # Сообщаем пользователю об ошибке
        await logger_service.log_action(user_id, "evening_reflection_summary_failed", {"reason": str(ai_err)})
        ai_summary_text = None # Убедимся, что в БД не запишется ошибка
    # --- КОНЕЦ ИНТЕГРАЦИИ AI ---

    # Сохранение данных в БД (включая ai_summary_text, который может быть None)
    good_moments = data.get("good_moments")
    gratitude = data.get("gratitude")

    try:
        today_str = datetime.now(TIMEZONE).strftime('%Y-%m-%d')
        created_at_iso = datetime.now(TIMEZONE).isoformat()
        # --- ИСПРАВЛЕНИЕ: УБИРАЕМ await ПЕРЕД db.save_evening_reflection ---
        db.save_evening_reflection(
            user_id=user_id,
            date=today_str,
            good_moments=good_moments,
            gratitude=gratitude,
            hard_moments=hard_moments_answer,
            created_at=created_at_iso,
            ai_summary=ai_summary_text # <--- ПЕРЕДАЕМ РЕЗЮМЕ
        )
        # Лог об успешном сохранении будет внутри db.save_evening_reflection
        await logger_service.log_action(user_id, "evening_reflection_saved_to_db") # Оставляем этот общий лог
    except Exception as db_err:
        logger.error(f"Failed to save evening reflection for user {user_id}: {db_err}", exc_info=True)
        await message.answer("Ой, не получилось сохранить твою рефлексию в базу данных. Но спасибо, что поделился(ась)!")
        # Важно: очищаем состояние, даже если не сохранилось в БД, чтобы не зацикливаться
        await state.clear()
        return # Выходим, не показывая стандартное завершение

    # Завершаем сценарий "Вечерняя рефлексия"
    db.complete_user_scenario(user_id, 'evening_reflection', session_id)
    db.log_scenario_step(user_id, 'evening_reflection', 'completed', {
        'session_id': session_id,
        'ai_summary_generated': ai_summary_text is not None,
        'good_moments_length': len(good_moments) if good_moments else 0,
        'gratitude_length': len(gratitude) if gratitude else 0,
        'hard_moments_length': len(hard_moments_answer)
    })
    
    # Завершение (отправка стандартного сообщения и меню)
    await message.answer(MSG_CONCLUSION, reply_markup=await get_main_menu(user_id, db))
    await state.clear() # Очищаем состояние
