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

# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)
logging.debug("Starting script...")

# Настройки
TOKEN = "8054930534:AAFDdyp5_xiX0ZPQnSEZKpfOhk2PCdchKvg"
CHANNEL_ID = "@TopPsyGame"
BOT_LINK = "t.me/choose_a_card_bot"
TIMEZONE = pytz.timezone("Europe/Moscow")
ADMIN_ID = 6682555021  # Укажите ваш Telegram ID как администратора

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

# Файлы для хранения данных
DATA_DIR = "/data"
LAST_REQUEST_FILE = f"{DATA_DIR}/last_request.json"
USER_NAMES_FILE = f"{DATA_DIR}/user_names.json"
REFERRALS_FILE = f"{DATA_DIR}/referrals.json"
BONUS_AVAILABLE_FILE = f"{DATA_DIR}/bonus_available.json"
REMINDER_TIMES_FILE = f"{DATA_DIR}/reminder_times.json"
STATS_FILE = f"{DATA_DIR}/card_feedback.json"
FEEDBACK_FILE = f"{DATA_DIR}/feedback.json"
USER_ACTIONS_FILE = f"{DATA_DIR}/user_actions.json"  # Файл для логов

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
    chat = await bot.get_chat(user_id)  # Добавляем await
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
    logs_today = []
    for log in user_actions:
        log_date = datetime.fromisoformat(log["timestamp"]).date()
        if log_date == today:
            logs_today.append(log)
    return logs_today

logging.debug("JSON functions defined.")

# Инициализация данных
LAST_REQUEST = load_json(LAST_REQUEST_FILE, {})
USER_NAMES = load_json(USER_NAMES_FILE, {})
REFERRALS = load_json(REFERRALS_FILE, {})
BONUS_AVAILABLE = load_json(BONUS_AVAILABLE_FILE, {})
REMINDER_TIMES = load_json(REMINDER_TIMES_FILE, {})
FEEDBACK = load_json(FEEDBACK_FILE, {})
USER_ACTIONS = load_user_actions()  # Инициализация логов

for user_id, timestamp in LAST_REQUEST.items():
    LAST_REQUEST[user_id] = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(TIMEZONE)

logging.debug("Data initialized.")

# Список вопросов и советов
REFLECTION_QUESTIONS = [
    "Какой ресурс даёт мне эта карта?",
    "Как этот образ может поддержать меня в сложившейся ситуации?",
    "Какую энергию или силу несёт эта карта?",
    "Какой природный элемент здесь преобладает, и что он для меня значит?",
    "Как этот образ связан с моими текущими переживаниями?",
    "Какой совет может дать мне этот природный символ?",
    "В какой сфере жизни мне сейчас нужен этот ресурс?",
    "Как я могу интегрировать энергию этой карты в свою жизнь?",
    "Каким было бы моё состояние, если бы я уже обладала этим ресурсом?",
    "Как природа через этот образ говорит со мной?",
    "Какую важную мысль или осознание мне даёт эта карта?",
    "Если бы эта карта была ответом на мой вопрос, что бы она сказала?",
    "Как я могу проявить этот ресурс в своём поведении или действиях?",
    "Что в этой карте напоминает мне о чём-то важном в моей жизни?",
    "Как этот образ может помочь мне восстановить баланс и гармонию?",
    "Как я могу поблагодарить природу за её поддержку через этот образ?",
    "Какой главный ресурс заключён в этой карте для меня?",
    "Каким образом этот ресурс уже проявляется в моей жизни?",
    "В какой сфере мне сейчас больше всего нужен этот ресурс?",
    "Как я могу активировать этот ресурс в себе?",
    "Как этот образ помогает мне сейчас осознать мои внутренние силы?",
    "Какой символ на карте больше всего откликается мне как источник поддержки?",
    "Если бы этот ресурс был внутри меня, как бы он проявлялся?",
    "В каком жизненном периоде мне уже помогал подобный ресурс?",
    "Что мешает мне полноценно использовать этот ресурс?",
    "Какой первый шаг я могу сделать, чтобы приблизиться к этому ресурсу?",
    "Какими качествами я наполняюсь, глядя на эту карту?",
    "Что в этом образе даёт мне ощущение уверенности и устойчивости?",
    "Как природа подсказывает мне здесь, где искать свою опору?",
    "Каким образом образ на карте поможет мне решить текущий запрос?",
    "Как я могу поддерживать этот ресурс в себе ежедневно?",
    "Если бы я уже обладала этим ресурсом, как бы я себя чувствовала?",
    "Что изменится в моей жизни, если я приму этот ресурс?",
    "Как я могу делиться этим ресурсом с другими?",
    "Как я могу поблагодарить себя за открытие этого ресурса?"
]
UNIVERSE_ADVICE = [
    "<b>💌 Ты — источник силы.</b> Всё, что тебе нужно, уже внутри. Просто доверься себе и сделай первый шаг.",
    "<b>💌 Вселенная ведёт тебя к ресурсам.</b> Заметь возможности вокруг и позволь себе их принять.",
    "<b>💌 Твой потенциал безграничен.</b> Осмелься проявить себя и мир откроется тебе навстречу.",
    "<b>💌 Каждый шаг — это рост.</b> Даже малое движение приближает тебя к мечте.",
    "<b>💌 Ты достойна изобилия.</b> Позволь себе больше — энергии, радости, успеха.",
    "<b>💌 Наполни себя ресурсами.</b> Когда ты сильна внутри, весь мир поддерживает тебя.",
    "<b>💌 Доверяй процессу.</b> Всё складывается наилучшим образом, даже если пока ты этого не видишь.",
    "<b>💌 Сегодня — идеальный день для действия.</b> Сделай хотя бы один шаг к лучшей версии себя.",
    "<b>💌 Твой путь освещён светом возможностей.</b> Открывай сердце — и увидишь новые горизонты.",
    "<b>💌 Ты сама создаёшь свою реальность.</b> Чем больше ресурса в тебе, тем ярче твоя жизнь.",
    "<b>💌 Достаточно просто быть.</b> Цени себя прямо сейчас, без условий и ожиданий.",
    "<b>💌 Все ответы внутри тебя.</b> Прислушайся — Вселенная говорит с тобой через интуицию.",
    "<b>💌 Ты магнит для благополучия.</b> Позволь хорошему прийти легко и естественно.",
    "<b>💌 Смелость меняет реальность.</b> Позволь себе выйти за границы привычного.",
    "<b>💌 Радость — твой естественный ресурс.</b> Найди её в простых вещах, и жизнь наполнится смыслом.",
    "<b>💌 Сей добро — и оно вернётся.</b> Чем больше света ты даёшь, тем больше получаешь.",
    "<b>💌 Природа поддерживает тебя.</b> Наполнись её энергией и почувствуй свою силу.",
    "<b>💌 Нет предела твоему развитию.</b> Позволь себе стать ещё лучше, ещё счастливее.",
    "<b>💌 У тебя уже есть всё необходимое для успеха.</b> Доверься себе и сделай шаг вперёд.",
    "<b>💌 Ты заслуживаешь самого лучшего.</b> Вселенная щедра к тем, кто открыт её дарам.",
    "<b>💌 Всё в тебе уже готово для нового этапа.</b> Просто начни двигаться вперёд.",
    "<b>💌 Ты ценность для этого мира.</b> Твой свет нужен другим, не скрывай его.",
    "<b>💌 Ресурсы вокруг тебя, просто позволь себе их принять.</b> Ты достоина поддержки и благополучия。",
    "<b>💌 Сегодня – лучший день, чтобы позаботиться о себе.</b> Наполни себя тем, что приносит радость。",
    "<b>💌 Вселенная всегда даёт тебе именно то, что нужно для роста.</b> Используй этот момент。",
    "<b>💌 Ты сильнее, чем тебе кажется.</b> Сделай шаг, и ты увидишь, как легко всё меняется。",
    "<b>💌 Любая ситуация — это возможность.</b> Найди ресурс даже там, откуда его не ждёшь。",
    "<b>💌 Твои мечты достижимы.</b> Главное — верить и действовать。",
    "<b>💌 Ты творец своей жизни.</b> Прямо сейчас можешь изменить её к лучшему。",
    "<b>💌 Пусть энергия потока ведёт тебя.</b> Доверься и отпусти контроль — всё сложится идеально。",
    "<b>💌 Ты заслуживаешь лёгкости.</b> Позволь себе радоваться жизни здесь и сейчас。",
    "<b>💌 Природа всегда возрождается — и ты тоже можешь.</b> Новый день — новые возможности。",
    "<b>💌 Чем больше ты наполняешь себя ресурсами, тем больше можешь дать миру.</b> Начни с себя。",
    "<b>💌 Ты находишься в идеальном месте в своей жизни.</b> Всё происходит вовремя。",
    "<b>💌 Любое препятствие — это лишь ступенька к твоему росту.</b> Твои способности безграничны。",
    "<b>💌 Открываясь новому, ты расширяешь свои границы.</b> Не бойся идти в неизведанное。",
    "<b>💌 Ты уже достаточно хороша, чтобы получать лучшее.</b> Позволь себе принимать。",
    "<b>💌 Будь в гармонии с собой — и мир откликнется взаимностью.</b> Наполняй своё пространство любовью。",
    "<b>💌 То, о чём ты мечтаешь, уже движется к тебе.</b> Открывайся чудесам。",
    "<b>💌 Ресурсы не заканчиваются, они перетекают.</b> Подключись к потоку жизни и доверься её ритму。"
]

# Загрузка и сохранение статистики
def load_stats():
    return load_json(STATS_FILE, {"users": {}, "total": {"yes": 0, "no": 0}})

def save_stats(stats):
    save_json(STATS_FILE, stats)

logging.debug("Stats functions defined.")

# Генерация главного меню (убрали "⚙️ Настройки")
def get_main_menu(user_id):
    keyboard = [
        [KeyboardButton(text="✨ Карта дня")]
    ]
    if BONUS_AVAILABLE.get(user_id, False):
        keyboard.append([KeyboardButton(text="💌 Подсказка Вселенной ")])
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

# --- Новая функциональность: Рассылка сообщений ---
BROADCAST = {
    "datetime": datetime(2025, 4, 3, 10, 0, tzinfo=TIMEZONE),  # 03.04.2025 10A:00 по Москве
    "text": "Привет! У нас обновления в боте:  \n✨ \"Карта дня\" теперь доступна раз в сутки с 00:00 по Москве (UTC+3) — проверка идёт по дате, а не по 24 часам от последнего запроса.  \n⚙️ Теперь вместо кнопок используй команды: /name, /remind, /share, /feedback.  \nОтправь /start, чтобы увидеть всё новое!",
    "recipients": "[6682555021]"  # Отправить всем пользователям
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
                    logging.info(f"Broadcast sent to {user_id}")
                except Exception as e:
                    logging.error(f"Failed to send broadcast to {user_id}: {e}")
            BROADCAST_SENT = True
            logging.info("Broadcast completed")
        await asyncio.sleep(60)

# Фоновая задача для проверки напоминаний
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
                    logging.info(f"Reminder sent to {user_id} at {reminder_time_normalized}")
                except Exception as e:
                    logging.error(f"Failed to send reminder to {user_id}: {e}")
        await asyncio.sleep(60)

logging.debug("Reminder check function defined.")

# Предложение напоминания
async def suggest_reminder(user_id, state: FSMContext):
    name = USER_NAMES.get(user_id, "")
    if user_id not in REMINDER_TIMES:
        text = f"{name}, если хочешь, я могу напоминать тебе о карте дня! Используй /remind, чтобы установить время." if name else "Если хочешь, я могу напоминать тебе о карте дня! Используй /remind, чтобы установить время."
        try:
            await bot.send_message(user_id, text, reply_markup=get_main_menu(user_id), protect_content=True)
        except Exception as e:
            logging.error(f"Failed to suggest reminder to {user_id}: {e}")

# Команда /start
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    
    # Логируем запуск бота
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

# Команда /share
@dp.message(Command("share"))
async def share_command(message: types.Message):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    ref_link = f"{BOT_LINK}?start=ref_{user_id}"
    text = f"{name}, этот бот — находка для вдохновения! Поделись: {ref_link}. Если кто-то зайдёт, получишь '💌 Подсказку Вселенной'!" if name else f"Этот бот — находка для вдохновения! Поделись: {ref_link}. Если кто-то зайдёт, получишь '💌 Подсказку Вселенной'!"
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=False)

# Команда /remind
@dp.message(Command("remind"))
async def remind_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    current_reminder = REMINDER_TIMES.get(user_id, "не установлено")
    text = f"{name}, текущее время напоминания: {current_reminder}. Введи новое время в формате чч:мм (например, 10:00) по Москве (UTC+3)." if name else f"Текущее время напоминания: {current_reminder}. Введи новое время в формате чч:мм (например, 10:00) по Москве (UTC+3)."
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
    await state.set_state(UserState.waiting_for_reminder_time)

# Команда /name
@dp.message(Command("name"))
async def name_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    text = f"{name}, как тебя зовут? Введи новое имя или нажми 'Пропустить', если не хочешь его менять." if name else "Как тебя зовут? Введи имя или нажми 'Пропустить', если не хочешь его указывать."
    skip_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]])
    await message.answer(text, reply_markup=skip_keyboard, protect_content=True)
    await state.set_state(UserState.waiting_for_name)

# Команда /feedback
@dp.message(Command("feedback"))
async def feedback_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    text = f"{name}, напиши свой вопрос или идею по улучшению бота. Я сохраню твои мысли!" if name else "Напиши свой вопрос или идею по улучшению бота. Я сохраню твои мысли!"
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
    await state.set_state(UserState.waiting_for_feedback)

# Команда /logs (для администратора)
@dp.message(Command("logs"))
async def logs_command(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("Эта команда доступна только администратору.", protect_content=True)
        return

    logs = get_logs_for_today()
    if not logs:
        await message.answer("Логов за сегодня нет.", protect_content=True)
        return

    # Формируем текст логов
    log_text = "Логи за сегодня:\n\n"
    for log in logs:
        log_text += f"Время: {log['timestamp']}\n"
        log_text += f"Пользователь: {log['name']} (@{log['username']}, ID: {log['user_id']})\n"
        log_text += f"Действие: {log['action']}\n"
        log_text += f"Детали: {json.dumps(log['details'], ensure_ascii=False)}\n"
        log_text += "-" * 30 + "\n"

    # Отправляем логи (разбиваем, если текст слишком длинный)
    MAX_MESSAGE_LENGTH = 4096
    if len(log_text) <= MAX_MESSAGE_LENGTH:
        await message.answer(log_text, protect_content=True)
    else:
        parts = [log_text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(log_text), MAX_MESSAGE_LENGTH)]
        for part in parts:
            await message.answer(part, protect_content=True)
            await asyncio.sleep(0.5)  # Небольшая задержка между сообщениями

# Обработка ввода имени
@dp.message(UserState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    USER_NAMES[user_id] = name
    save_json(USER_NAMES_FILE, USER_NAMES)
    
    # Логируем установку имени
    await save_user_action(user_id, "set_name", {"name": name})

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
    
    # Логируем пропуск имени
    await save_user_action(user_id, "skip_name")

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
        
        # Логируем установку времени напоминания
        await save_user_action(user_id, "set_reminder_time", {"reminder_time": reminder_time_normalized})

        text = f"{name}, супер! Я буду напоминать тебе о карте дня в {reminder_time_normalized} по Москве (UTC+3)." if name else f"Супер! Я буду напоминать тебе о карте дня в {reminder_time_normalized} по Москве (UTC+3)."
        await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
        await state.clear()
    except ValueError:
        text = f"{name}, кажется, время указано неверно. Попробуй ещё раз в формате чч:мм (например, 10:00)." if name else "Кажется, время указано неверно. Попробуй ещё раз в формате чч:мм (например, 10:00)."
        await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)

# Обработка ввода отзыва
@dp.message(UserState.waiting_for_feedback)
async def process_feedback_submission(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    feedback_text = message.text.strip()
    FEEDBACK[user_id] = {"name": name, "feedback": feedback_text, "timestamp": datetime.now(TIMEZONE).isoformat()}
    save_json(FEEDBACK_FILE, FEEDBACK)
    
    # Логируем отправку отзыва
    await save_user_action(user_id, "submit_feedback", {"feedback": feedback_text})

    text = f"{name}, спасибо за твой отзыв! Я сохранила его." if name else "Спасибо за твой отзыв! Я сохранила его."
    await message.answer(text, reply_markup=get_main_menu(user_id), protect_content=True)
    await state.clear()

# Обработка "Карта дня"
@dp.message(lambda message: message.text == "✨ Карта дня")
async def handle_card_request(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = USER_NAMES.get(user_id, "")
    now = datetime.now(TIMEZONE)
    today = now.date()

    last_request_time = LAST_REQUEST.get(user_id)
    if last_request_time and last_request_time.date() == today:
        text = f"{name}, ты уже вытянула карту сегодня! Новая будет доступна завтра в 00:00 по Москве (UTC+3)." if name else "Ты уже вытянула карту сегодня! Новая будет доступна завтра в 00:00 по Москве (UTC+3)."
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
    today = now.date()

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

        # Логируем выбор карты
        await save_user_action(user_id, "card_request", {"card_number": card_number, "reflection_question": reflection_question})

        await suggest_reminder(user_id, state)

        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при отправке карты: {e}")
        await callback.message.answer("Что-то пошло не так... попробуй позже.", reply_markup=get_main_menu(user_id), protect_content=True)
        await state.clear()
    await callback.answer()

# Обработка "Совет от Вселенной"
@dp.message(lambda message: message.text == "💌 Подсказка Вселенной ")
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

    # Логируем получение совета
    await save_user_action(user_id, "bonus_request", {"advice": advice})

# Обработка обратной связи по картам
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

    # Логируем обратную связь
    await save_user_action(user_id, "card_feedback", {"card_number": card_number, "feedback": feedback})

    await callback.message.answer("Спасибо за ответ!", reply_markup=get_main_menu(user_id), protect_content=True)
    await callback.answer()

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
