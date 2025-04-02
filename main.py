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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import pytz

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)
logging.debug("Starting script...")

# Настройки
TOKEN = "8054930534:AAFDdyp5_xiX0ZPQnSEZKpfOhk2PCdchKvg"
CHANNEL_ID = "@TopPsyGame"
BOT_LINK = "t.me/choose_a_card_bot"
TIMEZONE = pytz.timezone("Europe/Moscow")

logging.debug("Settings loaded, initializing bot...")

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

# Файлы для хранения данных (используем /data для персистентного хранилища)
DATA_DIR = "/data"
LAST_REQUEST_FILE = f"{DATA_DIR}/last_request.json"
USER_NAMES_FILE = f"{DATA_DIR}/user_names.json"
REFERRALS_FILE = f"{DATA_DIR}/referrals.json"
BONUS_AVAILABLE_FILE = f"{DATA_DIR}/bonus_available.json"
REMINDER_TIMES_FILE = f"{DATA_DIR}/reminder_times.json"
STATS_FILE = f"{DATA_DIR}/card_feedback.json"

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

logging.debug("JSON functions defined.")

# Инициализация данных
LAST_REQUEST = load_json(LAST_REQUEST_FILE, {})
USER_NAMES = load_json(USER_NAMES_FILE, {})
REFERRALS = load_json(REFERRALS_FILE, {})
BONUS_AVAILABLE = load_json(BONUS_AVAILABLE_FILE, {})
REMINDER_TIMES = load_json(REMINDER_TIMES_FILE, {})

for user_id, timestamp in LAST_REQUEST.items():
    LAST_REQUEST[user_id] = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(TIMEZONE)

logging.debug("Data initialized.")

# Список вопросов и советов (сокращено для примера)
REFLECTION_QUESTIONS = ["Какой ресурс даёт мне эта карта?", "Как этот образ может поддержать меня?"]
UNIVERSE_ADVICE = ["<b>💌 Ты — источник силы.</b> Всё внутри.", "<b>💌 Вселенная ведёт тебя.</b> Заметь возможности."]

# Загрузка и сохранение статистики
def load_stats():
    return load_json(STATS_FILE, {"users": {}, "total": {"yes": 0, "no": 0}})

def save_stats(stats):
    save_json(STATS_FILE, stats)

logging.debug("Stats functions defined.")

# Генерация меню
def get_main_menu(user_id):
    keyboard = [
        [KeyboardButton(text="✨ Карта дня"), KeyboardButton(text="🕊 Поделиться")],
        [KeyboardButton(text="⏰ Напоминание")]
    ]
    if BONUS_AVAILABLE.get(user_id, False):
        keyboard.append([KeyboardButton(text="💌 Подсказка Вселенной")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, persistent=True)

logging.debug("Menu generation function defined.")

# Middleware для проверки подписки
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
logging.debug("Subscription middleware registered.")

# Фоновая задача для проверки напоминаний
async def check_reminders():
    while True:
        now = datetime.now(TIMEZONE)
        current_time = now.strftime("%H:%M")
        logging.info(f"Checking reminders at {current_time}, REMINDER_TIMES: {REMINDER_TIMES}")
        for user_id, reminder_time in list(REMINDER_TIMES.items()):
            reminder_time_normalized = datetime.strptime(reminder_time, "%H:%M").strftime("%H:%M")
            last_request_time = LAST_REQUEST.get(user_id)
            card_available = not last_request_time or (now - last_request_time >= timedelta(minutes=1))
            logging.info(f"User {user_id}: reminder_time={reminder_time_normalized}, current_time={current_time}, card_available={card_available}, last_request={last_request_time}")
            if current_time == reminder_time_normalized and card_available:
                name = USER_NAMES.get(user_id, "")
                text = f"{name}, привет! Пришло время вытянуть свою карту дня. ✨ Она уже ждет тебя!" if name else "Привет! Пришло время вытянуть свою карту дня. ✨ Она уже ждет тебя!"
                try:
                    await bot.send_message(user_id, text, reply_markup=get_main_menu(user_id), protect_content=True)
                    logging.info(f"Reminder sent to {user_id} at {reminder_time_normalized}")
                except Exception as e:
                    logging.error(f"Failed to send reminder to {user_id}: {e}")
        await asyncio.sleep(60)

logging.debug("Reminder check function defined.")

# Предложение напоминания
async def suggest_reminder(user_id, state: FSMContext):
    name = USER_NAMES.get(user_id, "")
    logging.info(f"Suggesting reminder to {user_id}: in REMINDER_TIMES={user_id in REMINDER_TIMES}")
    if user_id not in REMINDER_TIMES:
        text = f"{name}, если хочешь, я могу напоминать тебе о карте дня! Введи время в формате чч:мм (например, 10:00) по московскому времени (UTC+3)." if name else "Если хочешь, я могу напоминать тебе о карте дня! Введи время в формате чч:мм (например, 10:00) по московскому времени (UTC+3)."
        try:
            await bot.send_message(user_id, text, reply_markup=get_main_menu(user_id), protect_content=True)
            await state.set_state(UserState.waiting_for_reminder_time)
            logging.info(f"Reminder suggestion sent to {user_id}")
        except Exception as e:
            logging.error(f"Failed to suggest reminder to {user_id}: {e}")
    else:
        logging.info(f"No reminder suggestion for {user_id}: already has reminder time")

# Команда /start
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
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

# Команда /reminder
@dp.message(Command("reminder"))
async def reminder_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    current_reminder = REMINDER_TIMES.get(user_id, "не установлено")
    text = f"{name}, текущее время напоминания: {current_reminder}. Введи новое время в формате чч:мм (например, 10:00) по московскому времени (UTC+3)." if name else f"Текущее время напоминания: {current_reminder}. Введи новое время в формате чч:мм (например, 10:00) по московскому времени (UTC+3)."
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
    await state.set_state(UserState.waiting_for_reminder_time)

# Обработка кнопки "⏰ Напоминание"
@dp.message(lambda message: message.text == "⏰ Напоминание")
async def handle_reminder_button(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    current_reminder = REMINDER_TIMES.get(user_id, "не установлено")
    text = f"{name}, текущее время напоминания: {current_reminder}. Введи новое время в формате чч:мм (например, 10:00) по московскому времени (UTC+3)." if name else f"Текущее время напоминания: {current_reminder}. Введи новое время в формате чч:мм (например, 10:00) по московскому времени (UTC+3)."
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
    await state.set_state(UserState.waiting_for_reminder_time)

# Обработка ввода имени
@dp.message(UserState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    USER_NAMES[user_id] = name
    save_json(USER_NAMES_FILE, USER_NAMES)
    await message.answer(
        f"{name}, рада тебя видеть! Нажми '✨ Карта дня' в меню.",
        reply_markup=get_main_menu(user_id),
        protect_content=True
    )
    await state.clear()

# Обработка кнопки "Пропустить"
@dp.callback_query(lambda c: c.data == "skip_name")
async def process_skip_name(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    USER_NAMES[user_id] = ""
    save_json(USER_NAMES_FILE, USER_NAMES)
    await callback.message.answer(
        "Хорошо, без имени тоже здорово! Выбери '✨ Карта дня' в меню!",
        reply_markup=get_main_menu(user_id),
        protect_content=True
    )
    await state.clear()
    await callback.answer()

# Обработка ввода времени напоминания
@dp.message(UserState.waiting_for_reminder_time)
async def process_reminder_time(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    reminder_time = message.text.strip()
    try:
        reminder_time_normalized = datetime.strptime(reminder_time, "%H:%M").strftime("%H:%M")
        REMINDER_TIMES[user_id] = reminder_time_normalized
        save_json(REMINDER_TIMES_FILE, REMINDER_TIMES)
        text = f"{name}, супер! Я буду напоминать тебе о карте дня в {reminder_time_normalized} (UTC+3)." if name else f"Супер! Я буду напоминать тебе о карте дня в {reminder_time_normalized} (UTC+3)."
        await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
        await state.clear()
    except ValueError:
        text = f"{name}, кажется, время указано неверно. Попробуй ещё раз в формате чч:мм (например, 10:00)." if name else "Кажется, время указано неверно. Попробуй ещё раз в формате чч:мм (например, 10:00)."
        await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)

# Обработка "Карта дня"
@dp.message(lambda message: message.text == "✨ Карта дня")
async def handle_card_request(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    now = datetime.now(TIMEZONE)

    if user_id in LAST_REQUEST and now - LAST_REQUEST[user_id] < timedelta(minutes=1):
        text = f"{name}, карту дня можно вытянуть только раз в минуту – всему своё время! 🌿 Подожди немного." if name else "Карту дня можно вытянуть только раз в минуту – всему своё время! 🌿 Подожди немного."
        await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
        return

    text = f"{name}, давай сделаем это осознанно! 🌿 Подумай: какой вопрос ты хочешь задать карте? Нажми кнопку, когда будешь готова!" if name else "Давай сделаем это осознанно! 🌿 Подумай: какой вопрос ты хочешь задать карте? Нажми кнопку, когда будешь готова!"
    confirmation_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Запрос готов!", callback_data="confirm_request")]])
    await message.answer(text, reply_markup=confirmation_keyboard, protect_content=True)
    await state.set_state(UserState.waiting_for_request_confirmation)

# Обработка подтверждения запроса для "Карта дня"
@dp.callback_query(lambda c: c.data == "confirm_request")
async def process_request_confirmation(callback: types.CallbackQuery, state: FSMContext):
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

        await suggest_reminder(user_id, state)

        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при отправке карты: {e}")
        await callback.message.answer("Что-то пошло не так... попробуй позже.", reply_markup=get_main_menu(user_id), protect_content=True)
        await state.clear()
    await callback.answer()

# Обработка "Поделиться"
@dp.message(lambda message: message.text == "🕊 Поделиться")
async def handle_share_info(message: types.Message):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    ref_link = f"{BOT_LINK}?start=ref_{user_id}"
    text = f"{name}, этот бот — находка для вдохновения! Поделись: {ref_link}. Если кто-то зайдёт, получишь '💌 Подсказку Вселенной'!" if name else f"Этот бот — находка для вдохновения! Поделись: {ref_link}. Если кто-то зайдёт, получишь '💌 Подсказку Вселенной'!"
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=False)

# Обработка "Совет от Вселенной"
@dp.message(lambda message: message.text == "💌 Подсказка Вселенной")
async def handle_bonus_request(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    if not BONUS_AVAILABLE.get(user_id, False):
        text = f"{name}, этот совет пока спрятан! Поделись ботом через 'Поделиться', и он откроется, когда кто-то зайдёт!" if name else "Этот совет пока спрятан! Поделись ботом через 'Поделиться', и он откроется, когда кто-то зайдёт!"
        await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
        return

    advice = random.choice(UNIVERSE_ADVICE)
    text = f"{name}, вот послание для тебя:\n{advice}" if name else f"Вот послание для тебя:\n{advice}"
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)

# Обработка обратной связи
@dp.callback_query(lambda c: c.data.startswith("feedback_"))
async def process_feedback(callback: types.CallbackQuery):
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

    await callback.message.answer("Спасибо за ответ!", reply_markup=get_main_menu(user_id), protect_content=True)
    await callback.answer()

# Запуск бота
async def main():
    logging.info("Bot starting...")
    asyncio.create_task(check_reminders())
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