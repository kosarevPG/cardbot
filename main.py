import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
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
from modules.ai_service import build_user_profile
import random
from datetime import datetime, timedelta
import os
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger_root = logging.getLogger()

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
                    text = f"{name}, привет! Чтобы начать, подпишись на <a href='https://t.me/TopPsyGame'>канал автора</a>!" if name else "Привет! Чтобы начать, подпишись на <a href='https://t.me/TopPsyGame'>канал автора</a>!"
                    await event.answer(text, disable_web_page_preview=True)
                    return
            except Exception as e:
                logger_root.error(f"Subscription check failed for user {user_id}: {e}")
                await event.answer("Ой, что-то сломалось... Попробуй позже.")
                return
        return await handler(event, data)

dp.message.middleware(SubscriptionMiddleware())

# Обработчик опросника
async def send_survey(message: types.Message, db, logger):
    user_id = message.from_user.id
    allowed_users = [6682555021, 392141189]
    
    logger_root.info(f"Processing /survey for user {user_id}")
    if user_id not in allowed_users:
        await message.answer("Этот опрос пока доступен только избранным пользователям.")
        return

    name = db.get_user(user_id)["name"]
    text = (
        f"Привет, {name}! 🌟 Ты уже успела поработать с картами — как впечатления? Помоги мне стать лучше:\n"
        "1. Пробовала делиться мной через /share?\n"
        "2. Пишешь запрос перед картой или держишь в голове?\n"
        "3. Вопросы после карты — твоё?\n"
        "4. Хочешь более глубокий анализ твоих ответов?\n"
        "5. Какие новые идеи тебе интересны?\n"
        "Выбери ответы кнопками ниже. Спасибо! 💌"
        if name else
        "Привет! 🌟 Ты уже успела поработать с картами — как впечатления? Помоги мне стать лучше:\n"
        "1. Пробовала делиться мной через /share?\n"
        "2. Пишешь запрос перед картой или держишь в голове?\n"
        "3. Вопросы после карты — твоё?\n"
        "4. Хочешь более глубокий анализ твоих ответов?\n"
        "5. Какие новые идеи тебе интересны?\n"
        "Выбери ответы кнопками ниже. Спасибо! 💌"
    )

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="1. Да", callback_data="survey_1_yes"),
         types.InlineKeyboardButton(text="1. Нет, не вижу смысла", callback_data="survey_1_no_reason"),
         types.InlineKeyboardButton(text="1. Не знала", callback_data="survey_1_no_knowledge")],
        [types.InlineKeyboardButton(text="2. Пишу", callback_data="survey_2_write"),
         types.InlineKeyboardButton(text="2. В голове", callback_data="survey_2_head"),
         types.InlineKeyboardButton(text="2. Не хочу делиться", callback_data="survey_2_private")],
        [types.InlineKeyboardButton(text="3. Нравятся", callback_data="survey_3_like"),
         types.InlineKeyboardButton(text="3. Хочу глубины", callback_data="survey_3_depth"),
         types.InlineKeyboardButton(text="3. Не моё", callback_data="survey_3_not_mine")],
        [types.InlineKeyboardButton(text="4. Да", callback_data="survey_4_yes"),
         types.InlineKeyboardButton(text="4. Нет", callback_data="survey_4_no"),
         types.InlineKeyboardButton(text="4. Боюсь последствий", callback_data="survey_4_fear")],
        [types.InlineKeyboardButton(text="5. Напоминания", callback_data="survey_5_reminders"),
         types.InlineKeyboardButton(text="5. Больше карт", callback_data="survey_5_cards"),
         types.InlineKeyboardButton(text="5. Глубокий разбор", callback_data="survey_5_depth")]
    ])

    try:
        await message.answer(text, reply_markup=keyboard)
        await logger.log_action(user_id, "survey_initiated")
    except Exception as e:
        logger_root.error(f"Failed to send survey to user {user_id}: {e}")

# Обработчик ответов опросника
async def process_survey_response(callback: types.CallbackQuery, db, logger):
    user_id = callback.from_user.id
    callback_data = callback.data
    question, answer = callback_data.split("_", 1)

    logger_root.info(f"Processing survey response for user {user_id}: {callback_data}")

    answer_map = {
        "survey_1_yes": "Да",
        "survey_1_no_reason": "Нет, не вижу смысла",
        "survey_1_no_knowledge": "Не знала",
        "survey_2_write": "Пишу",
        "survey_2_head": "В голове",
        "survey_2_private": "Не хочу делиться",
        "survey_3_like": "Нравятся",
        "survey_3_depth": "Хочу глубины",
        "survey_3_not_mine": "Не моё",
        "survey_4_yes": "Да",
        "survey_4_no": "Нет",
        "survey_4_fear": "Боюсь последствий",
        "survey_5_reminders": "Напоминания",
        "survey_5_cards": "Больше карт",
        "survey_5_depth": "Глубокий разбор"
    }

    question_num = question.split("_")[1]
    response = answer_map.get(callback_data, "Неизвестный ответ")

    try:
        await logger.log_action(user_id, "survey_response", {
            "question": f"Вопрос {question_num}",
            "answer": response
        })
        await callback.answer(f"Спасибо за ответ на вопрос {question_num}!")
    except Exception as e:
        logger_root.error(f"Failed to process survey response for user {user_id}: {e}")

# Явная асинхронная функция для /survey
async def handle_survey(message: types.Message):
    logger_root.info(f"Handle_survey called for message: {message.text} from user {message.from_user.id}")
    await send_survey(message, db, logger)

# Фабрики для команд
def make_start_handler(db, logger, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        username = message.from_user.username or ""
        args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
        
        user_data = db.get_user(user_id)
        if user_data["username"] != username:
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
    return wrapped_handler

def make_share_handler(db):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        username = message.from_user.username or ""
        user_data = db.get_user(user_id)
        if user_data["username"] != username:
            user_data["username"] = username
            db.update_user(user_id, user_data)

        name = db.get_user(user_id)["name"]
        ref_link = f"{BOT_LINK}?start=ref_{user_id}"
        text = f"{name}, поделись: {ref_link}. Если кто-то зайдёт, получишь '💌 Подсказку Вселенной'!" if name else f"Поделись: {ref_link}. Если кто-то зайдёт, получишь '💌 Подсказку Вселенной'!"
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
    return wrapped_handler

def make_remind_handler(db, logger, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = db.get_user(user_id)["name"]
        current_reminder = db.get_user(user_id)["reminder_time"] or "не установлено"
        text = f"{name}, текущее время напоминания: {current_reminder}. Введи новое время (чч:мм)." if name else f"Текущее время напоминания: {current_reminder}. Введи новое время (чч:мм)."
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await state.set_state(UserState.waiting_for_reminder_time)
    return wrapped_handler

def make_users_handler(db):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if user_id != ADMIN_ID:
            await message.answer("Эта команда доступна только администратору.")
            return

        users = db.get_all_users()
        if not users:
            await message.answer("Пользователей пока нет.")
            return

        excluded_users = set(NO_LOGS_USERS)
        filtered_users = [uid for uid in users if uid not in excluded_users]
        if not filtered_users:
            await message.answer("Нет пользователей, кроме исключённых.")
            return

        user_list = []
        for uid in filtered_users:
            user_data = db.get_user(uid)
            name = user_data["name"] or "Без имени"
            username = user_data["username"] or "Нет никнейма"
            
            user_actions = db.get_actions(uid)
            last_action_time = "Нет действий"
            last_action_timestamp = "1970-01-01T00:00:00+00:00"
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

        user_list.sort(key=lambda x: x["last_action_timestamp"])

        formatted_list = [
            f"ID: {user['uid']}, Ник: @{user['username']}, Имя: {user['name']}, Последнее действие: {user['last_action_time']}"
            for user in user_list
        ]

        if len("\n".join(formatted_list)) > 4096:
            chunk_size = 10
            for i in range(0, len(formatted_list), chunk_size):
                chunk = formatted_list[i:i + chunk_size]
                chunk_text = f"Список пользователей (часть {i // chunk_size + 1}):\n" + "\n".join(chunk)
                await message.answer(chunk_text)
        else:
            text = "Список пользователей:\n" + "\n".join(formatted_list)
            await message.answer(text)
    return wrapped_handler

def make_user_profile_handler(db, logger):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        await state.clear()
        user_id = message.from_user.id
        await logger.log_action(user_id, "user_profile_viewed")
        profile = await build_user_profile(user_id, db)

        if not profile:
            await message.answer("У тебя пока нет профиля. Попробуй вытянуть карту дня и ответить на вопросы! ✨")
            return

        mood = profile["mood"]
        mood_trend = " → ".join(profile["mood_trend"]) if profile["mood_trend"] else "Нет данных"
        themes = ", ".join(profile["themes"]) if profile["themes"] else "Нет данных"
        response_count = profile["response_count"]
        request_count = profile["request_count"]
        avg_response_length = round(profile["avg_response_length"], 2)
        days_active = profile["days_active"]
        interactions_per_day = round(profile["interactions_per_day"], 2)
        last_updated = profile["last_updated"].strftime("%Y-%m-%d %H:%M:%S") if profile["last_updated"] else "Не обновлялся"

        text = (
            f"🌟 Твой профиль:\n\n"
            f"Настроение: {mood}\n"
            f"Тренд настроения: {mood_trend}\n"
            f"Основные темы: {themes}\n"
            f"Количество ответов: {response_count}\n"
            f"Количество запросов: {request_count}\n"
            f"Средняя длина ответа: {avg_response_length} символов\n"
            f"Дней активности: {days_active}\n"
            f"Взаимодействий в день: {interactions_per_day}\n"
            f"Последнее обновление: {last_updated}"
        )

        await message.answer(text)
    return wrapped_handler

def make_admin_user_profile_handler(db):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if user_id != ADMIN_ID:
            await message.answer("Эта команда доступна только администратору.")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer("Укажите ID пользователя: /admin_user_profile <user_id>")
            return

        try:
            target_user_id = int(args[1])
        except ValueError:
            await message.answer("ID пользователя должен быть числом.")
            return

        profile = await build_user_profile(target_user_id, db)

        if not profile:
            await message.answer(f"Профиль пользователя {target_user_id} не найден.")
            return

        mood = profile["mood"]
        mood_trend = " → ".join(profile["mood_trend"]) if profile["mood_trend"] else "Нет данных"
        themes = ", ".join(profile["themes"]) if profile["themes"] else "Нет данных"
        response_count = profile["response_count"]
        request_count = profile["request_count"]
        avg_response_length = round(profile["avg_response_length"], 2)
        days_active = profile["days_active"]
        interactions_per_day = round(profile["interactions_per_day"], 2)
        last_updated = profile["last_updated"].strftime("%Y-%m-%d %H:%M:%S") if profile["last_updated"] else "Не обновлялся"

        text = (
            f"Профиль пользователя {target_user_id}:\n\n"
            f"Настроение: {mood}\n"
            f"Тренд настроения: {mood_trend}\n"
            f"Основные темы: {themes}\n"
            f"Количество ответов: {response_count}\n"
            f"Количество запросов: {request_count}\n"
            f"Средняя длина ответа: {avg_response_length} символов\n"
            f"Дней активности: {days_active}\n"
            f"Взаимодействий в день: {interactions_per_day}\n"
            f"Последнее обновление: {last_updated}"
        )
        await message.answer(text)
    return wrapped_handler

def make_feedback_handler(db, logger):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = db.get_user(user_id)["name"]
        text = (
            f"{name}, напиши свой вопрос или идею, чтобы я смог стать ещё полезнее. Я сохраню ваши мысли!"
            if name
            else "Напиши свой вопрос или идею, чтобы я смог стать ещё полезнее. Я сохраню ваши мысли!"
        )
        await message.answer(
            text,
            reply_markup=await get_main_menu(user_id, db),
            protect_content=True
        )
        await state.set_state(UserState.waiting_for_feedback)
        await logger.log_action(user_id, "feedback_initiated")
    return wrapped_handler

def make_process_feedback_handler(db, logger):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        feedback_text = message.text.strip()
        name = db.get_user(user_id)["name"]
        timestamp = datetime.now(TIMEZONE).isoformat()

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
            protect_content=True
        )
        await state.clear()
    return wrapped_handler

def make_name_handler(db, logger, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = db.get_user(user_id)["name"]
        text = f"{name}, как тебя зовут? Введи новое имя или 'Пропустить'." if name else "Как тебя зовут? Введи имя или 'Пропустить'."
        await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]
        ]))
        await state.set_state(UserState.waiting_for_name)
    return wrapped_handler

def make_process_name_handler(db, logger, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = message.text.strip()
        if name == "✨ Карта дня":
            await message.answer("Пожалуйста, выбери другое имя. Это имя зарезервировано.")
            return
        await user_manager.set_name(user_id, name)
        await logger.log_action(user_id, "set_name", {"name": name})
        await message.answer(f"{name}, рада тебя видеть! Нажми '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()
    return wrapped_handler

def make_process_skip_name_handler(db, logger, user_manager):
    async def wrapped_handler(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        await user_manager.set_name(user_id, "")
        await logger.log_action(user_id, "skip_name")
        await callback.message.answer("Хорошо, без имени тоже здорово! Выбери '✨ Карта дня'!", reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        await callback.answer()
    return wrapped_handler

def make_process_reminder_time_handler(db, logger, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
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
    return wrapped_handler

def make_logs_handler(db):
    async def wrapped_handler(message: types.Message):
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
            target_date = datetime.now(TIMEZONE).date()

        logs = db.get_actions()
        filtered_logs = []
        excluded_users = set(NO_LOGS_USERS)
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

        chunk_size = 20
        for i in range(0, len(filtered_logs), chunk_size):
            chunk = filtered_logs[i:i + chunk_size]
            text = f"Логи за {target_date} (часть {i // chunk_size + 1}):\n"
            for log in chunk:
                text += f"User {log['user_id']}: {log['action']} at {log['timestamp']}, details: {log['details']}\n"
            
            if len(text) > 4096:
                await message.answer("Сообщение слишком длинное, уменьшите chunk_size.")
                return
            
            await message.answer(text)
    return wrapped_handler

def make_bonus_request_handler(db, logger):
    async def wrapped_handler(message: types.Message):
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
    return wrapped_handler

# Фабрики обработчиков для карты дня
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

# Регистрация обработчиков
dp.message.register(make_start_handler(db, logger, user_manager), Command("start"))
dp.message.register(make_share_handler(db), Command("share"))
dp.message.register(make_remind_handler(db, logger, user_manager), Command("remind"))
dp.message.register(make_users_handler(db), Command("users"))
dp.message.register(make_user_profile_handler(db, logger), Command("user_profile"), StateFilter("*"))
dp.message.register(make_admin_user_profile_handler(db), Command("admin_user_profile"))
dp.message.register(make_feedback_handler(db, logger), Command("feedback"))
dp.message.register(make_process_feedback_handler(db, logger), UserState.waiting_for_feedback)
dp.message.register(make_name_handler(db, logger, user_manager), Command("name"))
dp.message.register(make_process_name_handler(db, logger, user_manager), UserState.waiting_for_name)
dp.callback_query.register(make_process_skip_name_handler(db, logger, user_manager), lambda c: c.data == "skip_name")
dp.message.register(make_process_reminder_time_handler(db, logger, user_manager), UserState.waiting_for_reminder_time)
dp.message.register(make_logs_handler(db), Command("logs"))
dp.message.register(make_bonus_request_handler(db, logger), lambda m: m.text == "💌 Подсказка Вселенной")
dp.message.register(handle_survey, Command("survey"))
dp.callback_query.register(lambda c: process_survey_response(c, db, logger), lambda c: c.data.startswith("survey_"))

# Обработка "Карта дня"
dp.message.register(make_card_request_handler(db, logger), lambda m: m.text == "✨ Карта дня")
dp.callback_query.register(make_draw_card_handler(db, logger), lambda c: c.data == "draw_card")
dp.message.register(make_process_request_text_handler(db, logger), UserState.waiting_for_request_text)
dp.message.register(make_process_initial_response_handler(db, logger), UserState.waiting_for_initial_response)
dp.message.register(make_process_first_grok_response_handler(db, logger), UserState.waiting_for_first_grok_response)
dp.message.register(make_process_second_grok_response_handler(db, logger), UserState.waiting_for_second_grok_response)
dp.message.register(make_process_third_grok_response_handler(db, logger), UserState.waiting_for_third_grok_response)
dp.callback_query.register(make_process_card_feedback_handler(db, logger), lambda c: c.data.startswith("feedback_"))

# Обработчик для неизвестных сообщений
@dp.message()
async def handle_unknown_message(message: types.Message):
    await message.answer("Извините, я не понял ваш запрос. Попробуйте нажать '✨ Карта дня' или используйте команды /start, /name, /remind, /share, /feedback, /user_profile")

# Запуск
async def main():
    try:
        db.bot = bot
        logger_root.info("Starting bot initialization")
        
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

        # Устанавливаем команды для бота
        commands = [
            types.BotCommand(command="start", description="🔄 Перезагрузка"),
            types.BotCommand(command="name", description="У🧑 Указать имя"),
            types.BotCommand(command="remind", description="⏰ Напоминание"),
            types.BotCommand(command="share", description="🎁 Поделиться"),
            types.BotCommand(command="feedback", description="📩 Отзыв")
        ]
        await bot.set_my_commands(commands)
        logger_root.info("Bot commands set successfully")

        asyncio.create_task(notifier.check_reminders())
        
        # Рассылка опросника конкретным пользователям
        survey_users = [6682555021, 392141189]
        broadcast_data_survey = {
            "datetime": datetime.now(TIMEZONE).replace(second=0, microsecond=0),
            "text": "Привет! 🌟 Нажми /survey, чтобы поделиться впечатлениями и помочь мне стать лучше!",
            "recipients": survey_users
        }
        asyncio.create_task(notifier.send_broadcast(broadcast_data_survey))
        logger_root.info("Survey broadcast task created")

        logger_root.info("Entering polling loop")
        await dp.start_polling(bot)
        logger_root.info("Polling stopped unexpectedly")
    except Exception as e:
        logger.log_action(0, "main_error", {"error": str(e)})
        logger_root.error(f"Main loop failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
