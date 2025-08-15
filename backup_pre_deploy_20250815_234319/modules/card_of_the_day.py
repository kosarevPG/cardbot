# код/modules/card_of_the_day.py

import random
import os
import uuid  # <--- ДОБАВЛЕНО
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
try:
    from config_local import TIMEZONE, NO_CARD_LIMIT_USERS, DATA_DIR, pytz
except ImportError:
    from config import TIMEZONE, NO_CARD_LIMIT_USERS, DATA_DIR, pytz # Убедимся, что pytz импортирован
# Импортируем функции из ai_service
from .ai_service import (
    get_grok_question, get_grok_summary, build_user_profile,
    get_grok_supportive_message
)
from datetime import datetime, date # Добавили date
from modules.user_management import UserState
from database.db import Database
import logging

logger = logging.getLogger(__name__)

# --- СЛОВАРЬ ЗНАЧЕНИЙ КАРТ ---
CARD_MEANINGS = {
    1: {
        "name": "Маг",
        "meaning": "Творческая сила, новые начинания, воля к действию, мастерство"
    },
    2: {
        "name": "Верховная Жрица",
        "meaning": "Интуиция, внутренняя мудрость, тайные знания, медитация"
    },
    3: {
        "name": "Императрица",
        "meaning": "Плодородие, изобилие, материнство, творчество, природа"
    },
    4: {
        "name": "Император",
        "meaning": "Власть, стабильность, структура, лидерство, авторитет"
    },
    5: {
        "name": "Иерофант",
        "meaning": "Духовность, традиции, обучение, наставничество, вера"
    },
    6: {
        "name": "Влюбленные",
        "meaning": "Любовь, выбор, гармония, партнерство, единство"
    },
    7: {
        "name": "Колесница",
        "meaning": "Движение вперед, контроль, победа, прогресс, решимость"
    },
    8: {
        "name": "Сила",
        "meaning": "Внутренняя сила, мужество, терпение, мягкая власть"
    },
    9: {
        "name": "Отшельник",
        "meaning": "Самоанализ, одиночество, поиск истины, внутренний свет"
    },
    10: {
        "name": "Колесо Фортуны",
        "meaning": "Изменения, циклы, судьба, новые возможности, поворот"
    },
    11: {
        "name": "Справедливость",
        "meaning": "Баланс, справедливость, правда, карма, равновесие"
    },
    12: {
        "name": "Повешенный",
        "meaning": "Жертва, новый взгляд, пауза, духовное пробуждение"
    },
    13: {
        "name": "Смерть",
        "meaning": "Трансформация, конец и начало, глубокие изменения"
    },
    14: {
        "name": "Умеренность",
        "meaning": "Баланс, гармония, терпение, исцеление, смешение"
    },
    15: {
        "name": "Дьявол",
        "meaning": "Искушения, привязанности, материализм, освобождение"
    },
    16: {
        "name": "Башня",
        "meaning": "Внезапные изменения, разрушение старых структур, откровение"
    },
    17: {
        "name": "Звезда",
        "meaning": "Надежда, вдохновение, духовность, исцеление, вера"
    },
    18: {
        "name": "Луна",
        "meaning": "Интуиция, иллюзии, подсознание, творчество, тайны"
    },
    19: {
        "name": "Солнце",
        "meaning": "Радость, успех, энергия, оптимизм, жизненная сила"
    },
    20: {
        "name": "Суд",
        "meaning": "Возрождение, призыв, трансформация, прощение, обновление"
    },
    21: {
        "name": "Мир",
        "meaning": "Завершение, интеграция, путешествие, целостность, гармония"
    },
    22: {
        "name": "Шут",
        "meaning": "Новые начинания, спонтанность, свобода, приключения, вера"
    },
    23: {
        "name": "Король Мечей",
        "meaning": "Интеллект, ясность мысли, правда, справедливость, власть"
    },
    24: {
        "name": "Королева Мечей",
        "meaning": "Независимость, ясность, мудрость, одиночество, сила"
    },
    25: {
        "name": "Рыцарь Мечей",
        "meaning": "Действие, конфликт, скорость, перемены, решительность"
    },
    26: {
        "name": "Паж Мечей",
        "meaning": "Новые идеи, обучение, любопытство, сообщения, начало"
    },
    27: {
        "name": "Десятка Мечей",
        "meaning": "Конец, поражение, боль, переход, освобождение"
    },
    28: {
        "name": "Девятка Мечей",
        "meaning": "Тревога, страх, беспокойство, кошмары, стресс"
    },
    29: {
        "name": "Восьмерка Мечей",
        "meaning": "Ограничения, ловушка, беспомощность, выбор, освобождение"
    },
    30: {
        "name": "Семерка Мечей",
        "meaning": "Хитрость, скрытность, стратегия, обман, тактика"
    },
    31: {
        "name": "Шестерка Мечей",
        "meaning": "Переход, путешествие, исцеление, движение, надежда"
    },
    32: {
        "name": "Пятерка Мечей",
        "meaning": "Конфликт, поражение, потеря, разочарование, урок"
    },
    33: {
        "name": "Четверка Мечей",
        "meaning": "Отдых, восстановление, медитация, покой, исцеление"
    },
    34: {
        "name": "Тройка Мечей",
        "meaning": "Боль, разбитое сердце, страдание, разлука, печаль"
    },
    35: {
        "name": "Двойка Мечей",
        "meaning": "Выбор, баланс, нерешительность, компромисс, равновесие"
    },
    36: {
        "name": "Туз Мечей",
        "meaning": "Новые идеи, прорыв, ясность, правда, победа"
    },
    37: {
        "name": "Король Пентаклей",
        "meaning": "Материальный успех, стабильность, богатство, практичность"
    },
    38: {
        "name": "Королева Пентаклей",
        "meaning": "Изобилие, забота, материнство, процветание, дом"
    },
    39: {
        "name": "Рыцарь Пентаклей",
        "meaning": "Трудолюбие, надежность, медленный прогресс, преданность"
    },
    40: {
        "name": "Паж Пентаклей",
        "meaning": "Новые возможности, обучение, практические навыки, рост"
    }
}

def get_card_info(card_number: int) -> dict:
    """
    Получает информацию о карте по номеру.
    
    Args:
        card_number: Номер карты (1-40)
        
    Returns:
        dict: Словарь с названием и значением карты
    """
    return CARD_MEANINGS.get(card_number, {
        "name": f"Карта {card_number}",
        "meaning": "Значение не определено"
    })

# --- КОНЕЦ СЛОВАРЯ ЗНАЧЕНИЙ КАРТ ---

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


# --- Основная клавиатура (ИЗМЕНЕНО) ---
async def get_main_menu(user_id, db: Database):
    """Возвращает основную клавиатуру меню. (ИЗМЕНЕНО)"""
    keyboard = [
        [types.KeyboardButton(text="✨ Карта дня")],
        [types.KeyboardButton(text="🌙 Итог дня")]
    ]
    try:
        user_data = db.get_user(user_id)
        # --- ИЗМЕНЕНИЕ: Добавляем кнопку в конец, если бонус доступен ---
        if user_data and user_data.get("bonus_available"):
            # Используем append вместо insert(1, ...)
            keyboard.append([types.KeyboardButton(text="💌 Подсказка Вселенной")])
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    except Exception as e:
        logger.error(f"Error getting user data for main menu (user {user_id}): {e}", exc_info=True)
    # Используем persistent=True для постоянного отображения
    return types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, persistent=True)


# ================================
# === НОВЫЙ СЦЕНАРИЙ КАРТЫ ДНЯ ===
# ================================

# --- Шаг 0: Начало флоу ---
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
        
        # Логируем попытку повторного использования
        db.log_scenario_step(user_id, 'card_of_day', 'already_used_today', {
            'last_request_time': last_req_time_str,
            'today': today.isoformat()
        })
        
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        return

    logger.info(f"User {user_id}: Card available, starting initial resource check.")
    
    # Начинаем сценарий "Карта дня"
    session_id = db.start_user_scenario(user_id, 'card_of_day')
    db.log_scenario_step(user_id, 'card_of_day', 'started', {
        'session_id': session_id,
        'today': today.isoformat(),
        'card_available': card_available
    })
    
    # Сохраняем session_id в состоянии
    await state.update_data(session_id=session_id)

    await logger_service.log_action(user_id, "card_flow_started", {
        "trigger": "button",
        "session_id": session_id
    })
    await ask_initial_resource(message, state, db, logger_service)

# --- Шаг 1: Замер начального ресурса ---
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

# --- Обработка Шага 1 ---
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
    
    # Логируем выбор начального ресурса
    db.log_scenario_step(user_id, 'card_of_day', 'initial_resource_selected', {
        'resource': resource_choice_label,
        'session_id': session_id
    })
    
    await logger_service.log_action(user_id, "initial_resource_selected", {
        "resource": resource_choice_label,
        "session_id": session_id
    })
    await callback.answer(f"Понял, твое состояние: {resource_choice_label.split()[0]}")
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e: logger.warning(f"Could not edit message reply markup (initial resource) for user {user_id}: {e}")
    await ask_request_type_choice(callback, state, db, logger_service)

# --- Шаг 2: Выбор типа запроса ---
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

# --- Обработка Шага 2 ---
async def process_request_type_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Шаг 2.5: Обрабатывает выбор типа запроса."""
    user_id = callback.from_user.id
    request_type = callback.data
    
    # --- ИЗМЕНЕНИЕ: Получение ID сессии и новое событие ---
    fsm_data = await state.get_data()
    session_id = fsm_data.get("session_id", "unknown")
    choice_mode = "mental" if request_type == "request_type_mental" else "typed"
    
    await state.update_data(request_type=request_type)
    
    # Логируем выбор типа запроса
    db.log_scenario_step(user_id, 'card_of_day', 'request_type_selected', {
        'request_type': choice_mode,
        'session_id': session_id
    })
    
    await logger_service.log_action(user_id, "question_mode_chosen", {
        "mode": choice_mode,
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

# --- Шаг 3: Обработка текстового запроса ---
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
    
    # Логируем текстовый запрос
    db.log_scenario_step(user_id, 'card_of_day', 'text_request_provided', {
        'request_length': len(request_text),
        'session_id': session_id
    })
    
    # Сохраняем запрос для анализа
    db.save_user_request(user_id, request_text, session_id)
    
    await logger_service.log_action(user_id, "typed_question_submitted", {
        "request": request_text,
        "length": len(request_text),
        "session_id": session_id
    })
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    await message.answer("Спасибо! ✨ Сейчас вытяну карту для твоего запроса...")
    await draw_card_direct(message, state, db, logger_service, user_id=user_id)

# --- Функция вытягивания карты ---
async def draw_card_direct(message: types.Message, state: FSMContext, db: Database, logger_service, user_id: int):
    """Шаг 3b: Вытягивает карту, отправляет ее и первый вопрос об ассоциациях."""
    user_data_fsm = await state.get_data()
    user_request = user_data_fsm.get("user_request", "")
    session_id = user_data_fsm.get("session_id", "unknown")
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
        used_cards = db.get_user_cards(user_id)
        if not os.path.isdir(CARDS_DIR):
             logger.error(f"Cards directory not found or not a directory: {CARDS_DIR}")
             await message.answer("Не могу найти папку с картами..."); await state.clear(); return
        all_card_files = [f for f in os.listdir(CARDS_DIR) if f.startswith("card_") and f.endswith(".jpg")]
        if not all_card_files:
            logger.error(f"No card images found in {CARDS_DIR}.")
            await message.answer("В папке нет изображений карт..."); await state.clear(); return
        all_cards = [int(f.replace("card_", "").replace(".jpg", "")) for f in all_card_files]
        available_cards = [c for c in all_cards if c not in used_cards]
        if not available_cards:
            logger.info(f"Card deck reset for user {user_id} as all cards were used.")
            db.reset_user_cards(user_id)
            available_cards = all_cards
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
        
        # Логируем вытягивание карты
        db.log_scenario_step(user_id, 'card_of_day', 'card_drawn', {
            'card_number': card_number,
            'session_id': session_id,
            'user_request': user_request[:100] if user_request else None
        })
        
        # --- ИЗМЕНЕНИЕ: Обновлен лог события ---
        await logger_service.log_action(user_id, "card_drawn", {
            "card_number": card_number,
            "session_id": session_id
        })
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---

        if user_request:
            text = (f"{name}, вот карта для твоего запроса:\n<i>«{user_request}»</i>\n\nВзгляни на карту и прислушайся к себе. Какие чувства и мысли она у тебя вызывает? Выбери эмоцию или напиши свой вариант."
                    if name
                    else f"Вот карта для твоего запроса:\n<i>«{user_request}»</i>\n\nВзгляни на карту и прислушайся к себе. Какие чувства и мысли она у тебя вызывает? Выбери эмоцию или напиши свой вариант.")
        else:
            text = (f"{name}, вот твоя карта дня.\n\nВзгляни на карту и прислушайся к себе. Какие чувства и мысли она у тебя вызывает? Выбери эмоцию или напиши свой вариант."
                    if name
                    else f"Вот твоя карта дня.\n\nВзгляни на карту и прислушайся к себе. Какие чувства и мысли она у тебя вызывает? Выбери эмоцию или напиши свой вариант.")

        # Создаем клавиатуру с эмоциями
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="😊 Радость", callback_data="emotion_joy"),
                types.InlineKeyboardButton(text="🤔 Задумчивость", callback_data="emotion_thoughtful")
            ],
            [
                types.InlineKeyboardButton(text="😥 Печаль", callback_data="emotion_sadness"),
                types.InlineKeyboardButton(text="😠 Злость", callback_data="emotion_anger")
            ],
            [
                types.InlineKeyboardButton(text="✨ Надежда", callback_data="emotion_hope"),
                types.InlineKeyboardButton(text="😌 Спокойствие", callback_data="emotion_calm")
            ],
            [
                types.InlineKeyboardButton(text="✍️ Написать свой вариант", callback_data="emotion_custom")
            ]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(UserState.waiting_for_emotion_choice)
    except Exception as e:
        logger.error(f"Failed to send card photo or initial question to user {user_id}: {e}", exc_info=True)
        await message.answer("Ой, не получилось отправить карту или вопрос...")
        await state.clear()

# --- Шаг 4: Обработка первой ассоциации ---
async def process_initial_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    user_id = message.from_user.id
    initial_response_text = message.text.strip()
    if not initial_response_text: await message.answer("Кажется, ты ничего не написала..."); return
    if len(initial_response_text) < 3: await message.answer("Пожалуйста, опиши ассоциации чуть подробнее..."); return
    
    # --- ИЗМЕНЕНИЕ: Получение ID сессии и обновление лога ---
    data = await state.get_data()
    session_id = data.get("session_id", "unknown")

    await state.update_data(initial_response=initial_response_text)

    # Логируем первую ассоциацию
    db.log_scenario_step(user_id, 'card_of_day', 'initial_response_provided', {
        'response_length': len(initial_response_text),
        'session_id': session_id
    })

    await logger_service.log_action(user_id, "initial_response_provided", {
        "response": initial_response_text,
        "length": len(initial_response_text),
        "session_id": session_id
    })
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    await ask_exploration_choice(message, state, db, logger_service)

# --- Шаг 5: Выбор - исследовать дальше? ---
async def ask_exploration_choice(message: types.Message, state: FSMContext, db: Database, logger_service):
    user_id = message.from_user.id
    user_data = db.get_user(user_id) or {}
    name = user_data.get("name") or ""
    name = name.strip() if isinstance(name, str) else ""
    text = (f"{name}, спасибо, что поделилась! Хочешь поисследовать эти ассоциации глубже с помощью нескольких вопросов от меня (это займет пару минут)?" if name else "Спасибо, что поделилась! Хочешь поисследовать эти ассоциации глубже с помощью нескольких вопросов от меня (это займет пару минут)?")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="✅ Да, давай исследуем", callback_data="explore_yes")], [types.InlineKeyboardButton(text="❌ Нет, на сегодня хватит", callback_data="explore_no")]])
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(UserState.waiting_for_exploration_choice)

# --- Обработка Шага 5 ---
async def process_exploration_choice_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    user_id = callback.from_user.id
    choice = callback.data
    
    # --- ИЗМЕНЕНИЕ: Получение ID сессии и обновление лога ---
    fsm_data = await state.get_data()
    session_id = fsm_data.get("session_id", "unknown")
    choice_value = "yes" if choice == "explore_yes" else "no"
    
    # Логируем выбор рефлексии с ИИ
    db.log_scenario_step(user_id, 'card_of_day', 'ai_reflection_choice', {
        'choice': choice_value,
        'session_id': session_id
    })
    
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

# --- Шаг 6: Цикл вопросов Grok ---
async def ask_grok_question(message: types.Message, state: FSMContext, db: Database, logger_service, step: int, user_id: int):
    data = await state.get_data()
    session_id = data.get("session_id", "unknown")
    user_request = data.get("user_request", "")
    initial_response = data.get("initial_response", "")
    previous_responses_context = { "initial_response": initial_response }
    if step > 1:
        previous_responses_context["grok_question_1"] = data.get("grok_question_1")
        previous_responses_context["first_grok_response"] = data.get("first_grok_response")
    if step > 2:
        previous_responses_context["grok_question_2"] = data.get("grok_question_2")
        previous_responses_context["second_grok_response"] = data.get("second_grok_response")

    if step == 1: current_user_response = initial_response
    elif step == 2: current_user_response = data.get("first_grok_response", "")
    elif step == 3: current_user_response = data.get("second_grok_response", "")
    else:
        logger.error(f"Invalid step number {step} for Grok question for user {user_id}.")
        await message.answer("Произошла внутренняя ошибка шага..."); await state.clear(); return

    if not current_user_response:
        logger.error(f"Missing user response data for step {step} for user {user_id}.")
        await message.answer("Не могу найти предыдущий ответ для вопроса..."); await state.clear(); return

    try:
        await message.bot.send_chat_action(user_id, 'typing')
    except Exception as e:
        logger.error(f"Failed send_chat_action (typing) to user {user_id} in ask_grok_question: {e}")

    grok_question = await get_grok_question(user_id=user_id, user_request=user_request, user_response=current_user_response, feedback_type="exploration", step=step, previous_responses=previous_responses_context, db=db)
    await state.update_data({f"grok_question_{step}": grok_question})
    
    await logger_service.log_action(user_id, "grok_question_asked", {
        "step": step, 
        "question_length": len(grok_question),
        "question": grok_question,
        "session_id": session_id
    })

    try:
        await message.answer(grok_question)
    except Exception as e:
        logger.error(f"Failed to send Grok question (step {step}) to user {user_id}: {e}", exc_info=True)
        await message.answer("Не удалось отправить вопрос..."); await state.clear(); return

    if step == 1: await state.set_state(UserState.waiting_for_first_grok_response)
    elif step == 2: await state.set_state(UserState.waiting_for_second_grok_response)
    elif step == 3: await state.set_state(UserState.waiting_for_third_grok_response)
    else:
        logger.error(f"Invalid step {step} when trying to set next state for user {user_id}.")
        await state.clear()

# --- Обработка ответов на вопросы Grok ---
async def process_first_grok_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    user_id = message.from_user.id
    first_response = message.text.strip()
    if not first_response or len(first_response) < 2: await message.answer("Пожалуйста, попробуй ответить чуть подробнее."); return
    data = await state.get_data()
    session_id = data.get("session_id", "unknown")
    await state.update_data(first_grok_response=first_response)
    
    # Логируем ответ на первый ИИ-вопрос
    db.log_scenario_step(user_id, 'card_of_day', 'ai_response_1_provided', {
        'response_length': len(first_response),
        'session_id': session_id
    })
    
    await logger_service.log_action(user_id, "grok_response_provided", {
        "step": 1,
        "response": first_response,
        "length": len(first_response),
        "session_id": session_id
    })
    await ask_grok_question(message, state, db, logger_service, step=2, user_id=user_id)

async def process_second_grok_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    user_id = message.from_user.id
    second_response = message.text.strip()
    if not second_response or len(second_response) < 2: await message.answer("Пожалуйста, попробуй ответить чуть подробнее."); return
    data = await state.get_data()
    session_id = data.get("session_id", "unknown")
    await state.update_data(second_grok_response=second_response)
    
    # Логируем ответ на второй ИИ-вопрос
    db.log_scenario_step(user_id, 'card_of_day', 'ai_response_2_provided', {
        'response_length': len(second_response),
        'session_id': session_id
    })
    
    await logger_service.log_action(user_id, "grok_response_provided", {
        "step": 2,
        "response": second_response,
        "length": len(second_response),
        "session_id": session_id
    })
    await ask_grok_question(message, state, db, logger_service, step=3, user_id=user_id)

async def process_third_grok_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    user_id = message.from_user.id
    third_response = message.text.strip()
    if not third_response or len(third_response) < 2: await message.answer("Пожалуйста, попробуй ответить чуть подробнее."); return
    data = await state.get_data()
    session_id = data.get("session_id", "unknown")
    await state.update_data(third_grok_response=third_response)
    
    # Логируем ответ на третий ИИ-вопрос
    db.log_scenario_step(user_id, 'card_of_day', 'ai_response_3_provided', {
        'response_length': len(third_response),
        'session_id': session_id
    })
    
    await logger_service.log_action(user_id, "grok_response_provided", {
        "step": 3,
        "response": third_response,
        "length": len(third_response),
        "session_id": session_id
    })
    await generate_and_send_summary(user_id=user_id, message=message, state=state, db=db, logger_service=logger_service)
    try:
        await build_user_profile(user_id, db)
        logger.info(f"User profile updated after full Grok interaction for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to update user profile after interaction for user {user_id}: {e}", exc_info=True)
    await finish_interaction_flow(user_id=user_id, message=message, state=state, db=db, logger_service=logger_service)

# --- Генерация и отправка саммари ---
async def generate_and_send_summary(user_id: int, message: types.Message, state: FSMContext, db: Database, logger_service):
    if not isinstance(user_id, int):
        logger.error("Invalid user_id passed to generate_and_send_summary")
        return

    data = await state.get_data()
    session_id = data.get("session_id", "unknown")
    logger.info(f"Starting summary generation for user {user_id}")
    try:
        await message.bot.send_chat_action(user_id, 'typing')
    except Exception as e:
        logger.error(f"Failed send_chat_action (typing) to user {user_id} in generate_and_send_summary: {e}")

    interaction_summary_data = {
        "user_request": data.get("user_request", ""),
        "card_number": data.get("card_number", "N/A"),
        "initial_response": data.get("initial_response"),
        "qna": [
            {"question": data.get("grok_question_1"), "answer": data.get("first_grok_response")},
            {"question": data.get("grok_question_2"), "answer": data.get("second_grok_response")},
            {"question": data.get("grok_question_3"), "answer": data.get("third_grok_response")}
        ]
    }
    interaction_summary_data["qna"] = [item for item in interaction_summary_data["qna"] if item.get("question") and item.get("answer")]
    summary_text = await get_grok_summary(user_id, interaction_summary_data, db)

    if summary_text and not summary_text.startswith(("Ошибка", "К сожалению", "Не получилось", "Произошла")):
        try:
            await message.answer(f"✨ Давай попробуем подвести итог нашей беседы:\n\n<i>{summary_text}</i>", parse_mode="HTML")
            await logger_service.log_action(user_id, "summary_sent", {
                "summary_length": len(summary_text),
                "summary": summary_text,
                "session_id": session_id
            })
        except Exception as e:
            logger.error(f"Failed to send summary message to user {user_id}: {e}", exc_info=True)
    else:
        await logger_service.log_action(user_id, "summary_failed", {"error_message": summary_text, "session_id": session_id})
        try:
            fallback_msg = summary_text if isinstance(summary_text, str) and summary_text.startswith(("Ошибка", "К сожалению", "Не получилось", "Произошла")) else "Спасибо за твои глубокие размышления!"
            await message.answer(fallback_msg)
        except Exception as e:
            logger.error(f"Failed to send fallback/error summary message to user {user_id}: {e}", exc_info=True)

# --- Шаг 7: Завершение ---
async def finish_interaction_flow(user_id: int, message: types.Message, state: FSMContext, db: Database, logger_service):
    if not isinstance(user_id, int):
        logger.error("Invalid user_id passed to finish_interaction_flow")
        try:
            menu_user_id = message.from_user.id if message and message.from_user else user_id
            await message.answer("Завершаю сессию...", reply_markup=await get_main_menu(menu_user_id, db))
            await state.clear()
            logger.warning(f"Cleared state for INVALID user_id reference after failing to send final resource question.")
        except Exception as clear_err:
             logger.error(f"Failed to clear state for INVALID user_id reference: {clear_err}", exc_info=True)
        return

    user_db_data = db.get_user(user_id) or {}
    name = user_db_data.get("name") or ""
    name = name.strip() if isinstance(name, str) else ""
    data = await state.get_data()
    initial_resource = data.get("initial_resource", "неизвестно")

    text = (f"{name}, наша работа с картой на сегодня подходит к концу. 🙏\nТы начала с состоянием '{initial_resource}'.\n\nКак ты чувствуешь себя <b>сейчас</b>? Как изменился твой уровень ресурса?"
            if name
            else f"Наша работа с картой на сегодня подходит к концу. 🙏\nТы начала с состоянием '{initial_resource}'.\n\nКак ты чувствуешь себя <b>сейчас</b>? Как изменился твой уровень ресурса?")
    buttons = [types.InlineKeyboardButton(text=label.split()[0], callback_data=key) for key, label in RESOURCE_LEVELS.items()]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[buttons])
    try:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(UserState.waiting_for_final_resource)
    except Exception as e:
        logger.error(f"Failed to send final resource question to user {user_id}: {e}", exc_info=True)
        try:
            await message.answer("Не удалось задать финальный вопрос, но сессия завершена.", reply_markup=await get_main_menu(user_id, db))
            await state.clear()
            logger.warning(f"Cleared state for user {user_id} after failing to send final resource question.")
        except Exception as clear_err:
            logger.error(f"Failed to clear state for user {user_id} after message send failure: {clear_err}", exc_info=True)

# --- Шаг 8: Обработка финального ресурса ---
async def process_final_resource_callback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    user_id = callback.from_user.id
    resource_choice_key = callback.data
    resource_choice_label = RESOURCE_LEVELS.get(resource_choice_key, "Неизвестно")
    data = await state.get_data()
    session_id = data.get("session_id", "unknown")
    await state.update_data(final_resource=resource_choice_label)
    initial_resource = data.get("initial_resource", "неизвестно")
    resource_change = "same"
    if initial_resource != resource_choice_label:
        resource_levels = ["😔 Низко", "😐 Средне", "😊 Хорошо", "🤩 Отлично"]
        try:
            initial_index = resource_levels.index(initial_resource)
            final_index = resource_levels.index(resource_choice_label)
            if final_index > initial_index:
                resource_change = "better"
            elif final_index < initial_index:
                resource_change = "worse"
        except ValueError:
            resource_change = "unknown"
    db.log_scenario_step(user_id, 'card_of_day', 'mood_change_recorded', {
        'initial_resource': initial_resource,
        'final_resource': resource_choice_label,
        'change_direction': resource_change,
        'session_id': session_id
    })
    await logger_service.log_action(user_id, "final_resource_selected", {
        "resource": resource_choice_label,
        "session_id": session_id
    })
    await callback.answer(f"Понял, твое состояние сейчас: {resource_choice_label.split()[0]}")
    try: await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e: logger.warning(f"Could not edit message reply markup (final resource) for user {user_id}: {e}")

    if resource_choice_key == "resource_low":
        # Новый UX: если есть сохранённый способ восстановления, предложить его
        last_method = db.get_last_recharge_method(user_id)
        logger.info(f"User {user_id}: Resource is low. Last recharge method: {last_method}")
        
        if last_method:
            logger.info(f"User {user_id}: Offering saved recharge method: {last_method}")
            text = (f"Ранее ты отмечал(а), что тебе помогает восстанавливать ресурс: <b>{last_method}</b>.\n\n"
                    "Хочешь воспользоваться этим способом сейчас или добавить новый?")
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="Да, воспользуюсь этим", callback_data="use_last_recharge")],
                [types.InlineKeyboardButton(text="Добавить новый способ", callback_data="add_new_recharge")]
            ])
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            await state.set_state(UserState.waiting_for_recharge_method_choice)
            return
        else:
            logger.info(f"User {user_id}: No saved recharge method found, asking for new one")
            try:
                await callback.message.answer("Мне жаль слышать, что ресурс на низком уровне...")
                await callback.message.bot.send_chat_action(user_id, 'typing')
                supportive_message_with_question = await get_grok_supportive_message(user_id, db)
                await callback.message.answer(supportive_message_with_question)
                await logger_service.log_action(user_id, "support_message_sent", {"session_id": session_id})
                await state.set_state(UserState.waiting_for_recharge_method)
            except Exception as e:
                logger.error(f"Failed to send supportive message or set state for user {user_id}: {e}", exc_info=True)
                await show_final_feedback_and_menu(callback.message, state, db, logger_service, user_id=user_id)
    else:
        await callback.message.answer(f"Здорово, что твое состояние '{resource_choice_label}'! ✨")
        await show_final_feedback_and_menu(callback.message, state, db, logger_service, user_id=user_id)

# Новый обработчик выбора способа восстановления
async def process_recharge_method_choice(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    user_id = callback.from_user.id
    data = await state.get_data()
    session_id = data.get("session_id", "unknown")
    if callback.data == "use_last_recharge":
        last_method = db.get_last_recharge_method(user_id)
        if last_method:
            await callback.message.answer(f"Отлично! Попробуй сейчас воспользоваться этим способом: <b>{last_method}</b>\n\nЕсли захочешь добавить новый — просто напиши его в следующий раз.", parse_mode="HTML")
            await show_final_feedback_and_menu(callback.message, state, db, logger_service, user_id=user_id)
        else:
            await callback.message.answer("Не удалось найти твой способ восстановления. Пожалуйста, напиши, что тебе помогает восстановиться.")
            await state.set_state(UserState.waiting_for_recharge_method)
    elif callback.data == "add_new_recharge":
        await callback.message.answer("Пожалуйста, напиши, что тебе помогает восстановиться.")
        await state.set_state(UserState.waiting_for_recharge_method)
    else:
        await callback.answer("Выбери вариант на кнопках.", show_alert=True)

# --- Шаг 8.5: Обработка метода восстановления ---
async def process_recharge_method(message: types.Message, state: FSMContext, db: Database, logger_service):
    user_id = message.from_user.id
    recharge_method_text = message.text.strip()
    user_db_data = db.get_user(user_id) or {}
    name = user_db_data.get("name") or ""
    name = name.strip() if isinstance(name, str) else ""
    if not recharge_method_text: await message.answer("Пожалуйста, напиши, что тебе помогает восстановиться."); return
    if len(recharge_method_text) < 5: await message.answer("Расскажи чуть подробнее, пожалуйста (хотя бы 5 символов)."); return

    data = await state.get_data()
    session_id = data.get("session_id", "unknown")

    try:
        now_iso = datetime.now(TIMEZONE).isoformat()
        db.add_recharge_method(user_id, recharge_method_text, now_iso)
        await state.update_data(recharge_method=recharge_method_text)
        await logger_service.log_action(user_id, "recharge_method_provided", {
            "length": len(recharge_method_text),
            "response": recharge_method_text,
            "session_id": session_id
        })
        logger.info(f"Recharge method '{recharge_method_text}' added to separate table for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to add recharge method to DB for user {user_id}: {e}", exc_info=True)

    final_text = (f"{name}, спасибо, что поделилась! Запомню это. Пожалуйста, найди возможность применить это для себя сегодня. Ты этого достоин(на). ❤️" if name else f"Спасибо, что поделилась! Запомню это. Пожалуйста, найди возможность применить это для себя сегодня. Ты этого достоин(на). ❤️")
    await message.answer(final_text, parse_mode="HTML")
    await show_final_feedback_and_menu(message, state, db, logger_service, user_id=user_id)


# --- Шаг 9: Финальное сообщение, обратная связь, очистка ---
async def show_final_feedback_and_menu(message: types.Message, state: FSMContext, db: Database, logger_service, user_id: int):
    if not isinstance(user_id, int):
        logger.error("Invalid user_id passed to show_final_feedback_and_menu")
        await state.clear(); return

    user_db_data = db.get_user(user_id) or {}
    name = user_db_data.get("name") or ""
    name = name.strip() if isinstance(name, str) else ""
    data = await state.get_data()
    card_number = data.get("card_number", 0)
    session_id = data.get("session_id", "unknown")

    try:
        final_profile_data = {
            "initial_resource": data.get("initial_resource"),
            "final_resource": data.get("final_resource"),
            "last_updated": datetime.now(TIMEZONE)
        }
        final_profile_data = {k: v for k, v in final_profile_data.items() if v is not None}
        if final_profile_data:
            db.update_user_profile(user_id, final_profile_data)
            logger.info(f"Final profile data (resources) saved for user {user_id} before state clear.")
    except Exception as e:
        logger.error(f"Error saving final profile resource data for user {user_id} before clear: {e}", exc_info=True)
    
    # Завершаем сценарий "Карта дня"
    db.complete_user_scenario(user_id, 'card_of_day', session_id)
    db.log_scenario_step(user_id, 'card_of_day', 'completed', {
        'card_number': card_number,
        'session_id': session_id,
        'initial_resource': data.get("initial_resource"),
        'final_resource': data.get("final_resource")
    })
    
    # --- ИЗМЕНЕНИЕ: Добавлен лог о завершении ---
    await logger_service.log_action(user_id, "card_flow_completed", {
        "card_session": card_number,
        "session_id": session_id
    })
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    try:
        await message.answer("Благодарю за твою открытость и уделённое время! 🙏 Работа с картами - это путь к себе.", reply_markup=await get_main_menu(user_id, db))
    except Exception as e:
        logger.error(f"Failed to send final thank you message to user {user_id}: {e}", exc_info=True)

    feedback_text = f"{name}, и последний момент: насколько ценной для тебя оказалась эта сессия в целом? Удалось ли найти что-то важное или по-новому взглянуть на свой запрос?" if name else "И последний момент: насколько ценной для тебя оказалась эта сессия в целом? Удалось ли найти что-то важное или по-новому взглянуть на свой запрос?"
    feedback_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👍 Да, помогло!", callback_data=f"feedback_v2_helped_{card_number}")],
        [types.InlineKeyboardButton(text="🤔 Было интересно", callback_data=f"feedback_v2_interesting_{card_number}")],
        [types.InlineKeyboardButton(text="😕 Не очень / Не хватило", callback_data=f"feedback_v2_notdeep_{card_number}")]
    ])
    try:
        await message.answer(feedback_text, reply_markup=feedback_keyboard)
        await logger_service.log_action(user_id, "final_feedback_prompted", {
            "card_session": card_number,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Failed to send final feedback prompt to user {user_id}: {e}", exc_info=True)

    try:
        current_state_before_clear = await state.get_state()
        current_data_before_clear = await state.get_data()
        logger.info(f"Clearing state for user {user_id} after card session. Current state: {current_state_before_clear}. Data: {current_data_before_clear}")
        await state.clear()
        current_state_after_clear = await state.get_state()
        logger.info(f"State cleared for user {user_id}. New state: {current_state_after_clear}")
    except Exception as e:
         logger.error(f"Failed to clear state for user {user_id}: {e}", exc_info=True)

# === Обработчик финальной обратной связи (👍/🤔/😕) ===
async def process_card_feedback(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    user_id = callback.from_user.id
    user_data = db.get_user(user_id) or {}
    name = user_data.get("name") or ""
    name = name.strip() if isinstance(name, str) else ""
    callback_data = callback.data
    feedback_type = "unknown"
    card_number = 0

    fsm_data = await state.get_data()
    session_id = fsm_data.get("session_id", "unknown_post_session") # Может быть пустым, если состояние уже очищено

    try:
        parts = callback_data.split('_');
        if len(parts) >= 4 and parts[0] == 'feedback' and parts[1] == 'v2':
            feedback_type = parts[2]
            try:
                card_number = int(parts[-1])
            except ValueError:
                logger.error(f"Could not parse card number from feedback callback data: {callback_data} for user {user_id}")
                card_number = 0

            text_map = {
                "helped": "Отлично! Рад, что наша беседа была для тебя полезной. 😊 Жду тебя завтра!",
                "interesting": "Здорово, что было интересно! Размышления и новые углы зрения - это тоже важный результат. 👍",
                "notdeep": f"{name}, спасибо за честность! Мне жаль, если не удалось копнуть достаточно глубоко в этот раз. Твои идеи в /feedback помогут мне учиться и развиваться." if name else "Спасибо за честность! Мне жаль, если не удалось копнуть достаточно глубоко в этот раз. Твои идеи в /feedback помогут мне учиться и развиваться."
            }
            text = text_map.get(feedback_type)

            if not text:
                logger.warning(f"Unknown feedback_v2 type: {feedback_type} received from user {user_id}")
                await callback.answer("Спасибо за ответ!", show_alert=False)
                try: await callback.message.edit_reply_markup(reply_markup=None)
                except Exception: pass
                return

            # Логируем оценку полезности
            db.log_scenario_step(user_id, 'card_of_day', 'usefulness_rating', {
                'rating': feedback_type,
                'card_number': card_number,
                'session_id': session_id
            })
            
            await logger_service.log_action(user_id, "interaction_feedback_provided", {
                "card_session": card_number, 
                "feedback": feedback_type,
                "bot_response": text,
                "session_id": session_id
            })

            try: await callback.message.edit_reply_markup(reply_markup=None)
            except Exception as e: logger.warning(f"Could not edit message reply markup (feedback buttons) for user {user_id}: {e}")

            try:
                await callback.message.answer(text, reply_markup=await get_main_menu(user_id, db))
                await callback.answer()
            except Exception as e:
                logger.error(f"Failed to send feedback confirmation message to user {user_id}: {e}", exc_info=True)
                await callback.answer("Спасибо!", show_alert=False)

        else:
             logger.warning(f"Unknown or old feedback callback data format received: {callback_data} from user {user_id}")
             await callback.answer("Спасибо за ответ!", show_alert=False)
             try: await callback.message.edit_reply_markup(reply_markup=None)
             except Exception: pass
             return

    except Exception as e:
        logger.error(f"Error processing interaction feedback for user {user_id}: {e}", exc_info=True)
        try: await callback.answer("Произошла ошибка при обработке твоего ответа.", show_alert=True)
        except Exception: pass

# --- Шаг 4: Обработка выбора эмоции ---
async def process_emotion_choice(callback: types.CallbackQuery, state: FSMContext, db: Database, logger_service):
    """Обрабатывает выбор эмоции пользователем."""
    user_id = callback.from_user.id
    emotion_choice = callback.data
    
    # Получаем данные сессии
    data = await state.get_data()
    session_id = data.get("session_id", "unknown")
    
    # Маппинг эмоций на русские названия
    emotion_mapping = {
        "emotion_joy": "Радость",
        "emotion_thoughtful": "Задумчивость", 
        "emotion_sadness": "Печаль",
        "emotion_anger": "Злость",
        "emotion_hope": "Надежда",
        "emotion_calm": "Спокойствие"
    }
    
    if emotion_choice == "emotion_custom":
        # Пользователь хочет написать свой вариант
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Напишите, что вы видите или чувствуете...")
        await state.set_state(UserState.waiting_for_custom_response)
        await callback.answer()
        return
    
    # Пользователь выбрал одну из эмоций
    selected_emotion = emotion_mapping.get(emotion_choice, "Неизвестная эмоция")
    
    # Убираем клавиатуру
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.warning(f"Could not edit message reply markup (emotion choice) for user {user_id}: {e}")
    
    # Сохраняем выбранную эмоцию
    await state.update_data(initial_response=selected_emotion)
    
    # Логируем выбор эмоции
    db.log_scenario_step(user_id, 'card_of_day', 'emotion_choice_provided', {
        'emotion': selected_emotion,
        'session_id': session_id
    })
    
    await logger_service.log_action(user_id, "emotion_choice_provided", {
        "emotion": selected_emotion,
        "session_id": session_id
    })
    
    await callback.answer()
    
    # Переходим к следующему шагу
    await ask_exploration_choice(callback.message, state, db, logger_service)

# --- Обработка пользовательского текста ---
async def process_custom_response(message: types.Message, state: FSMContext, db: Database, logger_service):
    """Обрабатывает пользовательский текст после выбора 'Написать свой вариант'."""
    user_id = message.from_user.id
    custom_response_text = message.text.strip()
    
    if not custom_response_text:
        await message.answer("Кажется, ты ничего не написала...")
        return
    
    if len(custom_response_text) < 3:
        await message.answer("Пожалуйста, опиши ассоциации чуть подробнее...")
        return
    
    # Получаем данные сессии
    data = await state.get_data()
    session_id = data.get("session_id", "unknown")
    
    # Сохраняем пользовательский ответ
    await state.update_data(initial_response=custom_response_text)
    
    # Логируем пользовательский ответ
    db.log_scenario_step(user_id, 'card_of_day', 'custom_response_provided', {
        'response_length': len(custom_response_text),
        'session_id': session_id
    })
    
    await logger_service.log_action(user_id, "custom_response_provided", {
        "response": custom_response_text,
        "length": len(custom_response_text),
        "session_id": session_id
    })
    
    # Переходим к следующему шагу
    await ask_exploration_choice(message, state, db, logger_service)
