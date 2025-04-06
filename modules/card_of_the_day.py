import random
import os
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import TIMEZONE, NO_CARD_LIMIT_USERS
from .ai_service import get_grok_question
from datetime import datetime

async def get_main_menu(user_id, db):
    keyboard = [[types.KeyboardButton(text="✨ Карта дня")]]
    if db.get_user(user_id)["bonus_available"]:
        keyboard.append([types.KeyboardButton(text="💌 Подсказка Вселенной")])
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, persistent=True)

async def handle_card_request(message: types.Message, state: FSMContext, db, logger):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    now = datetime.now(TIMEZONE)
    today = now.date()

    if user_id not in NO_CARD_LIMIT_USERS and db.get_user(user_id)["last_request"] and db.get_user(user_id)["last_request"].date() == today:
        text = f"{name}, ты уже вытянула карту сегодня! Новая будет завтра в 00:00 по Москве." if name else "Ты уже вытянула карту сегодня! Новая будет завтра в 00:00 по Москве."
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        return

    text = f"{name}, давай вытянем карту осознанно! 🌿 Напиши свой вопрос или нажми 'Вытянуть карту'!" if name else "Давай вытянем карту осознанно! 🌿 Напиши свой вопрос или нажми 'Вытянуть карту'!"
    await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Вытянуть карту", callback_data="draw_card")]
    ]))
    await state.set_state("waiting_for_request_text")
    await logger.log_action(user_id, "card_request_initiated")

async def draw_card(callback: types.CallbackQuery, state: FSMContext, db, logger):
    user_id = callback.from_user.id
    name = db.get_user(user_id)["name"]
    now = datetime.now(TIMEZONE)

    used_cards = db.get_user_cards(user_id)
    all_cards = list(range(1, 41))
    available_cards = [c for c in all_cards if c not in used_cards]

    if not available_cards:
        db.reset_user_cards(user_id)
        available_cards = all_cards.copy()

    card_number = random.choice(available_cards)
    db.add_user_card(user_id, card_number)
    db.update_user(user_id, {"last_request": now})

    card_path = f"cards/card_{card_number}.jpg"
    if os.path.exists(card_path):
        await callback.message.bot.send_photo(user_id, types.FSInputFile(card_path), reply_markup=await get_main_menu(user_id, db))
        text = f"{name}, как этот образ отвечает на твой запрос? Напиши свои мысли!" if name else "Как этот образ отвечает на твой запрос? Напиши свои мысли!"
        await callback.message.answer(text)
        await state.update_data(card_number=card_number, user_request="")
        await state.set_state("waiting_for_initial_response")
        await logger.log_action(user_id, "card_drawn", {"card_number": card_number})
    await callback.answer()

async def process_request_text(message: types.Message, state: FSMContext, db, logger):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    request_text = message.text.strip()
    now = datetime.now(TIMEZONE)

    used_cards = db.get_user_cards(user_id)
    all_cards = list(range(1, 41))
    available_cards = [c for c in all_cards if c not in used_cards]

    if not available_cards:
        db.reset_user_cards(user_id)
        available_cards = all_cards.copy()

    card_number = random.choice(available_cards)
    db.add_user_card(user_id, card_number)
    db.update_user(user_id, {"last_request": now})

    card_path = f"cards/card_{card_number}.jpg"
    if os.path.exists(card_path):
        await message.bot.send_photo(user_id, types.FSInputFile(card_path), reply_markup=await get_main_menu(user_id, db))
        text = f"{name}, как этот образ отвечает на твой запрос? Напиши свои мысли!" if name else "Как этот образ отвечает на твой запрос? Напиши свои мысли!"
        await message.answer(text)
        await state.update_data(card_number=card_number, user_request=request_text)
        await state.set_state("waiting_for_initial_response")
        await logger.log_action(user_id, "card_drawn_with_request", {"card_number": card_number, "request": request_text})

async def process_initial_response(message: types.Message, state: FSMContext, db, logger):
    user_id = message.from_user.id
    response_text = message.text.strip()
    data = await state.get_data()
    card_number = data["card_number"]
    user_request = data.get("user_request", "")

    await logger.log_action(user_id, "initial_response", {"card_number": card_number, "request": user_request, "response": response_text})
    grok_question = await get_grok_question(user_id, user_request or "Нет запроса", response_text, "Начало", step=1)
    await message.answer(grok_question, reply_markup=await get_main_menu(user_id, db))
    await state.update_data(first_grok_question=grok_question, initial_response=response_text)
    await state.set_state("waiting_for_first_grok_response")

async def process_first_grok_response(message: types.Message, state: FSMContext, db, logger):
    user_id = message.from_user.id
    first_response = message.text.strip()
    data = await state.get_data()
    card_number = data["card_number"]
    user_request = data.get("user_request", "")
    first_grok_question = data["first_grok_question"]

    await logger.log_action(user_id, "first_grok_response", {"card_number": card_number, "request": user_request, "question": first_grok_question, "response": first_response})
    previous_responses = {"first_question": first_grok_question, "first_response": first_response}
    second_grok_question = await get_grok_question(user_id, user_request or "Нет запроса", first_response, "Начало", step=2, previous_responses=previous_responses)
    await message.answer(second_grok_question, reply_markup=await get_main_menu(user_id, db))
    await state.update_data(second_grok_question=second_grok_question, previous_responses=previous_responses)
    await state.set_state("waiting_for_second_grok_response")

async def process_second_grok_response(message: types.Message, state: FSMContext, db, logger):
    user_id = message.from_user.id
    second_response = message.text.strip()
    data = await state.get_data()
    card_number = data["card_number"]
    user_request = data.get("user_request", "")
    previous_responses = data["previous_responses"]

    await logger.log_action(user_id, "second_grok_response", {"card_number": card_number, "request": user_request, "question": data["second_grok_question"], "response": second_response})
    previous_responses.update({"second_question": data["second_grok_question"], "second_response": second_response})
    third_grok_question = await get_grok_question(user_id, user_request or "Нет запроса", second_response, "Начало", step=3, previous_responses=previous_responses)
    await message.answer(third_grok_question, reply_markup=await get_main_menu(user_id, db))
    await state.update_data(third_grok_question=third_grok_question)
    await state.set_state("waiting_for_third_grok_response")

async def process_third_grok_response(message: types.Message, state: FSMContext, db, logger):
    user_id = message.from_user.id
    third_response = message.text.strip()
    data = await state.get_data()
    card_number = data["card_number"]
    user_request = data.get("user_request", "")

    await logger.log_action(user_id, "third_grok_response", {"card_number": card_number, "request": user_request, "question": data["third_grok_question"], "response": third_response})
    await message.answer("Благодарю за твои мысли!", reply_markup=await get_main_menu(user_id, db))
    await state.clear()
