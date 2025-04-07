import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN, CHANNEL_ID, ADMIN_ID, UNIVERSE_ADVICE, BOT_LINK, TIMEZONE, NO_LOGS_USERS 
from database.db import Database
from modules.logging_service import LoggingService
from modules.notification_service import NotificationService
from modules.card_of_the_day import handle_card_request, draw_card, process_request_text, process_initial_response, process_first_grok_response, process_second_grok_response, process_third_grok_response, process_card_feedback, get_main_menu
from modules.user_management import UserState, UserManager
import random
from datetime import datetime, timedelta  # Добавляем timedelta
import os

# Инициализация
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db_path = "/data/bot.db"
print(f"Checking if database file exists at {db_path}: {os.path.exists(db_path)}")
db = Database(path=db_path)
print(f"Database initialized at {db.conn}")
logger = LoggingService(db)
notifier = NotificationService(bot, db)
user_manager = UserManager(db)

# Проверка базы данных
try:
    db.get_user(0)
    print("Database check successful")
except Exception as e:
    logger.log_action(0, "db_init_error", {"error": str(e)})
    print(f"Database initialization failed: {e}")
    raise

# Middleware для проверки подписки
class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            if user_id == ADMIN_ID:  # Пропускаем проверку для админа
                return await handler(event, data)
            try:
                user_status = await bot.get_chat_member(CHANNEL_ID, user_id)
                if user_status.status not in ["member", "administrator", "creator"]:
                    name = db.get_user(user_id)["name"]
                    text = f"{name}, привет! Подпишись на <a href='https://t.me/TopPsyGame'>канал автора</a>!" if name else "Привет! Подпишись на <a href='https://t.me/TopPsyGame'>канал автора</a>!"
                    await event.answer(text, disable_web_page_preview=True)
                    return
            except Exception:
                await event.answer("Ой, что-то сломалось... Попробуй позже.")
                return
        return await handler(event, data)

dp.message.middleware(SubscriptionMiddleware())

# Команда /start
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or ""  # Получаем никнейм из Telegram
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    
    # Обновляем username в базе данных
    user_data = db.get_user(user_id)
    if user_data["username"] != username:  # Обновляем только если ник изменился
        user_data["username"] = username
        db.update_user(user_id, user_data)

    await logger.log_action(user_id, "start", {"args": args})

    if args.startswith("ref_"):
        referrer_id = int(args[4:])
        if referrer_id != user_id and user_id not in db.get_referrals(referrer_id):
            db.add_referral(referrer_id, user_id)
            if not db.get_user(referrer_id)["bonus_available"]:
                await user_manager.set_bonus_available(referrer_id, True)
                name = db.get_user(referrer_id)["name"]
                text = f"{name}, ура! Кто-то открыл карту по твоей ссылке! Возьми '💌 Подсказку Вселенной'." if name else "Ура! Кто-то открыл карту по твоей ссылке! Возьми '💌 Подсказку Вселенной'."
                await bot.send_message(referrer_id, text, reply_markup=await get_main_menu(referrer_id, db))

    if not db.get_user(user_id)["name"]:
        await message.answer("Привет! Давай знакомиться! Как тебя зовут?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]
        ]))
        await state.set_state(UserState.waiting_for_name)
    else:
        name = db.get_user(user_id)["name"]
        await message.answer(f"{name}, рада тебя видеть! Нажми '✨ Карта дня'." if name else "Рада тебя видеть! Нажми '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))

# Команда /share
@dp.message(Command("share"))
async def share_command(message: types.Message):
    user_id = message.from
