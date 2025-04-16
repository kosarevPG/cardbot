import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter, CommandObject # Added CommandObject
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage # Using MemoryStorage as before

# Import necessary components from updated files
from config import TOKEN, CHANNEL_ID, ADMIN_ID, UNIVERSE_ADVICE, BOT_LINK, TIMEZONE, NO_LOGS_USERS, DATA_DIR # Ensure DATA_DIR is used if needed elsewhere
from database.db import Database # Updated db.py
from modules.logging_service import LoggingService
from modules.notification_service import NotificationService
from modules.user_management import UserState, UserManager # Updated user_management.py
from modules.ai_service import build_user_profile # Updated ai_service.py

# Import ALL handlers from the updated card_of_the_day.py
from modules.card_of_the_day import (
    get_main_menu,
    handle_card_request,
    process_initial_resource_callback,
    process_request_type_callback,
    process_request_text,
    draw_card_direct, # Renamed/refactored function
    process_initial_response,
    ask_exploration_choice, # Function to ask the choice
    process_exploration_choice_callback,
    ask_grok_question, # Function to ask Grok question
    process_first_grok_response,
    process_second_grok_response,
    process_third_grok_response,
    finish_interaction_flow, # Function to start final resource check
    process_final_resource_callback,
    process_recharge_method,
    show_final_feedback_and_menu, # Function to show final feedback buttons
    process_card_feedback # Handler for the final feedback buttons (like/dislike)
)

import random
from datetime import datetime, timedelta
import os
import json
import logging

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger_root = logging.getLogger() # Root logger
logger = logging.getLogger(__name__) # Module logger

# --- Initialization ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage() # Consider RedisStorage or other persistent storage for production
dp = Dispatcher(storage=storage)

# Ensure data directory exists (important for SQLite path)
os.makedirs(DATA_DIR, exist_ok=True)
db_path = os.path.join(DATA_DIR, "bot.db") # Use DATA_DIR from config

logger.info(f"Initializing database at: {db_path}")
print(f"Initializing database at: {db_path}") # Keep print for Amvera logs visibility
try:
    db = Database(path=db_path)
    logger.info(f"Database connection established: {db.conn}")
    # Assign bot instance to db if needed (check db.py implementation)
    db.bot = bot # Assuming db.py uses this for get_chat etc.
except Exception as e:
    logger.exception(f"CRITICAL: Database initialization failed at {db_path}: {e}")
    print(f"CRITICAL: Database initialization failed at {db_path}: {e}")
    raise SystemExit(f"Database failed to initialize: {e}")

logging_service = LoggingService(db) # Use specific logger name
notifier = NotificationService(bot, db)
user_manager = UserManager(db)

# --- Middleware for Subscription Check ---
class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        # Check only for Messages and CallbackQueries originating from users
        if isinstance(event, (types.Message, types.CallbackQuery)):
            user = event.from_user
            if not user or user.is_bot: # Ignore bots
                return await handler(event, data)

            user_id = user.id
            # Allow admin and specific users to bypass check
            if user_id == ADMIN_ID: # Add other bypass IDs if needed
                return await handler(event, data)

            try:
                # Use get_chat_member for checking subscription
                user_status = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
                # Check if the user is a member, administrator, or creator
                if user_status.status not in ["member", "administrator", "creator"]:
                    user_db_data = db.get_user(user_id) # Get user data for name
                    name = user_db_data.get("name") if user_db_data else None # Safely get name
                    text = f"{name}, привет! Чтобы начать, подпишись на <a href='https://t.me/TopPsyGame'>канал автора</a>! ✨" if name else "Привет! Чтобы начать, подпишись на <a href='https://t.me/TopPsyGame'>канал автора</a>! ✨"

                    # Send message based on event type
                    if isinstance(event, types.Message):
                        await event.answer(text, disable_web_page_preview=True)
                    elif isinstance(event, types.CallbackQuery):
                        # Answer callback to prevent "loading" state, then send message
                        await event.answer("Пожалуйста, подпишись на канал.", show_alert=True)
                        await event.message.answer(text, disable_web_page_preview=True)
                    return # Stop processing further handlers
            except Exception as e:
                # Handle potential errors like "user not found" in channel etc.
                logger.error(f"Subscription check failed for user {user_id}: {e}")
                error_text = "Ой, не могу проверить подписку. Попробуй позже или проверь, что ты подписан(а) на канал @TopPsyGame."
                if isinstance(event, types.Message):
                     await event.answer(error_text)
                elif isinstance(event, types.CallbackQuery):
                     await event.answer("Ошибка проверки подписки.", show_alert=True)
                     await event.message.answer(error_text)
                return # Stop processing further handlers

        # If check passed or not applicable, proceed to the handler
        return await handler(event, data)

# Apply middleware to both messages and callback queries
dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())


# --- Survey Handlers (kept from original main.py, ensure SurveyState is defined if used) ---
# NOTE: SurveyState is NOT defined in the provided user_management.py.
# Add this class definition if surveys are still needed.
# class SurveyState(StatesGroup):
#     question_1 = State()
#     # ... other survey states
async def send_survey(message: types.Message, state: FSMContext, db, logger_service):
    # Implementation from original main.py...
    pass # Placeholder
async def process_survey_response(callback: types.CallbackQuery, state: FSMContext, db, logger_service):
    # Implementation from original main.py...
    pass # Placeholder
async def handle_survey(message: types.Message, state: FSMContext):
    logger.info(f"Handle_survey called for message: {message.text} from user {message.from_user.id}")
    # Assuming send_survey exists and SurveyState is defined
    # await send_survey(message, state, db, logging_service)
    await message.answer("Опрос временно недоступен.") # Placeholder if SurveyState missing

def make_process_survey_response_handler(db, logger_service):
    async def wrapped_handler(callback: types.CallbackQuery, state: FSMContext):
        # await process_survey_response(callback, state, db, logger_service)
        pass # Placeholder
    return wrapped_handler

# --- Factory Functions for Standard Command Handlers (Mostly unchanged) ---

def make_start_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        await state.clear() # Clear state on /start
        user_id = message.from_user.id
        username = message.from_user.username or ""
        # args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "" # Old way
        # Use CommandObject for cleaner argument parsing
        command: CommandObject | None = data.get("command")
        args = command.args if command else ""

        # Log start action
        await logger_service.log_action(user_id, "start_command", {"args": args})

        # Get/Update user data
        user_data = db.get_user(user_id) # Creates default if not exists
        if user_data.get("username") != username:
            db.update_user(user_id, {"username": username})

        # Referral logic
        if args and args.startswith("ref_"):
            try:
                referrer_id = int(args[4:])
                if referrer_id != user_id and not db.get_referrals(referrer_id): # Simplified check
                    db.add_referral(referrer_id, user_id)
                    referrer_data = db.get_user(referrer_id)
                    if referrer_data and not referrer_data.get("bonus_available"):
                        await user_manager.set_bonus_available(referrer_id, True)
                        ref_name = referrer_data.get("name", "Друг")
                        text = f"{ref_name}, ура! Кто-то открыл карту по твоей ссылке! Возьми '💌 Подсказку Вселенной'."
                        try:
                            await bot.send_message(referrer_id, text, reply_markup=await get_main_menu(referrer_id, db))
                            await logger_service.log_action(referrer_id, "referral_bonus_granted", {"referred_user": user_id})
                        except Exception as send_err:
                            logger.error(f"Failed to send referral bonus message to {referrer_id}: {send_err}")
            except (ValueError, TypeError) as ref_err:
                 logger.warning(f"Invalid referral code '{args}' from user {user_id}: {ref_err}")

        # Greeting logic
        user_name = user_data.get("name")
        if not user_name:
            await message.answer("Привет! Давай знакомиться! Как тебя зовут?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]
            ]))
            await state.set_state(UserState.waiting_for_name)
        else:
            await message.answer(f"{user_name}, рад(а) тебя видеть! Нажми '✨ Карта дня', когда будешь готова.", reply_markup=await get_main_menu(user_id, db))

    return wrapped_handler

def make_share_handler(db, logger_service):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        name = db.get_user(user_id).get("name", "Друг") # Use default name
        ref_link = f"{BOT_LINK}?start=ref_{user_id}"
        text = f"{name}, поделись этой ссылкой с друзьями: {ref_link}\nЕсли кто-то перейдет по ней и воспользуется ботом, ты получишь доступ к '💌 Подсказке Вселенной'!"
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await logger_service.log_action(user_id, "share_command")
    return wrapped_handler

def make_remind_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        user_data = db.get_user(user_id)
        name = user_data.get("name", "Друг")
        current_reminder = user_data.get("reminder_time")

        current_reminder_text = f"Текущее время напоминания: <b>{current_reminder}</b> МСК." if current_reminder else "Напоминания сейчас отключены."
        purpose_text = "⏰ Ежедневное напоминание поможет тебе не забывать уделять время себе и сделать работу с картами регулярной практикой самопознания."
        instruction_text = "Введи удобное время (например, <b>09:00</b> или <b>21:30</b>), чтобы получать напоминание по Москве.\nИли используй команду /remind_off, чтобы отключить их совсем."
        text = f"{name}, привет!\n\n{purpose_text}\n\n{current_reminder_text}\n{instruction_text}"

        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await state.set_state(UserState.waiting_for_reminder_time)
        await logger_service.log_action(user_id, "remind_command")
    return wrapped_handler

def make_users_handler(db, logger_service):
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
            await message.answer("Нет пользователей для отображения (кроме исключённых).")
            return

        user_list = []
        for uid in filtered_users:
            user_data = db.get_user(uid)
            name = user_data.get("name", "Без имени")
            username = user_data.get("username", "Нет никнейма")
            last_action_time = "Нет действий"
            last_action_timestamp_iso = "1970-01-01T00:00:00+00:00" # Default for sorting

            user_actions = db.get_actions(uid) # Get sorted actions
            if user_actions:
                last_action = user_actions[-1] # Last action because they are sorted ASC
                last_action_timestamp_iso = last_action["timestamp"]
                try:
                    # Format timestamp nicely
                    last_action_dt = datetime.fromisoformat(last_action_timestamp_iso).astimezone(TIMEZONE)
                    last_action_time = last_action_dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    last_action_time = last_action_timestamp_iso # Show raw if format error

            user_list.append({
                "uid": uid,
                "username": username,
                "name": name,
                "last_action_time": last_action_time,
                "last_action_timestamp_iso": last_action_timestamp_iso
            })

        # Sort by last action time (descending)
        user_list.sort(key=lambda x: x["last_action_timestamp_iso"], reverse=True)

        formatted_list = [
            f"ID: <code>{user['uid']}</code> | @{user['username']} | {user['name']} | Посл. действие: {user['last_action_time']}"
            for user in user_list
        ]

        header = f"👥 <b>Список пользователей ({len(formatted_list)}):</b>\n(Отсортировано по последней активности)\n\n"
        full_text = header + "\n".join(formatted_list)

        # Splitting message if too long
        max_len = 4000 # Slightly less than 4096 limit
        if len(full_text) > max_len:
            current_chunk = header
            for line in formatted_list:
                if len(current_chunk) + len(line) + 1 > max_len:
                    await message.answer(current_chunk)
                    current_chunk = header # Start new chunk with header? Maybe not needed.
                    current_chunk = "" # Start new chunk empty
                current_chunk += line + "\n"
            if current_chunk: # Send the last part
                await message.answer(current_chunk)
        else:
            await message.answer(full_text)
        await logger_service.log_action(user_id, "users_command")
    return wrapped_handler

def make_user_profile_handler(db, logger_service):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        await state.clear() # Clear any state
        user_id = message.from_user.id
        await logger_service.log_action(user_id, "user_profile_viewed")
        profile = await build_user_profile(user_id, db) # build_user_profile now handles non-existent profiles

        # Use get for safe access with defaults
        mood = profile.get("mood", "неизвестно")
        mood_trend_list = profile.get("mood_trend", [])
        mood_trend = " → ".join(mood_trend_list) if mood_trend_list else "нет данных"
        themes_list = profile.get("themes", [])
        themes = ", ".join(themes_list) if themes_list else "нет данных"
        response_count = profile.get("response_count", 0)
        request_count = profile.get("request_count", 0)
        avg_response_length = round(profile.get("avg_response_length", 0), 1)
        days_active = profile.get("days_active", 0)
        interactions_per_day = round(profile.get("interactions_per_day", 0), 1)
        last_updated_dt = profile.get("last_updated")
        last_updated = last_updated_dt.strftime("%Y-%m-%d %H:%M") if isinstance(last_updated_dt, datetime) else "не обновлялся"
        # New fields
        initial_resource = profile.get("initial_resource", "нет данных")
        final_resource = profile.get("final_resource", "нет данных")
        recharge_method = profile.get("recharge_method", "нет данных")


        text = (
            f"📊 <b>Твой профиль взаимодействия:</b>\n\n"
            f"👤 <b>Состояние & Темы:</b>\n"
            f"  - Настроение (последнее): {mood}\n"
            f"  - Тренд настроения: {mood_trend}\n"
            f"  - Ключевые темы: {themes}\n\n"
            f"🌿 <b>Ресурс (последняя сессия):</b>\n"
            f"  - В начале: {initial_resource}\n"
            f"  - В конце: {final_resource}\n"
            f"  - Способ восстановления: {recharge_method}\n\n"
            f"📈 <b>Статистика:</b>\n"
            f"  - Ответов на вопросы: {response_count}\n"
            f"  - Запросов к картам (с текстом): {request_count}\n"
            f"  - Ср. длина ответа: {avg_response_length} симв.\n"
            f"  - Дней активности: {days_active}\n"
            f"  - Взаимодействий в день: {interactions_per_day}\n\n"
            f"⏱ <b>Профиль обновлен:</b> {last_updated} МСК\n\n"
            f"<i>Этот профиль помогает мне лучше понимать тебя и адаптировать вопросы во время работы с картами.</i>"
        )

        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
    return wrapped_handler

def make_admin_user_profile_handler(db, logger_service):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if user_id != ADMIN_ID:
            await message.answer("Эта команда доступна только администратору.")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.answer("Укажите ID пользователя: `/admin_user_profile <user_id>`", parse_mode="MarkdownV2")
            return

        try:
            target_user_id = int(args[1])
        except ValueError:
            await message.answer("ID пользователя должен быть числом.")
            return

        profile = await build_user_profile(target_user_id, db) # Use the same function

        # Get user info for header
        user_info = db.get_user(target_user_id)
        name = user_info.get("name", "N/A")
        username = user_info.get("username", "N/A")

        mood = profile.get("mood", "N/A")
        mood_trend = " → ".join(profile.get("mood_trend", [])) or "N/A"
        themes = ", ".join(profile.get("themes", [])) or "N/A"
        response_count = profile.get("response_count", "N/A")
        request_count = profile.get("request_count", "N/A")
        avg_response_length = round(profile.get("avg_response_length", 0), 2)
        days_active = profile.get("days_active", "N/A")
        interactions_per_day = round(profile.get("interactions_per_day", 0), 2)
        last_updated_dt = profile.get("last_updated")
        last_updated = last_updated_dt.strftime("%Y-%m-%d %H:%M") if isinstance(last_updated_dt, datetime) else "N/A"
        initial_resource = profile.get("initial_resource", "N/A")
        final_resource = profile.get("final_resource", "N/A")
        recharge_method = profile.get("recharge_method", "N/A")

        text = (
            f"👤 <b>Профиль пользователя:</b> <code>{target_user_id}</code>\n"
            f"   Имя: {name}, Ник: @{username}\n\n"
            f"<b>Состояние & Темы:</b>\n"
            f"  Настроение: {mood}\n"
            f"  Тренд: {mood_trend}\n"
            f"  Темы: {themes}\n\n"
            f"<b>Ресурс (последний):</b>\n"
            f"  Начало: {initial_resource}\n"
            f"  Конец: {final_resource}\n"
            f"  Восстановление: {recharge_method}\n\n"
            f"<b>Статистика:</b>\n"
            f"  Ответов: {response_count}, Запросов: {request_count}\n"
            f"  Ср. длина отв.: {avg_response_length}\n"
            f"  Дней актив.: {days_active}, Взаим./день: {interactions_per_day}\n\n"
            f"<b>Обновлено:</b> {last_updated} МСК"
        )
        await message.answer(text)
        await logger_service.log_action(user_id, "admin_user_profile_viewed", {"target_user_id": target_user_id})
    return wrapped_handler

def make_feedback_handler(db, logger_service):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = db.get_user(user_id).get("name", "Друг")
        text = (
            f"{name}, хочешь поделиться идеей, как сделать меня лучше, или рассказать о проблеме?\n"
            "Я внимательно читаю все сообщения! Напиши здесь все, что думаешь."
        )
        await message.answer(
            text,
            reply_markup=await get_main_menu(user_id, db),
            protect_content=True # Keep protect_content if desired
        )
        await state.set_state(UserState.waiting_for_feedback)
        await logger_service.log_action(user_id, "feedback_initiated")
    return wrapped_handler

def make_process_feedback_handler(db, logger_service):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        feedback_text = message.text.strip()
        if not feedback_text:
            await message.answer("Кажется, ты ничего не написал(а). Попробуй еще раз.", reply_markup=await get_main_menu(user_id, db))
            return # Remain in feedback state

        user_data = db.get_user(user_id)
        name = user_data.get("name", "Аноним")
        username = user_data.get("username", "N/A")
        timestamp_iso = datetime.now(TIMEZONE).isoformat()

        # Save feedback to DB (assuming feedback table exists)
        try:
            with db.conn:
                db.conn.execute(
                    "INSERT INTO feedback (user_id, name, feedback, timestamp) VALUES (?, ?, ?, ?)",
                    (user_id, name, feedback_text, timestamp_iso)
                )
            await logger_service.log_action(user_id, "feedback_submitted", {"feedback": feedback_text})
            await message.answer(
                f"{name}, спасибо за твой отзыв! Я обязательно его учту.",
                reply_markup=await get_main_menu(user_id, db),
                protect_content=True
            )
            # Notify admin (optional)
            try:
                admin_notify_text = f"📝 Новый фидбек от:\nID: {user_id}\nИмя: {name}\nНик: @{username}\n\nТекст:\n{feedback_text}"
                await bot.send_message(ADMIN_ID, admin_notify_text)
            except Exception as admin_err:
                logger.error(f"Failed to send feedback notification to admin: {admin_err}")

            await state.clear()
        except sqlite3.Error as db_err:
             logger.error(f"Failed to save feedback from user {user_id} to DB: {db_err}")
             await message.answer("Ой, не получилось сохранить твой отзыв. Попробуй позже.", reply_markup=await get_main_menu(user_id, db))
             # Don't clear state on DB error, maybe user wants to try again
    return wrapped_handler

def make_name_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = db.get_user(user_id).get("name")
        text = f"{name}, хочешь изменить имя?" if name else "Как тебя зовут?"
        text += " Введи новое имя или нажми 'Пропустить'."
        await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]
        ]))
        await state.set_state(UserState.waiting_for_name)
        await logger_service.log_action(user_id, "name_change_initiated")
    return wrapped_handler

def make_process_name_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = message.text.strip()

        # Basic validation
        if not name or len(name) > 50: # Add length limit
            await message.answer("Пожалуйста, введи корректное имя (до 50 символов).")
            return # Remain in waiting_for_name state
        # Prevent using reserved button texts as names
        if name in ["✨ Карта дня", "💌 Подсказка Вселенной"]:
            await message.answer("Это имя использовать нельзя :) Попробуй другое.")
            return

        await user_manager.set_name(user_id, name)
        await logger_service.log_action(user_id, "set_name", {"name": name})
        await message.answer(f"Приятно познакомиться, {name}! Нажми '✨ Карта дня', когда будешь готова.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()
    return wrapped_handler

def make_process_skip_name_handler(db, logger_service, user_manager):
    async def wrapped_handler(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        await user_manager.set_name(user_id, "") # Set name to empty string
        await logger_service.log_action(user_id, "skip_name")
        await callback.message.edit_reply_markup(reply_markup=None) # Remove button
        await callback.message.answer("Понимаю. Имя не главное. Тогда просто нажми '✨ Карта дня', когда будешь готова.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        await callback.answer()
    return wrapped_handler

def make_remind_off_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        # await state.clear() # Clear state just in case
        current_state = await state.get_state()
        if current_state == UserState.waiting_for_reminder_time:
            await state.clear() # Clear only if in reminder setting state

        try:
            await user_manager.set_reminder(user_id, None) # Set time to None
            await logger_service.log_action(user_id, "set_reminder_time_off")
            name = db.get_user(user_id).get("name", "Друг")
            text = f"{name}, я отключил напоминания для тебя."
            await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        except Exception as e:
            logger.error(f"Failed to disable reminders for user {user_id}: {e}")
            await message.answer("Ой, не получилось отключить напоминания. Попробуй еще раз позже.")
    return wrapped_handler

def make_process_reminder_time_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = db.get_user(user_id).get("name", "Друг")
        reminder_time_str = message.text.strip()
        try:
            # Validate format HH:MM
            reminder_dt = datetime.strptime(reminder_time_str, "%H:%M")
            reminder_time_normalized = reminder_dt.strftime("%H:%M")
            await user_manager.set_reminder(user_id, reminder_time_normalized)
            await logger_service.log_action(user_id, "set_reminder_time", {"reminder_time": reminder_time_normalized})
            text = f"{name}, отлично! Буду напоминать тебе в <b>{reminder_time_normalized}</b> по Москве."
            await message.answer(text, reply_markup=await get_main_menu(user_id, db))
            await state.clear()
        except ValueError:
            text = f"{name}, не совсем понял время. Пожалуйста, используй формат ЧЧ:ММ (например, <b>08:30</b> или <b>21:00</b>)."
            await message.answer(text) # No menu markup, keep user in state
            # Remain in UserState.waiting_for_reminder_time
    return wrapped_handler

def make_logs_handler(db, logger_service):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if user_id != ADMIN_ID:
            await message.answer("Эта команда доступна только администратору.")
            return

        args = message.text.split()
        target_date_str = None
        if len(args) > 1:
            target_date_str = args[1]
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                await message.answer("Укажите дату в формате ГГГГ-ММ-ДД, например: `/logs 2024-04-16`", parse_mode="MarkdownV2")
                return
        else:
            target_date = datetime.now(TIMEZONE).date()
            target_date_str = target_date.strftime("%Y-%m-%d")

        await logger_service.log_action(user_id, "logs_command", {"date": target_date_str})
        logs = db.get_actions() # Get all logs (sorted by timestamp ASC)
        filtered_logs = []
        excluded_users = set(NO_LOGS_USERS)
        for log in logs:
            try:
                # Compare dates correctly
                log_timestamp_dt = datetime.fromisoformat(log["timestamp"]).astimezone(TIMEZONE)
                if log_timestamp_dt.date() == target_date and log.get("user_id") not in excluded_users:
                    filtered_logs.append(log)
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse timestamp in log for admin view: {log.get('timestamp')}, error: {e}")
                continue

        if not filtered_logs:
            await message.answer(f"Логов за {target_date_str} нет (кроме исключенных пользователей).")
            return

        # Formatting logs
        log_lines = []
        for log in filtered_logs:
            ts = datetime.fromisoformat(log['timestamp']).astimezone(TIMEZONE).strftime('%H:%M:%S')
            uid = log['user_id']
            action = log['action']
            # Format details nicely
            details_str = ""
            if isinstance(log['details'], dict) and log['details']:
                 details_str = ", ".join([f"{k}={v}" for k,v in log['details'].items()])
                 # Limit details length
                 details_str = f" ({details_str[:100]}{'...' if len(details_str)>100 else ''})"
            log_lines.append(f"{ts} U:{uid} A:{action}{details_str}")

        header = f"📜 <b>Логи за {target_date_str} ({len(log_lines)} записей):</b>\n\n"
        full_text = header + "\n".join(log_lines)

        # Splitting message
        max_len = 4000
        if len(full_text) > max_len:
            current_chunk = header
            for line in log_lines:
                if len(current_chunk) + len(line) + 1 > max_len:
                    await message.answer(current_chunk)
                    current_chunk = "" # Start new chunk empty
                current_chunk += line + "\n"
            if current_chunk:
                await message.answer(current_chunk)
        else:
            await message.answer(full_text)
    return wrapped_handler

def make_bonus_request_handler(db, logger_service):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        user_data = db.get_user(user_id)
        name = user_data.get("name", "Друг")
        if not user_data.get("bonus_available"):
            text = f"{name}, этот совет пока спрятан! Используй /share, чтобы получить к нему доступ, когда кто-то воспользуется твоей ссылкой."
            await message.answer(text, reply_markup=await get_main_menu(user_id, db))
            return

        advice = random.choice(UNIVERSE_ADVICE)
        text = f"{name}, вот послание Вселенной специально для тебя:\n\n{advice}"
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await logger_service.log_action(user_id, "bonus_request_used", {"advice": advice})
        # Bonus is usually single-use, disable it after use
        await user_manager.set_bonus_available(user_id, False)
        await logger_service.log_action(user_id, "bonus_disabled_after_use")
    return wrapped_handler

# --- Error Handlers for Incorrect Input Types ---
async def handle_text_when_waiting_callback(message: types.Message, state: FSMContext):
    """Handles text messages received when a callback query (button press) is expected."""
    user_id = message.from_user.id
    current_state = await state.get_state()
    logger.warning(f"User {user_id} sent text '{message.text}' while in state {current_state}, expected callback.")
    await message.answer("Пожалуйста, нажми на одну из кнопок выше 👆")

async def handle_callback_when_waiting_text(callback: types.CallbackQuery, state: FSMContext):
    """Handles callback queries received when a text message is expected."""
    user_id = callback.from_user.id
    current_state = await state.get_state()
    logger.warning(f"User {user_id} sent callback '{callback.data}' while in state {current_state}, expected text.")
    await callback.answer("Пожалуйста, отправь ответ текстовым сообщением.", show_alert=True)

# --- Handler Registration ---
def register_handlers(dp: Dispatcher, db: Database, logger_service: LoggingService, user_manager: UserManager):
    logger.info("Registering handlers...")

    # --- Standard Commands ---
    dp.message.register(make_start_handler(db, logger_service, user_manager), Command("start"), StateFilter("*")) # Allow /start from any state
    dp.message.register(make_share_handler(db, logger_service), Command("share"), StateFilter("*"))
    dp.message.register(make_remind_handler(db, logger_service, user_manager), Command("remind"), StateFilter("*"))
    dp.message.register(make_remind_off_handler(db, logger_service, user_manager), Command("remind_off"), StateFilter("*"))
    dp.message.register(make_name_handler(db, logger_service, user_manager), Command("name"), StateFilter("*"))
    dp.message.register(make_feedback_handler(db, logger_service), Command("feedback"), StateFilter("*"))
    dp.message.register(make_user_profile_handler(db, logger_service), Command("user_profile"), StateFilter("*"))

    # --- Admin Commands ---
    dp.message.register(make_users_handler(db, logger_service), Command("users"))
    dp.message.register(make_logs_handler(db, logger_service), Command("logs"))
    dp.message.register(make_admin_user_profile_handler(db, logger_service), Command("admin_user_profile"))

    # --- Text Button Handlers ---
    # Note: Use F.text filter in aiogram 3.x+ for better practice
    dp.message.register(make_bonus_request_handler(db, logger_service), lambda m: m.text == "💌 Подсказка Вселенной", StateFilter("*"))

    # --- State Handlers ---
    # Name setting
    dp.message.register(make_process_name_handler(db, logger_service, user_manager), UserState.waiting_for_name)
    dp.callback_query.register(make_process_skip_name_handler(db, logger_service, user_manager), lambda c: c.data == "skip_name", UserState.waiting_for_name)
    dp.message.register(handle_text_when_waiting_callback, StateFilter(UserState.waiting_for_name)) # Error handler if user types instead of skipping via button

    # Reminder setting
    dp.message.register(make_process_reminder_time_handler(db, logger_service, user_manager), UserState.waiting_for_reminder_time)
    dp.callback_query.register(handle_callback_when_waiting_text, StateFilter(UserState.waiting_for_reminder_time)) # Error handler

    # Feedback submission
    dp.message.register(make_process_feedback_handler(db, logger_service), UserState.waiting_for_feedback)
    dp.callback_query.register(handle_callback_when_waiting_text, StateFilter(UserState.waiting_for_feedback)) # Error handler

    # --- Card of the Day Flow Handlers ---
    # Entry point ("Карта дня" button) -> triggers initial resource check
    dp.message.register(handle_card_request, lambda m: m.text == "✨ Карта дня", StateFilter("*")) # Start flow from any state

    # Step 1: Initial Resource Check
    dp.callback_query.register(process_initial_resource_callback, UserState.waiting_for_initial_resource, lambda c: c.data.startswith("resource_"))
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_initial_resource) # Error handler

    # Step 2: Request Type Choice
    dp.callback_query.register(process_request_type_callback, UserState.waiting_for_request_type_choice, lambda c: c.data.startswith("request_type_"))
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_request_type_choice) # Error handler

    # Step 3a: Waiting for Request Text (if chosen)
    dp.message.register(process_request_text, UserState.waiting_for_request_text_input)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_request_text_input) # Error handler

    # Step 4: Waiting for Initial Association (after card shown)
    dp.message.register(process_initial_response, UserState.waiting_for_initial_response)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_initial_response) # Error handler

    # Step 5: Exploration Choice
    dp.callback_query.register(process_exploration_choice_callback, UserState.waiting_for_exploration_choice, lambda c: c.data.startswith("explore_"))
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_exploration_choice) # Error handler

    # Step 6: Grok Responses
    dp.message.register(process_first_grok_response, UserState.waiting_for_first_grok_response)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_first_grok_response) # Error handler

    dp.message.register(process_second_grok_response, UserState.waiting_for_second_grok_response)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_second_grok_response) # Error handler

    dp.message.register(process_third_grok_response, UserState.waiting_for_third_grok_response)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_third_grok_response) # Error handler

    # Step 7: Final Resource Check
    dp.callback_query.register(process_final_resource_callback, UserState.waiting_for_final_resource, lambda c: c.data.startswith("resource_"))
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_final_resource) # Error handler

    # Step 8: Recharge Method Input (if resource low)
    dp.message.register(process_recharge_method, UserState.waiting_for_recharge_method)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_recharge_method) # Error handler

    # Final Feedback Callback (like/dislike buttons shown at the very end)
    # This can be triggered even after state is cleared, so no StateFilter needed? Or use "*"
    dp.callback_query.register(process_card_feedback, lambda c: c.data.startswith("feedback_v2_"), StateFilter("*")) # Allow from any state

    # --- Survey Handlers Registration (Optional, if needed) ---
    # dp.message.register(handle_survey, Command("survey"))
    # dp.callback_query.register(make_process_survey_response_handler(db, logging_service), lambda c: c.data.startswith("survey_"), StateFilter(SurveyState)) # Requires SurveyState definition

    # --- Default Handler for Unknown Messages ---
    # Make sure this is registered LAST
    @dp.message(StateFilter("*")) # Catches any message in any state not handled above
    async def handle_unknown_message_state(message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        logger.warning(f"Unknown message '{message.text}' received from user {message.from_user.id} in state {current_state}")
        # Provide more context-specific help if possible
        if current_state:
            await message.answer("Кажется, я ожидал(а) другого ответа на этом шаге. Попробуй использовать кнопки или ответить на последний вопрос. Или нажми /start для перезапуска.")
        else:
            # Already handled by the handler below if state is None
             await handle_unknown_message(message)


    @dp.message() # Catches any message with no state and not handled above
    async def handle_unknown_message(message: types.Message):
        logger.warning(f"Unknown message '{message.text}' received from user {message.from_user.id} with no state.")
        await message.answer("Извини, не понял(а) твой запрос. Попробуй нажать '✨ Карта дня' или используй команды /start, /name, /remind, /share, /feedback, /user_profile.")

    @dp.callback_query() # Catches any callback not handled above
    async def handle_unknown_callback(callback: types.CallbackQuery, state: FSMContext):
         current_state = await state.get_state()
         logger.warning(f"Unknown callback '{callback.data}' received from user {callback.from_user.id} in state {current_state}")
         await callback.answer("Неизвестное действие.", show_alert=True)


    logger.info("Handlers registered successfully.")

# --- Main Execution ---
async def main():
    logger.info("Starting bot...")
    # Set bot commands displayed in Telegram
    commands = [
            types.BotCommand(command="start", description="🔄 Перезагрузка"),
            types.BotCommand(command="name", description="🧑 Указать имя"),
            types.BotCommand(command="remind", description="⏰ Напоминание"),
            types.BotCommand(command="share", description="🎁 Поделиться"),
            types.BotCommand(command="feedback", description="📩 Отзыв")
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands set successfully.")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

    # Register all handlers
    register_handlers(dp, db, logging_service, user_manager)

    # Start background tasks (like reminders)
    # Ensure notifier.check_reminders() is awaitable and handles errors internally
    reminder_task = asyncio.create_task(notifier.check_reminders())
    logger.info("Reminder check task started.")

    # Start polling
    logger.info("Starting polling...")
    try:
        # Run polling loop
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.critical(f"Polling failed: {e}", exc_info=True)
    finally:
        logger.info("Stopping bot...")
        # Cancel background tasks gracefully
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            logger.info("Reminder task cancelled.")
        # Close DB connection
        if db and db.conn:
            db.conn.close()
            logger.info("Database connection closed.")
        # Close bot session
        await bot.session.close()
        logger.info("Bot session closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}", exc_info=True)
