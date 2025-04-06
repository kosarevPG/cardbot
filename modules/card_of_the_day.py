import random
import os
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import TIMEZONE, NO_CARD_LIMIT_USERS, DATA_DIR
from datetime import datetime
from .ai_service import get_grok_question

async def handle_card_request(message: types.Message, state: FSMContext, db):
    user_id = message.from_user.id
    now = datetime.now(TIMEZONE)
    today = now.date()
    user_data = db.get_user(user_id)

    if user_id not in NO_CARD_LIMIT_USERS and user_data["last_request"] and user_data["last_request"].date() == today:
        await message.answer("Ты уже вытянула карту сегодня! Завтра в 00:00 по Москве будет новая.")
        return

    await message.answer("Напиши свой вопрос или нажми 'Вытянуть карту'!", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Вытянуть карту", callback_data="draw_card")]
    ]))
    await state.set_state("waiting_for_request_text")

async def draw_card(callback: types.CallbackQuery, state: FSMContext, db):
    user_id = callback.from_user.id
    now = datetime.now(TIMEZONE)
    used_cards = db.get_user_cards(user_id)
    all_cards = list(range(1, 41))
    available_cards = [c for c in all_cards if c not in used_cards]

    if not available_cards:
        used_cards = []
        db.reset_user_cards(user_id)

    card_number = random.choice(available_cards)
    db.add_user_card(user_id, card_number)
    db.update_last_request(user_id, now)

    card_path = f"cards/card_{card_number}.jpg"
    if os.path.exists(card_path):
        await callback.message.bot.send_photo(user_id, types.FSInputFile(card_path))
        await callback.message.answer("Как этот образ отвечает на твой запрос? Напиши свои мысли!")
        await state.update_data(card_number=card_number)
        await state.set_state("waiting_for_initial_response")
    await callback.answer()

async def process_initial_response(message: types.Message, state: FSMContext, db):
    user_id = message.from_user.id
    response_text = message.text.strip()
    data = await state.get_data()
    card_number = data["card_number"]
    user_request = data.get("user_request", "")
    
    db.log_action(user_id, "initial_response", {"card_number": card_number, "response": response_text})
    grok_question = await get_grok_question(user_id, user_request, response_text, "Начало", step=1)
    await message.answer(grok_question)
    await state.update_data(first_grok_question=grok_question)
    await state.set_state("waiting_for_first_grok_response")
