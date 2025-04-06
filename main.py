import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext  # Импорт FSMContext
from aiogram.fsm.storage.memory import MemoryStorage  # Хранилище состояний
from config import TOKEN, CHANNEL_ID, ADMIN_ID, UNIVERSE_ADVICE, BOT_LINK, TIMEZONE
from database.db import Database
from modules.logging_service import LoggingService
from modules.notification_service import NotificationService
from modules.card_of_the_day import handle_card_request, draw_card, process_request_text, process_initial_response, process_first_grok_response, process_second_grok_response, process_third_grok_response, get_main_menu
from modules.user_management import UserState, UserManager
import random
from datetime import datetime

# Инициализация
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()  # Добавляем хранилище состояний
dp = Dispatcher(storage=storage)  # Передаём хранилище в Dispatcher
db = Database()
logger = LoggingService(db)
notifier = NotificationService(bot, db)
user_manager = UserManager(db)

# Middleware для проверки подписки
class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            user_id = event.from_user.id
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
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    
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
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    ref_link = f"{BOT_LINK}?start=ref_{user_id}"
    text = f"{name}, поделись: {ref_link}. Если кто-то зайдёт, получишь '💌 Подсказку Вселенной'!" if name else f"Поделись: {ref_link}. Если кто-то зайдёт, получишь '💌 Подсказку Вселенной'!"
    await message.answer(text, reply_markup=await get_main_menu(user_id, db))

# Команда /remind
@dp.message(Command("remind"))
async def remind_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    current_reminder = db.get_user(user_id)["reminder_time"] or "не установлено"
    text = f"{name}, текущее время напоминания: {current_reminder}. Введи новое время (чч:мм)." if name else f"Текущее время напоминания: {current_reminder}. Введи новое время (чч:мм)."
    await message.answer(text, reply_markup=await get_main_menu(user_id, db))
    await state.set_state(UserState.waiting_for_reminder_time)

# Команда /name
@dp.message(Command("name"))
async def name_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    text = f"{name}, как тебя зовут? Введи новое имя или 'Пропустить'." if name else "Как тебя зовут? Введи имя или 'Пропустить'."
    await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]
    ]))
    await state.set_state(UserState.waiting_for_name)

# Обработка имени
@dp.message(UserState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    await user_manager.set_name(user_id, name)
    await logger.log_action(user_id, "set_name", {"name": name})
    await message.answer(f"{name}, рада тебя видеть! Нажми '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
    await state.clear()

@dp.callback_query(lambda c: c.data == "skip_name")
async def process_skip_name(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await user_manager.set_name(user_id, "")
    await logger.log_action(user_id, "skip_name")
    await callback.message.answer("Хорошо, без имени тоже здорово! Выбери '✨ Карта дня'!", reply_markup=await get_main_menu(user_id, db))
    await state.clear()
    await callback.answer()

# Обработка времени напоминания
@dp.message(UserState.waiting_for_reminder_time)
async def process_reminder_time(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    reminder_time = message.text.strip()
    try:
        reminder_time_normalized = datetime.strptime(reminder_time, "%H:%M").strftime("%H:%M")
        await user_manager.set_reminder(user_id, reminder_time_normalized)
        await logger.log_action(user_id, "set_reminder_time", {"reminder_time": reminder_time_normalized})
        text = f"{name}, я буду напоминать тебе в {reminder_time_normalized} по Москве." if name else f"Я буду напоминать тебе в {reminder_time_normalized} по Москве."
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await state.clear()
    except ValueError:
        text = f"{name}, время указано неверно. Попробуй ещё раз (чч:мм)." if name else "Время указано неверно. Попробуй ещё раз (чч:мм)."
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))

# Обработка "Карта дня"
dp.message.register(handle_card_request, lambda m: m.text == "✨ Карта дня")
dp.callback_query.register(draw_card, lambda c: c.data == "draw_card")
dp.message.register(process_request_text, UserState.waiting_for_request_text)
dp.message.register(process_initial_response, UserState.waiting_for_initial_response)
dp.message.register(process_first_grok_response, UserState.waiting_for_first_grok_response)
dp.message.register(process_second_grok_response, UserState.waiting_for_second_grok_response)
dp.message.register(process_third_grok_response, UserState.waiting_for_third_grok_response)

# Обработка "Подсказка Вселенной"
@dp.message(lambda m: m.text == "💌 Подсказка Вселенной")
async def handle_bonus_request(message: types.Message):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    if not db.get_user(user_id)["bonus_available"]:
        text = f"{name}, этот совет пока спрятан! Используй /share, чтобы получить его." if name else "Этот совет пока спрятан! Используй /share, чтобы получить его."
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        return
    advice = random.choice(UNIVERSE_ADVICE)
    text = f"{name}, вот послание для тебя:\n{advice}" if name else f"Вот послание для тебя:\n{advice}"
    await message.answer(text, reply_markup=await get_main_menu(user_id, db))
    await logger.log_action(user_id, "bonus_request", {"advice": advice})

# Запуск
async def main():
    db.bot = bot  # Передаем bot в db для логирования
    asyncio.create_task(notifier.check_reminders())
    broadcast_data = {
        "datetime": datetime(2025, 4, 6, 2, 8, tzinfo=TIMEZONE),
        "text": "Привет! У нас обновления: 'Карта дня' теперь доступна раз в сутки с 00:00 по Москве.",
        "recipients": [6682555021]
    }
    asyncio.create_task(notifier.send_broadcast(broadcast_data))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
