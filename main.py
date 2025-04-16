# код/main.py

import asyncio
from aiogram import Bot, Dispatcher, types, F # Добавили F для фильтров по тексту
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage # Используем MemoryStorage

# --- Импорты из проекта ---
from config import (
    TOKEN, CHANNEL_ID, ADMIN_ID, UNIVERSE_ADVICE, BOT_LINK,
    TIMEZONE, NO_LOGS_USERS, DATA_DIR
)
# Используем ИСПРАВЛЕННЫЕ версии файлов:
from database.db import Database # Правильная db.py
from modules.logging_service import LoggingService
from modules.notification_service import NotificationService
from modules.user_management import UserState, UserManager # Правильная user_management.py
from modules.ai_service import build_user_profile # ИСПРАВЛЕННАЯ ai_service.py

# Импортируем ВСЕ необходимые обработчики из ПРАВИЛЬНОЙ card_of_the_day.py
from modules.card_of_the_day import (
    get_main_menu,
    # --- Шаги нового флоу ---
    handle_card_request,                 # 0. Нажатие "Карта дня"
    ask_initial_resource,                # 1. Показ вопроса о нач. ресурсе (вызывается из handle_card_request)
    process_initial_resource_callback,   # 1.5 Обработка callback нач. ресурса
    ask_request_type_choice,             # 2. Показ вопроса о типе запроса (вызывается из 1.5)
    process_request_type_callback,       # 2.5 Обработка callback типа запроса
    process_request_text,                # 3а. Обработка текста запроса
    draw_card_direct,                    # 3б. Вытягивание карты (вызывается из 2.5 или 3а)
    process_initial_response,            # 4. Обработка первой ассоциации
    ask_exploration_choice,              # 5. Показ вопроса "исследовать дальше?" (вызывается из 4)
    process_exploration_choice_callback, # 5.5 Обработка callback исследования
    ask_grok_question,                   # 6. Функция запроса вопроса Grok (вызывается из 5.5 или след. шагов)
    process_first_grok_response,         # 6а. Обработка ответа на 1й вопрос Grok
    process_second_grok_response,        # 6б. Обработка ответа на 2й вопрос Grok
    process_third_grok_response,         # 6в. Обработка ответа на 3й вопрос Grok
    generate_and_send_summary,           # Вспомогательная - генерация и отправка саммари
    finish_interaction_flow,             # 7. Показ вопроса о кон. ресурсе (вызывается из 5.5 или 6в)
    process_final_resource_callback,     # 7.5 Обработка callback кон. ресурса
    process_recharge_method,             # 8. Обработка текста о методе восстановления
    show_final_feedback_and_menu,        # 9. Финальное сообщение + кнопки фидбека + очистка state
    process_card_feedback                # Обработка кнопок финального фидбека (👍/🤔/😕)
)

# --- Стандартные импорты ---
import random
from datetime import datetime, timedelta
import os
import json
import logging
import sqlite3 # Для обработки ошибок БД

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger_root = logging.getLogger() # Корневой логгер
logger = logging.getLogger(__name__) # Логгер модуля main

# --- Инициализация основных компонентов ---
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage() # Для продакшена лучше RedisStorage или другое персистентное хранилище
dp = Dispatcher(storage=storage)

# Инициализация БД с проверкой и логированием
# Убедимся, что директория /data существует (важно для Amvera и Docker)
os.makedirs(DATA_DIR, exist_ok=True)
db_path = os.path.join(DATA_DIR, "bot.db")
logger.info(f"Initializing database at: {db_path}")
print(f"Initializing database at: {db_path}") # Оставляем для видимости в логах Amvera
try:
    db = Database(path=db_path)
    # Проверка соединения (опционально)
    db.conn.execute("SELECT 1")
    logger.info(f"Database connection established successfully: {db.conn}")
    # Передаем экземпляр бота в db, если он там используется (например, для get_chat)
    db.bot = bot
except sqlite3.Error as e:
    logger.exception(f"CRITICAL: Database initialization failed at {db_path}: {e}")
    print(f"CRITICAL: Database initialization failed at {db_path}: {e}")
    # Завершаем работу, если БД не инициализирована
    raise SystemExit(f"Database failed to initialize: {e}")
except Exception as e: # Ловим другие возможные ошибки при инициализации
    logger.exception(f"CRITICAL: Unexpected error during Database initialization: {e}")
    print(f"CRITICAL: Unexpected error during Database initialization: {e}")
    raise SystemExit(f"Unexpected error initializing Database: {e}")


# Инициализация сервисов
logging_service = LoggingService(db)
notifier = NotificationService(bot, db)
user_manager = UserManager(db)

# --- Middleware для проверки подписки ---
class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        # Проверяем только сообщения и колбэки от пользователей
        if isinstance(event, (types.Message, types.CallbackQuery)):
            user = event.from_user
            # Игнорируем ботов и случаи без пользователя
            if not user or user.is_bot:
                return await handler(event, data)

            user_id = user.id
            # Пропускаем админа
            if user_id == ADMIN_ID:
                return await handler(event, data)

            try:
                # Проверяем статус подписки
                user_status = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
                # Разрешенные статусы
                allowed_statuses = ["member", "administrator", "creator"]
                if user_status.status not in allowed_statuses:
                    user_db_data = db.get_user(user_id) # Получаем данные пользователя (создастся, если нет)
                    name = user_db_data.get("name") if user_db_data else None
                    link = f"https://t.me/{CHANNEL_ID.lstrip('@')}" # Формируем ссылку
                    text = f"{name}, привет! 👋\nЧтобы пользоваться ботом, пожалуйста, подпишись на <a href='{link}'>канал автора</a>. ✨\n\nПосле подписки нажми /start." if name else f"Привет! 👋\nЧтобы пользоваться ботом, пожалуйста, подпишись на <a href='{link}'>канал автора</a>. ✨\n\nПосле подписки нажми /start."

                    # Отправляем сообщение в зависимости от типа события
                    if isinstance(event, types.Message):
                        await event.answer(text, disable_web_page_preview=True)
                    elif isinstance(event, types.CallbackQuery):
                        # Отвечаем на колбэк, чтобы убрать часики
                        await event.answer("Пожалуйста, подпишись на канал.", show_alert=True)
                        # Отправляем сообщение в чат
                        await event.message.answer(text, disable_web_page_preview=True)
                    return # Прерываем дальнейшую обработку

            except Exception as e:
                # Обрабатываем ошибки (например, пользователь заблокировал бота или нет в канале)
                # Код ошибки 'chat member not found' часто означает, что пользователь не в канале
                logger.error(f"Subscription check failed for user {user_id}: {e}")
                error_text = f"Ой, не могу проверить твою подписку на канал {CHANNEL_ID}. Пожалуйста, убедись, что ты подписан(а), и попробуй еще раз через /start."
                if isinstance(event, types.Message):
                     await event.answer(error_text)
                elif isinstance(event, types.CallbackQuery):
                     # Отвечаем на колбэк + сообщение
                     await event.answer("Ошибка проверки подписки", show_alert=False)
                     await event.message.answer(error_text)
                return # Прерываем обработку

        # Если проверка пройдена или не применялась, передаем управление дальше
        return await handler(event, data)

# Применяем Middleware к сообщениям и колбэкам
dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())
logger.info("SubscriptionMiddleware registered.")

# --- Обработчики стандартных команд (фабрики) ---
# (Используем версии из предоставленного '#доработтанный_код main.py.txt', т.к. они выглядят рабочими и не требуют изменений по задаче)

def make_start_handler(db, logger_service, user_manager):
    async def wrapped_handler(message: types.Message, state: FSMContext, command: CommandObject | None = None): # Добавили command
        await state.clear() # Всегда очищаем состояние при /start
        user_id = message.from_user.id
        username = message.from_user.username or ""
        args = command.args if command else "" # Получаем аргументы команды

        await logger_service.log_action(user_id, "start_command", {"args": args})

        user_data = db.get_user(user_id) # Получит или создаст пользователя
        if user_data.get("username") != username:
            db.update_user(user_id, {"username": username})

        # Логика рефералов
        if args and args.startswith("ref_"):
            try:
                referrer_id = int(args[4:])
                if referrer_id != user_id:
                    # add_referral вернет True, если реферал добавлен впервые
                    if db.add_referral(referrer_id, user_id):
                         referrer_data = db.get_user(referrer_id)
                         # Даем бонус, если его еще нет
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

        # Приветствие и запрос имени, если его нет
        user_name = user_data.get("name")
        if not user_name:
            await message.answer("Привет! ✨ Рад(а) знакомству!\nКак я могу к тебе обращаться?", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="Пропустить", callback_data="skip_name")]
            ]))
            await state.set_state(UserState.waiting_for_name)
        else:
            await message.answer(f"{user_name}, снова привет! 👋\nГотов(а) к карте дня?", reply_markup=await get_main_menu(user_id, db))

    return wrapped_handler

def make_share_handler(db, logger_service):
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
                     last_action_dt = datetime.fromisoformat(last_action_timestamp_iso.replace('Z', '+00:00')).astimezone(TIMEZONE)
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
                     current_chunk = "" # Start new chunk empty
                 current_chunk += line + "\n"
             if current_chunk:
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
         # Используем ИСПРАВЛЕННУЮ функцию, которая вернет профиль или создаст пустой
         profile = await build_user_profile(user_id, db)

         # Безопасное извлечение данных
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
         last_updated = last_updated_dt.strftime("%Y-%m-%d %H:%M") if isinstance(last_updated_dt, datetime) else "не обновлялся"
         # Новые поля ресурса
         initial_resource = profile.get("initial_resource") or "нет данных"
         final_resource = profile.get("final_resource") or "нет данных"
         recharge_method = profile.get("recharge_method") or "нет данных"

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

         # Получаем данные пользователя и его профиль
         user_info = db.get_user(target_user_id)
         if not user_info: # Проверяем, существует ли пользователь
             await message.answer(f"Пользователь с ID {target_user_id} не найден в базе.")
             return

         profile = await build_user_profile(target_user_id, db) # Получаем или строим профиль

         # Форматируем данные для вывода
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
             protect_content=True # Оставляем защиту контента, если нужна
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
              return # Остаемся в состоянии ожидания фидбека

          user_data = db.get_user(user_id)
          name = user_data.get("name", "Аноним")
          username = user_data.get("username", "N/A")
          timestamp_iso = datetime.now(TIMEZONE).isoformat()

          try:
              # Сохраняем фидбек в БД
              with db.conn:
                  db.conn.execute(
                      "INSERT INTO feedback (user_id, name, feedback, timestamp) VALUES (?, ?, ?, ?)",
                      (user_id, name, feedback_text, timestamp_iso)
                  )
              await logger_service.log_action(user_id, "feedback_submitted", {"feedback_length": len(feedback_text)}) # Логируем длину вместо текста
              await message.answer(
                  f"{name}, спасибо за твой отзыв! Я обязательно его учту. 🙏",
                  reply_markup=await get_main_menu(user_id, db),
                  protect_content=True
              )
              # Уведомляем админа
              try:
                  admin_notify_text = (f"📝 Новый фидбек от:\n"
                                       f"ID: <code>{user_id}</code>\n"
                                       f"Имя: {name}\n"
                                       f"Ник: @{username}\n\n"
                                       f"<b>Текст:</b>\n{feedback_text}")
                  await bot.send_message(ADMIN_ID, admin_notify_text[:4090]) # Обрезаем на всякий случай
              except Exception as admin_err:
                  logger.error(f"Failed to send feedback notification to admin: {admin_err}")

              await state.clear() # Очищаем состояние после успешной обработки

          except sqlite3.Error as db_err:
               logger.error(f"Failed to save feedback from user {user_id} to DB: {db_err}", exc_info=True)
               await message.answer("Ой, не получилось сохранить твой отзыв. Попробуй позже.", reply_markup=await get_main_menu(user_id, db))
               # Не очищаем состояние при ошибке БД
      return wrapped_handler

def make_name_handler(db, logger_service, user_manager):
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

def make_process_name_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message, state: FSMContext):
         user_id = message.from_user.id
         name = message.text.strip()
         # Валидация имени
         if not name:
             await message.answer("Имя не может быть пустым. Попробуй еще раз или нажми 'Пропустить' выше.")
             return
         if len(name) > 50:
             await message.answer("Слишком длинное имя. Пожалуйста, используй не более 50 символов.")
             return
         # Запрет на использование текстов кнопок меню
         reserved_names = ["✨ Карта дня", "💌 Подсказка Вселенной"]
         if name in reserved_names:
             await message.answer(f"Имя '{name}' использовать нельзя :) Пожалуйста, выбери другое.")
             return

         await user_manager.set_name(user_id, name)
         await logger_service.log_action(user_id, "set_name", {"name": name})
         await message.answer(f"Приятно познакомиться, {name}! 😊\nТеперь можешь нажать '✨ Карта дня'.", reply_markup=await get_main_menu(user_id, db))
         await state.clear()
     return wrapped_handler

def make_process_skip_name_handler(db, logger_service, user_manager):
     async def wrapped_handler(callback: types.CallbackQuery, state: FSMContext):
         user_id = callback.from_user.id
         await user_manager.set_name(user_id, "") # Сохраняем пустое имя
         await logger_service.log_action(user_id, "skip_name")
         try:
             await callback.message.edit_reply_markup(reply_markup=None) # Убираем кнопку
         except Exception as e:
              logger.warning(f"Could not edit message on skip_name for user {user_id}: {e}")
         await callback.message.answer("Хорошо, буду обращаться к тебе без имени.\nНажми '✨ Карта дня', когда будешь готов(а).", reply_markup=await get_main_menu(user_id, db))
         await state.clear()
         await callback.answer()
     return wrapped_handler

def make_remind_off_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message, state: FSMContext):
         user_id = message.from_user.id
         # Очищаем состояние, только если оно было связано с установкой напоминания
         current_state = await state.get_state()
         if current_state == UserState.waiting_for_reminder_time:
             await state.clear()

         try:
             await user_manager.set_reminder(user_id, None) # Устанавливаем время в None
             await logger_service.log_action(user_id, "set_reminder_time_off")
             name = db.get_user(user_id).get("name", "Друг")
             text = f"{name}, я отключил напоминания для тебя. Если захочешь включить снова, используй /remind."
             await message.answer(text, reply_markup=await get_main_menu(user_id, db))
         except Exception as e:
             logger.error(f"Failed to disable reminders for user {user_id}: {e}", exc_info=True)
             await message.answer("Ой, не получилось отключить напоминания. Попробуй еще раз позже.")
     return wrapped_handler

def make_process_reminder_time_handler(db, logger_service, user_manager):
     async def wrapped_handler(message: types.Message, state: FSMContext):
         user_id = message.from_user.id
         name = db.get_user(user_id).get("name", "Друг")
         reminder_time_str = message.text.strip()
         try:
             # Валидация формата ЧЧ:ММ
             reminder_dt = datetime.strptime(reminder_time_str, "%H:%M")
             reminder_time_normalized = reminder_dt.strftime("%H:%M") # Нормализуем формат
             await user_manager.set_reminder(user_id, reminder_time_normalized)
             await logger_service.log_action(user_id, "set_reminder_time", {"reminder_time": reminder_time_normalized})
             text = f"{name}, отлично! 👍 Буду напоминать тебе ежедневно в <b>{reminder_time_normalized}</b> по московскому времени."
             await message.answer(text, reply_markup=await get_main_menu(user_id, db))
             await state.clear()
         except ValueError:
             # Если формат неверный, просим ввести снова
             text = f"{name}, не совсем понял время. 🕰️ Пожалуйста, используй формат ЧЧ:ММ (например, <b>08:30</b> или <b>21:00</b>)."
             await message.answer(text) # Не добавляем меню, остаемся в состоянии ожидания
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
         logs = db.get_actions() # Получаем все логи (отсортированы ASC)
         filtered_logs = []
         excluded_users = set(NO_LOGS_USERS)

         for log in logs:
             try:
                 # Сравниваем даты в нужной таймзоне
                 log_timestamp_dt = datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00')).astimezone(TIMEZONE)
                 if log_timestamp_dt.date() == target_date and log.get("user_id") not in excluded_users:
                     filtered_logs.append(log)
             except (ValueError, TypeError, KeyError) as e: # Добавлен KeyError
                 logger.warning(f"Could not parse timestamp or missing data in log for admin view: {log}, error: {e}")
                 continue

         if not filtered_logs:
             await message.answer(f"Логов за {target_date_str} нет (кроме исключенных пользователей).")
             return

         # Форматируем логи для вывода
         log_lines = []
         for log in filtered_logs:
             ts_str = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')).astimezone(TIMEZONE).strftime('%H:%M:%S')
             uid = log.get('user_id', 'N/A')
             action = log.get('action', 'N/A')
             details = log.get('details', {})
             details_str = ""
             if isinstance(details, dict) and details:
                 details_str = ", ".join([f"{k}={v}" for k, v in details.items()])
                 details_str = f" ({details_str[:100]}{'...' if len(details_str) > 100 else ''})" # Ограничиваем длину деталей
             log_lines.append(f"{ts_str} U:{uid} A:{action}{details_str}")

         header = f"📜 <b>Логи за {target_date_str} ({len(log_lines)} записей):</b>\n\n"
         full_text = header + "\n".join(log_lines)

         # Разбиваем на части, если сообщение слишком длинное
         max_len = 4000
         if len(full_text) > max_len:
             current_chunk = header
             for line in log_lines:
                 if len(current_chunk) + len(line) + 1 > max_len:
                     await message.answer(current_chunk)
                     current_chunk = "" # Новый чанк начинаем пустым
                 current_chunk += line + "\n"
             if current_chunk: # Отправляем остаток
                 await message.answer(current_chunk)
         else:
             await message.answer(full_text)
     return wrapped_handler

def make_bonus_request_handler(db, logger_service, user_manager): # Добавил user_manager
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
         await logger_service.log_action(user_id, "bonus_request_used", {"advice_preview": advice[:50]}) # Логируем только часть совета

         # Отключаем бонус после использования
         await user_manager.set_bonus_available(user_id, False)
         await logger_service.log_action(user_id, "bonus_disabled_after_use")
     return wrapped_handler

# --- Обработчики некорректных вводов ---
async def handle_text_when_waiting_callback(message: types.Message, state: FSMContext):
    """Обрабатывает текст, когда ожидается нажатие кнопки."""
    current_state = await state.get_state()
    logger.warning(f"User {message.from_user.id} sent text '{message.text}' while in state {current_state}, expected callback.")
    # Отвечаем вежливо, не сбрасывая состояние
    await message.reply("Пожалуйста, используй кнопки выше, чтобы сделать выбор. 👆")

async def handle_callback_when_waiting_text(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие кнопки, когда ожидается текст."""
    current_state = await state.get_state()
    logger.warning(f"User {callback.from_user.id} sent callback '{callback.data}' while in state {current_state}, expected text.")
    # Отвечаем на колбэк и просим ввести текст
    await callback.answer("Пожалуйста, отправь ответ текстом в чат.", show_alert=True)

# --- Регистрация всех обработчиков ---
def register_handlers(dp: Dispatcher, db: Database, logger_service: LoggingService, user_manager: UserManager):
    """Регистрирует все обработчики сообщений и колбэков."""
    logger.info("Registering handlers...")

    # --- Стандартные команды ---
    # Регистрируем с CommandObject для /start
    dp.message.register(make_start_handler(db, logger_service, user_manager), Command("start"), StateFilter(None, UserState.waiting_for_name)) # Разрешаем /start без состояния или при ожидании имени
    dp.message.register(make_share_handler(db, logger_service), Command("share"), StateFilter("*")) # Разрешаем из любого состояния
    dp.message.register(make_remind_handler(db, logger_service, user_manager), Command("remind"), StateFilter("*"))
    dp.message.register(make_remind_off_handler(db, logger_service, user_manager), Command("remind_off"), StateFilter("*"))
    dp.message.register(make_name_handler(db, logger_service, user_manager), Command("name"), StateFilter("*"))
    dp.message.register(make_feedback_handler(db, logger_service), Command("feedback"), StateFilter("*"))
    dp.message.register(make_user_profile_handler(db, logger_service), Command("user_profile"), StateFilter("*"))

    # --- Админские команды ---
    dp.message.register(make_users_handler(db, logger_service), Command("users"))
    dp.message.register(make_logs_handler(db, logger_service), Command("logs"))
    dp.message.register(make_admin_user_profile_handler(db, logger_service), Command("admin_user_profile"))

    # --- Обработчики текстовых кнопок меню ---
    # Используем F.text == "..." для явного указания текста кнопки
    dp.message.register(make_bonus_request_handler(db, logger_service, user_manager), F.text == "💌 Подсказка Вселенной", StateFilter("*"))
    # Обработчик кнопки "Карта дня" - точка входа в новый флоу
    dp.message.register(handle_card_request, F.text == "✨ Карта дня", StateFilter("*"))

    # --- Обработчики состояний FSM ---

    # 1. Установка имени
    dp.message.register(make_process_name_handler(db, logger_service, user_manager), UserState.waiting_for_name)
    dp.callback_query.register(make_process_skip_name_handler(db, logger_service, user_manager), F.data == "skip_name", UserState.waiting_for_name)
    # Обработка некорректного ввода (текст вместо нажатия skip_name не нужен, т.к. мы ожидаем текст имени)
    # dp.callback_query.register(handle_callback_when_waiting_text, StateFilter(UserState.waiting_for_name)) # Не нужен, т.к. есть skip_name

    # 2. Установка напоминания
    dp.message.register(make_process_reminder_time_handler(db, logger_service, user_manager), UserState.waiting_for_reminder_time)
    dp.callback_query.register(handle_callback_when_waiting_text, StateFilter(UserState.waiting_for_reminder_time)) # Обработка кнопки вместо текста

    # 3. Отправка общего фидбека
    dp.message.register(make_process_feedback_handler(db, logger_service), UserState.waiting_for_feedback)
    dp.callback_query.register(handle_callback_when_waiting_text, StateFilter(UserState.waiting_for_feedback)) # Обработка кнопки вместо текста

    # --- Флоу "Карты Дня" (регистрация в порядке шагов) ---

    # Шаг 1: Ожидание выбора НАЧАЛЬНОГО ресурса
    dp.callback_query.register(process_initial_resource_callback, UserState.waiting_for_initial_resource, F.data.startswith("resource_"))
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_initial_resource) # Ошибка: текст вместо кнопки

    # Шаг 2: Ожидание выбора ТИПА запроса (в уме / написать)
    dp.callback_query.register(process_request_type_callback, UserState.waiting_for_request_type_choice, F.data.startswith("request_type_"))
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_request_type_choice) # Ошибка: текст вместо кнопки

    # Шаг 3а: Ожидание ввода ТЕКСТА запроса
    dp.message.register(process_request_text, UserState.waiting_for_request_text_input)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_request_text_input) # Ошибка: кнопка вместо текста

    # Шаг 4: Ожидание ПЕРВОЙ АССОЦИАЦИИ (текст)
    dp.message.register(process_initial_response, UserState.waiting_for_initial_response)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_initial_response) # Ошибка: кнопка вместо текста

    # Шаг 5: Ожидание выбора ИССЛЕДОВАТЬ ДАЛЬШЕ (да/нет)
    dp.callback_query.register(process_exploration_choice_callback, UserState.waiting_for_exploration_choice, F.data.startswith("explore_"))
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_exploration_choice) # Ошибка: текст вместо кнопки

    # Шаг 6: Ожидание ответов на вопросы GROK (текст)
    dp.message.register(process_first_grok_response, UserState.waiting_for_first_grok_response)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_first_grok_response)

    dp.message.register(process_second_grok_response, UserState.waiting_for_second_grok_response)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_second_grok_response)

    dp.message.register(process_third_grok_response, UserState.waiting_for_third_grok_response)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_third_grok_response)

    # Шаг 7: Ожидание выбора КОНЕЧНОГО ресурса
    dp.callback_query.register(process_final_resource_callback, UserState.waiting_for_final_resource, F.data.startswith("resource_"))
    dp.message.register(handle_text_when_waiting_callback, UserState.waiting_for_final_resource) # Ошибка: текст вместо кнопки

    # Шаг 8: Ожидание ввода СПОСОБА ВОССТАНОВЛЕНИЯ (текст)
    dp.message.register(process_recharge_method, UserState.waiting_for_recharge_method)
    dp.callback_query.register(handle_callback_when_waiting_text, UserState.waiting_for_recharge_method) # Ошибка: кнопка вместо текста

    # Шаг 9: Обработка кнопок ФИНАЛЬНОГО ФИДБЕКА (👍/🤔/😕)
    # Эти кнопки появляются после очистки состояния, поэтому StateFilter("*")
    dp.callback_query.register(process_card_feedback, F.data.startswith("feedback_v2_"), StateFilter("*"))

    # --- Обработчики неизвестных команд/сообщений (должны быть последними) ---
    @dp.message(StateFilter("*")) # Ловит любое не обработанное сообщение В ЛЮБОМ СОСТОЯНИИ
    async def handle_unknown_message_state(message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        logger.warning(f"Unknown message '{message.text}' received from user {message.from_user.id} in state {current_state}")
        # Даем подсказку или предлагаем сбросить
        await message.reply("Ой, кажется, я не ожидал(а) этого сейчас. 🤔 Попробуй ответить на последний вопрос или используй кнопки, если они есть. Для выхода из текущего диалога можно нажать /start.")

    @dp.message() # Ловит любое не обработанное сообщение БЕЗ СОСТОЯНИЯ
    async def handle_unknown_message_no_state(message: types.Message):
        logger.warning(f"Unknown message '{message.text}' received from user {message.from_user.id} with no state.")
        await message.reply("Извини, не понял(а) твой запрос. 🤔 Попробуй нажать '✨ Карта дня' или используй одну из команд: /start, /name, /remind, /share, /feedback, /user_profile.")

    @dp.callback_query(StateFilter("*")) # Ловит любой не обработанный колбэк В ЛЮБОМ СОСТОЯНИИ
    async def handle_unknown_callback_state(callback: types.CallbackQuery, state: FSMContext):
         current_state = await state.get_state()
         logger.warning(f"Unknown callback '{callback.data}' received from user {callback.from_user.id} in state {current_state}")
         await callback.answer("Это действие сейчас недоступно.", show_alert=True)

    @dp.callback_query() # Ловит любой не обработанный колбэк БЕЗ СОСТОЯНИЯ
    async def handle_unknown_callback_no_state(callback: types.CallbackQuery):
         logger.warning(f"Unknown callback '{callback.data}' received from user {callback.from_user.id} with no state.")
         await callback.answer("Неизвестное действие.", show_alert=True)


    logger.info("Handlers registered successfully.")


# --- Запуск бота ---
async def main():
    logger.info("Starting bot...")
    # Устанавливаем команды меню для бота
    commands = [
        types.BotCommand(command="start", description="▶️ Начать / Перезапустить"),
        types.BotCommand(command="name", description="👤 Изменить имя"),
        types.BotCommand(command="remind", description="⏰ Напоминания (вкл/изм)"),
        types.BotCommand(command="remind_off", description="🔕 Выключить напоминания"),
        types.BotCommand(command="share", description="🎁 Поделиться с другом"),
        types.BotCommand(command="feedback", description="✉️ Оставить отзыв / Идею"),
        types.BotCommand(command="user_profile", description="📊 Мой профиль"),
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Bot commands set successfully.")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

    # Регистрируем все обработчики
    register_handlers(dp, db, logging_service, user_manager)

    # Запускаем фоновую задачу проверки напоминаний
    # Убедимся, что check_reminders обрабатывает ошибки внутри себя
    reminder_task = asyncio.create_task(notifier.check_reminders())
    logger.info("Reminder check task scheduled.")

    # Запускаем поллинг
    logger.info("Starting polling...")
    print("Bot is starting polling...") # Для логов Amvera
    try:
        # allowed_updates нужен, чтобы не получать лишние апдейты
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.critical(f"Polling failed: {e}", exc_info=True)
        print(f"CRITICAL: Polling failed: {e}")
    finally:
        logger.info("Stopping bot...")
        print("Bot is stopping...")
        # Отменяем фоновые задачи
        reminder_task.cancel()
        try:
            await reminder_task # Даем задаче завершиться после отмены
        except asyncio.CancelledError:
            logger.info("Reminder task cancelled successfully.")
        # Закрываем соединение с БД
        if db and db.conn:
            try:
                db.conn.close()
                logger.info("Database connection closed.")
            except Exception as db_close_err:
                 logger.error(f"Error closing database connection: {db_close_err}")
        # Закрываем сессию бота
        try:
            await bot.session.close()
            logger.info("Bot session closed.")
        except Exception as session_close_err:
             logger.error(f"Error closing bot session: {session_close_err}")
        print("Bot stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually (KeyboardInterrupt/SystemExit).")
    except Exception as e:
        # Ловим любые другие ошибки на самом верхнем уровне
        logger.critical(f"Critical error in main execution scope: {e}", exc_info=True)
        print(f"CRITICAL error in main execution scope: {e}")
