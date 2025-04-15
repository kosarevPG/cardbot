import random
import os
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import TIMEZONE, NO_CARD_LIMIT_USERS
from .ai_service import get_grok_question, get_grok_summary, build_user_profile, get_supportive_message
from datetime import datetime
from modules.user_management import UserState
import logging

logger = logging.getLogger(__name__)

async def get_main_menu(user_id, db):
    keyboard = [[types.KeyboardButton(text="✨ Карта дня")]]
    user_data = db.get_user(user_id)
    if user_data and user_data.get("bonus_available"):
        keyboard.append([types.KeyboardButton(text="💌 Подсказка Вселенной")])
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, persistent=True)

async def handle_card_request(message: types.Message, state: FSMContext, db, logger_service):
    user_id = message.from_user.id
    name = db.get_user(user_id).get("name", "")
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

    # Генерируем уникальный session_id (используем timestamp)
    session_id = int(now.timestamp())

    # Шаг 1: Запрашиваем начальное ресурсное состояние
    text = f"{name}, как ты чувствуешь себя сейчас? Оцени свой внутренний ресурс:" if name else "Как ты чувствуешь себя сейчас? Оцени свой внутренний ресурс:"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="😊 Хорошо", callback_data=f"resource_initial_good_{session_id}"),
            types.InlineKeyboardButton(text="😐 Средне", callback_data=f"resource_initial_medium_{session_id}"),
            types.InlineKeyboardButton(text="😔 Низко", callback_data=f"resource_initial_low_{session_id}")
        ]
    ])
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(UserState.waiting_for_initial_resource)
    await state.update_data(session_id=session_id)
    await logger_service.log_action(user_id, "card_request_initiated", {"session_id": session_id})

async def process_initial_resource(callback: types.CallbackQuery, state: FSMContext, db, logger_service):
    user_id = callback.from_user.id
    name = db.get_user(user_id).get("name", "")
    callback_data = callback.data
    data = await state.get_data()
    session_id = data.get("session_id")

    try:
        parts = callback_data.split("_")
        if len(parts) != 4 or parts[0] != "resource" or parts[1] != "initial":
            raise ValueError("Invalid callback data format")
        resource_state = parts[2]  # good, medium, low
        callback_session_id = int(parts[3])
        if callback_session_id != session_id:
            raise ValueError("Session ID mismatch")
        
        state_map = {
            "good": "😊",
            "medium": "😐",
            "low": "😔"
        }
        resource_emoji = state_map.get(resource_state)
        if not resource_emoji:
            raise ValueError("Invalid resource state")

        db.save_resource_state(user_id, session_id, resource_emoji)
        await logger_service.log_action(user_id, "initial_resource", {"session_id": session_id, "state": resource_emoji})

        # Шаг 2: Запрашиваем выбор сценария
        text = (
            f"{name}, как хочешь работать с картой сегодня? Написав запрос, ты сделаешь взаимодействие более глубоким — я смогу задавать вопросы, опираясь на него."
            if name else
            "Как хочешь работать с картой сегодня? Написав запрос, ты сделаешь взаимодействие более глубоким — я смогу задавать вопросы, опираясь на него."
        )
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Сформулировать в голове", callback_data=f"scenario_mental_{session_id}")],
            [types.InlineKeyboardButton(text="Написать запрос", callback_data=f"scenario_written_{session_id}")]
        ])
        await callback.message.answer(text, reply_markup=keyboard)
        await state.set_state(UserState.waiting_for_scenario_choice)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error processing initial resource for user {user_id}: {e}")
        await callback.message.answer("Ой, что-то пошло не так. Попробуй начать заново с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()

async def process_scenario_choice(callback: types.CallbackQuery, state: FSMContext, db, logger_service):
    user_id = callback.from_user.id
    name = db.get_user(user_id).get("name", "")
    callback_data = callback.data
    data = await state.get_data()
    session_id = data.get("session_id")

    try:
        parts = callback_data.split("_")
        if len(parts) != 3 or parts[0] != "scenario":
            raise ValueError("Invalid callback data format")
        scenario = parts[1]  # mental, written
        callback_session_id = int(parts[2])
        if callback_session_id != session_id:
            raise ValueError("Session ID mismatch")

        await logger_service.log_action(user_id, "scenario_choice", {"session_id": session_id, "scenario": scenario})

        if scenario == "mental":
            text = f"{name}, хорошо, держи свой запрос в голове. Нажми, чтобы вытянуть карту!" if name else "Хорошо, держи свой запрос в голове. Нажми, чтобы вытянуть карту!"
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="Вытянуть карту", callback_data=f"draw_card_{session_id}")]
            ])
            await callback.message.answer(text, reply_markup=keyboard)
            await state.set_state(UserState.waiting_for_card_draw)
        elif scenario == "written":
            text = f"{name}, напиши, о чём хочешь поразмышлять с картой сегодня." if name else "Напиши, о чём хочешь поразмышлять с картой сегодня."
            await callback.message.answer(text)
            await state.set_state(UserState.waiting_for_request_text)
        else:
            raise ValueError("Invalid scenario")

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error processing scenario choice for user {user_id}: {e}")
        await callback.message.answer("Ой, что-то пошло не так. Попробуй начать заново с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()

async def draw_card(callback: types.CallbackQuery, state: FSMContext, db, logger_service):
    user_id = callback.from_user.id
    name = db.get_user(user_id).get("name", "")
    now_iso = datetime.now(TIMEZONE).isoformat()
    data = await state.get_data()
    session_id = data.get("session_id")

    try:
        parts = callback.data.split("_")
        if len(parts) != 3 or parts[0] != "draw":
            raise ValueError("Invalid callback data format")
        callback_session_id = int(parts[2])
        if callback_session_id != session_id:
            raise ValueError("Session ID mismatch")

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
            await callback.message.bot.send_photo(
                user_id,
                types.FSInputFile(card_path),
                protect_content=True
            )
            text = f"{name}, взгляни на карту. Какие первые чувства, образы, воспоминания приходят? Как это может быть связано с твоим сегодняшним состоянием или запросом? Поделись своими ассоциациями." if name else "Взгляни на карту. Какие первые чувства, образы, воспоминания приходят? Как это может быть связано с твоим сегодняшним состоянием или запросом? Поделись своими ассоциациями."
            await callback.message.answer(text)
            await state.update_data(card_number=card_number, user_request="")
            await state.set_state(UserState.waiting_for_initial_response)
            await logger_service.log_action(user_id, "card_drawn", {"session_id": session_id, "card_number": card_number})
        else:
            logger.error(f"Card image not found: {card_path}")
            await callback.message.answer("Кажется, изображение для этой карты потерялось. Попробуй вытянуть еще раз.", reply_markup=await get_main_menu(user_id, db))
            await state.clear()

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error drawing card for user {user_id}: {e}")
        await callback.message.answer("Ой, не получилось вытянуть карту. Попробуй еще раз с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()

async def process_request_text(message: types.Message, state: FSMContext, db, logger_service):
    user_id = message.from_user.id
    name = db.get_user(user_id).get("name", "")
    request_text = message.text.strip()
    now_iso = datetime.now(TIMEZONE).isoformat()
    data = await state.get_data()
    session_id = data.get("session_id")

    try:
        if not request_text:
            raise ValueError("Empty request text")

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
            await message.bot.send_photo(
                user_id,
                types.FSInputFile(card_path),
                protect_content=True
            )
            text = f"{name}, вот карта для твоего запроса: '{request_text}'. Рассмотри ее внимательно. Что замечаешь? Какие мысли или чувства она вызывает в контексте твоего вопроса?" if name else f"Вот карта для твоего запроса: '{request_text}'. Рассмотри ее внимательно. Что замечаешь? Какие мысли или чувства она вызывает в контексте твоего вопроса?"
            await message.answer(text)
            await state.update_data(card_number=card_number, user_request=request_text)
            await state.set_state(UserState.waiting_for_initial_response)
            await logger_service.log_action(user_id, "card_drawn_with_request", {"session_id": session_id, "card_number": card_number, "request": request_text})
        else:
            logger.error(f"Card image not found: {card_path}")
            await message.answer("Кажется, изображение для этой карты потерялось. Попробуй вытянуть еще раз.", reply_markup=await get_main_menu(user_id, db))
            await state.clear()

    except Exception as e:
        logger.error(f"Error processing request text for user {user_id}: {e}")
        await message.answer("Ой, не получилось обработать твой запрос. Попробуй еще раз с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()

async def process_initial_response(message: types.Message, state: FSMContext, db, logger_service):
    user_id = message.from_user.id
    name = db.get_user(user_id).get("name", "")
    response_text = message.text.strip()
    data = await state.get_data()
    card_number = data.get("card_number", "N/A")
    user_request = data.get("user_request", "")
    session_id = data.get("session_id")

    try:
        if not response_text:
            raise ValueError("Empty initial response")

        await logger_service.log_action(user_id, "initial_response", {"session_id": session_id, "card_number": card_number, "request": user_request, "response": response_text})

        # Запрашиваем выбор: завершить или продолжить
        text = f"{name}, спасибо за твои ассоциации! Хочешь завершить или углубиться дальше?" if name else "Спасибо за твои ассоциации! Хочешь завершить или углубиться дальше?"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Завершить", callback_data=f"scenario_end_{session_id}")],
            [types.InlineKeyboardButton(text="Исследовать дальше", callback_data=f"scenario_continue_{session_id}")]
        ])
        await message.answer(text, reply_markup=keyboard)
        await state.update_data(initial_response=response_text)
        await state.set_state(UserState.waiting_for_continue_choice)

    except Exception as e:
        logger.error(f"Error processing initial response for user {user_id}: {e}")
        await message.answer("Ой, не получилось обработать твой ответ. Попробуй еще раз с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()

async def process_continue_choice(callback: types.CallbackQuery, state: FSMContext, db, logger_service):
    user_id = callback.from_user.id
    name = db.get_user(user_id).get("name", "")
    callback_data = callback.data
    data = await state.get_data()
    session_id = data.get("session_id")
    card_number = data.get("card_number", "N/A")
    user_request = data.get("user_request", "")
    initial_response = data.get("initial_response", "")

    try:
        parts = callback_data.split("_")
        if len(parts) != 3 or parts[0] != "scenario":
            raise ValueError("Invalid callback data format")
        choice = parts[1]  # end, continue
        callback_session_id = int(parts[2])
        if callback_session_id != session_id:
            raise ValueError("Session ID mismatch")

        await logger_service.log_action(user_id, "continue_choice", {"session_id": session_id, "choice": choice})

        if choice == "end":
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Хорошо, завершаем работу с картой. Спасибо за твои размышления! 🙏", reply_markup=await get_main_menu(user_id, db))
            await process_final_resource(callback.message, state, db, logger_service, card_number, session_id)
        elif choice == "continue":
            await callback.message.bot.send_chat_action(user_id, 'typing')
            grok_question = await get_grok_question(user_id, user_request, initial_response, "Начало", step=1, db=db)
            await logger_service.log_action(user_id, "grok_question", {"session_id": session_id, "step": 1, "grok_question": grok_question})
            await callback.message.answer(grok_question)
            await state.update_data(first_grok_question=grok_question)
            await state.set_state(UserState.waiting_for_first_grok_response)
            await callback.message.edit_reply_markup(reply_markup=None)
        else:
            raise ValueError("Invalid continue choice")

        await callback.answer()

    except Exception as e:
        logger.error(f"Error processing continue choice for user {user_id}: {e}")
        await callback.message.answer("Ой, что-то пошло не так. Попробуй начать заново с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()

async def process_first_grok_response(message: types.Message, state: FSMContext, db, logger_service):
    user_id = message.from_user.id
    first_response = message.text.strip()
    data = await state.get_data()
    card_number = data.get("card_number", "N/A")
    user_request = data.get("user_request", "")
    first_grok_question = data.get("first_grok_question", "")
    session_id = data.get("session_id")

    try:
        if not first_response:
            raise ValueError("Empty first response")

        await message.bot.send_chat_action(message.from_user.id, 'typing')
        await logger_service.log_action(user_id, "first_grok_response", {"session_id": session_id, "card_number": card_number, "request": user_request, "question": first_grok_question, "response": first_response})
        previous_responses_context = {
            "first_question": first_grok_question,
            "first_response": first_response
        }
        second_grok_question = await get_grok_question(user_id, user_request, first_response, "Продолжение", step=2, previous_responses=previous_responses_context, db=db)
        await logger_service.log_action(user_id, "grok_question", {"session_id": session_id, "step": 2, "grok_question": second_grok_question})
        await message.answer(second_grok_question)
        await state.update_data(second_grok_question=second_grok_question, previous_responses=previous_responses_context)
        await state.set_state(UserState.waiting_for_second_grok_response)

    except Exception as e:
        logger.error(f"Error processing first grok response for user {user_id}: {e}")
        await message.answer("Ой, не получилось обработать твой ответ. Попробуй еще раз с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()

async def process_second_grok_response(message: types.Message, state: FSMContext, db, logger_service):
    user_id = message.from_user.id
    second_response = message.text.strip()
    data = await state.get_data()
    card_number = data.get("card_number", "N/A")
    user_request = data.get("user_request", "")
    second_grok_question = data.get("second_grok_question", "")
    previous_responses_context = data.get("previous_responses", {})
    session_id = data.get("session_id")

    try:
        if not second_response:
            raise ValueError("Empty second response")

        await logger_service.log_action(user_id, "second_grok_response", {"session_id": session_id, "card_number": card_number, "request": user_request, "question": second_grok_question, "response": second_response})
        previous_responses_context["second_question"] = second_grok_question
        previous_responses_context["second_response"] = second_response
        third_grok_question = await get_grok_question(user_id, user_request, second_response, "Завершение", step=3, previous_responses=previous_responses_context, db=db)
        await logger_service.log_action(user_id, "grok_question", {"session_id": session_id, "step": 3, "grok_question": third_grok_question})
        await message.answer(third_grok_question)
        await state.update_data(third_grok_question=third_grok_question, previous_responses=previous_responses_context)
        await state.set_state(UserState.waiting_for_third_grok_response)

    except Exception as e:
        logger.error(f"Error processing second grok response for user {user_id}: {e}")
        await message.answer("Ой, не получилось обработать твой ответ. Попробуй еще раз с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()

async def process_third_grok_response(message: types.Message, state: FSMContext, db, logger_service):
    user_id = message.from_user.id
    name = db.get_user(user_id).get("name", "")
    third_response = message.text.strip()
    data = await state.get_data()
    card_number = data.get("card_number", 0)
    user_request = data.get("user_request", "")
    third_grok_question = data.get("third_grok_question", "")
    previous_responses_context = data.get("previous_responses", {})
    session_id = data.get("session_id")

    try:
        if not third_response:
            raise ValueError("Empty third response")

        await logger_service.log_action(user_id, "third_grok_response", {"session_id": session_id, "card_number": card_number, "request": user_request, "question": third_grok_question, "response": third_response})

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

        await message.bot.send_chat_action(message.from_user.id, 'typing')
        summary_text = await get_grok_summary(user_id, interaction_summary_data, db)

        if summary_text and not summary_text.startswith("Ошибка") and not summary_text.startswith("К сожалению") and not summary_text.startswith("Не получилось"):
            await message.answer(f"✨ Давай попробуем подвести итог нашей беседы:\n{summary_text}")
            await logger_service.log_action(user_id, "summary_sent", {"session_id": session_id, "summary": summary_text})
        else:
            await logger_service.log_action(user_id, "summary_failed", {"session_id": session_id, "error_message": summary_text})

        await message.bot.send_chat_action(message.from_user.id, 'typing')
        try:
            await build_user_profile(user_id, db)
            logger.info(f"User profile updated after interaction for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to update user profile for user {user_id} after interaction: {e}")

        await process_final_resource(message, state, db, logger_service, card_number, session_id)

    except Exception as e:
        logger.error(f"Error processing third grok response for user {user_id}: {e}")
        await message.answer("Ой, не получилось обработать твой ответ. Попробуй еще раз с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()

async def process_final_resource(message: types.Message, state: FSMContext, db, logger_service, card_number, session_id):
    user_id = message.from_user.id
    name = db.get_user(user_id).get("name", "")

    text = f"{name}, как ты чувствуешь себя теперь? Как изменился твой внутренний ресурс?" if name else "Как ты чувствуешь себя теперь? Как изменился твой внутренний ресурс?"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="😊 Хорошо", callback_data=f"resource_final_good_{session_id}"),
            types.InlineKeyboardButton(text="😐 Средне", callback_data=f"resource_final_medium_{session_id}"),
            types.InlineKeyboardButton(text="😔 Низко", callback_data=f"resource_final_low_{session_id}")
        ]
    ])
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(UserState.waiting_for_final_resource)
    await state.update_data(card_number=card_number)

async def process_final_resource_response(callback: types.CallbackQuery, state: FSMContext, db, logger_service):
    user_id = callback.from_user.id
    name = db.get_user(user_id).get("name", "")
    callback_data = callback.data
    data = await state.get_data()
    session_id = data.get("session_id")
    card_number = data.get("card_number", 0)

    try:
        parts = callback_data.split("_")
        if len(parts) != 4 or parts[0] != "resource" or parts[1] != "final":
            raise ValueError("Invalid callback data format")
        resource_state = parts[2]
        callback_session_id = int(parts[3])
        if callback_session_id != session_id:
            raise ValueError("Session ID mismatch")

        state_map = {
            "good": "😊",
            "medium": "😐",
            "low": "😔"
        }
        resource_emoji = state_map.get(resource_state)
        if not resource_emoji:
            raise ValueError("Invalid resource state")

        await logger_service.log_action(user_id, "final_resource", {"session_id": session_id, "state": resource_emoji})

        if resource_state == "low":
            await callback.message.bot.send_chat_action(user_id, 'typing')
            supportive_message = await get_supportive_message(user_id, db)
            await callback.message.answer(supportive_message)
            await callback.message.answer(f"{name}, что обычно помогает тебе восстановить силы?" if name else "Что обычно помогает тебе восстановить силы?")
            db.update_resource_final_state(user_id, session_id, resource_emoji)
            await state.set_state(UserState.waiting_for_recovery_method)
        else:
            db.update_resource_final_state(user_id, session_id, resource_emoji)
            await callback.message.answer(f"{name}, благодарю за твои мысли и открытость! 🙏" if name else "Благодарю за твои мысли и открытость! 🙏", reply_markup=await get_main_menu(user_id, db))
            feedback_text = f"{name}, насколько ценной для тебя оказалась эта сессия? Удалось ли найти что-то важное или по-новому взглянуть на свой запрос?" if name else "Насколько ценной для тебя оказалась эта сессия? Удалось ли найти что-то важное или по-новому взглянуть на свой запрос?"
            feedback_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="👍 Помогло", callback_data=f"feedback_v2_helped_{card_number}")],
                [types.InlineKeyboardButton(text="🤔 Интересно", callback_data=f"feedback_v2_interesting_{card_number}")],
                [types.InlineKeyboardButton(text="😕 Не хватило глубины", callback_data=f"feedback_v2_notdeep_{card_number}")]
            ])
            await callback.message.answer(feedback_text, reply_markup=feedback_keyboard)
            await state.set_state(UserState.waiting_for_card_feedback)

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error processing final resource for user {user_id}: {e}")
        await callback.message.answer("Ой, что-то пошло не так. Попробуй начать заново с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()

async def process_recovery_method(message: types.Message, state: FSMContext, db, logger_service):
    user_id = message.from_user.id
    name = db.get_user(user_id).get("name", "")
    recovery_method = message.text.strip()
    data = await state.get_data()
    session_id = data.get("session_id")
    card_number = data.get("card_number", 0)

    try:
        if not recovery_method:
            raise ValueError("Empty recovery method")

        db.update_resource_final_state(user_id, session_id, "😔", recovery_method)
        await logger_service.log_action(user_id, "recovery_method", {"session_id": session_id, "method": recovery_method})

        await message.answer(f"{name}, спасибо, что поделилась! Я запомню. 🙏" if name else "Спасибо, что поделилась! Я запомню. 🙏", reply_markup=await get_main_menu(user_id, db))
        feedback_text = f"{name}, насколько ценной для тебя оказалась эта сессия? Удалось ли найти что-то важное или по-новому взглянуть на свой запрос?" if name else "Насколько ценной для тебя оказалась эта сессия? Удалось ли найти что-то важное или по-новому взглянуть на свой запрос?"
        feedback_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="👍 Помогло", callback_data=f"feedback_v2_helped_{card_number}")],
            [types.InlineKeyboardButton(text="🤔 Интересно", callback_data=f"feedback_v2_interesting_{card_number}")],
            [types.InlineKeyboardButton(text="😕 Не хватило глубины", callback_data=f"feedback_v2_notdeep_{card_number}")]
        ])
        await message.answer(feedback_text, reply_markup=feedback_keyboard)
        await state.set_state(UserState.waiting_for_card_feedback)

    except Exception as e:
        logger.error(f"Error processing recovery method for user {user_id}: {e}")
        await message.answer("Ой, не получилось сохранить твой ответ. Попробуй еще раз с '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()

async def process_card_feedback(callback: types.CallbackQuery, state: FSMContext, db, logger_service):
    user_id = callback.from_user.id
    name = db.get_user(user_id).get("name", "")
    callback_data = callback.data
    feedback_type = "unknown"
    card_number = 0

    try:
        parts = callback_data.split('_')
        if len(parts) >= 4 and parts[0] == 'feedback' and parts[1] == 'v2':
            feedback_type = parts[2]
            try:
                card_number = int(parts[-1])
            except ValueError:
                logger.error(f"Could not parse card number from feedback callback data: {callback_data}")
                card_number = 0

            if feedback_type == "helped":
                text = "Отлично! Рад, что наша беседа была для тебя полезной. 😊 Жду тебя завтра!"
            elif feedback_type == "interesting":
                text = "Здорово, что было интересно! Размышления и новые углы зрения - это тоже важный результат. 👍"
            elif feedback_type == "notdeep":
                text = f"{name}, спасибо за честность! Мне жаль, если не удалось копнуть достаточно глубоко в этот раз. Твои идеи в /feedback помогут мне учиться и развиваться." if name else "Спасибо за честность! Мне жаль, если не удалось копнуть достаточно глубоко в этот раз. Твои идеи в /feedback помогут мне учиться и развиваться."
            else:
                logger.warning(f"Unknown feedback_v2 type: {feedback_type} in {callback_data}")
                await callback.answer("Неизвестный тип ответа.", show_alert=True)
                return

            await logger_service.log_action(user_id, "interaction_feedback", {"card_session": card_number, "feedback": feedback_type})
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(text, reply_markup=await get_main_menu(user_id, db))
            await state.clear()
            await callback.answer()

        elif callback_data.startswith("feedback_yes_") or callback_data.startswith("feedback_no_"):
            logger.warning(f"Received old format feedback callback: {callback_data}")
            await callback.answer("Формат ответа обновлен.", show_alert=True)
            return

        else:
            logger.warning(f"Unknown feedback callback data format: {callback_data}")
            await callback.answer("Неизвестная команда.", show_alert=True)
            return

    except Exception as e:
        logger.error(f"Error processing interaction feedback for user {user_id}: {e}")
        await callback.answer("Произошла ошибка при обработке ответа.", show_alert=True)
        try:
            await state.clear()
        except Exception as clear_err:
            logger.error(f"Failed to clear state after feedback error: {clear_err}")
