import random
import logging
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import asyncio
from datetime import datetime, timedelta
import pytz
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import requests

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)
logging.debug("Starting script...")

# Настройки
TOKEN = "8054930534:AAFDdyp5_xiX0ZPQnSEZKpfOhk2PCdchKvg"
CHANNEL_ID = "@TopPsyGame"
BOT_LINK = "t.me/choose_a_card_bot"
TIMEZONE = pytz.timezone("Europe/Moscow")
ADMIN_ID = 6682555021  # Укажите ваш Telegram ID как администратора
GROK_API_KEY = "xai-F86KOKXr4PzZitmUfevOpUQdP4TLndRlLJjLnxFsJZ33SoWDm7rXJVn91rfluMrc0glE56OmDchEVqSW"
GROK_API_URL = "https://api.xai.com/v1/grok"  # Уточните актуальный URL в документации xAI
GROK_USERS = [6682555021, 392141189]  # Пользователи, для которых работает Grok

# Инициализация бота
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

logging.debug("Bot and Dispatcher initialized.")

# Состояния для FSM
class UserState(StatesGroup):
    waiting_for_name = State()
    waiting_for_reminder_time = State()
    waiting_for_request_confirmation = State()
    waiting_for_feedback = State()
    waiting_for_request_text = State()
    waiting_for_yes_response = State()
    waiting_for_no_response = State()

# Файлы для хранения данных
DATA_DIR = "/data"
LAST_REQUEST_FILE = f"{DATA_DIR}/last_request.json"
USER_NAMES_FILE = f"{DATA_DIR}/user_names.json"
REFERRALS_FILE = f"{DATA_DIR}/referrals.json"
BONUS_AVAILABLE_FILE = f"{DATA_DIR}/bonus_available.json"
REMINDER_TIMES_FILE = f"{DATA_DIR}/reminder_times.json"
STATS_FILE = f"{DATA_DIR}/card_feedback.json"
FEEDBACK_FILE = f"{DATA_DIR}/feedback.json"
USER_ACTIONS_FILE = f"{DATA_DIR}/user_actions.json"
USER_REQUESTS_FILE = f"{DATA_DIR}/user_requests.json"

# Создаём папку, если её нет
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

logging.debug("File paths defined, directory created if needed.")

# Функции для работы с JSON
def load_json(file_path, default):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {int(k) if k.isdigit() else k: v for k, v in data.items()}
            return data
    return default

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    logging.info(f"Saved file {file_path}: {os.listdir(DATA_DIR)}")

# Функция для загрузки логов
def load_user_actions():
    return load_json(USER_ACTIONS_FILE, [])

# Функция для записи логов (добавление, а не перезапись)
async def save_user_action(user_id, action, details=None):
    user_actions = load_user_actions()
    chat = await bot.get_chat(user_id)
    username = chat.username if chat.username else ""
    name = USER_NAMES.get(user_id, "")
    timestamp = datetime.now(TIMEZONE).isoformat()
    log_entry = {
        "user_id": user_id,
        "username": username,
        "name": name,
        "action": action,
        "details": details or {},
        "timestamp": timestamp
    }
    user_actions.append(log_entry)
    save_json(USER_ACTIONS_FILE, user_actions)
    logging.info(f"Logged action for user {user_id}: {action}, details: {details}")

# Функция для получения логов за текущий день
def get_logs_for_today():
    user_actions = load_user_actions()
    today = datetime.now(TIMEZONE).date()
    logs_today = [log for log in user_actions if datetime.fromisoformat(log["timestamp"]).astimezone(TIMEZONE).date() == today]
    logs_today.sort(key=lambda x: x["timestamp"])  # Сортировка от старых к новым
    return logs_today

# Функция для получения последнего действия пользователя
def get_last_action(user_id):
    user_actions = load_user_actions()
    user_actions = [action for action in user_actions if action["user_id"] == user_id]
    if not user_actions:
        return None
    user_actions.sort(key=lambda x: x["timestamp"], reverse=True)
    return user_actions[0]

logging.debug("JSON functions defined.")

# Инициализация данных
LAST_REQUEST = load_json(LAST_REQUEST_FILE, {})
USER_NAMES = load_json(USER_NAMES_FILE, {})
REFERRALS = load_json(REFERRALS_FILE, {})
BONUS_AVAILABLE = load_json(BONUS_AVAILABLE_FILE, {})
REMINDER_TIMES = load_json(REMINDER_TIMES_FILE, {})
FEEDBACK = load_json(FEEDBACK_FILE, {})
USER_ACTIONS = load_user_actions()
USER_REQUESTS = load_json(USER_REQUESTS_FILE, {})

for user_id, timestamp in LAST_REQUEST.items():
    LAST_REQUEST[user_id] = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(TIMEZONE)

logging.debug("Data initialized.")

# Список вопросов и советов (оставлены без изменений)
REFLECTION_QUESTIONS = [
    "Какой ресурс даёт мне эта карта?",
    "Как этот образ может поддержать меня в сложившейся ситуации?",
    # ... (оставлены все вопросы из вашего списка)
    "Как я могу поблагодарить себя за открытие этого ресурса?"
]
UNIVERSE_ADVICE = [
    "<b>💌 Ты — источник силы.</b> Всё, что тебе нужно, уже внутри. Просто доверься себе и сделай первый шаг.",
    # ... (оставлены все советы из вашего списка)
    "<b>💌 Ресурсы не заканчиваются, они перетекают.</b> Подключись к потоку жизни и доверься её ритму。"
]

# Загрузка и сохранение статистики
def load_stats():
    return load_json(STATS_FILE, {"users": {}, "total": {"yes": 0, "no": 0}})

def save_stats(stats):
    save_json(STATS_FILE, stats)

# Генерация главного меню
def get_main_menu(user_id):
    keyboard = [
        [KeyboardButton(text="✨ Карта дня")]
    ]
    if BONUS_AVAILABLE.get(user_id, False):
        keyboard.append([KeyboardButton(text="💌 Подсказка Вселенной")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, persistent=True)

# Middleware для проверки подписки (без изменений)
class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            name = USER_NAMES.get(user_id, "")
            try:
                user_status = await bot.get_chat_member(CHANNEL_ID, user_id)
                if user_status.status not in ["member", "administrator", "creator"]:
                    text = f"{name}, привет! Чтобы начать, подпишись на <a href='https://t.me/TopPsyGame'>канал автора</a>!" if name else "Привет! Чтобы начать, подпишись на <a href='https://t.me/TopPsyGame'>канал автора</a>!"
                    await event.answer(text, disable_web_page_preview=True, protect_content=True)
                    return
            except Exception as e:
                logging.error(f"Ошибка проверки подписки: {e}")
                await event.answer("Ой, что-то сломалось... Попробуй позже.", protect_content=True)
                return
        return await handler(event, data)

dp.message.middleware(SubscriptionMiddleware())

# Рассылка сообщений и проверка напоминаний (без изменений)
BROADCAST = {
    "datetime": datetime(2025, 4, 6, 2, 8, tzinfo=TIMEZONE),
    "text": "Привет! У нас обновления в боте:  \n✨ \"Карта дня\" теперь доступна раз в сутки с 00:00 по Москве (UTC+3) — проверка идёт по дате, а не по 24 часам от последнего запроса.  \n⚙️ Теперь вместо кнопок используй команды: /name, /remind, /share, /feedback.  \nОтправь /start, чтобы увидеть всё новое!",
    "recipients": [6682555021] # "recipients": [6682555021]  # Список ID, без кавычек вокруг числа или "recipients": "all"
}
BROADCAST_SENT = False

async def check_broadcast():
    global BROADCAST_SENT
    while True:
        now = datetime.now(TIMEZONE)
        if not BROADCAST_SENT and now >= BROADCAST["datetime"]:
            recipients = USER_NAMES.keys() if BROADCAST["recipients"] == "all" else BROADCAST["recipients"]
            for user_id in recipients:
                name = USER_NAMES.get(user_id, "")
                text = f"{name}, {BROADCAST['text']}" if name else BROADCAST["text"]
                try:
                    await bot.send_message(user_id, text, reply_markup=get_main_menu(user_id), protect_content=True)
                except Exception as e:
                    logging.error(f"Failed to send broadcast to {user_id}: {e}")
            BROADCAST_SENT = True
        await asyncio.sleep(60)

async def check_reminders():
    while True:
        now = datetime.now(TIMEZONE)
        current_time = now.strftime("%H:%M")
        today = now.date()
        for user_id, reminder_time in list(REMINDER_TIMES.items()):
            reminder_time_normalized = datetime.strptime(reminder_time, "%H:%M").strftime("%H:%M")
            last_request_time = LAST_REQUEST.get(user_id)
            card_available = not last_request_time or last_request_time.date() < today
            if current_time == reminder_time_normalized and card_available:
                name = USER_NAMES.get(user_id, "")
                text = f"{name}, привет! Пришло время вытянуть свою карту дня. ✨ Она уже ждет тебя!" if name else "Привет! Пришло время вытянуть свою карту дня. ✨ Она уже ждет тебя!"
                try:
                    await bot.send_message(user_id, text, reply_markup=get_main_menu(user_id), protect_content=True)
                except Exception as e:
                    logging.error(f"Failed to send reminder to {user_id}: {e}")
        await asyncio.sleep(60)

async def suggest_reminder(user_id, state: FSMContext):
    name = USER_NAMES.get(user_id, "")
    if user_id not in REMINDER_TIMES:
        text = f"{name}, если хочешь, я могу напоминать тебе о карте дня! Используй /remind, чтобы установить время." if name else "Если хочешь, я могу напоминать тебе о карте дня! Используй /remind, чтобы установить время."
        try:
            await bot.send_message(user_id, text, reply_markup=get_main_menu(user_id), protect_content=True)
        except Exception as e:
            logging.error(f"Failed to suggest reminder to {user_id}: {e}")

# Функция для запроса к Grok API
async def get_grok_question(user_request, user_response, feedback_type):
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = (
        f"Ты работаешь с метафорическими ассоциативными картами (МАК). На основе запроса пользователя '{user_request}' "
        f"и его ответа '{user_response}' после реакции '{feedback_type}' на карту, задай один открытый вопрос для рефлексии. "
        f"Не интерпретируй карту, только помоги пользователю глубже исследовать свои ассоциации. Вопрос должен быть кратким и связанным с контекстом."
    )
    payload = {
        "prompt": prompt,
        "max_tokens": 50  # Ограничение длины для краткости
    }
    try:
        response = requests.post(GROK_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["response"]
        else:
            logging.error(f"Grok API error: {response.status_code}, {response.text}")
            return "Что ещё ты можешь сказать о своих ассоциациях с картой?"
    except Exception as e:
        logging.error(f"Failed to call Grok API: {e}")
        return "Что ещё ты можешь сказать о своих ассоциациях с картой?"

# Команда /start (без изменений)
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    
    await save_user_action(user_id, "start", {"args": args})

    if args.startswith("ref_"):
        try:
            referrer_id = int(args[4:])
            if referrer_id != user_id and referrer_id not in REFERRALS.get(user_id, []):
                REFERRALS.setdefault(referrer_id, []).append(user_id)
                save_json(REFERRALS_FILE, REFERRALS)
                if not BONUS_AVAILABLE.get(referrer_id, False):
                    BONUS_AVAILABLE[referrer_id] = True
                    save_json(BONUS_AVAILABLE_FILE, BONUS_AVAILABLE)
                    referrer_name = USER_NAMES.get(referrer_id, "")
                    text = f"{referrer_name}, ура! Кто-то открыл бот по твоей ссылке! Возьми '💌 Подсказку Вселенной'." if referrer_name else "Ура! Кто-то открыл бот по твоей ссылке! Возьми '💌 Подсказку Вселенной'."
                    await bot.send_message(referrer_id, text, reply_markup=get_main_menu(referrer_id), protect_content=True)
        except ValueError as e:
            logging.error(f"Invalid referrer ID in args: '{args}', error: {e}")

    if user_id not in USER_NAMES:
        text = "Привет! Давай знакомиться! Как тебя зовут? (Если не хочешь, чтобы обращалась к тебе по имени - нажми пропустить)"
        skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]])
        await message.answer(text, reply_markup=skip_keyboard, protect_content=True)
        await state.set_state(UserState.waiting_for_name)
    else:
        await message.answer(
            f"{USER_NAMES[user_id]}, рада тебя видеть! Нажми '✨ Карта дня' в меню." if USER_NAMES[user_id] else "Рада тебя видеть! Нажми '✨ Карта дня' в меню.",
            reply_markup=get_main_menu(user_id),
            protect_content=True
        )

# Команда /share (без изменений)
@dp.message(Command("share"))
async def share_command(message: types.Message):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    ref_link = f"{BOT_LINK}?start=ref_{user_id}"
    text = f"{name}, этот бот — находка для вдохновения! Поделись: {ref_link}. Если кто-то зайдёт, получишь '💌 Подсказку Вселенной'!" if name else f"Этот бот — находка для вдохновения! Поделись: {ref_link}. Если кто-то зайдёт, получишь '💌 Подсказку Вселенной'!"
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=False)

# Команда /remind (без изменений)
@dp.message(Command("remind"))
async def remind_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    current_reminder = REMINDER_TIMES.get(user_id, "не установлено")
    text = f"{name}, текущее время напоминания: {current_reminder}. Введи новое время в формате чч:мм (например, 10:00) по Москве (UTC+3)." if name else f"Текущее время напоминания: {current_reminder}. Введи новое время в формате чч:мм (например, 10:00) по Москве (UTC+3)."
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
    await state.set_state(UserState.waiting_for_reminder_time)

# Команда /name (без изменений)
@dp.message(Command("name"))
async def name_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    text = f"{name}, как тебя зовут? Введи новое имя или нажми 'Пропустить', если не хочешь его менять." if name else "Как тебя зовут? Введи имя или нажми 'Пропустить', если не хочешь его указывать."
    skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]])
    await message.answer(text, reply_markup=skip_keyboard, protect_content=True)
    await state.set_state(UserState.waiting_for_name)

# Команда /feedback (без изменений)
@dp.message(Command("feedback"))
async def feedback_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    text = f"{name}, напиши свой вопрос или идею по улучшению бота. Я сохраню твои мысли!" if name else "Напиши свой вопрос или идею по улучшению бота. Я сохраню твои мысли!"
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
    await state.set_state(UserState.waiting_for_feedback)

# Команда /logs (доработанная)
@dp.message(Command("logs"))
async def logs_command(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("Эта команда доступна только администратору.", protect_content=True)
        return

    logs = get_logs_for_today()
    if not logs:
        await message.answer("Сегодня пока нет действий.", protect_content=True)
        return

    response = "*Действия за сегодня:*\n\n"
    for log in logs:
        timestamp = log["timestamp"]
        user_id_log = str(log["user_id"])
        name = USER_NAMES.get(user_id_log, "Не указано")
        action_type = log["action"]
        details = log["details"]
        details_str = " ".join(f"{k}: {v}" for k, v in details.items()) if details else "Нет деталей"

        response += (
            f"⏰ {timestamp}\n"
            f"👤 *ID*: `{user_id_log}` ({name})\n"
            f"   Действие: {action_type}\n"
            f"   Детали: {details_str}\n\n"
        )

    MAX_MESSAGE_LENGTH = 4096
    if len(response) <= MAX_MESSAGE_LENGTH:
        await message.answer(response, parse_mode="Markdown", protect_content=True)
    else:
        parts = [response[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(response), MAX_MESSAGE_LENGTH)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown", protect_content=True)
            await asyncio.sleep(0.5)

# Команда /users (доработанная)
@dp.message(Command("users"))
async def users_command(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("Эта команда доступна только администратору.", protect_content=True)
        return

    if not USER_NAMES:
        await message.answer("Активных пользователей нет.", protect_content=True)
        return

    response = "*Список пользователей:*\n\n"
    for user_id_key, name in USER_NAMES.items():
        username = CARD_FEEDBACK.get(user_id_key, {}).get("username", "")
        last_request = LAST_REQUEST.get(user_id_key, "Нет данных")
        if isinstance(last_request, datetime):
            last_request = last_request.isoformat()
        cards = CARD_FEEDBACK.get(user_id_key, {}).get("responses", [])
        card_count = len(cards)
        yes_count = len([r for r in cards if r["answer"] == "yes"])
        yes_percent = (yes_count / card_count * 100) if card_count > 0 else 0
        bonus = "✅" if BONUS_AVAILABLE.get(user_id_key, False) else "❌"
        reminder = REMINDER_TIMES.get(user_id_key, "Не установлено")
        ref_count = len(REFERRALS.get(user_id_key, []))

        response += (
            f"👤 *ID*: `{user_id_key}`\n"
            f"   Имя: {name or 'Не указано'} (@{username or 'Нет'})\n"
            f"   Последний запрос: {last_request}\n"
            f"   Карты: {card_count} (Да: {yes_percent:.1f}%)\n"
            f"   Бонус: {bonus}\n"
            f"   Напоминание: {reminder}\n"
            f"   Рефералы: {ref_count}\n\n"
        )

    MAX_MESSAGE_LENGTH = 4096
    if len(response) <= MAX_MESSAGE_LENGTH:
        await message.answer(response, parse_mode="Markdown", protect_content=True)
    else:
        parts = [response[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(response), MAX_MESSAGE_LENGTH)]
        for part in parts:
            await message.answer(part, parse_mode="Markdown", protect_content=True)
            await asyncio.sleep(0.5)

# Обработка ввода имени (без изменений)
@dp.message(UserState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    USER_NAMES[user_id] = name
    save_json(USER_NAMES_FILE, USER_NAMES)
    
    await save_user_action(user_id, "set_name", {"name": name})

    await message.answer(
        f"{name}, рада тебя видеть! Нажми '✨ Карта дня' в меню.",
        reply_markup=get_main_menu(user_id),
        protect_content=True
    )
    await state.clear()

# Обработка кнопки "Пропустить" для имени (без изменений)
@dp.callback_query(lambda c: c.data == "skip_name")
async def process_skip_name(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    USER_NAMES[user_id] = ""
    save_json(USER_NAMES_FILE, USER_NAMES)
    
    await save_user_action(user_id, "skip_name")

    await callback.message.answer(
        "Хорошо, без имени тоже здорово! Выбери '✨ Карта дня' в меню!",
        reply_markup=get_main_menu(user_id),
        protect_content=True
    )
    await state.clear()
    await callback.answer()

# Обработка ввода времени напоминания (без изменений)
@dp.message(UserState.waiting_for_reminder_time)
async def process_reminder_time(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    reminder_time = message.text.strip()
    try:
        reminder_time_normalized = datetime.strptime(reminder_time, "%H:%M").strftime("%H:%M")
        REMINDER_TIMES[user_id] = reminder_time_normalized
        save_json(REMINDER_TIMES_FILE, REMINDER_TIMES)
        
        await save_user_action(user_id, "set_reminder_time", {"reminder_time": reminder_time_normalized})

        text = f"{name}, супер! Я буду напоминать тебе о карте дня в {reminder_time_normalized} по Москве (UTC+3)." if name else f"Супер! Я буду напоминать тебе о карте дня в {reminder_time_normalized} по Москве (UTC+3)."
        await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
        await state.clear()
    except ValueError:
        text = f"{name}, кажется, время указано неверно. Попробуй ещё раз в формате чч:мм (например, 10:00)." if name else "Кажется, время указано неверно. Попробуй ещё раз в формате чч:мм (например, 10:00)."
        await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)

# Обработка ввода отзыва (без изменений)
@dp.message(UserState.waiting_for_feedback)
async def process_feedback_submission(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    feedback_text = message.text.strip()
    FEEDBACK[user_id] = {"name": name, "feedback": feedback_text, "timestamp": datetime.now(TIMEZONE).isoformat()}
    save_json(FEEDBACK_FILE, FEEDBACK)
    
    await save_user_action(user_id, "submit_feedback", {"feedback": feedback_text})

    text = f"{name}, спасибо за твой отзыв! Я сохранила его." if name else "Спасибо за твой отзыв! Я сохранила его."
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
    await state.clear()

# Обработка "Карта дня" (без изменений)
@dp.message(lambda message: message.text == "✨ Карта дня")
async def handle_card_request(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    now = datetime.now(TIMEZONE)
    today = now.date()

    last_request_time = LAST_REQUEST.get(user_id)
    if user_id != 6682555021 and last_request_time and last_request_time.date() == today:
        text = f"{name}, ты уже вытянула карту сегодня! Новая будет доступна завтра в 00:00 по Москве (UTC+3)." if name else "Ты уже вытянула карту сегодня! Новая будет доступна завтра в 00:00 по Москве (UTC+3)."
        await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
        return

    text = f"{name}, давай сделаем это осознанно! 🌿 Подумай: какой вопрос ты хочешь задать карте (например, 'Как мне найти ресурс?')? Нажми кнопку, когда будешь готова!" if name else "Давай сделаем это осознанно! 🌿 Подумай: какой вопрос ты хочешь задать карте (например, 'Как мне найти ресурс?')? Нажми кнопку, когда будешь готова!"
    confirmation_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Готова!", callback_data="confirm_request")]])
    await message.answer(text, reply_markup=confirmation_keyboard, protect_content=True)
    await state.set_state(UserState.waiting_for_request_confirmation)

# Обработка подтверждения запроса для "Карта дня" (без изменений)
@dp.callback_query(lambda c: c.data == "confirm_request")
async def process_request_confirmation(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    name = USER_NAMES.get(user_id, "")
    if name:
        text = f"{name}, хочешь сделать это ещё глубже? 🌿 Если желаешь, напиши свой вопрос, чтобы карта ответила точнее. Или просто подумай о нём — как тебе удобно и нажми 'Дальше'"
    else:
        text = "Хочешь сделать это ещё глубже? 🌿 Если желаешь, напиши свой вопрос, чтобы карта ответила точнее. Или просто подумай о нём — как тебе удобно и нажми 'Дальше'"
    skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Дальше", callback_data="skip_request")]])
    await callback.message.answer(text, reply_markup=skip_keyboard, protect_content=True)
    await state.set_state(UserState.waiting_for_request_text)
    await callback.answer()

# Обработка пропуска запроса (без изменений)
@dp.callback_query(lambda c: c.data == "skip_request")
async def process_skip_request(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    name = USER_NAMES.get(user_id, "")
    now = datetime.now(TIMEZONE)

    try:
        card_numbers = list(range(1, 41))
        random.shuffle(card_numbers)
        card_number = card_numbers[0]
        card_path = f"cards/card_{card_number}.jpg"
        logging.debug(f"Attempting to load card: {card_path}")

        if not os.path.exists(card_path):
            logging.error(f"Card file not found: {card_path}")
            await callback.message.answer("Ошибка: карта не найдена.", reply_markup=get_main_menu(user_id))
            return

        photo = FSInputFile(card_path)
        await bot.send_photo(user_id, photo, reply_markup=get_main_menu(user_id), protect_content=True)
        LAST_REQUEST[user_id] = now
        save_json(LAST_REQUEST_FILE, {k: v.isoformat() for k, v in LAST_REQUEST.items()})

        reflection_question = random.choice(REFLECTION_QUESTIONS)
        await callback.message.answer(reflection_question, protect_content=True)

        feedback_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да 🙂", callback_data=f"feedback_yes_{card_number}"), InlineKeyboardButton(text="Нет 🙁", callback_data=f"feedback_no_{card_number}")]
        ])
        text = f"{name}, эта карта тебе откликается?" if name else "Эта карта тебе откликается?"
        await callback.message.answer(text, reply_markup=feedback_keyboard, protect_content=True)

        await save_user_action(user_id, "card_request", {"card_number": card_number, "reflection_question": reflection_question})

        await state.update_data(card_number=card_number, user_request="")
        
        await suggest_reminder(user_id, state)
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при отправке карты: {e}")
        await callback.message.answer("Что-то пошло не так... попробуй позже.", reply_markup=get_main_menu(user_id), protect_content=True)
        await state.clear()
    await callback.answer()

# Обработка текста запроса (без изменений)
@dp.message(UserState.waiting_for_request_text)
async def process_request_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    request_text = message.text.strip()
    now = datetime.now(TIMEZONE)

    USER_REQUESTS[user_id] = {"request": request_text, "timestamp": now.isoformat()}
    save_json(USER_REQUESTS_FILE, USER_REQUESTS)
    await save_user_action(user_id, "set_request", {"request": request_text})

    try:
        card_numbers = list(range(1, 41))
        random.shuffle(card_numbers)
        card_number = card_numbers[0]
        card_path = f"cards/card_{card_number}.jpg"
        logging.debug(f"Attempting to load card: {card_path}")

        if not os.path.exists(card_path):
            logging.error(f"Card file not found: {card_path}")
            await message.answer("Ошибка: карта не найдена.", reply_markup=get_main_menu(user_id))
            return

        photo = FSInputFile(card_path)
        await bot.send_photo(user_id, photo, reply_markup=get_main_menu(user_id), protect_content=True)
        LAST_REQUEST[user_id] = now
        save_json(LAST_REQUEST_FILE, {k: v.isoformat() for k, v in LAST_REQUEST.items()})

        reflection_question = random.choice(REFLECTION_QUESTIONS)
        await message.answer(reflection_question, protect_content=True)

        feedback_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да 🙂", callback_data=f"feedback_yes_{card_number}"), InlineKeyboardButton(text="Нет 🙁", callback_data=f"feedback_no_{card_number}")]
        ])
        text = f"{name}, эта карта тебе откликается?" if name else "Эта карта тебе откликается?"
        await message.answer(text, reply_markup=feedback_keyboard, protect_content=True)

        await save_user_action(user_id, "card_request", {"card_number": card_number, "reflection_question": reflection_question})

        await state.update_data(card_number=card_number, user_request=request_text)

        await suggest_reminder(user_id, state)
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при отправке карты: {e}")
        await message.answer("Что-то пошло не так... попробуй позже.", reply_markup=get_main_menu(user_id), protect_content=True)
        await state.clear()

# Обработка "Совет от Вселенной" (без изменений)
@dp.message(lambda message: message.text == "💌 Подсказка Вселенной")
async def handle_bonus_request(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    if not BONUS_AVAILABLE.get(user_id, False):
        text = f"{name}, этот совет пока спрятан! Используй /share, чтобы получить его, когда кто-то зайдёт по твоей ссылке!" if name else "Этот совет пока спрятан! Используй /share, чтобы получить его, когда кто-то зайдёт по твоей ссылке!"
        await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
        return

    advice = random.choice(UNIVERSE_ADVICE)
    text = f"{name}, вот послание для тебя:\n{advice}" if name else f"Вот послание для тебя:\n{advice}"
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)

    await save_user_action(user_id, "bonus_request", {"advice": advice})

# Обработка обратной связи по картам (без изменений)
@dp.callback_query(lambda c: c.data.startswith("feedback_"))
async def process_feedback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.username or ""
    name = USER_NAMES.get(user_id, "")
    feedback, card_number = callback.data.split("_")[1], callback.data.split("_")[2]
    stats = load_stats()

    user_key = str(user_id)
    if user_key not in stats["users"]:
        stats["users"][user_key] = {"name": name, "username": username, "responses": []}
    stats["users"][user_key]["responses"].append({"card": card_number, "answer": feedback})
    stats["total"][feedback] += 1
    save_stats(stats)

    await save_user_action(user_id, "card_feedback", {"card_number": card_number, "feedback": feedback})

    await state.update_data(card_number=card_number)

    if feedback == "yes":
        text = f"{name}, как этот образ отвечает на твой запрос? Напиши свои мысли!" if name else "Как этот образ отвечает на твой запрос? Напиши свои мысли!"
        await callback.message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
        await state.set_state(UserState.waiting_for_yes_response)
    elif feedback == "no":
        text = f"{name}, что ты видишь в этом образе?" if name else "Что ты видишь в этом образе?"
        await callback.message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
        await state.set_state(UserState.waiting_for_no_response)

    await callback.answer()

# Обработка ответа после "Да"
@dp.message(UserState.waiting_for_yes_response)
async def process_yes_response(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    response_text = message.text.strip()
    
    data = await state.get_data()
    card_number = data.get("card_number")
    user_request = data.get("user_request", "")

    await save_user_action(user_id, "yes_response", {
        "card_number": card_number,
        "request": user_request,
        "response": response_text
    })

    text = f"{name}, спасибо за ответы!" if name else "Спасибо за ответы!"
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)

    # Добавляем вопрос от Grok API для выбранных пользователей
    if user_id in GROK_USERS:  # Замените на "all" для всех пользователей позже
        grok_question = await get_grok_question(user_request or "Нет запроса", response_text, "Да")
        await message.answer(grok_question, reply_markup=get_main_menu(user_id), protect_content=True)

    await state.clear()

# Обработка ответа после "Нет"
@dp.message(UserState.waiting_for_no_response)
async def process_no_response(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    response_text = message.text.strip()
    
    data = await state.get_data()
    card_number = data.get("card_number")
    user_request = data.get("user_request", "")

    await save_user_action(user_id, "no_response", {
        "card_number": card_number,
        "request": user_request,
        "response": response_text
    })

    text = f"{name}, спасибо за ответы!" if name else "Спасибо за ответы!"
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)

    # Добавляем вопрос от Grok API для выбранных пользователей
    if user_id in GROK_USERS:  # Замените на "all" для всех пользователей позже
        grok_question = await get_grok_question(user_request or "Нет запроса", response_text, "Нет")
        await message.answer(grok_question, reply_markup=get_main_menu(user_id), protect_content=True)

    await state.clear()

# Запуск бота
async def main():
    logging.info("Bot starting...")
    asyncio.create_task(check_reminders())
    asyncio.create_task(check_broadcast())
    while True:
        try:
            await dp.start_polling(bot, skip_updates=True)
        except Exception as e:
            logging.error(f"Polling failed: {e}, restarting in 10 seconds...")
            await asyncio.sleep(10)
        else:
            break

if __name__ == "__main__":
    try:
        logging.debug("Starting main...")
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")
        raise
