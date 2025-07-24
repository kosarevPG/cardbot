# код/modules/card_of_the_day.py

import random
import os
import uuid  # <--- ДОБАВЛЕНО
from aiogram import types
from aiogram.fsm.context import FSMContext
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

RESOURCE_LEVELS = {
    "resource_good": "😊 Хорошо",
    "resource_medium": "😐 Средне",
    "resource_low": "😔 Низко",
}
CARDS_DIR = os.path.join(DATA_DIR, "cards") if DATA_DIR != "/data" else "cards"
if not CARDS_DIR.startswith("/data") and not os.path.exists(CARDS_DIR):
     os.makedirs(CARDS_DIR, exist_ok=True)
     logger.warning(f"Cards directory '{CARDS_DIR}' did not exist and was created. Make sure card images are present.")

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

# ================================
# === НОВЫЙ СЦЕНАРИЙ КАРТЫ ДНЯ ===
# ================================

async def handle_card_request(message: types.Message, state: FSMContext, db: Database, logger_service):
    """
    СТАРТОВАЯ ТОЧКА сценария 'Карта дня'.
    Проверяет доступность карты и запускает замер ресурса.
    """
    user_id = message.from_user.id
    user_data = db.get_user(user_id) or {}
    name = user_data.get("name") or ""
    name = name.strip() if isinstance(name, str) else ""
    now = datetime.now(TIMEZONE)
    today = now.date()

    logger.info(f"User {user_id}: Checking card availability for {today}")
    card_available = db.is_card_available(user_id, today)
    logger.info(f"User {user_id}: Card available? {card_available}")

    if user_id not in NO_CARD_LIMIT_USERS and not card_available:
        last_req_time_str = "неизвестно"
        if user_data and isinstance(user_data.get('last_request'), datetime):
            try:
                last_req_dt = user_data['last_request']
                if last_req_dt.tzinfo is None and pytz:
                    last_req_dt_local = TIMEZONE.localize(last_req_dt).astimezone(TIMEZONE)
                elif last_req_dt.tzinfo:
                    last_req_dt_local = last_req_dt.astimezone(TIMEZONE)
                else:
                    last_req_dt_local = last_req_dt
                last_req_time_str = last_req_dt_local.strftime('%H:%M %d.%m.%Y')
            except Exception as e:
                logger.error(f"Error formatting last_request time for user {user_id}: {e}")
                last_req_time_str = "ошибка времени"
        text = (f"{name}, ты уже вытянула карту сегодня (в {last_req_time_str} МСК)! Новая будет доступна завтра. ✨" if name else f"Ты уже вытянула карту сегодня (в {last_req_time_str} МСК)! Новая будет доступна завтра. ✨")
        logger.info(f"User {user_id}: Sending 'already drawn' message.")
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        return

    logger.info(f"User {user_id}: Card available, starting initial resource check.")
    
    # --- ИЗМЕНЕНИЕ: Генерация и сохранение ID сессии ---
    session_id = str(uuid.uuid4())
    await state.update_data(session_id=session_id)
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    await logger_service.log_action(user_id, "card_flow_started", {
        "trigger": "button", 
        "session_id": session_id # <--- ДОБАВЛЕНО
    })
    await ask_initial_resource(message, state, db, logger_service)

async def ask_initial_resource(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Шаг 1: Задает вопрос о начальном ресурсном состоянии."""
    user_id = message.from_user.id
    user_data = db.get_user(user_id) or {}
    name = user_data.get("name") or ""
    name = name.strip() if isinstance(name, str) else ""
    text = f"{name}, привет! ✨ Прежде чем мы начнем, как ты сейчас себя чувствуешь? Оцени свой уровень внутреннего ресурса:" if name else "Привет! ✨ Прежде чем мы начнем, как ты сейчас себя чувствуешь? Оцени свой уровень внутреннего ресурса:"
    buttons = [ types.InlineKeyboardButton(text=label.split()[0], callback_data=key) for key, label in RESOURCE_LEVELS.items() ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[buttons])
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(UserState.waiting_for_initial_resource)

async def process_initial_resource_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Шаг 1.5: Обрабатывает выбор ресурса, сохраняет его и переходит к выбору типа запроса."""
    user_id = callback.from_user.id
    resource_choice_key = callback.data
    resource_choice_label = RESOURCE_LEVELS.get(resource_choice_key, "Неизвестно")

    # --- ИЗМЕНЕНИЕ: Получение ID сессии из состояния ---
    fsm_data = await state.get_data()
    session_id = fsm_data.get("session_id", "unknown")
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    await state.update_data(initial_resource=resource_choice_label)
    await logger_service.log_action(user_id, "initial_resource_selected", {
        "resource": resource_choice_label,
        "session_id": session_id # <--- ДОБАВЛЕНО
    })
    await callback.answer(f"Понял, твое состояние: {resource_choice_label.split()[0]}")
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e: logger.warning(f"Could not edit message reply markup (initial resource) for user {user_id}: {e}")
    await ask_request_type_choice(callback, state, db, logger_service)

async def ask_request_type_choice(event: types.Message | types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Шаг 2: Спрашивает, как пользователь хочет сформулировать запрос."""
    if isinstance(event, types.CallbackQuery):
        user_id = event.from_user.id; message = event.message
    else:
        user_id = event.from_user.id; message = event
    user_data = db.get_user(user_id) or {}
    name = user_data.get("name") or ""; name = name.strip() if isinstance(name, str) else ""
    text = (f"{name}, теперь подумай о своем запросе или теме дня.\n" if name else "Теперь подумай о своем запросе или теме дня.\n") + ("Как тебе удобнее?\n\n1️⃣ Сформулировать запрос <b>в уме</b>?\n2️⃣ <b>Написать</b> запрос прямо здесь в чат?\n\n<i>(Если напишешь, я смогу задать более точные вопросы к твоим ассоциациям ✨).</i>")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[ types.InlineKeyboardButton(text="1️⃣ В уме", callback_data="request_type_mental"), types.InlineKeyboardButton(text="2️⃣ Написать", callback_data="request_type_typed"), ]])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(UserState.waiting_for_request_type_choice)

async def process_request_type_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Шаг 2.5: Обрабатывает выбор типа запроса."""
    user_id = callback.from_user.id
    request_type = callback.data
    
    # --- ИЗМЕНЕНИЕ: Получение ID сессии и новое событие ---
    fsm_data = await state.get_data()
    session_id = fsm_data.get("session_id", "unknown")
    choice_text = "mental" if request_type == "request_type_mental" else "typed"
    
    await state.update_data(request_type=request_type)
    
    # Новое событие 'question_mode_chosen'
    await logger_service.log_action(user_id, "question_mode_chosen", {
        "mode": choice_text,
        "session_id": session_id
    })
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    try: await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e: logger.warning(f"Could not edit message reply markup (request type) for user {user_id}: {e}")

    if request_type == "request_type_mental":
        await callback.answer("Хорошо, держи запрос в голове.")
        await callback.message.answer("Понял. Сейчас вытяну для тебя карту...")
        await draw_card_direct(callback.message, state, db, logger_service, user_id=user_id)
    elif request_type == "request_type_typed":
        await callback.answer("Отлично, жду твой запрос.")
        await callback.message.answer("Напиши, пожалуйста, свой запрос к карте (1-2 предложения):")
        await state.set_state(UserState.waiting_for_request_text_input)

async def process_request_text(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Шаг 3а: Получает текстовый запрос пользователя и тянет карту."""
    user_id = message.from_user.id
    request_text = message.text.strip()
    if not request_text: await message.answer("Запрос не может быть пустым..."); return
    if len(request_text) < 5: await message.answer("Пожалуйста, сформулируй запрос чуть подробнее..."); return
    
    # --- ИЗМЕНЕНИЕ: Получение ID сессии и новое событие ---
    fsm_data = await state.get_data()
    session_id = fsm_data.get("session_id", "unknown")
    
    await state.update_data(user_request=request_text)
    
    # Новое событие 'typed_question_submitted'
    await logger_service.log_action(user_id, "typed_question_submitted", {
        "length": len(request_text),
        "session_id": session_id
    })
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    await message.answer("Спасибо! ✨ Сейчас вытяну карту для твоего запроса...")
    await draw_card_direct(message, state, db, logger_service, user_id=user_id)

async def draw_card_direct(message: types.Message, state: FSMContext, db: Database, logger_service, user_id: int):
    """
    Шаг 3b / Завершение Шага 3а:
    Вытягивает карту, отправляет ее и первый вопрос об ассоциациях.
    """
    user_data_fsm = await state.get_data()
    user_request = user_data_fsm.get("user_request", "")
    session_id = user_data_fsm.get("session_id", "unknown") # <--- ДОБАВЛЕНО
    user_db_data = db.get_user(user_id) or {}
    name = user_db_data.get("name") or ""
    name = name.strip() if isinstance(name, str) else ""
    now_iso = datetime.now(TIMEZONE).isoformat()

    try:
         db.update_user(user_id, {"last_request": now_iso})
    except Exception as e:
         logger.error(f"Failed to update last_request time for user {user_id}: {e}", exc_info=True)

    card_number = None
    try:
        # ... (логика выбора карты остается без изменений) ...
        used_cards = db.get_user_cards(user_id)
        if not os.path.isdir(CARDS_DIR):
             logger.error(f"Cards directory not found or not a directory: {CARDS_DIR}")
             await message.answer("Не могу найти папку с картами..."); await state.clear(); return
        all_card_files = [f for f in os.listdir(CARDS_DIR) if f.startswith("card_") and f.endswith(".jpg")]
        if not all_card_files:
            logger.error(f"No card images found in {CARDS_DIR}.")
            await message.answer("В папке нет изображений карт..."); await state.clear(); return
        all_cards = []
        for fname in all_card_files:
             try:
                 num = int(fname.replace("card_", "").replace(".jpg", ""))
                 all_cards.append(num)
             except ValueError:
                 logger.warning(f"Could not parse card number from filename: {fname}")
                 continue
        if not all_cards:
            logger.error(f"Could not parse any valid card numbers from filenames in {CARDS_DIR}.")
            await message.answer("Проблема с именами файлов карт..."); await state.clear(); return
        available_cards = [c for c in all_cards if c not in used_cards]
        if not available_cards:
            logger.info(f"Card deck reset for user {user_id} as all cards were used.")
            db.reset_user_cards(user_id)
            available_cards = all_cards.copy()
        if not available_cards:
             logger.error(f"No available cards found even after potential reset for user {user_id}.")
             await message.answer("Не могу найти доступную карту..."); await state.clear(); return
        card_number = random.choice(available_cards)
        db.add_user_card(user_id, card_number)
        await state.update_data(card_number=card_number)
    except Exception as card_logic_err:
        logger.error(f"Error during card selection logic for user {user_id}: {card_logic_err}", exc_info=True)
        await message.answer("Произошла ошибка при выборе карты...")
        await state.clear()
        return

    card_path = os.path.join(CARDS_DIR, f"card_{card_number}.jpg")
    if not os.path.exists(card_path):
        logger.error(f"Card image file not found: {card_path} after selecting number {card_number} for user {user_id}.")
        await message.answer("Изображение для выбранной карты потерялось...")
        await state.clear()
        return

    try:
        await message.bot.send_chat_action(message.chat.id, 'upload_photo')
        await message.answer_photo(types.FSInputFile(card_path), protect_content=True)
        
        # --- ИЗМЕНЕНИЕ: Обновлен лог события ---
        await logger_service.log_action(user_id, "card_drawn", {
            "card_number": card_number,
            "request_provided": bool(user_request),
            "session_id": session_id
        })
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---

        if user_request:
            text = (f"{name}, вот карта для твоего запроса:\n<i>«{user_request}»</i>\n\nРассмотри ее внимательно. Какие <b>первые чувства, образы, мысли или воспоминания</b> приходят? Как это может быть связано с твоим запросом?"
                    if name
                    else f"Вот карта для твоего запроса:\n<i>«{user_request}»</i>\n\nРассмотри ее внимательно. Какие <b>первые чувства, образы, мысли или воспоминания</b> приходят? Как это может быть связано с твоим запросом?")
        else:
            text = (f"{name}, вот твоя карта дня.\n\nВзгляни на нее. Какие <b>первые чувства, образы, мысли или воспоминания</b> приходят? Как это может быть связано с твоим сегодняшним состоянием?"
                    if name
                    else f"Вот твоя карта дня.\n\nВзгляни на нее. Какие <b>первые чувства, образы, мысли или воспоминания</b> приходят? Как это может быть связано с твоим сегодняшним состоянием?")

        await message.answer(text, parse_mode="HTML")
        await state.set_state(UserState.waiting_for_initial_response)

    except Exception as e:
        logger.error(f"Failed to send card photo or initial question to user {user_id}: {e}", exc_info=True)
        await message.answer("Ой, не получилось отправить карту или вопрос...")
        await state.clear()

async def process_initial_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Шаг 4.5: Получает первую ассоциацию, сохраняет ее и предлагает выбор: исследовать дальше."""
    user_id = message.from_user.id
    initial_response_text = message.text.strip()
    if not initial_response_text: await message.answer("Кажется, ты ничего не написала..."); return
    if len(initial_response_text) < 3: await message.answer("Пожалуйста, опиши ассоциации чуть подробнее..."); return
    
    # --- ИЗМЕНЕНИЕ: Получение ID сессии и обновление лога ---
    data = await state.get_data()
    card_number = data.get("card_number", "N/A")
    user_request = data.get("user_request", "")
    session_id = data.get("session_id", "unknown")

    await state.update_data(initial_response=initial_response_text)

    await logger_service.log_action(user_id, "initial_response_provided", {
        "card_number": card_number,
        "request": user_request,
        "response_length": len(initial_response_text),
        "session_id": session_id
    })
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    await ask_exploration_choice(message, state, db, logger_service)

async def ask_exploration_choice(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Шаг 5: Спрашивает, хочет ли пользователь исследовать ассоциации дальше."""
    user_id = message.from_user.id
    user_data = db.get_user(user_id) or {}
    name = user_data.get("name") or ""
    name = name.strip() if isinstance(name, str) else ""
    text = (f"{name}, спасибо, что поделилась! Хочешь поисследовать эти ассоциации глубже с помощью нескольких вопросов от меня (это займет еще 5-7 минут)?" if name else "Спасибо, что поделилась! Хочешь поисследовать эти ассоциации глубже с помощью нескольких вопросов от меня (это займет еще 5-7 минут)?")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="✅ Да, давай исследуем", callback_data="explore_yes")], [types.InlineKeyboardButton(text="❌ Нет, на сегодня хватит", callback_data="explore_no")]])
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(UserState.waiting_for_exploration_choice)

async def process_exploration_choice_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Шаг 5.5: Обрабатывает выбор об исследовании."""
    user_id = callback.from_user.id
    choice = callback.data
    
    # --- ИЗМЕНЕНИЕ: Получение ID сессии и обновление лога ---
    fsm_data = await state.get_data()
    session_id = fsm_data.get("session_id", "unknown")
    choice_value = "yes" if choice == "explore_yes" else "no"
    
    await logger_service.log_action(user_id, "exploration_chosen", {
        "choice": choice_value,
        "session_id": session_id
    })
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.warning(f"Could not edit message reply markup (exploration choice) for user {user_id}: {e}")

    if choice == "explore_yes":
        await callback.answer("Отлично! Задаю первый вопрос...")
        await ask_grok_question(callback.message, state, db, logger_service, step=1, user_id=user_id)
    elif choice == "explore_no":
        await callback.answer("Хорошо, завершаем работу с картой.")
        await generate_and_send_summary(user_id=user_id, message=callback.message, state=state, db=db, logger_service=logger_service)
        await finish_interaction_flow(user_id=user_id, message=callback.message, state=state, db=db, logger_service=logger_service)

# ... (остальные функции остаются такими же, но с добавлением session_id в логи)

async def ask_grok_question(message: types.Message, state: FSMContext, db: Database, logger_service, step: int, user_id: int):
    # ... (код остается без изменений, кроме логгирования)
    data = await state.get_data()
    session_id = data.get("session_id", "unknown") # <--- ДОБАВЛЕНО
    # ...
    grok_question = await get_grok_question(...) # вызов вашей функции
    await state.update_data({f"grok_question_{step}": grok_question})
    await logger_service.log_action(user_id, "grok_question_asked", {
        "step": step, 
        "question_length": len(grok_question),
        "session_id": session_id # <--- ДОБАВЛЕНО
    })
    # ...

async def process_first_grok_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    user_id = message.from_user.id
    first_response = message.text.strip()
    if not first_response or len(first_response) < 2: await message.answer("Пожалуйста, попробуй ответить чуть подробнее."); return
    data = await state.get_data()
    session_id = data.get("session_id", "unknown") # <--- ДОБАВЛЕНО
    # ...
    await state.update_data(first_grok_response=first_response)
    await logger_service.log_action(user_id, "grok_response_provided", {
        "step": 1, 
        "response_length": len(first_response), 
        "session_id": session_id # <--- ДОБАВЛЕНО
    })
    await ask_grok_question(message, state, db, logger_service, step=2, user_id=user_id)

async def process_second_grok_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    user_id = message.from_user.id
    second_response = message.text.strip()
    if not second_response or len(second_response) < 2: await message.answer("Пожалуйста, попробуй ответить чуть подробнее."); return
    data = await state.get_data()
    session_id = data.get("session_id", "unknown") # <--- ДОБАВЛЕНО
    # ...
    await state.update_data(second_grok_response=second_response)
    await logger_service.log_action(user_id, "grok_response_provided", {
        "step": 2, 
        "response_length": len(second_response), 
        "session_id": session_id # <--- ДОБАВЛЕНО
    })
    await ask_grok_question(message, state, db, logger_service, step=3, user_id=user_id)

async def process_third_grok_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    user_id = message.from_user.id
    third_response = message.text.strip()
    if not third_response or len(third_response) < 2: await message.answer("Пожалуйста, попробуй ответить чуть подробнее."); return
    data = await state.get_data()
    session_id = data.get("session_id", "unknown") # <--- ДОБАВЛЕНО
    # ...
    await state.update_data(third_grok_response=third_response)
    await logger_service.log_action(user_id, "grok_response_provided", {
        "step": 3, 
        "response_length": len(third_response), 
        "session_id": session_id # <--- ДОБАВЛЕНО
    })
    await generate_and_send_summary(user_id=user_id, message=message, state=state, db=db, logger_service=logger_service)
    # ...
    await finish_interaction_flow(user_id=user_id, message=message, state=state, db=db, logger_service=logger_service)

async def generate_and_send_summary(user_id: int, message: types.Message, state: FSMContext, db: Database, logger_service):
    data = await state.get_data()
    session_id = data.get("session_id", "unknown") # <--- ДОБАВЛЕНО
    # ...
    summary_text = await get_grok_summary(user_id, ..., db)
    if summary_text and not summary_text.startswith(("Ошибка", "К сожалению")):
        # ...
        await logger_service.log_action(user_id, "summary_sent", {
            "summary_length": len(summary_text),
            "session_id": session_id # <--- ДОБАВЛЕНО
        })
    # ...

async def finish_interaction_flow(user_id: int, message: types.Message, state: FSMContext, db: Database, logger_service):
    # ... (код функции без изменений)
    await message.answer(...)
    await state.set_state(UserState.waiting_for_final_resource)

async def process_final_resource_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    user_id = callback.from_user.id
    resource_choice_label = ...
    data = await state.get_data()
    session_id = data.get("session_id", "unknown") # <--- ДОБАВЛЕНО
    
    await state.update_data(final_resource=resource_choice_label)
    await logger_service.log_action(user_id, "final_resource_selected", {
        "resource": resource_choice_label,
        "session_id": session_id # <--- ДОБАВЛЕНО
    })
    # ...

async def process_recharge_method(message: types.Message, state: FSMContext, db: Database, logger_service):
    user_id = message.from_user.id
    recharge_method_text = message.text.strip()
    # ...
    data = await state.get_data()
    session_id = data.get("session_id", "unknown") # <--- ДОБАВЛЕНО
    
    await logger_service.log_action(user_id, "recharge_method_provided", {
        "length": len(recharge_method_text),
        "session_id": session_id # <--- ДОБАВЛЕНО
    })
    # ...
    await show_final_feedback_and_menu(message, state, db, logger_service, user_id=user_id)

async def show_final_feedback_and_menu(message: types.Message, state: FSMContext, db: Database, logger_service, user_id: int):
    # ...
    data = await state.get_data()
    card_number = data.get("card_number", 0)
    session_id = data.get("session_id", "unknown") # <--- ДОБАВЛЕНО

    # --- ИЗМЕНЕНИЕ: Добавлен лог о завершении ---
    await logger_service.log_action(user_id, "card_flow_completed", {
        "card_session": card_number,
        "session_id": session_id
    })
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    # ... (код отправки фидбека)
    
    await logger_service.log_action(user_id, "final_feedback_prompted", {
        "card_session": card_number,
        "session_id": session_id # <--- ДОБАВЛЕНО
    })
    
    # ... (код очистки состояния)
    await state.clear()

async def process_card_feedback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    user_id = callback.from_user.id
    fsm_data = await state.get_data()
    # --- ИЗМЕНЕНИЕ: Пытаемся получить session_id из состояния, если оно еще есть ---
    session_id = fsm_data.get("session_id", "unknown_post_session")
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    
    # ...
    # Логируем действие с session_id
    await logger_service.log_action(user_id, "interaction_feedback_provided", {
        "card_session": card_number, 
        "feedback": feedback_type,
        "session_id": session_id # <--- ДОБАВЛЕНО
    })
    # ...
