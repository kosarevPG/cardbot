# Last Amvera rebuild: 2025-08-16 00:59:59 - Force rebuild for AI functions - PROD DEPLOY
# код/main.py

import subprocess
import shlex # Также импортируем shlex для безопасной обработки аргументов
import threading
import os

def run_sqlite_web():
    # Используем тот же путь к БД, что и для основного приложения
    try:
        from config_local import DATA_DIR
    except ImportError:
        from config import DATA_DIR
    
    if 'DB_PATH' in globals():
        db_path = DB_PATH
    else:
        db_path = os.path.join(DATA_DIR, "bot.db")
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
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
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
try:
    from config_local import *
    print("Using development configuration (config_local.py)")
except ImportError:
    from config import *
    print("Using production configuration (config.py)")
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
    process_final_resource_callback, process_recharge_method, process_recharge_method_choice, process_card_feedback,
    process_emotion_choice, process_custom_response
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

# Модули для работы с постами
from modules.post_management import PostManager
from modules.scheduler import MailingScheduler, ReflectionAnalysisScheduler  # Добавляем новый планировщик

# --- Стандартные импорты ---
import random
from datetime import datetime, timedelta, time, date # Добавляем time, date
import os
import json
import logging
import sqlite3

# --- Состояния для создания постов ---
class PostCreationStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_media = State()
    waiting_for_audience = State()
    waiting_for_user_ids = State()
    waiting_for_schedule = State()
    waiting_for_confirmation = State()

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Инициализация ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
# Используем локальную БД для разработки
if 'DB_PATH' in globals():
    db_path = DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
else:
    os.makedirs(DATA_DIR, exist_ok=True)
    db_path = os.path.join(DATA_DIR, "bot.db")
logger.info(f"Initializing database at: {db_path}")
print(f"Initializing database at: {db_path}")
try:
    db = Database(path=db_path)
    db.conn.execute("SELECT 1"); logger.info(f"Database connection established successfully: {db.conn}")
    db.bot = bot
    
    # Инициализация таблицы user_requests
    try:
        cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_requests'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            logger.info("Creating user_requests table...")
            db.conn.execute("""
                CREATE TABLE user_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    request_text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    card_number INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Создаем индексы
            db.conn.execute("CREATE INDEX idx_user_requests_user_id ON user_requests(user_id)")
            db.conn.execute("CREATE INDEX idx_user_requests_timestamp ON user_requests(timestamp)")
            db.conn.execute("CREATE INDEX idx_user_requests_session_id ON user_requests(session_id)")
            
            db.conn.commit()
            logger.info("user_requests table created successfully")
        else:
            # Проверяем структуру
            cursor = db.conn.execute("PRAGMA table_info(user_requests)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Добавляем недостающие колонки
            if 'request_text' not in column_names:
                db.conn.execute("ALTER TABLE user_requests ADD COLUMN request_text TEXT")
                logger.info("Added request_text column")
            
            if 'session_id' not in column_names:
                db.conn.execute("ALTER TABLE user_requests ADD COLUMN session_id TEXT")
                logger.info("Added session_id column")
            
            if 'card_number' not in column_names:
                db.conn.execute("ALTER TABLE user_requests ADD COLUMN card_number INTEGER")
                logger.info("Added card_number column")
            
            db.conn.commit()
            logger.info("user_requests table structure verified")
            
    except Exception as init_err:
        logger.error(f"Error initializing user_requests table: {init_err}")
        print(f"Warning: user_requests table initialization failed: {init_err}")
        
except (sqlite3.Error, Exception) as e:
    logger.exception(f"CRITICAL: Database initialization failed at {db_path}: {e}")
    print(f"CRITICAL: Database initialization failed at {db_path}: {e}"); raise SystemExit(f"Database failed: {e}")
logging_service = LoggingService(db)
notifier = NotificationService(bot, db)
user_manager = UserManager(db)


# --- Middleware ---
class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, (types.Message, types.CallbackQuery)):
            user = event.from_user
            if not user or user.is_bot or user.id == ADMIN_ID:
                return await handler(event, data)
            user_id = user.id
            try:
                # Получаем доступ к базе данных через data
                db = data.get("db")
                if not db:
                    logger.error("Database not found in middleware data")
                    return await handler(event, data)
                
                # Проверяем, завершил ли пользователь сценарий "Карта дня" впервые
                has_completed_card_scenario = db.has_completed_scenario_first_time(user_id, 'card_of_day')
                
                # Если пользователь еще не завершил сценарий "Карта дня" впервые, пропускаем проверку подписки
                if not has_completed_card_scenario:
                    return await handler(event, data)
                
                # Проверяем подписку только после первого успешного завершения сценария "Карта дня"
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
        
        # Проверяем, новый ли это пользователь (нет first_seen)
        is_new_user = not user_data.get("first_seen")
        if is_new_user:
            # Устанавливаем first_seen для нового пользователя
            db.update_user_first_seen(user_id)
            await logger_service.log_action(user_id, "new_user_first_seen", {"timestamp": datetime.now().isoformat()})
        
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

def make_create_post_handler(db: Database, logger_service: LoggingService):
    """Создает обработчик для создания постов."""
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if str(user_id) not in ADMIN_IDS:
            await message.reply("Эта команда доступна только администратору.")
            return
        
        # Парсим команду: /create_post "Заголовок" "Содержание"
        text = message.text[len("/create_post"):].strip()
        
        if not text:
            await message.reply("""📝 <b>СОЗДАНИЕ ПОСТА</b>

Использование: <code>/create_post "Заголовок" "Содержание"</code>

Пример:
<code>/create_post "Новости бота" "Привет! У нас обновления..."</code>""", parse_mode="HTML")
            return
        
        # Пытаемся найти заголовок и содержание в кавычках
        import re
        matches = re.findall(r'"([^"]*)"', text)
        
        if len(matches) < 2:
            await message.reply("❌ Неверный формат. Используйте: <code>/create_post \"Заголовок\" \"Содержание\"</code>", parse_mode="HTML")
            return
        
        title = matches[0]
        content = matches[1]
        
        # Валидируем данные
        from modules.post_management import PostManager
        post_manager = PostManager(db, message.bot, logger_service)
        validation = post_manager.validate_post_data(title, content)
        
        if not validation['valid']:
            errors = "\n".join([f"• {error}" for error in validation['errors']])
            await message.reply(f"❌ <b>Ошибки валидации:</b>\n{errors}", parse_mode="HTML")
            return
        
        try:
            # Создаем пост
            post_id = post_manager.create_post(title, content, user_id)
            
            await message.reply(f"""✅ <b>Пост создан успешно!</b>

📝 <b>Заголовок:</b> {title}
📄 <b>Содержание:</b> {content[:100]}{'...' if len(content) > 100 else ''}
🆔 <b>ID поста:</b> {post_id}

Теперь используйте команду <code>/send_post {post_id} all</code> для отправки всем пользователям или <code>/send_post {post_id} 123456,789012</code> для отправки конкретным пользователям.""", parse_mode="HTML")
            
            await logger_service.log_action(user_id, "post_created", {"post_id": post_id, "title": title})
            
        except Exception as e:
            logger.error(f"Error creating post: {e}", exc_info=True)
            await message.reply("❌ Ошибка при создании поста")
    
    return wrapped_handler

def make_list_posts_handler(db: Database, logger_service: LoggingService):
    """Создает обработчик для просмотра списка постов."""
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if str(user_id) not in ADMIN_IDS:
            await message.reply("Эта команда доступна только администратору.")
            return
        
        try:
            from modules.post_management import PostManager
            post_manager = PostManager(db, message.bot, logger_service)
            posts = post_manager.get_all_posts(limit=10)
            
            if not posts:
                await message.reply("📝 <b>СПИСОК ПОСТОВ</b>\n\nПостов пока нет.", parse_mode="HTML")
                return
            
            text = "📝 <b>СПИСОК ПОСТОВ</b>\n\n"
            for i, post in enumerate(posts, 1):
                preview = post_manager.format_post_preview(post, max_length=80)
                text += f"{i}. {preview}\n\n"
            
            await message.reply(text, parse_mode="HTML")
            await logger_service.log_action(user_id, "posts_list_viewed", {})
            
        except Exception as e:
            logger.error(f"Error listing posts: {e}", exc_info=True)
            await message.reply("❌ Ошибка при получении списка постов")
    
    return wrapped_handler

def make_send_post_handler(db: Database, logger_service: LoggingService):
    """Создает обработчик для отправки постов."""
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if str(user_id) not in ADMIN_IDS:
            await message.reply("Эта команда доступна только администратору.")
            return
        
        # Парсим команду: /send_post ID all [время] или /send_post ID 123,456 [время]
        text = message.text[len("/send_post"):].strip()
        
        if not text:
            await message.reply("""📤 <b>ОТПРАВКА ПОСТА</b>

Использование:
• <code>/send_post ID all</code> - отправить всем пользователям сейчас
• <code>/send_post ID all 2024-12-31 15:30</code> - отправить всем в указанное время
• <code>/send_post ID 123456,789012</code> - отправить конкретным пользователям сейчас
• <code>/send_post ID 123456,789012 2024-12-31 15:30</code> - отправить конкретным пользователям в указанное время

Формат времени: <code>YYYY-MM-DD HH:MM</code> (московское время)

Примеры:
• <code>/send_post 1 all</code> - отправить пост 1 всем сейчас
• <code>/send_post 1 all 2024-12-31 15:30</code> - отправить пост 1 всем 31 декабря в 15:30""", parse_mode="HTML")
            return
        
        parts = text.split()
        if len(parts) < 2:
            await message.reply("❌ Неверный формат. Используйте: <code>/send_post ID all [время]</code> или <code>/send_post ID 123,456 [время]</code>", parse_mode="HTML")
            return
        
        try:
            post_id = int(parts[0])
            target = parts[1]
            
            # Проверяем, есть ли время отправки
            scheduled_at = None
            if len(parts) >= 3:
                # Объединяем оставшиеся части как время
                time_parts = parts[2:]
                scheduled_at = " ".join(time_parts)
            
            from modules.post_management import PostManager
            post_manager = PostManager(db, message.bot, logger_service)
            
            # Получаем пост
            post = post_manager.get_post(post_id)
            if not post:
                await message.reply(f"❌ Пост с ID {post_id} не найден")
                return
            
            # Определяем получателей
            if target.lower() == "all":
                send_to_all = True
                target_user_ids = None
            else:
                send_to_all = False
                try:
                    target_user_ids = [int(uid.strip()) for uid in target.split(",")]
                except ValueError:
                    await message.reply("❌ Неверный формат ID пользователей. Используйте: <code>123456,789012</code>", parse_mode="HTML")
                    return
            
            # Валидируем данные рассылки
            validation = post_manager.validate_mailing_data(send_to_all, target_user_ids, scheduled_at)
            if not validation['valid']:
                errors = "\n".join([f"• {error}" for error in validation['errors']])
                await message.reply(f"❌ <b>Ошибки валидации:</b>\n{errors}", parse_mode="HTML")
                return
            
            # Создаем рассылку
            mailing_title = f"Рассылка поста '{post['title']}'"
            mailing_id = post_manager.create_mailing(
                post_id=post_id,
                title=mailing_title,
                send_to_all=send_to_all,
                created_by=user_id,
                target_user_ids=target_user_ids,
                scheduled_at=scheduled_at
            )
            
            # Показываем результат
            target_text = "всем пользователям" if send_to_all else f"{len(target_user_ids)} пользователям"
            
            if scheduled_at:
                # Отложенная отправка
                await message.reply(f"""⏰ <b>Пост запланирован!</b>

📝 <b>Пост:</b> {post['title']}
👥 <b>Получатели:</b> {target_text}
📅 <b>Время отправки:</b> {scheduled_at}
🆔 <b>ID рассылки:</b> {mailing_id}

Пост будет отправлен автоматически в указанное время.""", parse_mode="HTML")
            else:
                # Немедленная отправка
                mailing = post_manager.get_mailing(mailing_id)
                result = await post_manager.process_mailing(mailing)
                
                await message.reply(f"""✅ <b>Пост отправлен!</b>

📝 <b>Пост:</b> {post['title']}
👥 <b>Получатели:</b> {target_text}
📊 <b>Результат:</b>
• Отправлено: {result['sent']}
• Ошибок: {result['failed']}
• Всего: {result['total']}""", parse_mode="HTML")
            
            # Логируем действие
            log_data = {
                "post_id": post_id, 
                "mailing_id": mailing_id,
                "send_to_all": send_to_all,
                "target_count": len(target_user_ids) if target_user_ids else 0,
                "scheduled_at": scheduled_at
            }
            
            if scheduled_at:
                await logger_service.log_action(user_id, "post_scheduled", log_data)
            else:
                log_data["result"] = result
                await logger_service.log_action(user_id, "post_sent", log_data)
            
        except ValueError:
            await message.reply("❌ Неверный ID поста. Используйте число.")
        except Exception as e:
            logger.error(f"Error sending post: {e}", exc_info=True)
            await message.reply("❌ Ошибка при отправке поста")
    
    return wrapped_handler

def make_process_mailings_handler(db: Database, logger_service: LoggingService):
    """Создает обработчик для обработки рассылок."""
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if str(user_id) not in ADMIN_IDS:
            await message.reply("Эта команда доступна только администратору.")
            return
        
        try:
            from modules.scheduler import MailingScheduler
            from modules.post_management import PostManager
            
            post_manager = PostManager(db, message.bot, logger_service)
            scheduler = MailingScheduler(post_manager, check_interval=60)
            
            await message.reply("🔄 Обрабатываю рассылки...")
            
            result = await scheduler.process_mailings_now()
            
            await message.reply(f"""✅ <b>ОБРАБОТКА ЗАВЕРШЕНА</b>

📊 <b>Результат:</b>
• Обработано рассылок: {result['processed']}
• Успешно отправлено: {result['total_sent']}
• Ошибок: {result['total_failed']}""", parse_mode="HTML")
            
            await logger_service.log_action(user_id, "mailings_processed", result)
            
        except Exception as e:
            logger.error(f"Error processing mailings: {e}", exc_info=True)
            await message.reply("❌ Ошибка при обработке рассылок")
    
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
        
        # Получаем базовый профиль
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
        
        # Получаем расширенную статистику
        advanced_stats = db.get_user_advanced_stats(user_id)
        
        # Формируем текст профиля
        text = f"🎯 <b>{name}, твой расширенный профиль:</b>\n\n"
        
        # Достижения (если есть)
        if advanced_stats.get('achievements'):
            achievements_text = " ".join(advanced_stats['achievements'])
            text += f"🏆 <b>Достижения:</b> {achievements_text}\n\n"
        
        # Серии дней
        current_streak = advanced_stats.get('current_streak', 0)
        max_streak = advanced_stats.get('max_consecutive_days', 0)
        streak_emoji = "🔥" if current_streak >= 3 else "📅"
        text += f"{streak_emoji} <b>Серия дней:</b>\n"
        text += f"  • Текущая: {current_streak} дней подряд\n"
        text += f"  • Рекорд: {max_streak} дней подряд\n\n"
        
        # Временные паттерны
        favorite_time = advanced_stats.get('favorite_time', 'нет данных')
        favorite_day = advanced_stats.get('favorite_day', 'нет данных')
        text += f"⏰ <b>Твои паттерны:</b>\n"
        text += f"  • Любимое время: {favorite_time}\n"
        text += f"  • Любимый день: {favorite_day}\n\n"
        
        # Состояние и темы
        text += f"👤 <b>Состояние & Темы:</b>\n"
        text += f"  • Настроение: {mood}\n"
        text += f"  • Тренд: {mood_trend}\n"
        text += f"  • Ключевые темы: {themes}\n\n"
        
        # Ресурс
        text += f"🌿 <b>Ресурс (последняя 'Карта дня'):</b>\n"
        text += f"  • В начале: {initial_resource}\n"
        text += f"  • В конце: {final_resource}\n"
        text += f"  • Способ восстановления: {recharge_method}\n\n"
        
        # Вечерняя рефлексия
        text += f"🌙 <b>Вечерняя Рефлексия:</b>\n"
        text += f"  • Последний итог: {last_reflection_date}\n"
        text += f"  • Всего итогов: {reflection_count}\n\n"
        
        # Расширенная статистика
        completion_rate = advanced_stats.get('completion_rate', 0)
        avg_depth = advanced_stats.get('avg_session_depth', 0)
        avg_sessions = advanced_stats.get('avg_sessions_per_day', 0)
        total_days = advanced_stats.get('total_unique_days', 0)
        
        text += f"📊 <b>Расширенная статистика:</b>\n"
        text += f"  • Карт вытянуто: {total_cards_drawn}\n"
        text += f"  • Ответов в диалогах: {response_count}\n"
        text += f"  • Дней активности: {total_days}\n"
        text += f"  • Среднее сессий/день: {avg_sessions}\n"
        text += f"  • Завершенность: {completion_rate}%\n"
        text += f"  • Глубина сессий: {avg_depth} шагов\n\n"
        
        # История использования
        first_day = advanced_stats.get('first_day')
        if first_day:
            text += f"📅 <b>История:</b>\n"
            text += f"  • Первый день: {first_day}\n"
            text += f"  • Профиль обновлен: {last_updated} МСК\n\n"
        
        text += "<i>💡 Этот профиль показывает твои паттерны использования и прогресс. Чем больше ты взаимодействуешь, тем точнее становятся данные!</i>"
        
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

def make_scenario_stats_handler(db, logger_service):
     async def wrapped_handler(message: types.Message):
         user_id = message.from_user.id
         if user_id != ADMIN_ID: await message.answer("Эта команда доступна только администратору."); return
         
         args = message.text.split()
         days = 7  # По умолчанию за последние 7 дней
         if len(args) > 1:
             try:
                 days = int(args[1])
                 if days <= 0 or days > 365:
                     await message.answer("Количество дней должно быть от 1 до 365.")
                     return
             except ValueError:
                 await message.answer("Количество дней должно быть числом.")
                 return
         
         # Получаем статистику по сценариям (оптимизировано)
         summary = db.get_admin_dashboard_summary(days)
         card_stats = summary['card_stats']
         reflection_stats = summary['evening_stats']
         
         if not card_stats and not reflection_stats:
             await message.answer(f"Нет данных о сценариях за последние {days} дней.")
             return
         
         text = f"📊 <b>Статистика сценариев за последние {days} дней:</b>\n\n"
         
         if card_stats:
             text += f"🎴 <b>Карта дня:</b>\n"
             text += f"  • Запусков: {card_stats['total_starts']}\n"
             text += f"  • Завершений: {card_stats['total_completions']}\n"
             text += f"  • Брошено: {card_stats['total_abandoned']}\n"
             text += f"  • Процент завершения: {card_stats['completion_rate']:.1f}%\n"
             text += f"  • Среднее шагов: {card_stats['avg_steps']}\n\n"
         
         if reflection_stats:
             text += f"🌙 <b>Вечерняя рефлексия:</b>\n"
             text += f"  • Запусков: {reflection_stats['total_starts']}\n"
             text += f"  • Завершений: {reflection_stats['total_completions']}\n"
             text += f"  • Брошено: {reflection_stats['total_abandoned']}\n"
             text += f"  • Процент завершения: {reflection_stats['completion_rate']:.1f}%\n"
             text += f"  • Среднее шагов: {reflection_stats['avg_steps']}\n\n"
         
         # Получаем статистику по шагам
         card_steps = db.get_scenario_step_stats('card_of_day', days)
         reflection_steps = db.get_scenario_step_stats('evening_reflection', days)
         
         # Детальные метрики для "Карта дня"
         if card_stats:
             text += f"🎴 <b>Детальные метрики 'Карта дня':</b>\n"
             
             # 1. Тип запроса
             try:
                 excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
                 excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
                 
                 cursor = db.conn.execute(f"""
                     SELECT step, COUNT(*) as count
                     FROM scenario_logs 
                     WHERE scenario = 'card_of_day' 
                     AND step IN ('text_request_provided', 'request_type_selected')
                     AND timestamp >= datetime('now', '-{days} days')
                     {excluded_condition}
                     GROUP BY step
                 """, list(excluded_users) if excluded_users else [])
                 request_stats = cursor.fetchall()
                 
                 text_requests = 0
                 mental_requests = 0
                 for stat in request_stats:
                     if stat['step'] == 'text_request_provided':
                         text_requests = stat['count']
                     elif stat['step'] == 'request_type_selected':
                         mental_requests = stat['count']
                 
                 total_requests = text_requests + mental_requests
                 if total_requests > 0:
                     text += f"  📝 Запросы: {text_requests} текстовых, {mental_requests} мысленных\n"
             except Exception as e:
                 text += f"  📝 Запросы: ошибка анализа\n"
             
             # 2. Выбор рефлексии с ИИ
             try:
                 cursor = db.conn.execute(f"""
                     SELECT metadata, COUNT(*) as count
                     FROM scenario_logs 
                     WHERE scenario = 'card_of_day' 
                     AND step = 'ai_reflection_choice'
                     AND timestamp >= datetime('now', '-{days} days')
                     {excluded_condition}
                     GROUP BY metadata
                 """, list(excluded_users) if excluded_users else [])
                 ai_choice_stats = cursor.fetchall()
                 
                 ai_yes = 0
                 ai_no = 0
                 for stat in ai_choice_stats:
                     try:
                         import json
                         meta = json.loads(stat['metadata'])
                         if meta.get('choice') == 'yes':
                             ai_yes = stat['count']
                         elif meta.get('choice') == 'no':
                             ai_no = stat['count']
                     except:
                         pass
                 
                 total_ai_choices = ai_yes + ai_no
                 if total_ai_choices > 0:
                     text += f"  🤖 ИИ-рефлексия: {ai_yes} выбрали, {ai_no} отказались\n"
             except Exception as e:
                 text += f"  🤖 ИИ-рефлексия: ошибка анализа\n"
             
             # 3. Ответы на ИИ-вопросы
             try:
                 cursor = db.conn.execute(f"""
                     SELECT step, COUNT(*) as count
                     FROM scenario_logs 
                     WHERE scenario = 'card_of_day' 
                     AND step IN ('ai_response_1_provided', 'ai_response_2_provided', 'ai_response_3_provided')
                     AND timestamp >= datetime('now', '-{days} days')
                     {excluded_condition}
                     GROUP BY step
                 """, list(excluded_users) if excluded_users else [])
                 ai_responses = cursor.fetchall()
                 
                 responses_1 = 0
                 responses_2 = 0
                 responses_3 = 0
                 for stat in ai_responses:
                     if stat['step'] == 'ai_response_1_provided':
                         responses_1 = stat['count']
                     elif stat['step'] == 'ai_response_2_provided':
                         responses_2 = stat['count']
                     elif stat['step'] == 'ai_response_3_provided':
                         responses_3 = stat['count']
                 
                 if responses_1 > 0:
                     text += f"  💬 ИИ-ответы: {responses_1}→{responses_2}→{responses_3}\n"
             except Exception as e:
                 text += f"  💬 ИИ-ответы: ошибка анализа\n"
             
             # 4. Изменение самочувствия
             try:
                 cursor = db.conn.execute(f"""
                     SELECT metadata, COUNT(*) as count
                     FROM scenario_logs 
                     WHERE scenario = 'card_of_day' 
                     AND step = 'mood_change_recorded'
                     AND timestamp >= datetime('now', '-{days} days')
                     {excluded_condition}
                     GROUP BY metadata
                 """, list(excluded_users) if excluded_users else [])
                 mood_stats = cursor.fetchall()
                 
                 mood_better = 0
                 mood_worse = 0
                 mood_same = 0
                 
                 for stat in mood_stats:
                     try:
                         import json
                         meta = json.loads(stat['metadata'])
                         change = meta.get('change_direction', 'unknown')
                         if change == 'better':
                             mood_better = stat['count']
                         elif change == 'worse':
                             mood_worse = stat['count']
                         elif change == 'same':
                             mood_same = stat['count']
                     except:
                         pass
                 
                 total_mood_changes = mood_better + mood_worse + mood_same
                 if total_mood_changes > 0:
                     text += f"  😊 Самочувствие: +{mood_better} -{mood_worse} ={mood_same}\n"
             except Exception as e:
                 text += f"  😊 Самочувствие: ошибка анализа\n"
             
             # 5. Оценка полезности
             try:
                 cursor = db.conn.execute(f"""
                     SELECT metadata, COUNT(*) as count
                     FROM scenario_logs 
                     WHERE scenario = 'card_of_day' 
                     AND step = 'usefulness_rating'
                     AND timestamp >= datetime('now', '-{days} days')
                     {excluded_condition}
                     GROUP BY metadata
                 """, list(excluded_users) if excluded_users else [])
                 rating_stats = cursor.fetchall()
                 
                 rating_helped = 0
                 rating_interesting = 0
                 rating_notdeep = 0
                 
                 for stat in rating_stats:
                     try:
                         import json
                         meta = json.loads(stat['metadata'])
                         rating = meta.get('rating', 'unknown')
                         if rating == 'helped':
                             rating_helped = stat['count']
                         elif rating == 'interesting':
                             rating_interesting = stat['count']
                         elif rating == 'notdeep':
                             rating_notdeep = stat['count']
                     except:
                         pass
                 
                 total_ratings = rating_helped + rating_interesting + rating_notdeep
                 if total_ratings > 0:
                     text += f"  ⭐ Оценка: {rating_helped}👍 {rating_interesting}🤔 {rating_notdeep}😕\n"
             except Exception as e:
                 text += f"  ⭐ Оценка: ошибка анализа\n"
             
             text += "\n"
         
         if card_steps:
             text += f"🎴 <b>Популярные шаги 'Карта дня':</b>\n"
             for step in card_steps[:5]:  # Топ-5 шагов
                 text += f"  • {step['step']}: {step['count']} раз\n"
             text += "\n"
         
         if reflection_steps:
             text += f"🌙 <b>Популярные шаги 'Вечерняя рефлексия':</b>\n"
             for step in reflection_steps[:5]:  # Топ-5 шагов
                 text += f"  • {step['step']}: {step['count']} раз\n"
         
         await message.answer(text)
         await logger_service.log_action(user_id, "scenario_stats_viewed", {"days": days})
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

def make_admin_handler(db: Database, logger_service: LoggingService):
    """Создает обработчик для команды /admin."""
    async def admin_handler(message: types.Message):
        user_id = message.from_user.id
        
        # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
        try:
            from config import ADMIN_IDS
            if str(user_id) not in ADMIN_IDS:
                logger.warning(f"BLOCKED: User {user_id} attempted to access admin panel via /admin")
                await message.answer("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.")
                return
        except ImportError as e:
            logger.error(f"CRITICAL: Failed to import ADMIN_IDS in admin handler: {e}")
            await message.answer("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ")
            return
        
        # Главное меню админки
        text = """📊 <b>АДМИН ПАНЕЛЬ</b>

Выберите раздел для просмотра метрик:"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔍 Главный дашборд", callback_data="admin_dashboard")],
            [types.InlineKeyboardButton(text="📈 Метрики удержания", callback_data="admin_retention")],
            [types.InlineKeyboardButton(text="🔄 Воронка 'Карта дня'", callback_data="admin_funnel")],
            [types.InlineKeyboardButton(text="💎 Метрики ценности", callback_data="admin_value")],
            [types.InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [types.InlineKeyboardButton(text="📋 Детальные логи", callback_data="admin_logs")],
            [types.InlineKeyboardButton(text="📝 Управление постами", callback_data="admin_posts")]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await logger_service.log_action(user_id, "admin_panel_opened", {})
    
    return admin_handler

def make_admin_callback_handler(db: Database, logger_service: LoggingService):
    """Создает обработчик для callback'ов админ-панели."""
    async def admin_callback_handler(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        
        # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
        try:
            from config import ADMIN_IDS
            if str(user_id) not in ADMIN_IDS:
                logger.warning(f"BLOCKED: User {user_id} attempted to access admin callback: {callback.data}")
                await callback.answer("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", show_alert=True)
                return
        except ImportError as e:
            logger.error(f"CRITICAL: Failed to import ADMIN_IDS in callback handler: {e}")
            await callback.answer("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", show_alert=True)
            return
        
        action = callback.data
        
        if action == "admin_dashboard":
            await show_admin_dashboard(callback.message, db, logger_service, user_id, 7)
        elif action.startswith("admin_dashboard_"):
            try:
                days = int(action.split("_")[-1])
                await show_admin_dashboard(callback.message, db, logger_service, user_id, days)
            except ValueError:
                await show_admin_dashboard(callback.message, db, logger_service, user_id, 7)
        elif action == "admin_retention":
            await show_admin_retention(callback.message, db, logger_service, user_id)
        elif action == "admin_funnel":
            await show_admin_funnel(callback.message, db, logger_service, user_id, 7)
        elif action.startswith("admin_funnel_"):
            try:
                days = int(action.split("_")[-1])
                await show_admin_funnel(callback.message, db, logger_service, user_id, days)
            except ValueError:
                await show_admin_funnel(callback.message, db, logger_service, user_id, 7)
        elif action == "admin_value":
            await show_admin_value(callback.message, db, logger_service, user_id, 7)
        elif action.startswith("admin_value_"):
            try:
                days = int(action.split("_")[-1])
                await show_admin_value(callback.message, db, logger_service, user_id, days)
            except ValueError:
                await show_admin_value(callback.message, db, logger_service, user_id, 7)
        elif action == "admin_users":
            await show_admin_users(callback.message, db, logger_service, user_id)
        elif action == "admin_users_list":
            await show_admin_users_list(callback.message, db, logger_service, user_id)
        elif action.startswith("admin_users_page_"):
            try:
                page = int(action.split("_")[-1])
                await show_admin_users_list(callback.message, db, logger_service, user_id, page)
            except ValueError:
                await show_admin_users_list(callback.message, db, logger_service, user_id)
        elif action == "admin_requests":
            await show_admin_requests(callback.message, db, logger_service, user_id)
        elif action == "admin_requests_full":
            await show_admin_requests_full(callback.message, db, logger_service, user_id)
        elif action == "admin_logs":
            await show_admin_logs(callback.message, db, logger_service, user_id)
        elif action == "admin_posts":
            await show_admin_posts(callback.message, db, logger_service, user_id)
        elif action == "admin_create_post":
            await start_post_creation(callback.message, db, logger_service, user_id)
        elif action == "admin_list_posts":
            await show_posts_list(callback.message, db, logger_service, user_id)
        elif action == "admin_list_mailings":
            await show_mailings_list(callback.message, db, logger_service, user_id)
        elif action == "admin_process_mailings":
            await process_mailings_now(callback.message, db, logger_service, user_id)
        elif action == "admin_back":
            await show_admin_main_menu(callback.message, db, logger_service, user_id)
        
        await callback.answer()
    
    return admin_callback_handler

async def show_admin_main_menu(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает главное меню админ-панели."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin main menu")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        text = """📊 <b>АДМИН ПАНЕЛЬ</b>

Выберите раздел для просмотра метрик:"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔍 Главный дашборд", callback_data="admin_dashboard")],
            [types.InlineKeyboardButton(text="📈 Метрики удержания", callback_data="admin_retention")],
            [types.InlineKeyboardButton(text="🔄 Воронка 'Карта дня'", callback_data="admin_funnel")],
            [types.InlineKeyboardButton(text="💎 Метрики ценности", callback_data="admin_value")],
            [types.InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [types.InlineKeyboardButton(text="📋 Детальные логи", callback_data="admin_logs")],
            [types.InlineKeyboardButton(text="📝 Управление постами", callback_data="admin_posts")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await logger_service.log_action(user_id, "admin_main_menu_viewed", {})
    except Exception as e:
        logger.error(f"Error showing admin main menu: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке меню администратора"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

async def show_admin_dashboard(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, days: int = 7):
    """Показывает главный дашборд с ключевыми метриками."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin dashboard")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем сводку метрик (оптимизировано - все данные в одном запросе)
        summary = db.get_admin_dashboard_summary(days)
        
        if not summary:
            text = "❌ Ошибка при получении данных дашборда"
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_dashboard")],
                [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
            ])
            await message.edit_text(text, reply_markup=keyboard)
            return
        
        # Определяем период для отображения
        period_text = "Сегодня" if days == 1 else f"{days} дней"
        
        # Используем данные из summary (устраняем дублирование)
        dau_metrics = summary['dau']
        retention_metrics = summary['retention']
        
        # Формируем текст дашборда
        text = f"""🔍 <b>ГЛАВНЫЙ ДАШБОРД</b> ({period_text})

👥 <b>DAU:</b>
• Сегодня: {dau_metrics['dau_today']}
• Вчера: {dau_metrics['dau_yesterday']}
• 7 дней: {dau_metrics['dau_7']}
• 30 дней: {dau_metrics['dau_30']}

📈 <b>Retention:</b>
• D1: {retention_metrics.get('d1_retention', 0):.1f}%
• D7: {retention_metrics.get('d7_retention', 0):.1f}%

🔄 <b>Карта дня:</b>
• Запусков: {summary['card_stats']['total_starts']}
• Завершено: {summary['card_stats']['total_completions']} ({summary['card_stats']['completion_rate']:.1f}%)
• Среднее шагов: {summary['card_stats']['avg_steps']}

🌙 <b>Итог дня:</b>
• Запусков: {summary['evening_stats']['total_starts']}
• Завершено: {summary['evening_stats']['total_completions']} ({summary['evening_stats']['completion_rate']:.1f}%)

💎 <b>Ценность:</b>
• Положительная динамика ресурса: {summary['value']['resource_lift']['positive_pct']}%
• Feedback Score: {summary['value']['feedback_score']}%"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Сегодня", callback_data="admin_dashboard_1"),
                types.InlineKeyboardButton(text="7 дней", callback_data="admin_dashboard_7"),
                types.InlineKeyboardButton(text="30 дней", callback_data="admin_dashboard_30")
            ],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_dashboard_{days}")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_dashboard_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin dashboard: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке дашборда"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

async def show_admin_retention(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает метрики удержания."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin retention")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем все метрики одним запросом (оптимизировано)
        summary = db.get_admin_dashboard_summary(7)
        retention = summary['retention']
        dau = summary['dau']
        
        text = f"""📈 <b>МЕТРИКИ УДЕРЖАНИЯ</b> (за 7 дней)

🎯 <b>D1 Retention:</b>
• {retention['d1_retention']}% ({retention['d1_returned_users']}/{retention['d1_total_users']})
• Цель: >30%

📅 <b>D7 Retention:</b>
• {retention['d7_retention']}% ({retention['d7_returned_users']}/{retention['d7_total_users']})
• Цель: >25%

👥 <b>DAU:</b>
• Вчера: {dau['dau_yesterday']}
• Среднее за 7 дней: {dau['dau_7']}
• Среднее за 30 дней: {dau['dau_30']}"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_retention")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_retention_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin retention: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке метрик удержания"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

async def show_admin_funnel(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, days: int = 7):
    """Показывает воронку сценария 'Карта дня'."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin funnel")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем все метрики одним запросом (оптимизировано)
        summary = db.get_admin_dashboard_summary(days)
        funnel = summary['funnel']
        
        period_text = {
            1: "сегодня",
            7: "7 дней", 
            30: "30 дней"
        }.get(days, f"{days} дней")
        
        text = f"""🔄 <b>ВОРОНКА 'КАРТА ДНЯ'</b> (за {period_text})

📊 <b>Completion Rate: {funnel['completion_rate']}%</b>
Цель: >60%

📈 <b>Детальная воронка:</b>
1️⃣ Начали сессию: {funnel['step1']['count']} ({funnel['step1']['pct']}%)
2️⃣ Выбрали ресурс: {funnel['step2']['count']} ({funnel['step2']['pct']}%)
3️⃣ Выбрали тип запроса: {funnel['step3']['count']} ({funnel['step3']['pct']}%)
4️⃣ Вытянули карту: {funnel['step4']['count']} ({funnel['step4']['pct']}%)
5️⃣ Написали ассоциацию: {funnel['step5']['count']} ({funnel['step5']['pct']}%)
6️⃣ Выбрали углубляющий диалог: {funnel['step6']['count']} ({funnel['step6']['pct']}%)
7️⃣ Завершили сценарий: {funnel['step7']['count']} ({funnel['step7']['pct']}%)"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📅 Сегодня", callback_data="admin_funnel_1")],
            [types.InlineKeyboardButton(text="📅 7 дней", callback_data="admin_funnel_7")],
            [types.InlineKeyboardButton(text="📅 30 дней", callback_data="admin_funnel_30")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_funnel_{days}")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_funnel_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin funnel: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке воронки"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

async def show_admin_value(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, days: int = 7):
    """Показывает метрики ценности."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin value metrics")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем все метрики одним запросом (оптимизировано)
        summary = db.get_admin_dashboard_summary(days)
        value = summary['value']
        
        # Определяем период для отображения
        period_text = "Сегодня" if days == 1 else f"{days} дней"
        
        text = f"""💎 <b>МЕТРИКИ ЦЕННОСТИ</b> ({period_text})

📈 <b>Resource Lift:</b>
• Положительная динамика: {value['resource_lift']['positive_pct']}%
• Отрицательная динамика: {value['resource_lift']['negative_pct']}%
• Всего сессий: {value['resource_lift']['total_sessions']}

👍 <b>Feedback Score:</b>
• Позитивные отзывы: {value['feedback_score']}%
• Всего отзывов: {value['total_feedback']}
• Цель: ≥50%"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Сегодня", callback_data="admin_value_1"),
                types.InlineKeyboardButton(text="7 дней", callback_data="admin_value_7"),
                types.InlineKeyboardButton(text="30 дней", callback_data="admin_value_30")
            ],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_value_{days}")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_value_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin value: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке метрик ценности"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

async def show_admin_users(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает меню управления пользователями."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin users")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем базовую статистику пользователей
        all_users = db.get_all_users()
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        filtered_users = [uid for uid in all_users if uid not in excluded_users]
        total_users = len(filtered_users)
        
        # Активные пользователи за последние 7 дней
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
        
        cursor = db.conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as active_users
            FROM user_scenarios 
            WHERE started_at >= datetime('now', '-7 days')
            {excluded_condition}
        """, list(excluded_users) if excluded_users else [])
        active_users = cursor.fetchone()['active_users']
        
        activity_pct = (active_users/total_users*100) if total_users > 0 else 0
        
        # Получаем статистику по новым пользователям
        new_users_stats = db.get_new_users_stats(7)
        
        text = f"""👥 <b>ПОЛЬЗОВАТЕЛИ</b>

📊 <b>Общая статистика:</b>
• Всего пользователей: {total_users}
• Активных за 7 дней: {active_users}
• Процент активности: {activity_pct:.1f}%

🆕 <b>Новые пользователи (7 дней):</b>
• Всего новых: {new_users_stats['total_new_users']}
• С меткой first_seen: {new_users_stats['users_with_first_seen']}
• Без метки: {new_users_stats['users_without_first_seen']}

🔧 <b>Действия:</b>
• /users - список всех пользователей
• /user_profile [ID] - профиль пользователя"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users_list")],
            [types.InlineKeyboardButton(text="💬 Запросы пользователей", callback_data="admin_requests")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_users_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin users: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке данных пользователей"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

async def show_admin_users_list(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, page: int = 0):
    """Показывает список всех пользователей."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin users list")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем всех пользователей
        all_users = db.get_all_users()
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        filtered_users = [uid for uid in all_users if uid not in excluded_users]
        
        if not filtered_users:
            text = "👥 <b>СПИСОК ПОЛЬЗОВАТЕЛЕЙ</b>\n\nПока нет пользователей в базе данных."
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users_list")],
                [types.InlineKeyboardButton(text="← Назад", callback_data="admin_users")]
            ])
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            return
        
        # Формируем список пользователей
        text = f"👥 <b>СПИСОК ПОЛЬЗОВАТЕЛЕЙ</b> ({len(filtered_users)})\n\n"
        
        # Получаем данные пользователей
        user_list = []
        for uid in filtered_users:
            user_data = db.get_user(uid)
            if user_data:
                name = user_data.get("name", "Без имени")
                username = user_data.get("username", "")
                last_action_time = "Нет действий"
                
                # Получаем последнее действие
                user_actions = db.get_actions(uid)
                if user_actions:
                    last_action = user_actions[-1]
                    raw_timestamp = last_action.get("timestamp")
                    try:
                        from datetime import datetime
                        if isinstance(raw_timestamp, datetime):
                            last_action_dt = raw_timestamp.astimezone(TIMEZONE) if raw_timestamp.tzinfo else raw_timestamp
                            last_action_time = last_action_dt.strftime("%Y-%m-%d %H:%M")
                        elif isinstance(raw_timestamp, str):
                            last_action_dt = datetime.fromisoformat(raw_timestamp.replace('Z', '+00:00')).astimezone(TIMEZONE)
                            last_action_time = last_action_dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        last_action_time = "Ошибка даты"
                
                username_display = f"@{username}" if username else "без username"
                user_list.append({
                    'uid': uid,
                    'name': name,
                    'username': username_display,
                    'last_action_time': last_action_time
                })
        
        # Сортируем по времени последнего действия
        try:
            user_list.sort(key=lambda x: x['last_action_time'], reverse=True)
        except Exception as sort_err:
            logger.warning(f"Error sorting user list by timestamp: {sort_err}. List may be unsorted.")
        
        # Формируем текст списка с ограничением длины
        max_users_per_page = 15  # Максимум пользователей на страницу
        current_page = page
        start_idx = current_page * max_users_per_page
        end_idx = start_idx + max_users_per_page
        
        # Показываем только часть пользователей для избежания MESSAGE_TOO_LONG
        visible_users = user_list[start_idx:end_idx]
        
        for i, user in enumerate(visible_users, start_idx + 1):
            text += f"{i}. <code>{user['uid']}</code> | {user['username']} | {user['name']}\n"
            text += f"   Последнее действие: {user['last_action_time']}\n\n"
        
        # Добавляем информацию о пагинации
        total_pages = (len(user_list) + max_users_per_page - 1) // max_users_per_page
        current_page_display = current_page + 1
        
        if total_pages > 1:
            text += f"\n📄 Страница {current_page_display} из {total_pages}\n"
            text += f"Показано {len(visible_users)} из {len(user_list)} пользователей"
        else:
            text += f"\n📄 Всего пользователей: {len(user_list)}"
        
        # Создаем клавиатуру с навигацией
        keyboard_buttons = []
        
        # Кнопки навигации
        if total_pages > 1:
            nav_buttons = []
            if current_page > 0:
                nav_buttons.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_page_{current_page-1}"))
            nav_buttons.append(types.InlineKeyboardButton(text=f"{current_page_display}/{total_pages}", callback_data="admin_users_list"))
            if current_page < total_pages - 1:
                nav_buttons.append(types.InlineKeyboardButton(text="➡️", callback_data=f"admin_users_page_{current_page+1}"))
            keyboard_buttons.append(nav_buttons)
        
        # Основные кнопки
        keyboard_buttons.extend([
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users_list")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_users")]
        ])
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_users_list_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin users list: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке списка пользователей"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_users")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

async def show_admin_requests(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает запросы пользователей к картам."""
    # Проверяем права администратора
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("❌ У вас нет доступа к этой функции.", parse_mode="HTML")
            return
    except ImportError as e:
        logger.error(f"Failed to import ADMIN_IDS: {e}")
        await message.edit_text("❌ Ошибка проверки прав доступа.", parse_mode="HTML")
        return
    
    try:
        # Получаем статистику запросов
        requests_stats = db.get_user_requests_stats(7, user_id)
        requests_sample = db.get_user_requests_sample(5, 7, user_id)
        
        text = f"""💬 <b>ЗАПРОСЫ ПОЛЬЗОВАТЕЛЕЙ</b> (за 7 дней)

📊 <b>Статистика:</b>
• Всего запросов: {requests_stats.get('total_requests', 0)}
• Уникальных пользователей: {requests_stats.get('unique_users', 0)}
• Средняя длина: {requests_stats.get('avg_length', 0)} символов
• Минимум: {requests_stats.get('min_length', 0)} символов
• Максимум: {requests_stats.get('max_length', 0)} символов

📝 <b>Последние запросы:</b>"""
        
        if requests_sample:
            for i, req in enumerate(requests_sample, 1):
                user_id = req.get('user_id', 'N/A')
                user_name = req.get('user_name', 'Аноним')
                username = req.get('user_username', '')
                timestamp = req.get('timestamp', '')
                request_text = req['request_text']
                
                # Форматируем дату
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_date = timestamp
                
                # Форматируем username
                username_display = f"@{username}" if username else "без username"
                
                # Показываем полный текст без обрезки
                display_text = request_text
                
                text += f"\n{i}. <b>{formatted_date}</b>"
                text += f"\n   <i>«{display_text}»</i>"
                text += f"\n   👤 ID: {user_id} | {user_name} | {username_display}"
                text += f"\n"
        else:
            text += "\nПока нет запросов"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📋 Все запросы", callback_data="admin_requests_full")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_requests")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_users")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_requests_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin requests: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке запросов"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_users")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

async def show_admin_requests_full(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает полные запросы пользователей с детальной информацией."""
    # Проверяем права администратора
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("❌ У вас нет доступа к этой функции.", parse_mode="HTML")
            return
    except ImportError as e:
        logger.error(f"Failed to import ADMIN_IDS: {e}")
        await message.edit_text("❌ Ошибка проверки прав доступа.", parse_mode="HTML")
        return
    
    try:
        # Получаем больше запросов для детального просмотра
        requests_sample = db.get_user_requests_sample(20, 7, user_id)
        
        text = f"""📋 <b>ПОЛНЫЕ ЗАПРОСЫ ПОЛЬЗОВАТЕЛЕЙ</b> (за 7 дней)

📊 <b>Всего запросов:</b> {len(requests_sample)}

📝 <b>Детальная информация:</b>"""
        
        if requests_sample:
            for i, req in enumerate(requests_sample, 1):
                user_id = req.get('user_id', 'N/A')
                user_name = req.get('user_name', 'Аноним')
                username = req.get('user_username', '')
                timestamp = req.get('timestamp', '')
                request_text = req['request_text']
                card_number = req.get('card_number', 'N/A')
                
                # Форматируем дату
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_date = timestamp
                
                # Форматируем username
                username_display = f"@{username}" if username else "без username"
                
                text += f"\n\n<b>{i}. {formatted_date}</b>"
                text += f"\n🎴 Карта: {card_number}"
                text += f"\n👤 <b>Пользователь:</b>"
                text += f"\n   • ID: <code>{user_id}</code>"
                text += f"\n   • Имя: {user_name}"
                text += f"\n   • Username: {username_display}"
                text += f"\n💬 <b>Запрос:</b>"
                text += f"\n   «{request_text}»"
                text += f"\n{'─' * 40}"
        else:
            text += "\n\nПока нет запросов"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📊 Краткая статистика", callback_data="admin_requests")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_requests_full")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_users")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_requests_full_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin requests full: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке полных запросов"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_users")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

async def show_admin_logs(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает детальные логи."""
    # Проверяем права администратора
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("❌ У вас нет доступа к этой функции.", parse_mode="HTML")
            return
    except ImportError as e:
        logger.error(f"Failed to import ADMIN_IDS: {e}")
        await message.edit_text("❌ Ошибка проверки прав доступа.", parse_mode="HTML")
        return
    
    try:
        # Получаем последние логи
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
        
        cursor = db.conn.execute(f"""
            SELECT scenario, step, COUNT(*) as count
            FROM scenario_logs 
            WHERE timestamp >= datetime('now', '-7 days')
            {excluded_condition}
            GROUP BY scenario, step
            ORDER BY count DESC
            LIMIT 10
        """, list(excluded_users) if excluded_users else [])
        
        logs = cursor.fetchall()
        
        text = """📋 <b>ДЕТАЛЬНЫЕ ЛОГИ</b> (за 7 дней)

🔍 <b>Топ-10 шагов по частоте:</b>"""
        
        for i, log in enumerate(logs, 1):
            text += f"\n{i}. {log['scenario']} → {log['step']}: {log['count']}"
        
        text += "\n\n🔧 <b>Действия:</b>\n• /scenario_stats - статистика сценариев\n• /logs - все логи"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📊 Статистика сценариев", callback_data="admin_scenario_stats")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_logs")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await logger_service.log_action(user_id, "admin_logs_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin logs: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке логов"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        await message.edit_text(text, reply_markup=keyboard)

async def show_admin_posts(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает меню управления постами."""
    # Проверяем права администратора
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("❌ У вас нет доступа к этой функции.", parse_mode="HTML")
            return
    except ImportError as e:
        logger.error(f"Failed to import ADMIN_IDS: {e}")
        await message.edit_text("❌ Ошибка проверки прав доступа.", parse_mode="HTML")
        return
    
    try:
        # Получаем PostManager из диспетчера
        post_manager = None
        scheduler = None
        
        # Пытаемся получить из диспетчера
        if hasattr(message.bot, '_dispatcher') and message.bot._dispatcher:
            post_manager = message.bot._dispatcher.get("post_manager")
            scheduler = message.bot._dispatcher.get("scheduler")
        
        # Если не получилось, создаем временный
        if not post_manager:
            from modules.post_management import PostManager
            post_manager = PostManager(db, message.bot, logger_service)
        
        # Получаем последние посты и рассылки
        posts = post_manager.get_all_posts(limit=5)
        mailings = post_manager.get_all_mailings(limit=5)
        
        text = "📝 <b>УПРАВЛЕНИЕ ПОСТАМИ</b>\n\n"
        
        # Статистика
        text += f"📊 <b>Статистика:</b>\n"
        text += f"• Постов: {len(posts)}\n"
        text += f"• Рассылок: {len(mailings)}\n\n"
        
        # Последние посты
        if posts:
            text += "📝 <b>Последние посты:</b>\n"
            for post in posts[:3]:
                preview = post_manager.format_post_preview(post, max_length=50)
                text += f"• {preview}\n\n"
        else:
            text += "📝 <b>Постов пока нет</b>\n\n"
        
        # Последние рассылки
        if mailings:
            text += "📤 <b>Последние рассылки:</b>\n"
            for mailing in mailings[:3]:
                preview = post_manager.format_mailing_preview(mailing)
                text += f"• {preview}\n\n"
        else:
            text += "📤 <b>Рассылок пока нет</b>\n\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Создать пост", callback_data="admin_create_post")],
            [types.InlineKeyboardButton(text="📋 Список постов", callback_data="admin_list_posts")],
            [types.InlineKeyboardButton(text="📤 Список рассылок", callback_data="admin_list_mailings")],
            [types.InlineKeyboardButton(text="🔄 Обработать рассылки", callback_data="admin_process_mailings")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing admin posts: {e}", exc_info=True)
        text = "❌ Ошибка при получении данных о постах"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_posts")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        await message.edit_text(text, reply_markup=keyboard)

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ПОСТАМИ ---

async def start_post_creation(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Начинает процесс создания поста."""
    try:
        text = """📝 <b>СОЗДАНИЕ НОВОГО ПОСТА</b>

Введите заголовок поста (максимум 100 символов):"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="❌ Отмена", callback_data="admin_posts")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
        # Логируем действие
        await logger_service.log_action(user_id, "admin_post_creation_started", {})
        
    except Exception as e:
        logger.error(f"Error starting post creation: {e}", exc_info=True)
        await message.answer("❌ Ошибка при создании поста")

async def show_posts_list(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает список всех постов."""
    try:
        # Получаем PostManager
        post_manager = None
        if hasattr(message.bot, '_dispatcher') and message.bot._dispatcher:
            post_manager = message.bot._dispatcher.get("post_manager")
        
        if not post_manager:
            from modules.post_management import PostManager
            post_manager = PostManager(db, message.bot, logger_service)
        
        posts = post_manager.get_all_posts(limit=20)
        
        if not posts:
            text = "📝 <b>СПИСОК ПОСТОВ</b>\n\nПостов пока нет."
        else:
            text = "📝 <b>СПИСОК ПОСТОВ</b>\n\n"
            for i, post in enumerate(posts, 1):
                preview = post_manager.format_post_preview(post, max_length=80)
                text += f"{i}. {preview}\n\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_posts")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing posts list: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении списка постов")

async def show_mailings_list(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает список всех рассылок."""
    try:
        # Получаем PostManager
        post_manager = None
        if hasattr(message.bot, '_dispatcher') and message.bot._dispatcher:
            post_manager = message.bot._dispatcher.get("post_manager")
        
        if not post_manager:
            from modules.post_management import PostManager
            post_manager = PostManager(db, message.bot, logger_service)
        
        mailings = post_manager.get_all_mailings(limit=20)
        
        if not mailings:
            text = "📤 <b>СПИСОК РАССЫЛОК</b>\n\nРассылок пока нет."
        else:
            text = "📤 <b>СПИСОК РАССЫЛОК</b>\n\n"
            for i, mailing in enumerate(mailings, 1):
                preview = post_manager.format_mailing_preview(mailing)
                stats = post_manager.get_mailing_stats(mailing['id'])
                text += f"{i}. {preview}\n"
                text += f"📊 Отправлено: {stats['sent_count']}, Ошибок: {stats['failed_count']}\n\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_posts")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing mailings list: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении списка рассылок")

async def process_mailings_now(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Принудительно обрабатывает все ожидающие рассылки."""
    try:
        # Получаем Scheduler из диспетчера
        scheduler = None
        try:
            # В aiogram 3.x диспетчер доступен через message.bot._dispatcher
            if hasattr(message.bot, '_dispatcher'):
                scheduler = message.bot._dispatcher.get("scheduler")
        except:
            pass
        
        if not scheduler:
            # Попробуем создать новый планировщик
            try:
                from modules.post_management import PostManager
                from modules.scheduler import MailingScheduler
                post_manager = PostManager(db, message.bot, logger_service)
                scheduler = MailingScheduler(post_manager, check_interval=60)
                await scheduler.start()
            except Exception as e:
                logger.error(f"Failed to create scheduler: {e}")
                await message.answer("❌ Планировщик недоступен")
                return
        
        # Показываем сообщение о начале обработки
        await message.edit_text("🔄 Обрабатываю рассылки...", parse_mode="HTML")
        
        # Обрабатываем рассылки
        result = await scheduler.process_mailings_now()
        
        # Показываем результат
        text = f"""✅ <b>ОБРАБОТКА РАССЫЛОК ЗАВЕРШЕНА</b>

📊 <b>Результат:</b>
• Обработано рассылок: {result['processed']}
• Успешно отправлено: {result['total_sent']}
• Ошибок: {result['total_failed']}"""
        
        if 'error' in result:
            text += f"\n\n❌ <b>Ошибка:</b> {result['error']}"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_posts")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error processing mailings: {e}", exc_info=True)
        await message.answer("❌ Ошибка при обработке рассылок")

async def handle_admin_text_input(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Обрабатывает текстовый ввод для админ-функций."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin text input")
            await message.answer("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS in text input handler: {e}")
        await message.answer("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ")
        return
    
    try:
        text = message.text.strip()
        
        # Простой интерфейс создания поста
        if "|" in text:
            # Формат: "Заголовок | Содержание"
            parts = text.split("|", 1)
            if len(parts) == 2:
                title = parts[0].strip()
                content = parts[1].strip()
                
                if not title or not content:
                    await message.reply("❌ Заголовок и содержание не могут быть пустыми.\n\nИспользуйте формат:\n<code>Заголовок | Содержание</code>", parse_mode="HTML")
                    return
                
                # Валидируем данные
                from modules.post_management import PostManager
                post_manager = PostManager(db, message.bot, logger_service)
                validation = post_manager.validate_post_data(title, content)
                
                if not validation['valid']:
                    errors = "\n".join([f"• {error}" for error in validation['errors']])
                    await message.reply(f"❌ <b>Ошибки валидации:</b>\n{errors}", parse_mode="HTML")
                    return
                
                # Формируем контент с жирным заголовком
                formatted_content = f"<b>{title}</b>\n\n{content}"
                
                # Создаем пост
                post_id = post_manager.create_post(title, formatted_content, user_id)
                
                await message.reply(f"""✅ <b>Пост создан успешно!</b>

📝 <b>Заголовок:</b> {title}
📄 <b>Содержание:</b> {content[:100]}{'...' if len(content) > 100 else ''}
🆔 <b>ID поста:</b> {post_id}

<b>Отправка поста:</b>
• <code>/send_post {post_id} all</code> - отправить всем сейчас
• <code>/send_post {post_id} all 2024-12-31 15:30</code> - отправить всем в указанное время
• <code>/send_post {post_id} 123456,789012</code> - отправить конкретным пользователям сейчас
• <code>/send_post {post_id} 123456,789012 2024-12-31 15:30</code> - отправить конкретным пользователям в указанное время

Формат времени: <code>YYYY-MM-DD HH:MM</code> (московское время)""", parse_mode="HTML")
                
                await logger_service.log_action(user_id, "post_created_simple", {"post_id": post_id, "title": title})
                return
        
        # Если не распознали формат, показываем инструкцию
        await message.reply("""📝 <b>СОЗДАНИЕ ПОСТА</b>

Для создания поста используйте формат:
<code>Заголовок | Содержание</code>

Пример:
<code>Новости бота | Привет! У нас обновления. Теперь бот стал еще лучше!</code>

Или используйте команду:
<code>/create_post "Заголовок" "Содержание"</code>""", parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error handling admin text input: {e}", exc_info=True)
        await message.reply("❌ Ошибка при создании поста")

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
    scenario_stats_handler = make_scenario_stats_handler(db, logger_service)
    broadcast_handler = make_broadcast_handler(db, logger_service)
    create_post_handler = make_create_post_handler(db, logger_service)
    list_posts_handler = make_list_posts_handler(db, logger_service)
    send_post_handler = make_send_post_handler(db, logger_service)
    process_mailings_handler = make_process_mailings_handler(db, logger_service)
    admin_handler = make_admin_handler(db, logger_service)
    admin_callback_handler = make_admin_callback_handler(db, logger_service)

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
    dp.message.register(scenario_stats_handler, Command("scenario_stats"), StateFilter("*"))
    dp.message.register(broadcast_handler, Command("broadcast"), StateFilter("*"))
    dp.message.register(create_post_handler, Command("create_post"), StateFilter("*"))
    dp.message.register(list_posts_handler, Command("list_posts"), StateFilter("*"))
    dp.message.register(send_post_handler, Command("send_post"), StateFilter("*"))
    dp.message.register(process_mailings_handler, Command("process_mailings"), StateFilter("*"))
    dp.message.register(admin_handler, Command("admin"), StateFilter("*"))
    
    # Регистрируем callback-обработчики для админ-панели
    dp.callback_query.register(admin_callback_handler, F.data.startswith("admin_"))

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
    dp.callback_query.register(partial(process_emotion_choice, db=db, logger_service=logging_service), UserState.waiting_for_emotion_choice, F.data.startswith("emotion_"))
    dp.message.register(partial(process_custom_response, db=db, logger_service=logging_service), UserState.waiting_for_custom_response)
    dp.callback_query.register(partial(process_exploration_choice_callback, db=db, logger_service=logging_service), UserState.waiting_for_exploration_choice, F.data.startswith("explore_"))
    dp.message.register(partial(process_first_grok_response, db=db, logger_service=logging_service), UserState.waiting_for_first_grok_response)
    dp.message.register(partial(process_second_grok_response, db=db, logger_service=logging_service), UserState.waiting_for_second_grok_response)
    dp.message.register(partial(process_third_grok_response, db=db, logger_service=logging_service), UserState.waiting_for_third_grok_response)
    dp.callback_query.register(partial(process_final_resource_callback, db=db, logger_service=logging_service), UserState.waiting_for_final_resource, F.data.startswith("resource_"))
    dp.message.register(partial(process_recharge_method, db=db, logger_service=logging_service), UserState.waiting_for_recharge_method)
    dp.callback_query.register(partial(process_card_feedback, db=db, logger_service=logging_service), F.data.startswith("feedback_v2_"), StateFilter("*"))
    dp.callback_query.register(partial(process_recharge_method_choice, db=db, logger_service=logging_service), StateFilter(UserState.waiting_for_recharge_method_choice))

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
        UserState.waiting_for_custom_response,
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
        
        # Проверяем, является ли пользователь админом
        try:
            from config import ADMIN_IDS
            if str(user_id) in ADMIN_IDS and message.text and not message.text.startswith('/'):
                logger.info(f"DEBUG: Processing admin text message '{message.text}' from user {user_id} in state {current_state_str}")
                await handle_admin_text_input(message, db, logger_service, user_id)
                return
        except ImportError as e:
            logger.error(f"DEBUG: ImportError for ADMIN_IDS: {e}")
        
        logger.warning(f"Unknown message '{message.text}' from user {user_id} in state {current_state_str}")
        
        fsm_data = await state.get_data()
        session_id = fsm_data.get("session_id", "unknown_abandon")

        state_to_event_map = {
            UserState.waiting_for_initial_resource: "flow_abandoned_at_initial_resource",
            UserState.waiting_for_request_type_choice: "flow_abandoned_at_request_type",
            UserState.waiting_for_request_text_input: "flow_abandoned_at_request_input",
            UserState.waiting_for_initial_response: "flow_abandoned_at_initial_response",
            UserState.waiting_for_emotion_choice: "flow_abandoned_at_emotion_choice",
            UserState.waiting_for_custom_response: "flow_abandoned_at_custom_response",
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



    @dp.callback_query(StateFilter("*"))
    async def handle_unknown_callback_state(callback: types.CallbackQuery, state: FSMContext):
        logger.warning(f"Unknown callback '{callback.data}' from user {callback.from_user.id} in state {await state.get_state()}")
        await callback.answer("Это действие сейчас недоступно.", show_alert=True)

    @dp.callback_query()
    async def handle_unknown_callback_no_state(callback: types.CallbackQuery):
        logger.warning(f"Unknown callback '{callback.data}' from user {callback.from_user.id} with no state.")
        await callback.answer("Неизвестное действие.", show_alert=True)

    # Обработчик для сообщений без состояния (включая админские)
    @dp.message()
    async def handle_unknown_message_no_state(message: types.Message):
        user_id = message.from_user.id
        
        # Проверяем, является ли пользователь админом
        try:
            from config import ADMIN_IDS
            if str(user_id) in ADMIN_IDS and message.text and not message.text.startswith('/'):
                logger.info(f"DEBUG: Processing admin text message '{message.text}' from user {user_id} (no state)")
                await handle_admin_text_input(message, db, logger_service, user_id)
                return
        except ImportError as e:
            logger.error(f"DEBUG: ImportError for ADMIN_IDS: {e}")
        
        logger.warning(f"Unknown message '{message.text}' from user {user_id} with no state.")

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
    
    # Добавляем админские команды
    admin_commands = [
        types.BotCommand(command="create_post", description="📝 Создать пост (админ)"),
        types.BotCommand(command="list_posts", description="📋 Список постов (админ)"),
        types.BotCommand(command="send_post", description="📤 Отправить пост (админ)"),
        types.BotCommand(command="process_mailings", description="🔄 Обработать рассылки (админ)")
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands set successfully.")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

    # Инициализация PostManager и Scheduler
    post_manager = PostManager(db, bot, logging_service)
    scheduler = MailingScheduler(post_manager, check_interval=60)
    
    # Инициализация планировщика еженедельного анализа рефлексий
    reflection_scheduler = ReflectionAnalysisScheduler(bot, db, check_interval=3600)  # Проверяем каждый час
    
    # Инициализируем данные в диспетчере с проверками
    try:
        # Убеждаемся, что workflow_data существует
        if not hasattr(dp, 'workflow_data') or dp.workflow_data is None:
            dp.workflow_data = {}
        
        dp["db"] = db
        dp["logger_service"] = logging_service
        dp["user_manager"] = user_manager
        dp["post_manager"] = post_manager
        dp["scheduler"] = scheduler
        logger.info("Dispatcher data initialized successfully")
    except Exception as init_err:
        logger.error(f"Error initializing dispatcher data: {init_err}")
        print(f"Warning: Dispatcher data initialization failed: {init_err}")
    
    # Регистрируем middleware для проверки подписки
    subscription_middleware = SubscriptionMiddleware()
    dp.message.middleware(subscription_middleware)
    dp.callback_query.middleware(subscription_middleware)
    logger.info("Subscription middleware registered successfully")
    
    register_handlers(dp, db, logging_service, user_manager)
    
    # Запускаем планировщик рассылок
    await scheduler.start()
    logger.info("Mailing scheduler started.")
    
    # Запускаем планировщик еженедельного анализа рефлексий
    await reflection_scheduler.start()
    logger.info("Reflection analysis scheduler started.")
    
    reminder_task = asyncio.create_task(notifier.check_reminders())
    logger.info("Reminder check task scheduled.")
    logger.info("Starting polling...")
    print("Bot is starting polling...")
    try:
        # Проверяем, что все необходимые данные инициализированы
        if not hasattr(dp, 'workflow_data') or dp.workflow_data is None:
            dp.workflow_data = {}
        
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.critical(f"Polling failed: {e}", exc_info=True)
        print(f"CRITICAL: Polling failed: {e}")
    finally:
        logger.info("Stopping bot...")
        print("Bot is stopping...")
        
        # Останавливаем планировщик
        try:
            if 'scheduler' in dp and dp["scheduler"]:
                await dp["scheduler"].stop()
                logger.info("Mailing scheduler stopped.")
        except Exception as scheduler_err:
            logger.error(f"Error stopping scheduler: {scheduler_err}")
        
        # Останавливаем планировщик еженедельного анализа
        try:
            await reflection_scheduler.stop()
            logger.info("Reflection analysis scheduler stopped.")
        except Exception as reflection_scheduler_err:
            logger.error(f"Error stopping reflection analysis scheduler: {reflection_scheduler_err}")
        
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            logger.info("Reminder task cancelled successfully.")
        except Exception as reminder_err:
            logger.error(f"Error cancelling reminder task: {reminder_err}")
            
        if db and db.conn:
            try:
                db.close()
            except Exception as db_close_err:
                logger.error(f"Error closing database connection: {db_close_err}")
        logger.info("Bot session cleanup (handled by aiogram).")
        print("Bot stopped.")

# --- КОНЕЦ ФУНКЦИИ ---

# --- НОВАЯ ФУНКЦИЯ: Отправка еженедельного анализа ---
async def send_weekly_analysis(user_id: int, db: Database, bot: Bot):
    """
    Отправляет еженедельный анализ рефлексий пользователю.
    
    Args:
        user_id: ID пользователя
        db: Экземпляр базы данных
        bot: Экземпляр бота
    """
    try:
        # Получаем рефлексии за неделю
        reflections = db.get_reflections_for_last_n_days(user_id, 7)
        
        if len(reflections) >= 3:  # Минимум 3 записи для анализа
            # Импортируем здесь, чтобы избежать циклических импортов
            from modules.ai_service import get_weekly_analysis
            
            # Генерируем анализ
            analysis = await get_weekly_analysis(reflections)
            
            # Отправляем пользователю
            await bot.send_message(
                user_id,
                f"🌙 **Еженедельный анализ твоих рефлексий**\n\n{analysis}",
                parse_mode="Markdown"
            )
            
            logger.info(f"Weekly analysis sent to user {user_id}")
            return True
        else:
            logger.info(f"User {user_id} has only {len(reflections)} reflections, skipping weekly analysis")
            return False
            
    except Exception as e:
        logger.error(f"Error sending weekly analysis to user {user_id}: {e}", exc_info=True)
        return False

# --- КОНЕЦ НОВОЙ ФУНКЦИИ ---

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
        print("Bot stopped manually.")
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}", exc_info=True)
        print(f"CRITICAL error in main execution: {e}")
        # Дополнительная обработка для предотвращения KeyError
        if "KeyError" in str(e):
            print("KeyError detected - this might be related to dispatcher data access")
            logger.error("KeyError in dispatcher - check data initialization")
