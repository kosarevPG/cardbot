# код/main.py

import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from functools import partial
import pytz # Убедимся, что pytz импортирован

# --- Импорты из проекта ---
from config import (
    TOKEN, CHANNEL_ID, ADMIN_ID, UNIVERSE_ADVICE, BOT_LINK,
    TIMEZONE, NO_LOGS_USERS, DATA_DIR
)
# База данных и Сервисы
from database.db import Database
from modules.logging_service import LoggingService
from modules.notification_service import NotificationService
from modules.user_management import UserState, UserManager
from modules.ai_service import build_user_profile

# Модуль Карты Дня
from modules.card_of_the_day import (
    get_main_menu,
    handle_card_request,
    process_initial_resource_callback,
    process_request_type_callback,
    process_request_text,
    process_initial_response,
    process_exploration_choice_callback,
    process_first_grok_response,
    process_second_grok_response,
    process_third_grok_response,
    process_final_resource_callback,
    process_recharge_method,
    process_card_feedback
    # Убрал импорты ask_* функций, т.к. они вызываются внутри других
)

# НОВЫЙ ИМПОРТ: Модуль Вечерней Рефлексии
from modules.evening_reflection import (
    reflection_router, # Импортируем роутер из модуля
    start_evening_reflection # Импортируем стартовый хендлер
)


# --- Стандартные импорты ---
import random
from datetime import datetime, timedelta
import os
import json
import logging
import sqlite3

# --- Настройка логирования ---
# Устанавливаем формат один раз здесь
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger_root = logging.getLogger()
logger = logging.getLogger(__name__)

# --- Инициализация ---
# ... (инициализация bot, storage как раньше) ...
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация БД
os.makedirs(DATA_DIR, exist_ok=True)
db_path = os.path.join(DATA_DIR, "bot.db")
logger.info(f"Initializing database at: {db_path}")
print(f"Initializing database at: {db_path}")
try:
    db = Database(path=db_path)
    db.conn.execute("SELECT 1")
    logger.info(f"Database connection established successfully: {db.conn}")
    db.bot = bot # Передаем бота в DB
except (sqlite3.Error, Exception) as e:
    logger.exception(f"CRITICAL: Database initialization failed at {db_path}: {e}")
    print(f"CRITICAL: Database initialization failed at {db_path}: {e}")
    raise SystemExit(f"Database failed to initialize: {e}")

# Инициализация сервисов
logging_service = LoggingService(db)
notifier = NotificationService(bot, db)
user_manager = UserManager(db)

# --- Middleware ---
# ... (код SubscriptionMiddleware без изменений) ...
class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, (types.Message, types.CallbackQuery)):
            user = event.from_user
            if not user or user.is_bot:
                 return await handler(event, data)
            user_id = user.id
            if user_id == ADMIN_ID:
                return await handler(event, data)
            try:
                user_status = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
                allowed_statuses = ["member", "administrator", "creator"]
                if user_status.status not in allowed_statuses:
                    user_db_data = db.get_user(user_id)
                    name = user_db_data.get("name") if user_db_data else None
                    link = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
                    text = f"{name}, рад видеть тебя. ✨ Для нашей совместной работы, пожалуйста, подпишись на <a href='{link}'>канал автора</a>. Это важно для поддержки пространства. После подписки просто нажми /start." if name else f"Рад видеть тебя. ✨ Для нашей совместной работы, пожалуйста, подпишись на <a href='{link}'>канал автора</a>. Это важно для поддержки пространства. После подписки просто нажми /start."
                    if isinstance(event, types.Message):
                        await event.answer(text, disable_web_page_preview=True)
                    elif isinstance(event, types.CallbackQuery):
                        await event.answer("Пожалуйста, подпишись на канал.", show_alert=True)
                        await event.message.answer(text, disable_web_page_preview=True)
                    return
            except Exception as e:
                logger.error(f"Subscription check failed for user {user_id}: {e}")
                error_text = f"Не получается проверить твою подписку на канал {CHANNEL_ID}. Убедись, пожалуйста, что ты подписана, и попробуй снова через /start."
                if isinstance(event, types.Message):
                     await event.answer(error_text)
                elif isinstance(event, types.CallbackQuery):
                     await event.answer("Не удается проверить подписку.", show_alert=False)
                     await event.message.answer(error_text)
                return
        return await handler(event, data)

dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())
logger.info("SubscriptionMiddleware registered.")


# --- Обработчики стандартных команд ---
# Используем partial для передачи зависимостей

def make_start_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext, command: CommandObject | None = None):
        # ... (код start без изменений, т.к. рефералы и имя не меняются) ...
        await state.clear()
        user_id = message.from_user.id
        username = message.from_user.username or ""
        args = command.args if command else ""

        await logger_service.log_action(user_id, "start_command", {"args": args})

        user_data = db.get_user(user_id)
        if user_data.get("username") != username:
             db.update_user(user_id, {"username": username})

        if args and args.startswith("ref_"):
            try:
                referrer_id = int(args[4:])
                if referrer_id != user_id:
                    if db.add_referral(referrer_id, user_id):
                         referrer_data = db.get_user(referrer_id)
                         if referrer_data and not referrer_data.get("bonus_available"):
                             await user_manager.set_bonus_available(referrer_id, True)
                             ref_name = referrer_data.get("name", "Друг")
                             text = f"{ref_name}, ура! 🎉 Кто-то воспользовался твоей ссылкой! Теперь тебе доступна '💌 Подсказка Вселенной' в меню."
                             try:
                                 await bot.send_message(referrer_id, text, reply_markup=await get_main_menu(referrer_id, db))
                                 await logger_service.log_action(referrer_id, "referral_bonus_granted", {"referred_user": user_id})
                             except Exception as send_err:
                                 logger.error(f"Failed to send referral bonus message to {referrer_id}: {send_err}")
            except (ValueError, TypeError, IndexError) as ref_err:
                 logger.warning(f"Invalid referral code processing '{args}' from user {user_id}: {ref_err}")

        user_name = user_data.get("name")
        if not user_name:
            await message.answer("Здравствуй! ✨ Очень рад нашему знакомству. Подскажи, как мне лучше к тебе обращаться?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                 [types.InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]
            ]))
            await state.set_state(UserState.waiting_for_name)
        else:
            await message.answer(f"{user_name}, снова рад тебя видеть! 👋 Готова поработать с картой дня или подвести итог?", reply_markup=await get_main_menu(user_id, db))

    return wrapped_handler

# --- Команда /remind (Обновленная логика) ---
def make_remind_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        user_data = db.get_user(user_id)
        name = user_data.get("name", "Друг")
        morning_reminder = user_data.get("reminder_time")
        evening_reminder = user_data.get("reminder_time_evening") # Получаем вечернее

        morning_text = f"Напоминание 'Карта дня': <b>{morning_reminder}</b> МСК." if morning_reminder else "Напоминание 'Карта дня': <b>отключено</b>."
        # Устанавливаем вечернее по умолчанию, если его нет для отображения
        evening_default = "21:30"
        evening_text = f"Напоминание 'Итог дня': <b>{evening_reminder}</b> МСК." if evening_reminder else f"Напоминание 'Итог дня': <b>{evening_default}</b> МСК (по умолчанию)."

        purpose_text = "⏰ Ежедневные напоминания помогут тебе не забывать уделять время себе."
        instruction_text = (
            "Введи удобное время для <b>утреннего</b> напоминания 'Карта дня' (например, <b>09:00</b> или <b>08:15</b>).\n"
            f"Вечернее напоминание 'Итог дня' будет установлено на <b>{evening_default}</b> МСК.\n\n" # Указываем дефолтное вечернее
            "Используй /remind_off, чтобы отключить <b>оба</b> напоминания."
        )
        text = f"{name}, привет!\n\n{purpose_text}\n\n{morning_text}\n{evening_text}\n\n{instruction_text}"

        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await state.set_state(UserState.waiting_for_reminder_time)
        await logger_service.log_action(user_id, "remind_command_invoked")
    return wrapped_handler

# --- Команда /remind_off (Обновленная логика) ---
def make_remind_off_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message, state: FSMContext):
         user_id = message.from_user.id
         current_state = await state.get_state()
         if current_state == UserState.waiting_for_reminder_time:
             await state.clear()

         try:
             # Используем новый метод для очистки обоих времен
             await user_manager.clear_reminders(user_id)
             await logger_service.log_action(user_id, "reminders_cleared")
             name = db.get_user(user_id).get("name", "Друг")
             text = f"{name}, я отключил <b>все</b> напоминания для тебя (утреннее и вечернее). Если захочешь включить снова, используй /remind."
             await message.answer(text, reply_markup=await get_main_menu(user_id, db))
         except Exception as e:
             logger.error(f"Failed to disable reminders for user {user_id}: {e}", exc_info=True)
             await message.answer("Ой, не получилось отключить напоминания. Попробуй еще раз позже.")
     return wrapped_handler

# --- Обработчик ввода времени для /remind (Обновленная логика) ---
def make_process_reminder_time_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = db.get_user(user_id).get("name", "Друг")
        reminder_time_str = message.text.strip()
        evening_default_time = "21:30" # Вечернее время по умолчанию

        try:
            # Валидация формата ЧЧ:ММ для утреннего времени
            reminder_dt = datetime.strptime(reminder_time_str, "%H:%M")
            morning_time_normalized = reminder_dt.strftime("%H:%M")

            # Устанавливаем оба времени: введенное утро + дефолт вечер
            await user_manager.set_reminder(user_id, morning_time_normalized, evening_default_time)
            await logger_service.log_action(user_id, "reminders_set", {
                "morning_time": morning_time_normalized,
                "evening_time": evening_default_time
            })
            text = (f"{name}, отлично! 👍\n"
                    f"Установил напоминание 'Карта дня' на <b>{morning_time_normalized}</b> МСК.\n"
                    f"И напоминание 'Итог дня' на <b>{evening_default_time}</b> МСК.")
            await message.answer(text, reply_markup=await get_main_menu(user_id, db))
            await state.clear()
        except ValueError:
            # Если формат неверный, просим ввести снова (только утро)
            text = f"{name}, не совсем понял время. 🕰️ Пожалуйста, введи время для <b>утреннего</b> напоминания в формате ЧЧ:ММ (например, <b>08:30</b> или <b>21:00</b>)."
            await message.answer(text) # Не добавляем меню, остаемся в состоянии ожидания
     return wrapped_handler


# --- Остальные команды (без изменений в логике, только передача зависимостей) ---
def make_share_handler(db, logger_service):
    # ... (код share без изменений) ...
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        name = db.get_user(user_id).get("name", "Друг")
        ref_link = f"{BOT_LINK}?start=ref_{user_id}"
        text = (f"{name}, хочешь поделиться этим ботом с друзьями?\n"
                f"Вот твоя персональная ссылка: {ref_link}\n\n"
                f"Когда кто-нибудь перейдет по ней и начнет использовать бота, ты получишь доступ к '💌 Подсказке Вселенной' в главном меню! ✨")
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await logger_service.log_action(user_id, "share_command")
    return wrapped_handler

def make_name_handler(db, logger_service, user_manager):
    # ... (код name без изменений) ...
     async def wrapped_handler(message: types.Message, state: FSMContext):
         user_id = message.from_user.id
         name = db.get_user(user_id).get("name")
         text = f"Твое текущее имя: <b>{name}</b>.\nХочешь изменить?" if name else "Как тебя зовут?"
         text += "\nВведи новое имя или нажми 'Пропустить', если не хочешь указывать."
         await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
             [types.InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]
         ]))
         await state.set_state(UserState.waiting_for_name)
         await logger_service.log_action(user_id, "name_change_initiated")
     return wrapped_handler


def make_feedback_handler(db, logger_service):
    # ... (код feedback без изменений) ...
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
             protect_content=True
         )
         await state.set_state(UserState.waiting_for_feedback)
         await logger_service.log_action(user_id, "feedback_initiated")
     return wrapped_handler


def make_user_profile_handler(db, logger_service):
    # ... (код user_profile без изменений, т.к. build_user_profile уже учитывает новые поля) ...
     async def wrapped_handler(message: types.Message, state: FSMContext):
        await state.clear() # Clear any state
        user_id = message.from_user.id
        await logger_service.log_action(user_id, "user_profile_viewed")
        profile = await build_user_profile(user_id, db) # build_user_profile уже содержит новые поля

        mood = profile.get("mood", "неизвестно")
        mood_trend_list = profile.get("mood_trend", [])
        mood_trend = " → ".join(mood_trend_list) if mood_trend_list else "нет данных"
        themes_list = profile.get("themes", [])
        themes = ", ".join(themes_list) if themes_list and themes_list != ["не определено"] else "нет данных"
        response_count = profile.get("response_count", 0)
        request_count = profile.get("request_count", 0)
        avg_response_length = round(profile.get("avg_response_length", 0), 1)
        days_active = profile.get("days_active", 0)
        interactions_per_day = round(profile.get("interactions_per_day", 0), 1)
        last_updated_dt = profile.get("last_updated")
        last_updated = last_updated_dt.astimezone(pytz.timezone("Europe/Moscow")).strftime("%Y-%m-%d %H:%M") if isinstance(last_updated_dt, datetime) else "не обновлялся" # Используем TIMEZONE из config
        initial_resource = profile.get("initial_resource") or "нет данных"
        final_resource = profile.get("final_resource") or "нет данных"
        recharge_method = profile.get("recharge_method") or "нет данных"

        text = (
             f"📊 <b>Твой профиль взаимодействия:</b>\n\n"
             f"👤 <b>Состояние & Темы:</b>\n"
             f"  - Настроение (последнее): {mood}\n"
             f"  - Тренд настроения: {mood_trend}\n"
             f"  - Ключевые темы: {themes}\n\n"
             f"🌿 <b>Ресурс (последняя сессия 'Карта дня'):</b>\n"
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
             f"<i>Этот профиль помогает мне лучше понимать тебя и адаптировать вопросы. Данные из 'Итога дня' пока здесь не отображаются.</i>"
         )
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
     return wrapped_handler

# --- Админские команды (без изменений) ---
def make_admin_user_profile_handler(db, logger_service):
    # ... (код admin_user_profile без изменений) ...
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
         user_info = db.get_user(target_user_id)
         if not user_info:
             await message.answer(f"Пользователь с ID {target_user_id} не найден в базе.")
             return
         profile = await build_user_profile(target_user_id, db)
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
         last_updated = last_updated_dt.astimezone(pytz.timezone("Europe/Moscow")).strftime("%Y-%m-%d %H:%M") if isinstance(last_updated_dt, datetime) else "N/A"
         initial_resource = profile.get("initial_resource") or "N/A"
         final_resource = profile.get("final_resource") or "N/A"
         recharge_method = profile.get("recharge_method") or "N/A"
         text = (
             f"👤 <b>Профиль пользователя:</b> <code>{target_user_id}</code>\n"
             f"   Имя: {name}, Ник: @{username}\n\n"
             f"<b>Состояние & Темы:</b>\n"
             f"  Настроение: {mood}\n"
             f"  Тренд: {mood_trend}\n"
             f"  Темы: {themes}\n\n"
             f"<b>Ресурс (последний 'Карта дня'):</b>\n"
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

def make_users_handler(db, logger_service):
    # ... (код users без изменений) ...
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
             last_action_timestamp_iso = "1970-01-01T00:00:00+00:00"
             user_actions = db.get_actions(uid)
             if user_actions:
                 last_action = user_actions[-1]
                 last_action_timestamp_iso = last_action["timestamp"]
                 try:
                     last_action_dt = datetime.fromisoformat(last_action_timestamp_iso.replace('Z', '+00:00')).astimezone(pytz.timezone("Europe/Moscow")) # Use TIMEZONE
                     last_action_time = last_action_dt.strftime("%Y-%m-%d %H:%M")
                 except ValueError:
                     last_action_time = last_action_timestamp_iso
             user_list.append({
                 "uid": uid, "username": username, "name": name,
                 "last_action_time": last_action_time,
                 "last_action_timestamp_iso": last_action_timestamp_iso
             })
         user_list.sort(key=lambda x: x["last_action_timestamp_iso"], reverse=True)
         formatted_list = [
             f"ID: <code>{user['uid']}</code> | @{user['username']} | {user['name']} | Посл. действие: {user['last_action_time']}"
             for user in user_list
         ]
         header = f"👥 <b>Список пользователей ({len(formatted_list)}):</b>\n(Отсортировано по последней активности)\n\n"
         full_text = header + "\n".join(formatted_list)
         max_len = 4000
         if len(full_text) > max_len:
             current_chunk = header
             for line in formatted_list:
                 if len(current_chunk) + len(line) + 1 > max_len:
                     await message.answer(current_chunk)
                     current_chunk = ""
                 current_chunk += line + "\n"
             if current_chunk:
                 await message.answer(current_chunk)
         else:
             await message.answer(full_text)
         await logger_service.log_action(user_id, "users_command")
     return wrapped_handler


def make_logs_handler(db, logger_service):
    # ... (код logs без изменений) ...
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
             target_date = datetime.now(pytz.timezone("Europe/Moscow")).date() # Use TIMEZONE
             target_date_str = target_date.strftime("%Y-%m-%d")
         await logger_service.log_action(user_id, "logs_command", {"date": target_date_str})
         logs = db.get_actions()
         filtered_logs = []
         excluded_users = set(NO_LOGS_USERS)
         for log in logs:
             try:
                 log_timestamp_dt = datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00')).astimezone(pytz.timezone("Europe/Moscow")) # Use TIMEZONE
                 if log_timestamp_dt.date() == target_date and log.get("user_id") not in excluded_users:
                     filtered_logs.append(log)
             except (ValueError, TypeError, KeyError) as e:
                 logger.warning(f"Could not parse timestamp or missing data in log for admin view: {log}, error: {e}")
                 continue
         if not filtered_logs:
             await message.answer(f"Логов за {target_date_str} нет (кроме исключенных пользователей).")
             return
         log_lines = []
         for log in filtered_logs:
             ts_str = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')).astimezone(pytz.timezone("Europe/Moscow")).strftime('%H:%M:%S') # Use TIMEZONE
             uid = log.get('user_id', 'N/A')
             action = log.get('action', 'N/A')
             details = log.get('details', {})
             details_str = ""
             # Проверяем, что details это словарь перед итерацией
             if isinstance(details, dict) and details:
                 details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
                 details_str = f" ({details_str[:100]}{'...' if len(details_str) > 100 else ''})"
             # Если details не словарь (например, строка после ошибки JSON), просто выводим его
             elif isinstance(details, str):
                 details_str = f" (Details: {details[:100]}{'...' if len(details) > 100 else ''})"

             log_lines.append(f"{ts_str} U:{uid} A:{action}{details_str}")

         header = f"📜 <b>Логи за {target_date_str} ({len(log_lines)} записей):</b>\n\n"
         full_text = header + "\n".join(log_lines)
         max_len = 4000
         if len(full_text) > max_len:
             current_chunk = header
             for line in log_lines:
                 if len(current_chunk) + len(line) + 1 > max_len:
                     await message.answer(current_chunk)
                     current_chunk = ""
                 current_chunk += line + "\n"
             if current_chunk:
                 await message.answer(current_chunk)
         else:
             await message.answer(full_text)
     return wrapped_handler

# --- Обработчики ввода имени (без изменений) ---
def make_process_name_handler(db, logger_service, user_manager):
    # ... (код process_name без изменений) ...
     async def wrapped_handler(message: types.Message, state: FSMContext):
         user_id = message.from_user.id
         name = message.text.strip()
         if not name:
             await message.answer("Имя не может быть пустым. Попробуй еще раз или нажми 'Пропустить' выше.")
             return
         if len(name) > 50:
             await message.answer("Слишком длинное имя. Пожалуйста, используй не более 50 символов.")
             return
         reserved_names = ["✨ Карта дня", "💌 Подсказка Вселенной", "🌙 Итог дня"] # Добавил новую кнопку
         if name in reserved_names:
             await message.answer(f"Имя '{name}' использовать нельзя :) Пожалуйста, выбери другое.")
             return
         await user_manager.set_name(user_id, name)
         await logger_service.log_action(user_id, "set_name", {"name": name})
         await message.answer(f"Приятно познакомиться, {name}! 😊\nТеперь можешь выбрать действие в меню.", reply_markup=await get_main_menu(user_id, db)) # Обновил текст
         await state.clear()
     return wrapped_handler

def make_process_skip_name_handler(db, logger_service, user_manager):
    # ... (код skip_name без изменений) ...
     async def wrapped_handler(callback: types.CallbackQuery, state: FSMContext):
         user_id = callback.from_user.id
         await user_manager.set_name(user_id, "")
         await logger_service.log_action(user_id, "skip_name")
         try:
             await callback.message.edit_reply_markup(reply_markup=None)
         except Exception as e:
             logger.warning(f"Could not edit message on skip_name for user {user_id}: {e}")
         await callback.message.answer("Хорошо, буду обращаться к тебе без имени.\nВыбери действие в меню.", reply_markup=await get_main_menu(user_id, db)) # Обновил текст
         await state.clear()
         await callback.answer()
     return wrapped_handler


# --- Обработчики ввода фидбека (без изменений) ---
def make_process_feedback_handler(db, logger_service):
    # ... (код process_feedback без изменений) ...
      async def wrapped_handler(message: types.Message, state: FSMContext):
          user_id = message.from_user.id
          feedback_text = message.text.strip()
          if not feedback_text:
              await message.answer("Кажется, ты ничего не написала. Попробуй еще раз.", reply_markup=await get_main_menu(user_id, db))
              return

          user_data = db.get_user(user_id)
          name = user_data.get("name", "Аноним")
          username = user_data.get("username", "N/A")
          timestamp_iso = datetime.now(pytz.timezone("Europe/Moscow")).isoformat() # Use TIMEZONE

          try:
              with db.conn:
                  db.conn.execute(
                      "INSERT INTO feedback (user_id, name, feedback, timestamp) VALUES (?, ?, ?, ?)",
                      (user_id, name, feedback_text, timestamp_iso)
                  )
              await logger_service.log_action(user_id, "feedback_submitted", {"feedback_length": len(feedback_text)})
              await message.answer(
                  f"{name}, спасибо за твой отзыв! Я обязательно его учту. 🙏",
                  reply_markup=await get_main_menu(user_id, db),
                  protect_content=True
              )
              try:
                  admin_notify_text = (f"📝 Новый фидбек от:\n"
                                       f"ID: <code>{user_id}</code>\n"
                                       f"Имя: {name}\n"
                                       f"Ник: @{username}\n\n"
                                       f"<b>Текст:</b>\n{feedback_text}")
                  await bot.send_message(ADMIN_ID, admin_notify_text[:4090])
              except Exception as admin_err:
                  logger.error(f"Failed to send feedback notification to admin: {admin_err}")
              await state.clear()
          except sqlite3.Error as db_err:
               logger.error(f"Failed to save feedback from user {user_id} to DB: {db_err}", exc_info=True)
               await message.answer("Ой, не получилось сохранить твой отзыв. Попробуй позже.", reply_markup=await get_main_menu(user_id, db))
      return wrapped_handler


# --- Обработчик бонуса (без изменений) ---
def make_bonus_request_handler(db, logger_service, user_manager):
    # ... (код bonus_request без изменений) ...
     async def wrapped_handler(message: types.Message):
         user_id = message.from_user.id
         user_data = db.get_user(user_id)
         name = user_data.get("name", "Друг")
         if not user_data.get("bonus_available"):
             text = f"{name}, эта подсказка пока не доступна. Используй /share, чтобы получить к ней доступ, когда друг воспользуется твоей ссылкой."
             await message.answer(text, reply_markup=await get_main_menu(user_id, db))
             return

         advice = random.choice(UNIVERSE_ADVICE)
         text = f"{name}, вот послание Вселенной специально для тебя:\n\n{advice}"
         await message.answer(text, reply_markup=await get_main_menu(user_id, db))
         await logger_service.log_action(user_id, "bonus_request_used", {"advice_preview": advice[:50]})

         await user_manager.set_bonus_available(user_id, False)
         await logger_service.log_action(user_id, "bonus_disabled_after_use")
     return wrapped_handler


# --- Регистрация всех обработчиков ---
def register_handlers(dp: Dispatcher, db: Database, logger_service: LoggingService, user_manager: UserManager):
    logger.info("Registering handlers...")

    # Создаем частичные функции с зависимостями
    start_handler = make_start_handler(db, logger_service, user_manager)
    share_handler = make_share_handler(db, logger_service)
    remind_handler = make_remind_handler(db, logger_service, user_manager)
    remind_off_handler = make_remind_off_handler(db, logger_service, user_manager)
    process_reminder_time_handler = make_process_reminder_time_handler(db, logger_service, user_manager)
    name_handler = make_name_handler(db, logger_service, user_manager)
    process_name_handler = make_process_name_handler(db, logger_service, user_manager)
    process_skip_name_handler = make_process_skip_name_handler(db, logger_service, user_manager)
    feedback_handler = make_feedback_handler(db, logger_service)
    process_feedback_handler = make_process_feedback_handler(db, logger_service)
    user_profile_handler = make_user_profile_handler(db, logger_service)
    bonus_request_handler = make_bonus_request_handler(db, logger_service, user_manager)

    # Админские
    users_handler = make_users_handler(db, logger_service)
    logs_handler = make_logs_handler(db, logger_service)
    admin_user_profile_handler = make_admin_user_profile_handler(db, logger_service)

    # --- Регистрация команд ---
    dp.message.register(start_handler, Command("start"), StateFilter("*")) # Разрешаем /start из любого состояния для сброса
    dp.message.register(share_handler, Command("share"), StateFilter("*"))
    dp.message.register(remind_handler, Command("remind"), StateFilter("*"))
    dp.message.register(remind_off_handler, Command("remind_off"), StateFilter("*"))
    dp.message.register(name_handler, Command("name"), StateFilter("*"))
    dp.message.register(feedback_handler, Command("feedback"), StateFilter("*"))
    dp.message.register(user_profile_handler, Command("user_profile"), StateFilter("*"))
    dp.message.register(users_handler, Command("users"), StateFilter("*"))
    dp.message.register(logs_handler, Command("logs"), StateFilter("*"))
    dp.message.register(admin_user_profile_handler, Command("admin_user_profile"), StateFilter("*"))

    # --- Регистрация текстовых кнопок меню ---
    dp.message.register(bonus_request_handler, F.text == "💌 Подсказка Вселенной", StateFilter("*"))
    dp.message.register(
        partial(handle_card_request, db=db, logger_service=logger_service),
        F.text == "✨ Карта дня", StateFilter("*")
    )
    # НОВАЯ КНОПКА: Итог дня
    dp.message.register(
        partial(start_evening_reflection, db=db, logger_service=logger_service),
        F.text == "🌙 Итог дня", StateFilter("*")
    )


    # --- Регистрация состояний FSM ---

    # Имя
    dp.message.register(process_name_handler, UserState.waiting_for_name)
    dp.callback_query.register(process_skip_name_handler, F.data == "skip_name", UserState.waiting_for_name)

    # Напоминания
    dp.message.register(process_reminder_time_handler, UserState.waiting_for_reminder_time)

    # Общий фидбек
    dp.message.register(process_feedback_handler, UserState.waiting_for_feedback)

    # --- Флоу "Карты Дня" ---
    # Оставляем только те, что нужны для регистрации хендлеров
    dp.callback_query.register(partial(process_initial_resource_callback, db=db, logger_service=logging_service), UserState.waiting_for_initial_resource, F.data.startswith("resource_"))
    dp.callback_query.register(partial(process_request_type_callback, db=db, logger_service=logging_service), UserState.waiting_for_request_type_choice, F.data.startswith("request_type_"))
    dp.message.register(partial(process_request_text, db=db, logger_service=logging_service), UserState.waiting_for_request_text_input)
    dp.message.register(partial(process_initial_response, db=db, logger_service=logging_service), UserState.waiting_for_initial_response)
    dp.callback_query.register(partial(process_exploration_choice_callback, db=db, logger_service=logging_service), UserState.waiting_for_exploration_choice, F.data.startswith("explore_"))
    dp.message.register(partial(process_first_grok_response, db=db, logger_service=logging_service), UserState.waiting_for_first_grok_response)
    dp.message.register(partial(process_second_grok_response, db=db, logger_service=logging_service), UserState.waiting_for_second_grok_response)
    dp.message.register(partial(process_third_grok_response, db=db, logger_service=logging_service), UserState.waiting_for_third_grok_response)
    dp.callback_query.register(partial(process_final_resource_callback, db=db, logger_service=logging_service), UserState.waiting_for_final_resource, F.data.startswith("resource_"))
    dp.message.register(partial(process_recharge_method, db=db, logger_service=logging_service), UserState.waiting_for_recharge_method)
    dp.callback_query.register(partial(process_card_feedback, db=db, logger_service=logging_service), F.data.startswith("feedback_v2_"), StateFilter("*"))

    # --- НОВЫЙ ФЛОУ: "Итог дня" ---
    # Подключаем роутер из модуля evening_reflection
    # Передаем зависимости в хендлеры роутера через dp['key']
    # (Способ передачи зависимостей может отличаться в зависимости от версии aiogram,
    # но для aiogram 3.x это один из способов)
    # Однако, если роутер определен как в примере выше, он уже содержит хендлеры.
    # Мы можем просто включить его в основной dp.
    dp.include_router(reflection_router)
    # Важно: Убедись, что зависимости (db, logger_service) доступны внутри хендлеров роутера.
    # Если они не передаются автоматически, возможно, придется использовать middleware
    # или передавать их явно при регистрации роутера, если aiogram это поддерживает.
    # В данном случае, т.к. мы используем partial для других хендлеров,
    # можно зарегистрировать хендлеры "Итога дня" напрямую в dp, а не через роутер.
    # Выберем этот путь для явной передачи зависимостей:

# --- НОВЫЙ ФЛОУ: "Итог дня" ---
    # Регистрируем хендлеры напрямую с передачей зависимостей через partial
    dp.message.register(partial(start_evening_reflection, db=db, logger_service=logger_service), F.text == "🌙 Итог дня", StateFilter("*")) # Уже был выше, дубль убран
    dp.message.register(partial(process_good_moments, db=db, logger_service=logger_service), UserState.waiting_for_good_moments)
    dp.message.register(partial(process_gratitude, db=db, logger_service=logger_service), UserState.waiting_for_gratitude)
    dp.message.register(partial(process_hard_moments, db=db, logger_service=logger_service), UserState.waiting_for_hard_moments)

    # --- Обработчики некорректных вводов (без изменений) ---
    async def handle_text_when_waiting_callback(message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        logger.warning(f"User {message.from_user.id} sent text '{message.text}' while in state {current_state}, expected callback.")
        await message.reply("Пожалуйста, используй кнопки выше, чтобы сделать выбор. 👆")

    async def handle_callback_when_waiting_text(callback: types.CallbackQuery, state: FSMContext):
        current_state = await state.get_state()
        logger.warning(f"User {callback.from_user.id} sent callback '{callback.data}' while in state {current_state}, expected text.")
        await callback.answer("Пожалуйста, отправь ответ текстом в чат.", show_alert=True)

    # Регистрируем обработчики ошибок ввода для КОНКРЕТНЫХ состояний, где это нужно
    # Пример для Карты Дня:
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_initial_resource)
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_request_type_choice)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_request_text_input)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_initial_response)
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_exploration_choice)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_first_grok_response)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_second_grok_response)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_third_grok_response)
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_final_resource)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_recharge_method)

    # Новые для Итога Дня (если ожидаем только текст)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_good_moments)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_gratitude)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_hard_moments)

    # --- Обработчики неизвестных команд/сообщений (последние) ---
    @dp.message(StateFilter("*"))
    async def handle_unknown_message_state(message: types.Message, state: FSMContext):
        # ... (код без изменений) ...
        current_state = await state.get_state()
        logger.warning(f"Unknown message '{message.text}' received from user {message.from_user.id} in state {current_state}")
        await message.reply("Ой, кажется, я не ожидал этого сейчас. 🤔 Попробуй ответить на последний вопрос или используй кнопки, если они есть. Для выхода из текущего диалога можно нажать /start.")

    @dp.message()
    async def handle_unknown_message_no_state(message: types.Message):
        # ... (код без изменений) ...
        logger.warning(f"Unknown message '{message.text}' received from user {message.from_user.id} with no state.")
        await message.reply("Извини, не понял твой запрос. 🤔 Попробуй нажать '✨ Карта дня', '🌙 Итог дня' или используй одну из команд: /start, /name, /remind, /share, /feedback, /user_profile.") # Добавил кнопку

    @dp.callback_query(StateFilter("*"))
    async def handle_unknown_callback_state(callback: types.CallbackQuery, state: FSMContext):
        # ... (код без изменений) ...
         current_state = await state.get_state()
         logger.warning(f"Unknown callback '{callback.data}' received from user {callback.from_user.id} in state {current_state}")
         await callback.answer("Это действие сейчас недоступно.", show_alert=True)


    @dp.callback_query()
    async def handle_unknown_callback_no_state(callback: types.CallbackQuery):
        # ... (код без изменений) ...
         logger.warning(f"Unknown callback '{callback.data}' received from user {callback.from_user.id} with no state.")
         await callback.answer("Неизвестное действие.", show_alert=True)

    logger.info("Handlers registered successfully.")

# --- Запуск бота ---
async def main():
    logger.info("Starting bot...")
    # Устанавливаем команды меню
    commands = [
        types.BotCommand(command="start", description="▶️ Начать / Перезапустить"),
        types.BotCommand(command="name", description="👤 Изменить имя"),
        types.BotCommand(command="remind", description="⏰ Напоминания (Карта/Итог)"), # Обновил описание
        types.BotCommand(command="remind_off", description="🔕 Выключить все напоминания"), # Обновил описание
        types.BotCommand(command="share", description="🎁 Поделиться с другом"),
        types.BotCommand(command="feedback", description="✉️ Оставить отзыв / Идею"),
        types.BotCommand(command="user_profile", description="📊 Мой профиль"),
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands set successfully.")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

    # Регистрируем хендлеры (передаем зависимости)
    # ПЕРЕДЕЛКА: Передаем зависимости в dp для использования в роутерах
    dp["db"] = db
    dp["logger_service"] = logging_service
    dp["user_manager"] = user_manager # Если нужен в роутере

    register_handlers(dp, db, logging_service, user_manager)

    # Запускаем фоновую задачу проверки напоминаний
    reminder_task = asyncio.create_task(notifier.check_reminders())
    logger.info("Reminder check task scheduled.")

    # Запускаем поллинг
    logger.info("Starting polling...")
    print("Bot is starting polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.critical(f"Polling failed: {e}", exc_info=True)
        print(f"CRITICAL: Polling failed: {e}")
    finally:
        logger.info("Stopping bot...")
        print("Bot is stopping...")
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            logger.info("Reminder task cancelled successfully.")
        if db and db.conn:
            try:
                db.conn.close()
                logger.info("Database connection closed.")
            except Exception as db_close_err:
                 logger.error(f"Error closing database connection: {db_close_err}")
        try:
             # У aiogram 3 сессия закрывается автоматически с ботом, но можно и явно
             # await bot.session.close() - Зависит от версии aiogram, может не быть атрибута
             logger.info("Bot session cleanup (handled by aiogram).")
        except Exception as session_close_err:
             logger.error(f"Error closing bot session: {session_close_err}")
        print("Bot stopped.")


if __name__ == "__main__":
    # Устанавливаем TIMEZONE как переменную окружения, если возможно
    # os.environ['TZ'] = 'Europe/Moscow'
    # time.tzset() - для Unix-like систем
    try:
        # Устанавливаем глобальную таймзону для asyncio, если это возможно и нужно
        # (Обычно pytz используется для конкретных объектов datetime)
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually (KeyboardInterrupt/SystemExit).")
    except Exception as e:
        logger.critical(f"Critical error in main execution scope: {e}", exc_info=True)
        print(f"CRITICAL error in main execution scope: {e}")
