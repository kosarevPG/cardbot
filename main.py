# код/main.py

import subprocess
import shlex # Также импортируем shlex для безопасной обработки аргументов
import threading
import os

def run_sqlite_web():
    db_path = "/data/bot.db"
    port = os.environ.get("PORT", "80")
    host = "0.0.0.0"
    # Используем аргумент --password без значения, если пароль не нужен или задается иначе
    command = f"sqlite_web {shlex.quote(db_path)} --host {shlex.quote(host)} --port {shlex.quote(port)} --no-browser"

    print(f"Starting sqlite_web process with command: {command}", flush=True)
    try:
        # shell=True может быть рискованным, лучше передавать список аргументов, если возможно
        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
        print(f"sqlite_web process started with PID: {process.pid}", flush=True)

        # Читаем stdout в реальном времени
        for line in iter(process.stdout.readline, ''):
            print(f"[sqlite_web stdout]: {line.strip()}", flush=True)

        # Читаем stderr в реальном времени (после завершения stdout)
        for line in iter(process.stderr.readline, ''):
            print(f"[sqlite_web stderr]: {line.strip()}", flush=True)

        # Ждем завершения процесса (если он вдруг завершится)
        process.wait()
        print(f"sqlite_web process exited with code: {process.returncode}", flush=True)

    except FileNotFoundError:
         print(f"CRITICAL error: 'sqlite_web' command not found. Is it installed and in PATH?", flush=True)
    except Exception as e:
        print(f"CRITICAL error starting/running sqlite_web process: {e}", flush=True)

# Запуск потока остается тем же
t = threading.Thread(target=run_sqlite_web, daemon=True)
t.start()

import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.exceptions import TelegramAPIError
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
# --- ДОБАВЛЯЕМ ИМПОРТ State ---
from aiogram.fsm.state import State, StatesGroup
# --- КОНЕЦ ИЗМЕНЕНИЯ ---
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
# Убираем импорт State отсюда, т.к. он теперь выше
from modules.user_management import UserState, UserManager
from modules.ai_service import build_user_profile

# Модуль Карты Дня
from modules.card_of_the_day import (
    get_main_menu, handle_card_request, process_initial_resource_callback,
    process_request_type_callback, process_request_text, process_initial_response,
    process_exploration_choice_callback, process_first_grok_response,
    process_second_grok_response, process_third_grok_response,
    process_final_resource_callback, process_recharge_method, process_card_feedback
)

# Модуль Вечерней Рефлексии
# Импортируем функцию для старта и обработчики состояний
from modules.evening_reflection import (
    start_evening_reflection,
    process_good_moments,      # <--- Добавлено
    process_gratitude,       # <--- Добавлено
    process_hard_moments     # <--- Добавлено
    # reflection_router больше не импортируем здесь
)

# --- Стандартные импорты ---
import random
from datetime import datetime, timedelta, time, date # Добавляем time, date
import os
import json
import logging
import sqlite3

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Инициализация ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
os.makedirs(DATA_DIR, exist_ok=True)
db_path = os.path.join(DATA_DIR, "bot.db")
logger.info(f"Initializing database at: {db_path}")
print(f"Initializing database at: {db_path}")
try:
    db = Database(path=db_path)
    db.conn.execute("SELECT 1"); logger.info(f"Database connection established successfully: {db.conn}")
    db.bot = bot
except (sqlite3.Error, Exception) as e:
    logger.exception(f"CRITICAL: Database initialization failed at {db_path}: {e}")
    print(f"CRITICAL: Database initialization failed at {db_path}: {e}"); raise SystemExit(f"Database failed: {e}")
logging_service = LoggingService(db)
notifier = NotificationService(bot, db)
user_manager = UserManager(db)


# --- Middleware ---
class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        return await handler(event, data)
        if isinstance(event, (types.Message, types.CallbackQuery)):
            user = event.from_user
            if not user or user.is_bot or user.id == ADMIN_ID:
                return await handler(event, data)
            user_id = user.id
            try:
                user_status = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
                allowed_statuses = ["member", "administrator", "creator"]
                if user_status.status not in allowed_statuses:
                    user_db_data = db.get_user(user_id); name = user_db_data.get("name") if user_db_data else None
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
                if isinstance(event, types.Message): await event.answer(error_text)
                elif isinstance(event, types.CallbackQuery): await event.answer("Не удается проверить подписку.", show_alert=False); await event.message.answer(error_text)
                return
        return await handler(event, data)


# --- Общая функция для запроса времени ---
async def ask_for_time(message: types.Message, state: FSMContext, prompt_text: str, next_state: State):
    """Отправляет сообщение с запросом времени и устанавливает следующее состояние."""
    await message.answer(prompt_text)
    await state.set_state(next_state)

# --- Обработчики стандартных команд ---
def make_start_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext, command: CommandObject | None = None):
        await state.clear()
        user_id = message.from_user.id
        username = message.from_user.username or ""
        args = command.args if command else ""
        await logger_service.log_action(user_id, "start_command", {"args": args})
        user_data = db.get_user(user_id)
        if user_data.get("username") != username: db.update_user(user_id, {"username": username})
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
            await message.answer("Здравствуй! ✨ Очень рад нашему знакомству. Подскажи, как мне лучше к тебе обращаться?",
                                 reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]]))
            await state.set_state(UserState.waiting_for_name)
        else:
            await message.answer(f"{user_name}, снова рад тебя видеть! 👋 Готова поработать с картой дня или подвести итог?",
                                 reply_markup=await get_main_menu(user_id, db))
    return wrapped_handler

def make_remind_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        user_data = db.get_user(user_id)
        name = user_data.get("name", "Друг")
        morning_reminder = user_data.get("reminder_time")
        evening_reminder = user_data.get("reminder_time_evening")
        morning_text = f"Напоминание 'Карта дня' ✨: <b>{morning_reminder}</b> МСК" if morning_reminder else "Напоминание 'Карта дня' ✨: <b>отключено</b>"
        evening_text = f"Напоминание 'Итог дня' 🌙: <b>{evening_reminder}</b> МСК" if evening_reminder else "Напоминание 'Итог дня' 🌙: <b>отключено</b>"
        purpose_text = "⏰ Настроим ежедневные напоминания?"
        instruction_text = ("Сначала введи удобное время для <b>утреннего</b> напоминания 'Карта дня' в формате <b>ЧЧ:ММ</b> (например, <code>09:00</code>).\nИли напиши <code>выкл</code>, чтобы отключить это напоминание.\n\n"
                           f"<u>Текущие настройки:</u>\n- {morning_text}\n- {evening_text}")
        text = f"{name}, привет!\n\n{purpose_text}\n\n{instruction_text}"
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await state.set_state(UserState.waiting_for_morning_reminder_time)
        await logger_service.log_action(user_id, "remind_command_invoked")
    return wrapped_handler

def make_broadcast_handler(db: Database, logger_service: LoggingService):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if user_id != ADMIN_ID:
            await message.reply("Эта команда доступна только администратору.")
            return
        broadcast_text = message.text[len("/broadcast"):].strip()
        if not broadcast_text:
            await message.reply("Пожалуйста, укажите текст для рассылки после команды.\n"
                                "Пример: `/broadcast Привет! У бота обновления!`")
            return
        text_to_send = """Привет! Надеюсь, у вас все хорошо. ✨

Хочу поделиться новостями: я немного обновился, чтобы наша работа с картами и саморефлексией стала еще глубже и полезнее!

1) У меня новое имя – "Ресурсный помощник". Мне кажется, оно лучше отражает то, чем я могу быть для вас полезен. 😊

2) Теперь я умею составлять "Профиль пользователя" (загляните через команду /user_profile!), где бережно собираются важные моменты нашего взаимодействия. Узнайте себя немного лучше!

3) Появился уютный вечерний ритуал "🌙 Итог дня" – всего пара минут, чтобы мягко завершить день и позаботиться о себе.

Очень хочется снова пообщаться! Нажмите /start, чтобы увидеть обновленное меню и попробовать новинки.

С нетерпением жду встречи!
Ваш Ресурсный помощник ❤️"""
        users = [457463804, 478901963, 517423026, 644771890, 683970407, 684097293, 685995409, 806894927, 834325767, 1068630660, 1123817690, 1159751971, 1264280911, 1348873495, 1664012269, 1821666039, 1853568101, 1887924167, 5741110759,6288394996, 865377684, 171507422]
        if not users:
            await message.reply("Не удалось определить пользователя для тестовой рассылки.")
            return
        await message.reply(f"Начинаю ТЕСТОВУЮ рассылку сообщения для {len(users)} пользователя (ID: {users[0]})...")
        await logger_service.log_action(user_id, "broadcast_test_started", {"target_user_id": users[0], "text_preview": text_to_send[:50]})
        success_count = 0
        fail_count = 0
        failed_users = []
        for target_user_id in users:
            try:
                await bot.send_message(target_user_id, text_to_send, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
                success_count += 1
            except TelegramAPIError as e:
                fail_count += 1
                failed_users.append(target_user_id)
                logger.error(f"Failed to send broadcast to {target_user_id}: {e}")
                await logger_service.log_action(ADMIN_ID, "broadcast_failed_user", {"target_user_id": target_user_id, "error": str(e)})
            except Exception as e:
                fail_count += 1
                failed_users.append(target_user_id)
                logger.error(f"Unexpected error sending broadcast to {target_user_id}: {e}", exc_info=True)
                await logger_service.log_action(ADMIN_ID, "broadcast_failed_user", {"target_user_id": target_user_id, "error": f"Unexpected: {str(e)}"})
            await asyncio.sleep(0.05)
        result_text = f"✅ Тестовая рассылка завершена!\nУспешно отправлено: {success_count}\nНе удалось отправить: {fail_count}"
        if failed_users:
            result_text += f"\nID пользователя с ошибкой: {failed_users[0]}"
        await message.reply(result_text)
        await logger_service.log_action(ADMIN_ID, "broadcast_test_finished", {"success": success_count, "failed": fail_count})
    return wrapped_handler

def make_process_morning_reminder_time_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = db.get_user(user_id).get("name", "Друг")
        input_text = message.text.strip().lower()
        morning_time_to_save = None
        if input_text == "выкл":
            morning_time_to_save = None
            await logger_service.log_action(user_id, "reminder_set_morning", {"time": "disabled"})
            await message.reply("Хорошо, утреннее напоминание 'Карта дня' отключено.")
        else:
            try:
                reminder_dt = datetime.strptime(input_text, "%H:%M")
                morning_time_to_save = reminder_dt.strftime("%H:%M")
                await logger_service.log_action(user_id, "reminder_set_morning", {"time": morning_time_to_save})
                await message.reply(f"Утреннее время <code>{morning_time_to_save}</code> принято.")
            except ValueError:
                await message.reply(f"{name}, не совсем понял время. 🕰️ Пожалуйста, введи время для <b>утреннего</b> напоминания в формате ЧЧ:ММ (например, <code>08:30</code>) или напиши <code>выкл</code>.")
                return
        await state.update_data(morning_time=morning_time_to_save)
        evening_prompt = "Теперь введи время для <b>вечернего</b> напоминания 'Итог дня' 🌙 (ЧЧ:ММ) или напиши <code>выкл</code>."
        await ask_for_time(message, state, evening_prompt, UserState.waiting_for_evening_reminder_time)
     return wrapped_handler

def make_process_evening_reminder_time_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        name = db.get_user(user_id).get("name", "Друг")
        input_text = message.text.strip().lower()
        evening_time_to_save = None
        state_data = await state.get_data()
        morning_time = state_data.get("morning_time")
        if input_text == "выкл":
            evening_time_to_save = None
            await logger_service.log_action(user_id, "reminder_set_evening", {"time": "disabled"})
        else:
            try:
                reminder_dt = datetime.strptime(input_text, "%H:%M")
                evening_time_to_save = reminder_dt.strftime("%H:%M")
                await logger_service.log_action(user_id, "reminder_set_evening", {"time": evening_time_to_save})
            except ValueError:
                await message.reply(f"{name}, не понял время. 🕰️ Пожалуйста, введи время для <b>вечернего</b> напоминания (ЧЧ:ММ) или напиши <code>выкл</code>.")
                return
        try:
            await user_manager.set_reminder(user_id, morning_time, evening_time_to_save)
            await logger_service.log_action(user_id, "reminders_saved_total", {"morning_time": morning_time, "evening_time": evening_time_to_save})
            morning_confirm = f"'Карта дня' ✨: <b>{morning_time}</b> МСК" if morning_time else "'Карта дня' ✨: <b>отключено</b>"
            evening_confirm = f"'Итог дня' 🌙: <b>{evening_time_to_save}</b> МСК" if evening_time_to_save else "'Итог дня' 🌙: <b>отключено</b>"
            text = f"{name}, готово! ✅\nНапоминания установлены:\n- {morning_confirm}\n- {evening_confirm}"
            await message.answer(text, reply_markup=await get_main_menu(user_id, db))
            await state.clear()
        except Exception as e:
            logger.error(f"Failed to save reminders for user {user_id}: {e}", exc_info=True)
            await message.answer("Ой, произошла ошибка при сохранении настроек...")
            await state.clear()
     return wrapped_handler

def make_remind_off_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message, state: FSMContext):
         user_id = message.from_user.id
         current_state = await state.get_state()
         if current_state in [UserState.waiting_for_morning_reminder_time, UserState.waiting_for_evening_reminder_time]:
             await state.clear()
         try:
             await user_manager.clear_reminders(user_id)
             await logger_service.log_action(user_id, "reminders_cleared")
             name = db.get_user(user_id).get("name", "Друг")
             text = f"{name}, я отключил <b>все</b> напоминания для тебя (утреннее и вечернее). Если захочешь включить снова, используй /remind."
             await message.answer(text, reply_markup=await get_main_menu(user_id, db))
         except Exception as e:
             logger.error(f"Failed to disable reminders for user {user_id}: {e}", exc_info=True)
             await message.answer("Ой, не получилось отключить напоминания...")
     return wrapped_handler

def make_share_handler(db, logger_service):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        name = db.get_user(user_id).get("name", "Друг")
        ref_link = f"{BOT_LINK}?start=ref_{user_id}"
        text = (f"{name}, хочешь поделиться этим ботом с друзьями?\nВот твоя персональная ссылка: {ref_link}\n\n"
               f"Когда кто-нибудь перейдет по ней и начнет использовать бота, ты получишь доступ к '💌 Подсказке Вселенной' в главном меню! ✨")
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await logger_service.log_action(user_id, "share_command")
    return wrapped_handler

def make_name_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message, state: FSMContext):
         user_id = message.from_user.id
         name = db.get_user(user_id).get("name")
         text = f"Твое текущее имя: <b>{name}</b>.\nХочешь изменить?" if name else "Как тебя зовут?"
         text += "\nВведи новое имя или нажми 'Пропустить', если не хочешь указывать."
         await message.answer(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]]))
         await state.set_state(UserState.waiting_for_name)
         await logger_service.log_action(user_id, "name_change_initiated")
     return wrapped_handler

def make_feedback_handler(db, logger_service):
     async def wrapped_handler(message: types.Message, state: FSMContext):
         user_id = message.from_user.id
         name = db.get_user(user_id).get("name", "Друг")
         text = (f"{name}, хочешь поделиться идеей, как сделать меня лучше, или рассказать о проблеме?\nЯ внимательно читаю все сообщения! Напиши здесь все, что думаешь.")
         await message.answer(text, reply_markup=await get_main_menu(user_id, db))
         await state.set_state(UserState.waiting_for_feedback)
         await logger_service.log_action(user_id, "feedback_initiated")
     return wrapped_handler

def make_user_profile_handler(db, logger_service):
     async def wrapped_handler(message: types.Message, state: FSMContext):
        await state.clear()
        user_id = message.from_user.id
        name = db.get_user(user_id).get("name", "Друг")
        await logger_service.log_action(user_id, "user_profile_viewed")
        profile = await build_user_profile(user_id, db)
        mood = profile.get("mood", "неизвестно")
        mood_trend_list = [m for m in profile.get("mood_trend", []) if m != "unknown"]
        mood_trend = " → ".join(mood_trend_list) if mood_trend_list else "нет данных"
        themes_list = profile.get("themes", [])
        themes = ", ".join(themes_list) if themes_list and themes_list != ["не определено"] else "нет данных"
        initial_resource = profile.get("initial_resource") or "нет данных"
        final_resource = profile.get("final_resource") or "нет данных"
        recharge_method = profile.get("recharge_method") or "нет данных"
        last_reflection_date = profile.get("last_reflection_date") or "пока не было"
        reflection_count = profile.get("reflection_count", 0)
        response_count = profile.get("response_count", 0)
        days_active = profile.get("days_active", 0)
        total_cards_drawn = profile.get("total_cards_drawn", 0)
        last_updated_dt = profile.get("last_updated")
        last_updated = last_updated_dt.astimezone(TIMEZONE).strftime("%Y-%m-%d %H:%M") if isinstance(last_updated_dt, datetime) else "не обновлялся"
        text = (
             f"📊 <b>{name}, твой профиль взаимодействия:</b>\n\n"
             f"👤 <b>Состояние & Темы:</b>\n  - Настроение (последнее): {mood}\n  - Тренд настроения: {mood_trend}\n  - Ключевые темы (из карт и рефлексий): {themes}\n\n"
             f"🌿 <b>Ресурс (последняя 'Карта дня'):</b>\n  - В начале: {initial_resource}\n  - В конце: {final_resource}\n  - Способ восстановления: {recharge_method}\n\n"
             f"🌙 <b>Вечерняя Рефлексия:</b>\n  - Последний итог подведен: {last_reflection_date}\n  - Всего итогов подведено: {reflection_count}\n\n"
             f"📈 <b>Статистика Активности:</b>\n  - Ответов в диалогах с картой: {response_count}\n  - Всего карт вытянуто: {total_cards_drawn}\n  - Дней активности: {days_active}\n\n"
             f"⏱ <b>Профиль обновлен:</b> {last_updated} МСК\n\n"
             f"<i>Этот профиль помогает мне лучше понимать тебя. Он учитывает твои ответы в 'Карте дня' и 'Итогах дня'.</i>"
         )
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
     return wrapped_handler

def make_admin_user_profile_handler(db, logger_service):
     async def wrapped_handler(message: types.Message):
         user_id = message.from_user.id
         if user_id != ADMIN_ID: await message.answer("Эта команда доступна только администратору."); return
         args = message.text.split()
         if len(args) < 2:
             await message.answer("Укажи ID пользователя: /admin_user_profile <user_id>")
             return
         try:
             target_user_id = int(args[1])
         except ValueError:
             await message.answer("ID пользователя должен быть числом.")
             return
         user_info = db.get_user(target_user_id)
         if not user_info:
             await message.answer(f"Пользователь с ID {target_user_id} не найден в таблице users.")
             return
         profile = await build_user_profile(target_user_id, db)
         name = user_info.get("name", "N/A")
         username = user_info.get("username", "N/A")
         mood = profile.get("mood", "N/A")
         mood_trend_list = [m for m in profile.get("mood_trend", []) if m != "unknown"]
         mood_trend = " → ".join(mood_trend_list) if mood_trend_list else "N/A"
         themes_list = profile.get("themes", [])
         themes = ", ".join(themes_list) if themes_list and themes_list != ["не определено"] else "N/A"
         initial_resource = profile.get("initial_resource") or "N/A"
         final_resource = profile.get("final_resource") or "N/A"
         recharge_method = profile.get("recharge_method") or "N/A"
         last_reflection_date = profile.get("last_reflection_date") or "N/A"
         reflection_count = profile.get("reflection_count", 0)
         response_count = profile.get("response_count", 0)
         days_active = profile.get("days_active", 0)
         total_cards_drawn = profile.get("total_cards_drawn", 0)
         last_updated_dt = profile.get("last_updated")
         last_updated = last_updated_dt.astimezone(TIMEZONE).strftime("%Y-%m-%d %H:%M") if isinstance(last_updated_dt, datetime) else "N/A"
         text = (
             f"👤 <b>Профиль пользователя:</b> <code>{target_user_id}</code>\n   Имя: {name}, Ник: @{username}\n\n"
             f"<b>Состояние & Темы:</b>\n  Настроение: {mood}\n  Тренд: {mood_trend}\n  Темы: {themes}\n\n"
             f"<b>Ресурс (последний 'Карта дня'):</b>\n  Начало: {initial_resource}\n  Конец: {final_resource}\n  Восстановление: {recharge_method}\n\n"
             f"<b>Вечерняя Рефлексия:</b>\n  Последний итог: {last_reflection_date}\n  Всего итогов: {reflection_count}\n\n"
             f"<b>Статистика Активности:</b>\n  Ответов (карта): {response_count}\n  Карт вытянуто: {total_cards_drawn}\n  Дней актив.: {days_active}\n\n"
             f"<b>Обновлено:</b> {last_updated} МСК"
         )
         await message.answer(text)
         await logger_service.log_action(user_id, "admin_user_profile_viewed", {"target_user_id": target_user_id})
     return wrapped_handler

def make_users_handler(db, logger_service):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if user_id != ADMIN_ID: await message.answer("Эта команда доступна только администратору."); return
        users = db.get_all_users()
        if not users:
            await message.answer("В базе данных нет пользователей.")
            return
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        filtered_users = [uid for uid in users if uid not in excluded_users]
        if not filtered_users:
            await message.answer("Нет пользователей для отображения (все исключены или список пуст).")
            return
        user_list = []
        for uid in filtered_users:
            user_data = db.get_user(uid)
            if not user_data:
                logger.warning(f"User ID {uid} found by get_all_users but not found by get_user. Skipping.")
                continue
            name = user_data.get("name", "Без имени")
            username = user_data.get("username", "Нет никнейма")
            last_action_time = "Нет действий"
            last_action_timestamp_iso_or_dt = "1970-01-01T00:00:00+00:00"
            user_actions = db.get_actions(uid)
            if user_actions:
                last_action = user_actions[-1]
                raw_timestamp = last_action.get("timestamp")
                try:
                    last_action_dt = None
                    if isinstance(raw_timestamp, datetime):
                         last_action_dt = raw_timestamp.astimezone(TIMEZONE) if raw_timestamp.tzinfo and pytz else (TIMEZONE.localize(raw_timestamp) if pytz else raw_timestamp)
                         last_action_timestamp_iso_or_dt = raw_timestamp
                    elif isinstance(raw_timestamp, str):
                         last_action_dt = datetime.fromisoformat(raw_timestamp.replace('Z', '+00:00')).astimezone(TIMEZONE)
                         last_action_timestamp_iso_or_dt = raw_timestamp
                    else:
                         logger.warning(f"Invalid timestamp type for last action of user {uid}: {type(raw_timestamp)}")
                    if last_action_dt:
                         last_action_time = last_action_dt.strftime("%Y-%m-%d %H:%M")
                    else:
                         last_action_time = "Ошибка времени"
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing last action timestamp for user {uid}: {raw_timestamp}, error: {e}")
                    last_action_time = f"Ошибка ({raw_timestamp})"
                    last_action_timestamp_iso_or_dt = raw_timestamp if isinstance(raw_timestamp, str) else "1970-01-01T00:00:00+00:00"
            user_list.append({
                "uid": uid,
                "username": username,
                "name": name,
                "last_action_time": last_action_time,
                "last_action_timestamp_iso_or_dt": last_action_timestamp_iso_or_dt
            })
        try:
            user_list.sort(
                key=lambda x: (x["last_action_timestamp_iso_or_dt"].astimezone(TIMEZONE) if isinstance(x["last_action_timestamp_iso_or_dt"], datetime) and x["last_action_timestamp_iso_or_dt"].tzinfo
                                else datetime.fromisoformat(str(x["last_action_timestamp_iso_or_dt"]).replace('Z', '+00:00')).astimezone(TIMEZONE) if isinstance(x["last_action_timestamp_iso_or_dt"], str)
                                else datetime.min.replace(tzinfo=TIMEZONE)),
                reverse=True
            )
        except (ValueError, TypeError) as sort_err:
            logger.error(f"Error sorting user list by timestamp: {sort_err}. List may be unsorted.")
        formatted_list = [f"ID: <code>{user['uid']}</code> | @{user['username']} | {user['name']} | Посл. действие: {user['last_action_time']}" for user in user_list]
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
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if user_id != ADMIN_ID: await message.answer("Эта команда доступна только администратору."); return
        args = message.text.split()
        target_date_str = None
        target_date = None
        if len(args) > 1:
            target_date_str = args[1]
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                await message.answer("Неверный формат даты. Используй ГГГГ-ММ-ДД (например, 2024-12-31).")
                return
        else:
            target_date = datetime.now(TIMEZONE).date()
            target_date_str = target_date.strftime("%Y-%m-%d")
        await logger_service.log_action(user_id, "logs_command", {"date": target_date_str})
        logs = db.get_actions()
        filtered_logs = []
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        for log in logs:
            log_timestamp_dt = None
            try:
                raw_timestamp = log.get("timestamp")
                if isinstance(raw_timestamp, datetime):
                     log_timestamp_dt = raw_timestamp.astimezone(TIMEZONE) if raw_timestamp.tzinfo and pytz else (TIMEZONE.localize(raw_timestamp) if pytz else raw_timestamp)
                elif isinstance(raw_timestamp, str):
                     log_timestamp_dt = datetime.fromisoformat(raw_timestamp.replace('Z', '+00:00')).astimezone(TIMEZONE)
                else:
                     logger.warning(f"Skipping log due to invalid timestamp type: {type(raw_timestamp)} in action {log.get('id')}")
                     continue
                if log_timestamp_dt.date() == target_date and log.get("user_id") not in excluded_users:
                    log["parsed_datetime"] = log_timestamp_dt
                    filtered_logs.append(log)
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Could not parse timestamp or missing data in log for admin view: {log}, error: {e}")
                continue
        if not filtered_logs:
            await message.answer(f"Логов за {target_date_str} не найдено (или все пользователи исключены).")
            return
        log_lines = []
        for log in filtered_logs:
            ts_str = log["parsed_datetime"].strftime('%H:%M:%S')
            uid = log.get('user_id', 'N/A')
            action = log.get('action', 'N/A')
            details = log.get('details', {})
            details_str = ""
            if isinstance(details, dict) and details:
                safe_details = {k: str(v)[:50] + ('...' if len(str(v)) > 50 else '') for k, v in details.items()}
                details_str = ", ".join([f"{k}={v}" for k, v in safe_details.items()])
                details_str = f" ({details_str[:100]}{'...' if len(details_str) > 100 else ''})"
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

# --- Обработчики ввода имени ---
def make_process_name_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message, state: FSMContext):
         user_id = message.from_user.id
         name = message.text.strip()
         if not name: await message.answer("Имя не может быть пустым..."); return
         if len(name) > 50: await message.answer("Слишком длинное имя..."); return
         reserved_names = ["✨ Карта дня", "💌 Подсказка Вселенной", "🌙 Итог дня"]
         if name in reserved_names:
             await message.answer(f"Имя '{name}' использовать нельзя, оно совпадает с кнопкой меню.")
             return
         await user_manager.set_name(user_id, name)
         await logger_service.log_action(user_id, "set_name", {"name": name})
         await message.answer(f"Приятно познакомиться, {name}! 😊\nТеперь можешь выбрать действие в меню.", reply_markup=await get_main_menu(user_id, db))
         await state.clear()
     return wrapped_handler

def make_process_skip_name_handler(db, logger_service, user_manager):
     async def wrapped_handler(callback: types.CallbackQuery, state: FSMContext):
         user_id = callback.from_user.id
         await user_manager.set_name(user_id, "")
         await logger_service.log_action(user_id, "skip_name")
         try:
             await callback.message.edit_reply_markup(reply_markup=None)
         except Exception as e:
             logger.warning(f"Could not edit message on skip_name for user {user_id}: {e}")
         await callback.message.answer("Хорошо, буду обращаться к тебе без имени.\nВыбери действие в меню.", reply_markup=await get_main_menu(user_id, db))
         await state.clear()
         await callback.answer()
     return wrapped_handler

# --- Обработчики ввода фидбека ---
def make_process_feedback_handler(db, logger_service):
      async def wrapped_handler(message: types.Message, state: FSMContext):
          user_id = message.from_user.id
          feedback_text = message.text.strip()
          if not feedback_text: await message.answer("Кажется, ты ничего не написала..."); return
          user_data = db.get_user(user_id)
          name = user_data.get("name", "Аноним")
          username = user_data.get("username", "N/A")
          timestamp_iso = datetime.now(TIMEZONE).isoformat()
          try:
              with db.conn:
                  db.conn.execute("INSERT INTO feedback (user_id, name, feedback, timestamp) VALUES (?, ?, ?, ?)",
                                   (user_id, name, feedback_text, timestamp_iso))
              await logger_service.log_action(user_id, "feedback_submitted", {"feedback_length": len(feedback_text)})
              await message.answer(f"{name}, спасибо за твой отзыв! 🙏", reply_markup=await get_main_menu(user_id, db))
              try:
                  admin_notify_text = (f"📝 Новый фидбек от:\nID: <code>{user_id}</code>\nИмя: {name}\nНик: @{username}\n\n<b>Текст:</b>\n{feedback_text}")
                  await bot.send_message(ADMIN_ID, admin_notify_text[:4090])
              except Exception as admin_err:
                  logger.error(f"Failed to send feedback notification to admin: {admin_err}")
              await state.clear()
          except sqlite3.Error as db_err:
              logger.error(f"Failed to save feedback from user {user_id} to DB: {db_err}", exc_info=True)
              await message.answer("Ой, не получилось сохранить твой отзыв...", reply_markup=await get_main_menu(user_id, db))
              await state.clear()
      return wrapped_handler

# --- Обработчик бонуса ---
def make_bonus_request_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message):
         user_id = message.from_user.id
         user_data = db.get_user(user_id)
         name = user_data.get("name", "Друг")
         if not user_data.get("bonus_available"):
             text = f"{name}, эта подсказка пока не доступна. Поделись своей реферальной ссылкой (/share) с другом, чтобы ее получить! ✨"
             await message.answer(text, reply_markup=await get_main_menu(user_id, db))
             return
         advice = random.choice(UNIVERSE_ADVICE)
         text = f"{name}, вот послание Вселенной для тебя:\n\n<i>{advice}</i>"
         await message.answer(text, reply_markup=await get_main_menu(user_id, db))
         await logger_service.log_action(user_id, "bonus_request_used", {"advice_preview": advice[:50]})
     return wrapped_handler

# --- Регистрация всех обработчиков ---
def register_handlers(dp: Dispatcher, db: Database, logger_service: LoggingService, user_manager: UserManager):
    logger.info("Registering handlers...")
    start_handler = make_start_handler(db, logger_service, user_manager)
    share_handler = make_share_handler(db, logger_service)
    remind_handler = make_remind_handler(db, logger_service, user_manager)
    remind_off_handler = make_remind_off_handler(db, logger_service, user_manager)
    process_morning_reminder_time_handler = make_process_morning_reminder_time_handler(db, logger_service, user_manager)
    process_evening_reminder_time_handler = make_process_evening_reminder_time_handler(db, logger_service, user_manager)
    name_handler = make_name_handler(db, logger_service, user_manager)
    process_name_handler = make_process_name_handler(db, logger_service, user_manager)
    process_skip_name_handler = make_process_skip_name_handler(db, logger_service, user_manager)
    feedback_handler = make_feedback_handler(db, logger_service)
    process_feedback_handler = make_process_feedback_handler(db, logger_service)
    user_profile_handler = make_user_profile_handler(db, logger_service)
    bonus_request_handler = make_bonus_request_handler(db, logger_service, user_manager)
    users_handler = make_users_handler(db, logger_service)
    logs_handler = make_logs_handler(db, logger_service)
    admin_user_profile_handler = make_admin_user_profile_handler(db, logger_service)
    broadcast_handler = make_broadcast_handler(db, logger_service)

    dp.message.register(start_handler, Command("start"), StateFilter("*"))
    dp.message.register(share_handler, Command("share"), StateFilter("*"))
    dp.message.register(remind_handler, Command("remind"), StateFilter("*"))
    dp.message.register(remind_off_handler, Command("remind_off"), StateFilter("*"))
    dp.message.register(name_handler, Command("name"), StateFilter("*"))
    dp.message.register(feedback_handler, Command("feedback"), StateFilter("*"))
    dp.message.register(user_profile_handler, Command("user_profile"), StateFilter("*"))
    dp.message.register(users_handler, Command("users"), StateFilter("*"))
    dp.message.register(logs_handler, Command("logs"), StateFilter("*"))
    dp.message.register(admin_user_profile_handler, Command("admin_user_profile"), StateFilter("*"))
    dp.message.register(broadcast_handler, Command("broadcast"), StateFilter("*"))

    dp.message.register(bonus_request_handler, F.text == "💌 Подсказка Вселенной", StateFilter("*"))
    dp.message.register(partial(handle_card_request, db=db, logger_service=logger_service), F.text == "✨ Карта дня", StateFilter("*"))
    dp.message.register(partial(start_evening_reflection, db=db, logger_service=logger_service), F.text == "🌙 Итог дня", StateFilter("*"))
    
    dp.message.register(process_name_handler, UserState.waiting_for_name)
    dp.callback_query.register(process_skip_name_handler, F.data == "skip_name", UserState.waiting_for_name)
    dp.message.register(process_feedback_handler, UserState.waiting_for_feedback)

    dp.message.register(process_morning_reminder_time_handler, UserState.waiting_for_morning_reminder_time)
    dp.message.register(process_evening_reminder_time_handler, UserState.waiting_for_evening_reminder_time)

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

    dp.message.register(partial(process_good_moments, db=db, logger_service=logger_service), UserState.waiting_for_good_moments)
    dp.message.register(partial(process_gratitude, db=db, logger_service=logger_service), UserState.waiting_for_gratitude)
    dp.message.register(partial(process_hard_moments, db=db, logger_service=logger_service), UserState.waiting_for_hard_moments)

    async def handle_text_when_waiting_callback(message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        logger.warning(f"User {message.from_user.id} sent text '{message.text}' while in state {current_state}, expected callback.")
        await message.reply("Пожалуйста, используй кнопки для этого шага.")

    async def handle_callback_when_waiting_text(callback: types.CallbackQuery, state: FSMContext):
        current_state = await state.get_state()
        logger.warning(f"User {callback.from_user.id} sent callback '{callback.data}' while in state {current_state}, expected text.")
        await callback.answer("Пожалуйста, отправь ответ текстом...", show_alert=True)

    dp.message.register(handle_text_when_waiting_callback, StateFilter(
        UserState.waiting_for_initial_resource,
        UserState.waiting_for_request_type_choice,
        UserState.waiting_for_exploration_choice,
        UserState.waiting_for_final_resource
    ))
    dp.callback_query.register(handle_callback_when_waiting_text, StateFilter(
        UserState.waiting_for_name,
        UserState.waiting_for_request_text_input,
        UserState.waiting_for_initial_response,
        UserState.waiting_for_first_grok_response,
        UserState.waiting_for_second_grok_response,
        UserState.waiting_for_third_grok_response,
        UserState.waiting_for_recharge_method,
        UserState.waiting_for_feedback,
        UserState.waiting_for_morning_reminder_time,
        UserState.waiting_for_evening_reminder_time,
        UserState.waiting_for_good_moments,
        UserState.waiting_for_gratitude,
        UserState.waiting_for_hard_moments
    ))

    # --- ИЗМЕНЕНИЕ: Доработанный обработчик для логгирования "отвалов" ---
    @dp.message(StateFilter("*"))
    async def handle_unknown_message_state(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        current_state_str = await state.get_state()
        logger.warning(f"Unknown message '{message.text}' from user {user_id} in state {current_state_str}")
        
        fsm_data = await state.get_data()
        session_id = fsm_data.get("session_id", "unknown_abandon")

        state_to_event_map = {
            UserState.waiting_for_initial_resource: "flow_abandoned_at_initial_resource",
            UserState.waiting_for_request_type_choice: "flow_abandoned_at_request_type",
            UserState.waiting_for_request_text_input: "flow_abandoned_at_request_input",
            UserState.waiting_for_initial_response: "flow_abandoned_at_initial_response",
            UserState.waiting_for_exploration_choice: "flow_abandoned_at_exploration_choice",
            UserState.waiting_for_first_grok_response: "flow_abandoned_at_grok_1",
            UserState.waiting_for_second_grok_response: "flow_abandoned_at_grok_2",
            UserState.waiting_for_third_grok_response: "flow_abandoned_at_grok_3",
            UserState.waiting_for_final_resource: "flow_abandoned_at_final_resource",
            UserState.waiting_for_recharge_method: "flow_abandoned_at_recharge"
        }
        
        event_name = state_to_event_map.get(current_state_str)
        if event_name:
            await logger_service.log_action(
                user_id,
                event_name,
                {
                    "user_input": message.text[:200],
                    "session_id": session_id
                }
            )

        await message.reply("Ой, кажется, я не ожидал этого сейчас... Попробуй вернуться через /start или используй команду из меню.")
        await state.clear()
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    @dp.message()
    async def handle_unknown_message_no_state(message: types.Message):
        logger.warning(f"Unknown message '{message.text}' from user {message.from_user.id} with no state.")

    @dp.callback_query(StateFilter("*"))
    async def handle_unknown_callback_state(callback: types.CallbackQuery, state: FSMContext):
        logger.warning(f"Unknown callback '{callback.data}' from user {callback.from_user.id} in state {await state.get_state()}")
        await callback.answer("Это действие сейчас недоступно.", show_alert=True)

    @dp.callback_query()
    async def handle_unknown_callback_no_state(callback: types.CallbackQuery):
        logger.warning(f"Unknown callback '{callback.data}' from user {callback.from_user.id} with no state.")
        await callback.answer("Неизвестное действие.", show_alert=True)

    logger.info("Handlers registered successfully.")


# --- Запуск бота ---
async def main():
    logger.info("Starting bot...")
    commands = [
        types.BotCommand(command="start", description="🔄 Перезагрузка"),
        types.BotCommand(command="name", description="👩🏼 Указать имя"),
        types.BotCommand(command="remind", description="⏰ Настроить напоминания"),
        types.BotCommand(command="remind_off", description="🔕 Выключить все напоминания"),
        types.BotCommand(command="share", description="🎁 Поделиться с другом"),
        types.BotCommand(command="feedback", description="✉️ Оставить отзыв / Идею"),
        types.BotCommand(command="user_profile", description="📊 Мой профиль")
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands set successfully.")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

    dp["db"] = db
    dp["logger_service"] = logging_service
    dp["user_manager"] = user_manager
    register_handlers(dp, db, logging_service, user_manager)
    reminder_task = asyncio.create_task(notifier.check_reminders())
    logger.info("Reminder check task scheduled.")
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
                db.close()
            except Exception as db_close_err:
                logger.error(f"Error closing database connection: {db_close_err}")
        logger.info("Bot session cleanup (handled by aiogram).")
        print("Bot stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}", exc_info=True)
        print(f"CRITICAL error in main execution: {e}")
