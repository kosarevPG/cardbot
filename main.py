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
    user_id = message.from_user.id
    username = message.from_user.username or ""  # Получаем никнейм
    user_data = db.get_user(user_id)
    if user_data["username"] != username:
        user_data["username"] = username
        db.update_user(user_id, user_data)

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

# Команда /users
@dp.message(Command("users"))
async def users_command(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("Эта команда доступна только администратору.")
        return

    users = db.get_all_users()
    if not users:
        await message.answer("Пользователей пока нет.")
        return

    # Фильтруем пользователей, исключая NO_LOGS_USERS
    excluded_users = set(NO_LOGS_USERS)
    filtered_users = [uid for uid in users if uid not in excluded_users]
    if not filtered_users:
        await message.answer("Нет пользователей, кроме исключённых.")
        return

    # Собираем данные о пользователях с сортировкой по последнему действию
    user_list = []
    for uid in filtered_users:
        user_data = db.get_user(uid)
        name = user_data["name"] or "Без имени"
        username = user_data["username"] or "Нет никнейма"
        
        # Получаем последнее действие из таблицы actions
        user_actions = db.get_actions(uid)
        last_action_time = "Нет действий"
        last_action_timestamp = "1970-01-01T00:00:00+00:00"  # Минимальное значение для сортировки
        if user_actions:
            last_action = max(user_actions, key=lambda x: x["timestamp"])
            last_action_time = last_action["timestamp"]
            last_action_timestamp = last_action_time

        user_list.append({
            "uid": uid,
            "username": username,
            "name": name,
            "last_action_time": last_action_time,
            "last_action_timestamp": last_action_timestamp
        })

    # Сортируем по last_action_timestamp (по возрастанию)
    user_list.sort(key=lambda x: x["last_action_timestamp"])

    # Формируем строки для вывода
    formatted_list = [
        f"ID: {user['uid']}, Ник: @{user['username']}, Имя: {user['name']}, Последнее действие: {user['last_action_time']}"
        for user in user_list
    ]

    # Разбиваем на части, если список длинный
    if len("\n".join(formatted_list)) > 4096:
        chunk_size = 10
        for i in range(0, len(formatted_list), chunk_size):
            chunk = formatted_list[i:i + chunk_size]
            chunk_text = f"Список пользователей (часть {i // chunk_size + 1}):\n" + "\n".join(chunk)
            await message.answer(chunk_text)
    else:
        text = "Список пользователей:\n" + "\n".join(formatted_list)
        await message.answer(text)

# Команда /feedback (старая логика с адаптацией к SQLite)
@dp.message(Command("feedback"))
async def feedback_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]  # Берем имя из базы данных
    text = (
        f"{name}, напиши свой вопрос или идею, чтобы я смог стать ещё полезнее. Я сохраню ваши мысли!"
        if name
        else "Напиши свой вопрос или идею, чтобы я смог стать ещё полезнее. Я сохраню ваши мысли!"
    )
    await message.answer(
        text,
        reply_markup=await get_main_menu(user_id, db),  # Асинхронная функция, поэтому await
        protect_content=True  # Защищаем контент от копирования
    )
    await state.set_state(UserState.waiting_for_feedback)  # Устанавливаем состояние ожидания отзыва
    await logger.log_action(user_id, "feedback_initiated")

# Обработка ввода отзыва
@dp.message(UserState.waiting_for_feedback)
async def process_feedback(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    feedback_text = message.text.strip()
    name = db.get_user(user_id)["name"]
    timestamp = datetime.now(TIMEZONE).isoformat()

    # Сохраняем отзыв в таблицу feedback
    with db.conn:
        db.conn.execute(
            "INSERT INTO feedback (user_id, name, feedback, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, name, feedback_text, timestamp)
        )

    await logger.log_action(user_id, "feedback_submitted", {"feedback": feedback_text})
    text = f"{name}, спасибо за твой отзыв!" if name else "Спасибо за твой отзыв!"
    await message.answer(
        text,
        reply_markup=await get_main_menu(user_id, db),
        protect_content=True  # Сохраняем защиту контента
    )
    await state.clear()

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
    if name == "✨ Карта дня":  # Валидация имени
        await message.answer("Пожалуйста, выбери другое имя. Это имя зарезервировано.")
        return
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

# Команда /check_logs для проверки логов
@dp.message(Command("logs"))
async def logs_command(message: types.Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        await message.answer("Эта команда доступна только администратору.")
        return

    args = message.text.split()
    if len(args) > 1:
        try:
            target_date = datetime.strptime(args[1], "%Y-%m-%d").date()
        except ValueError:
            await message.answer("Укажите дату в формате YYYY-MM-DD, например: /logs 2025-04-07")
            return
    else:
        target_date = datetime.now(TIMEZONE).date()  # По умолчанию текущая дата

    logs = db.get_actions()
    filtered_logs = []
    excluded_users = set(NO_LOGS_USERS)  # Множество для быстрой проверки
    for log in logs:
        try:
            log_timestamp = datetime.fromisoformat(log["timestamp"]).astimezone(TIMEZONE)
            if log_timestamp.date() == target_date and log["user_id"] not in excluded_users:
                filtered_logs.append(log)
        except ValueError as e:
            await message.answer(f"Ошибка формата времени в логе: {log['timestamp']}, ошибка: {e}")
            return

    if not filtered_logs:
        await message.answer(f"Логов за {target_date} нет.")
        return

    # Разбиваем логи на части по 20 записей
    chunk_size = 20
    for i in range(0, len(filtered_logs), chunk_size):
        chunk = filtered_logs[i:i + chunk_size]
        text = f"Логи за {target_date} (часть {i // chunk_size + 1}):\n"
        for log in chunk:
            text += f"User {log['user_id']}: {log['action']} at {log['timestamp']}, details: {log['details']}\n"
        
        # Проверяем длину текста (для отладки, можно убрать позже)
        if len(text) > 4096:
            await message.answer("Сообщение слишком длинное, уменьшите chunk_size.")
            return
        
        await message.answer(text)

# Фабрики обработчиков
def make_card_request_handler(db, logger):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        return await handle_card_request(message, state, db, logger)
    return wrapped_handler

def make_draw_card_handler(db, logger):
    async def wrapped_handler(callback: types.CallbackQuery, state: FSMContext):
        return await draw_card(callback, state, db, logger)
    return wrapped_handler

def make_process_request_text_handler(db, logger):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        return await process_request_text(message, state, db, logger)
    return wrapped_handler

def make_process_initial_response_handler(db, logger):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        return await process_initial_response(message, state, db, logger)
    return wrapped_handler

def make_process_first_grok_response_handler(db, logger):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        return await process_first_grok_response(message, state, db, logger)
    return wrapped_handler

def make_process_second_grok_response_handler(db, logger):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        return await process_second_grok_response(message, state, db, logger)
    return wrapped_handler

def make_process_third_grok_response_handler(db, logger):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        return await process_third_grok_response(message, state, db, logger)
    return wrapped_handler

def make_process_card_feedback_handler(db, logger):
    async def wrapped_handler(callback: types.CallbackQuery, state: FSMContext):
        return await process_card_feedback(callback, state, db, logger)
    return wrapped_handler

# Обработка "Карта дня"
dp.message.register(make_card_request_handler(db, logger), lambda m: m.text == "✨ Карта дня")
dp.callback_query.register(make_draw_card_handler(db, logger), lambda c: c.data == "draw_card")
dp.message.register(make_process_request_text_handler(db, logger), UserState.waiting_for_request_text)
dp.message.register(make_process_initial_response_handler(db, logger), UserState.waiting_for_initial_response)
dp.message.register(make_process_first_grok_response_handler(db, logger), UserState.waiting_for_first_grok_response)
dp.message.register(make_process_second_grok_response_handler(db, logger), UserState.waiting_for_second_grok_response)
dp.message.register(make_process_third_grok_response_handler(db, logger), UserState.waiting_for_third_grok_response)
dp.callback_query.register(make_process_card_feedback_handler(db, logger), lambda c: c.data.startswith("feedback_"))  # Регистрируем обработчик для feedback

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

# Обработчик для неизвестных сообщений
@dp.message()
async def handle_unknown_message(message: types.Message):
    await message.answer("Извините, я не понял ваш запрос. Попробуйте нажать '✨ Карта дня' или используйте команды /start, /name, /remind, /share, /feedback")

# Запуск
async def main():
    try:
        db.bot = bot
        # Разовая миграция: обновляем username для всех пользователей
        users = db.get_all_users()
        for user_id in users:
            try:
                chat = await bot.get_chat(user_id)
                username = chat.username or ""
                user_data = db.get_user(user_id)
                if user_data["username"] != username:
                    user_data["username"] = username
                    db.update_user(user_id, user_data)
            except Exception as e:
                logger.log_action(user_id, "username_migration_error", {"error": str(e)})

        asyncio.create_task(notifier.check_reminders())
        broadcast_data = {
            "datetime": datetime.now(TIMEZONE).replace(second=0, microsecond=0) + timedelta(minutes=2),
            "text": "Тестовая рассылка",
            "recipients": [6682555021]
        }
        asyncio.create_task(notifier.send_broadcast(broadcast_data))
        while True:
            try:
                await dp.start_polling(bot)
                break
            except Exception as e:
                logger.log_action(0, "polling_error", {"error": str(e)})
                await asyncio.sleep(5)
    except Exception as e:
        logger.log_action(0, "main_error", {"error": str(e)})
        raise

if __name__ == "__main__":
    asyncio.run(main())
