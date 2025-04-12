# код/card_of_the_day.py

import random
import os
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import TIMEZONE, NO_CARD_LIMIT_USERS
# Импортируем обе функции из ai_service
from .ai_service import get_grok_question, get_grok_summary, build_user_profile
from datetime import datetime
from modules.user_management import UserState
import logging # Добавим логирование

logger = logging.getLogger(__name__)

async def get_main_menu(user_id, db):
    """Возвращает основную клавиатуру меню."""
    keyboard = [[types.KeyboardButton(text="✨ Карта дня")]]
    user_data = db.get_user(user_id) # Предполагаем, что get_user синхронный
    if user_data and user_data.get("bonus_available"):
        keyboard.append([types.KeyboardButton(text="💌 Подсказка Вселенной")])
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, persistent=True)

async def handle_card_request(message: types.Message, state: FSMContext, db, logger_service):
    """Обрабатывает запрос на получение карты дня."""
    user_id = message.from_user.id
    name = db.get_user(user_id).get("name", "") # Безопасное получение имени
    now = datetime.now(TIMEZONE)
    today = now.date()

    last_request_str = db.get_user(user_id).get("last_request")
    last_request_date = None
    if last_request_str:
        try:
            if isinstance(last_request_str, str):
                 last_request_dt = datetime.fromisoformat(last_request_str.replace('Z', '+00:00')).astimezone(TIMEZONE)
            elif isinstance(last_request_str, datetime):
                 last_request_dt = last_request_str.astimezone(TIMEZONE)
            else:
                 last_request_dt = None

            if last_request_dt:
                last_request_date = last_request_dt.date()
        except Exception as e:
             logger.error(f"Error parsing last_request timestamp '{last_request_str}' for user {user_id}: {e}")
             last_request_date = None

    if user_id not in NO_CARD_LIMIT_USERS and last_request_date == today:
        text = f"{name}, ты уже вытянула карту сегодня! Новая будет завтра в 00:00 по Москве." if name else "Ты уже вытянула карту сегодня! Новая будет завтра в 00:00 по Москве."
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        return

    text = f"{name}, готова поисследовать свой внутренний мир? 🌿 Подумай о своем запросе или теме дня. Можешь написать его мне или просто держать в голове, а затем нажми 'Вытянуть карту'" if name else ", Готова поисследовать свой внутренний мир? 🌿 Подумай о своем запросе или теме дня. Можешь написать его мне или просто держать в голове, а затем нажми 'Вытянуть карту'"
    await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Вытянуть карту", callback_data="draw_card")]
    ]))
    await state.set_state(UserState.waiting_for_request_text)
    await logger_service.log_action(user_id, "card_request_initiated")

async def draw_card(callback: types.CallbackQuery, state: FSMContext, db, logger_service):
    """Вытягивает карту без предварительного текстового запроса."""
    user_id = callback.from_user.id
    name = db.get_user(user_id).get("name", "")
    now_iso = datetime.now(TIMEZONE).isoformat() # Сохраняем в ISO формате

    used_cards = db.get_user_cards(user_id)
    all_cards = list(range(1, 41)) # Предполагаем 40 карт
    available_cards = [c for c in all_cards if c not in used_cards]

    if not available_cards:
        logger.info(f"Card deck reset for user {user_id}")
        db.reset_user_cards(user_id)
        available_cards = all_cards.copy()

    card_number = random.choice(available_cards)
    db.add_user_card(user_id, card_number)
    db.update_user(user_id, {"last_request": now_iso})

    card_path = f"cards/card_{card_number}.jpg"
    if os.path.exists(card_path):
        try:
            await callback.message.bot.send_photo(
                user_id,
                types.FSInputFile(card_path),
                protect_content=True
            )
            text = f"{name}, взгляни на карту. Какие первые чувства, образы, воспоминания приходят? Как это может быть связано с твоим сегодняшним состоянием или запросом? Поделись своими ассоциациями." if name else "Взгляни на карту. Какие первые чувства, образы, воспоминания приходят? Как это может быть связано с твоим сегодняшним состоянием или запросом? Поделись своими ассоциациями."
            await callback.message.answer(text) # Отправляем вопрос после карты

            await state.update_data(card_number=card_number, user_request="") # Запрос пустой
            await state.set_state(UserState.waiting_for_initial_response)
            await logger_service.log_action(user_id, "card_drawn", {"card_number": card_number})

        except Exception as e:
            logger.error(f"Failed to send card photo to user {user_id}: {e}")
            await callback.message.answer("Ой, не получилось отправить карту. Попробуй еще раз чуть позже.")
            await state.clear() # Очищаем состояние при ошибке
    else:
        logger.error(f"Card image not found: {card_path}")
        await callback.message.answer("Кажется, изображение для этой карты потерялось. Попробуй вытянуть еще раз.")
        await state.clear()

    await callback.answer() # Отвечаем на callback query

async def process_request_text(message: types.Message, state: FSMContext, db, logger_service):
    """Обрабатывает текстовый запрос пользователя и вытягивает карту."""
    user_id = message.from_user.id
    name = db.get_user(user_id).get("name", "")
    request_text = message.text.strip()
    now_iso = datetime.now(TIMEZONE).isoformat()

    used_cards = db.get_user_cards(user_id)
    all_cards = list(range(1, 41))
    available_cards = [c for c in all_cards if c not in used_cards]

    if not available_cards:
        logger.info(f"Card deck reset for user {user_id}")
        db.reset_user_cards(user_id)
        available_cards = all_cards.copy()

    card_number = random.choice(available_cards)
    db.add_user_card(user_id, card_number)
    db.update_user(user_id, {"last_request": now_iso})

    card_path = f"cards/card_{card_number}.jpg"
    if os.path.exists(card_path):
        try:
            await message.bot.send_photo(
                user_id,
                types.FSInputFile(card_path),
                protect_content=True
            )
            text = f"{name}, вот карта для твоего запроса: '{request_text}'. Рассмотри ее внимательно. Что замечаешь? Какие мысли или чувства она вызывает в контексте твоего вопроса?" if name else f"Вот карта для твоего запроса: '{request_text}'. Рассмотри ее внимательно. Что замечаешь? Какие мысли или чувства она вызывает в контексте твоего вопроса?"
            await message.answer(text) # Отправляем вопрос после карты

            await state.update_data(card_number=card_number, user_request=request_text)
            await state.set_state(UserState.waiting_for_initial_response)
            await logger_service.log_action(user_id, "card_drawn_with_request", {"card_number": card_number, "request": request_text})

        except Exception as e:
            logger.error(f"Failed to send card photo to user {user_id} after request: {e}")
            await message.answer("Ой, не получилось отправить карту. Попробуй еще раз чуть позже.")
            await state.clear()
    else:
        logger.error(f"Card image not found: {card_path}")
        await message.answer("Кажется, изображение для этой карты потерялось. Попробуй вытянуть еще раз.")
        await state.clear()

async def process_initial_response(message: types.Message, state: FSMContext, db, logger_service):
    """Обрабатывает первый ответ пользователя на карту и задает первый вопрос Grok."""
    user_id = message.from_user.id
    response_text = message.text.strip()
    data = await state.get_data()
    card_number = data.get("card_number", "N/A")
    user_request = data.get("user_request", "")

    await logger_service.log_action(user_id, "initial_response", {"card_number": card_number, "request": user_request, "response": response_text})
    grok_question = await get_grok_question(user_id, user_request, response_text, "Начало", step=1, db=db)
    await logger_service.log_action(user_id, "grok_question", {"step": 1, "grok_question": grok_question})
    await message.answer(grok_question)
    await state.update_data(first_grok_question=grok_question, initial_response=response_text)
    await state.set_state(UserState.waiting_for_first_grok_response)

async def process_first_grok_response(message: types.Message, state: FSMContext, db, logger_service):
    """Обрабатывает ответ на первый вопрос Grok и задает второй."""
    user_id = message.from_user.id
    first_response = message.text.strip()
    data = await state.get_data()
    card_number = data.get("card_number", "N/A")
    user_request = data.get("user_request", "")
    first_grok_question = data.get("first_grok_question", "")

    await logger_service.log_action(user_id, "first_grok_response", {"card_number": card_number, "request": user_request, "question": first_grok_question, "response": first_response})
    previous_responses_context = {
        "first_question": first_grok_question,
        "first_response": first_response
    }
    second_grok_question = await get_grok_question(user_id, user_request, first_response, "Продолжение", step=2, previous_responses=previous_responses_context, db=db)
    await logger_service.log_action(user_id, "grok_question", {"step": 2, "grok_question": second_grok_question})
    await message.answer(second_grok_question)
    await state.update_data(second_grok_question=second_grok_question, previous_responses=previous_responses_context)
    await state.set_state(UserState.waiting_for_second_grok_response)

async def process_second_grok_response(message: types.Message, state: FSMContext, db, logger_service):
    """Обрабатывает ответ на второй вопрос Grok и задает третий."""
    user_id = message.from_user.id
    second_response = message.text.strip()
    data = await state.get_data()
    card_number = data.get("card_number", "N/A")
    user_request = data.get("user_request", "")
    second_grok_question = data.get("second_grok_question", "")
    previous_responses_context = data.get("previous_responses", {})

    await logger_service.log_action(user_id, "second_grok_response", {"card_number": card_number, "request": user_request, "question": second_grok_question, "response": second_response})
    previous_responses_context["second_question"] = second_grok_question
    previous_responses_context["second_response"] = second_response
    third_grok_question = await get_grok_question(user_id, user_request, second_response, "Завершение", step=3, previous_responses=previous_responses_context, db=db)
    await logger_service.log_action(user_id, "grok_question", {"step": 3, "grok_question": third_grok_question})
    await message.answer(third_grok_question)
    await state.update_data(third_grok_question=third_grok_question, previous_responses=previous_responses_context)
    await state.set_state(UserState.waiting_for_third_grok_response)

async def process_third_grok_response(message: types.Message, state: FSMContext, db, logger_service):
    """Обрабатывает ответ на третий вопрос Grok, генерирует саммари и запрашивает фидбек о процессе."""
    user_id = message.from_user.id
    name = db.get_user(user_id).get("name", "")
    third_response = message.text.strip()
    data = await state.get_data()
    # Извлекаем card_number надежно, даже если N/A
    card_number = data.get("card_number")
    if card_number is None:
        logger.warning(f"Card number not found in state for user {user_id} at third response.")
        card_number = 0 # Или другое значение по умолчанию

    user_request = data.get("user_request", "")
    third_grok_question = data.get("third_grok_question", "")
    previous_responses_context = data.get("previous_responses", {})

    await logger_service.log_action(user_id, "third_grok_response", {"card_number": card_number, "request": user_request, "question": third_grok_question, "response": third_response})

    logger.info(f"Starting summary generation for user {user_id}")
    interaction_summary_data = {
        "user_request": user_request,
        "card_number": card_number,
        "initial_response": data.get("initial_response", "N/A"),
        "qna": [
            {"question": previous_responses_context.get("first_question", ""), "answer": previous_responses_context.get("first_response", "")},
            {"question": previous_responses_context.get("second_question", ""), "answer": previous_responses_context.get("second_response", "")},
            {"question": third_grok_question, "answer": third_response}
        ]
    }
    interaction_summary_data["qna"] = [item for item in interaction_summary_data["qna"] if item.get("question") and item.get("answer")]

    summary_text = await get_grok_summary(user_id, interaction_summary_data, db)

    if summary_text and not summary_text.startswith("Ошибка") and not summary_text.startswith("К сожалению") and not summary_text.startswith("Не получилось"):
         await message.answer(f"✨ Давай попробуем подвести итог нашей беседы:\n{summary_text}")
         await logger_service.log_action(user_id, "summary_sent", {"summary": summary_text})
    else:
         await logger_service.log_action(user_id, "summary_failed", {"error_message": summary_text})

    try:
         await build_user_profile(user_id, db)
         logger.info(f"User profile updated after interaction for user {user_id}")
    except Exception as e:
         logger.error(f"Failed to update user profile for user {user_id} after interaction: {e}")

    await message.answer("Благодарю за твои мысли и открытость! 🙏", reply_markup=await get_main_menu(user_id, db)) # Добавляем меню здесь

    # --- Начало изменений: Новый вопрос и кнопки фидбека ---
    feedback_text = f"{name}, насколько ценной для тебя оказалась эта сессия? Удалось ли найти что-то важное или по-новому взглянуть на свой запрос?" if name else "Насколько ценной для тебя оказалась эта сессия? Удалось ли найти что-то важное или по-новому взглянуть на свой запрос?"

    # Используем card_number в callback_data для связи с сессией
    feedback_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="👍 Помогло", callback_data=f"feedback_v2_helped_{card_number}"),
        ],
        [
            types.InlineKeyboardButton(text="🤔 Интересно", callback_data=f"feedback_v2_interesting_{card_number}"),
        ],
        [
             types.InlineKeyboardButton(text="😕 Не хватило глубины", callback_data=f"feedback_v2_not_deep_{card_number}")
        ]
    ])
    await message.answer(feedback_text, reply_markup=feedback_keyboard)
    # --- Конец изменений ---

async def process_card_feedback(callback: types.CallbackQuery, state: FSMContext, db, logger_service):
    """Обрабатывает новую систему обратной связи пользователя по сессии."""
    user_id = callback.from_user.id
    name = db.get_user(user_id).get("name", "")
    callback_data = callback.data
    feedback_type = "unknown"
    card_number = 0 # Значение по умолчанию

    try:
        # Парсим callback_data нового формата: feedback_v2_<type>_<card_number>
        parts = callback_data.split('_')
        if len(parts) >= 4 and parts[0] == 'feedback' and parts[1] == 'v2':
            feedback_type = parts[2] # helped, interesting, not_deep
            try:
                 card_number = int(parts[-1]) # Последняя часть - номер карты
            except ValueError:
                 logger.error(f"Could not parse card number from feedback callback data: {callback_data}")
                 # Можно попробовать извлечь из state, если он еще не очищен, но лучше полагаться на callback
                 card_number = 0 # Или другое дефолтное значение

            # --- Начало изменений: Ответы на новый фидбек ---
            if feedback_type == "helped":
                text = "Отлично! Рад, что наша беседа была для тебя полезной. 😊 Жду тебя завтра!"
            elif feedback_type == "interesting":
                text = "Здорово, что было интересно! Размышления и новые углы зрения - это тоже важный результат. 👍"
            elif feedback_type == "not_deep":
                text = f"{name}, спасибо за честность! Мне жаль, если не удалось копнуть достаточно глубоко в этот раз. Твои идеи в /feedback помогут мне учиться и развиваться." if name else "Спасибо за честность! Мне жаль, если не удалось копнуть достаточно глубоко в этот раз. Твои идеи в /feedback помогут мне учиться и развиваться."
            else:
                logger.warning(f"Unknown feedback_v2 type: {feedback_type} in {callback_data}")
                await callback.answer("Неизвестный тип ответа.", show_alert=True)
                return # Выходим, если тип фидбека неизвестен
            # --- Конец изменений ---

            # Логируем новый фидбек
            await logger_service.log_action(user_id, "interaction_feedback", {"card_session": card_number, "feedback": feedback_type}) # Используем новый тип action

            await callback.message.edit_reply_markup(reply_markup=None) # Убираем кнопки
            await callback.message.answer(text, reply_markup=await get_main_menu(user_id, db))
            await state.clear() # Очищаем состояние
            await callback.answer() # Отвечаем на callback query

        # Обработка старого формата для обратной совместимости (если нужно)
        elif callback_data.startswith("feedback_yes_") or callback_data.startswith("feedback_no_"):
             logger.warning(f"Received old format feedback callback: {callback_data}")
             # Можно обработать как раньше или просто сказать, что формат устарел
             await callback.answer("Формат ответа обновлен.", show_alert=True)
             # await state.clear() # Очистить состояние и тут, если надо
             return

        else:
             logger.warning(f"Unknown feedback callback data format: {callback_data}")
             await callback.answer("Неизвестная команда.", show_alert=True)
             return

    except Exception as e:
        logger.error(f"Error processing interaction feedback for user {user_id}: {e}")
        await callback.answer("Произошла ошибка при обработке ответа.", show_alert=True)
        # Попытаемся очистить состояние даже при ошибке
        try:
            await state.clear()
        except Exception as clear_err:
            logger.error(f"Failed to clear state after feedback error: {clear_err}")
