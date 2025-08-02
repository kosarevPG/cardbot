# код/modules/card_of_the_day.py

import random
import os
import uuid
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
try:
    from config_local import TIMEZONE, NO_CARD_LIMIT_USERS, DATA_DIR, pytz
except ImportError:
    from config import TIMEZONE, NO_CARD_LIMIT_USERS, DATA_DIR, pytz
from .ai_service import (
    get_grok_question, get_grok_summary, build_user_profile,
    get_grok_supportive_message
)
from datetime import datetime, date
from modules.user_management import UserState
from database.db import Database
import logging

logger = logging.getLogger(__name__)

# Словарь для маппинга callback -> emoji/text
RESOURCE_LEVELS = {
    "resource_good": "😊 Хорошо",
    "resource_medium": "😐 Средне",
    "resource_low": "😔 Низко",
}

# Путь к папке с картами
CARDS_DIR = os.path.join(DATA_DIR, "cards") if DATA_DIR != "/data" else "cards"
if not CARDS_DIR.startswith("/data") and not os.path.exists(CARDS_DIR):
     os.makedirs(CARDS_DIR, exist_ok=True)
     logger.warning(f"Cards directory '{CARDS_DIR}' did not exist and was created. Make sure card images are present.")

# --- Основная клавиатура ---
async def get_main_menu(user_id, db: Database):
    """Возвращает основную клавиатуру меню."""
    keyboard = [
        [types.KeyboardButton(text="✨ Карта дня")],
        [types.KeyboardButton(text="🌙 Итог дня")]
    ]
    try:
        user_data = db.get_user(user_id)
        if user_data and user_data.get("bonus_available"):
            keyboard.append([types.KeyboardButton(text="💌 Подсказка Вселенной")])
    except Exception as e:
        logger.error(f"Error getting user data for main menu (user {user_id}): {e}", exc_info=True)
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, persistent=True)

# Заглушки для функций, которые импортируются в main.py
async def handle_card_request(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Заглушка для handle_card_request"""
    await message.answer("Функция временно недоступна")

async def process_initial_resource_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_initial_resource_callback"""
    await callback.answer("Функция временно недоступна")

async def process_request_type_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_request_type_callback"""
    await callback.answer("Функция временно недоступна")

async def process_request_text(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_request_text"""
    await message.answer("Функция временно недоступна")

async def process_initial_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_initial_response"""
    await message.answer("Функция временно недоступна")

async def process_exploration_choice_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_exploration_choice_callback"""
    await callback.answer("Функция временно недоступна")

async def process_first_grok_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_first_grok_response"""
    await message.answer("Функция временно недоступна")

async def process_second_grok_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_second_grok_response"""
    await message.answer("Функция временно недоступна")

async def process_third_grok_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_third_grok_response"""
    await message.answer("Функция временно недоступна")

async def process_final_resource_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_final_resource_callback"""
    await callback.answer("Функция временно недоступна")

async def process_recharge_method(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_recharge_method"""
    await callback.answer("Функция временно недоступна")

async def process_recharge_method_choice(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_recharge_method_choice"""
    await callback.answer("Функция временно недоступна")

async def process_card_feedback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_card_feedback"""
    await callback.answer("Функция временно недоступна")

async def process_emotion_choice(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_emotion_choice"""
    await callback.answer("Функция временно недоступна")

async def process_custom_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Заглушка для process_custom_response"""
    await message.answer("Функция временно недоступна")
