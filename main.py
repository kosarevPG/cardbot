import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import TOKEN, CHANNEL_ID, ADMIN_ID, UNIVERSE_ADVICE, BOT_LINK, TIMEZONE, NO_LOGS_USERS
from database.db import Database
from modules.logging_service import LoggingService
from modules.notification_service import NotificationService
from modules.card_of_the_day import (
    handle_card_request, draw_card, process_request_text, process_initial_response,
    process_first_grok_response, process_second_grok_response, process_third_grok_response,
    process_card_feedback, get_main_menu, process_initial_resource, process_scenario_choice,
    process_continue_choice, process_final_resource, process_final_resource_response,
    process_recovery_method
)
from modules.user_management import UserState, UserManager
from modules.ai_service import build_user_profile
import random
from datetime import datetime, timedelta
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger_root = logging.getLogger()

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

try:
    db.get_user(0)
    print("Database check successful")
except Exception as e:
    logger.log_action(0, "db_init_error", {"error": str(e)})
    print(f"Database initialization failed: {e}")
    raise

class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            if user_id == ADMIN_ID:
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

class SurveyState(StatesGroup):
    question_1 = State()
    question_2 = State()
    question_3 = State()
    question_4 = State()
    question_5 = State()

async def send_survey(message: types.Message, state: FSMContext, db, logger):
    user_id = message.from_user.id
    allowed_users = [6682555021]
    logger_root.info(f"Processing /survey for user {user_id}")
    if user_id not in allowed_users:
        await message.answer("Этот опрос пока доступен только избранным пользователям.")
        return
    name = db.get_user(user_id)["name"]
    intro_text = (
        f"Привет, {name}! 🌟 Ты уже успела поработать с картами — как впечатления? "
        "Помоги мне стать лучше, ответь на вопросы по очереди. Начнём!"
        if name else
        "Привет! 🌟 Ты уже успела поработать с картами — как впечатления? "
        "Помоги мне стать лучше, ответь на вопросы по очереди. Начнём!"
    )
    question_1_text = "1. Пробовала делиться мной (Меню -> '🎁 Поделиться')?"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Да", callback_data="survey_1_yes")],
        [types.InlineKeyboardButton(text="Нет", callback_data="survey_1_no")]
    ])
    await message.answer(intro_text)
    await message.answer(question_1_text, reply_markup=keyboard)
    await state.set_state(SurveyState.question_1)

async def process_survey_response(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = callback.data
    current_state = await state.get_state()

    questions = {
        SurveyState.question_1: {
            "text": "2. Что больше всего нравится в работе со мной?",
            "next_state": SurveyState.question_2,
            "options": []
        },
        SurveyState.question_2: {
            "text": "3. Были моменты, когда что-то в работе со мной не понравилось или показалось неудобным?",
            "next_state": SurveyState.question_3,
            "options": []
        },
        SurveyState.question_3: {
            "text": "4. Как часто ты готова возвращаться к картам? Например, каждый день, раз в неделю?",
            "next_state": SurveyState.question_4,
            "options": []
        },
        SurveyState.question_4: {
            "text": "5. Какие темы или вопросы ты бы хотела исследовать с картами в будущем?",
            "next_state": SurveyState.question_5,
            "options": []
        }
    }

    if current_state in questions:
        await logger.log_action(user_id, "survey_response", {"question": current_state, "response": data})
        next_question = questions[current_state]
        if next_question["options"]:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text=opt, callback_data=f"survey_{current_state[-1]}_{opt.lower()}")]
                for opt in next_question["options"]
            ])
        else:
            await callback.message.answer(next_question["text"])
            await state.set_state(next_question["next_state"])
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()
    elif current_state == SurveyState.question_5:
        await logger.log_action(user_id, "survey_response", {"question": current_state, "response": data})
        await callback.message.answer("Спасибо за твои ответы! Они помогут мне стать лучше. 😊")
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()

async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.from_user.first_name
    username = message.from_user.username
    db.update_user(user_id, {"name": name, "username": username})
    text = (
        f"Привет, {name}! Я — твой проводник в мир метафорических карт. 🌟 "
        "Каждый день ты можешь вытянуть карту дня и поразмышлять над ней. "
        "Это как маленькое путешествие к себе — через образы, чувства и вопросы. "
        "Готова начать? Нажми '✨ Карта дня' или используй /card!"
    )
    await message.answer(text, reply_markup=await get_main_menu(user_id, db))
    await state.clear()
    await logger.log_action(user_id, "start_command", {})

async def set_name_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await message.answer("Как тебя зовут? Напиши своё имя.")
    await state.set_state(UserState.waiting_for_name)
    await logger.log_action(user_id, "set_name_command", {})

async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    if name:
        await user_manager.set_name(user_id, name)
        await message.answer(f"Приятно познакомиться, {name}! 😊 Теперь я буду обращаться к тебе так.", reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        await logger.log_action(user_id, "name_set", {"name": name})
    else:
        await message.answer("Пожалуйста, напиши своё имя.")
        await logger.log_action(user_id, "name_set_failed", {"reason": "empty_name"})

async def set_reminder_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    text = f"{name}, во сколько напоминать тебе о карте дня? Напиши время в формате ЧЧ:ММ (по Москве, например, 09:00)." if name else "Во сколько напоминать тебе о карте дня? Напиши время в формате ЧЧ:ММ (по Москве, например, 09:00)."
    await message.answer(text)
    await state.set_state(UserState.waiting_for_reminder_time)
    await logger.log_action(user_id, "set_reminder_command", {})

async def process_reminder_time(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    time_str = message.text.strip()
    name = db.get_user(user_id)["name"]
    try:
        datetime.strptime(time_str, "%H:%M")
        await user_manager.set_reminder(user_id, time_str)
        text = f"{name}, я запомнил! Буду напоминать тебе о карте дня в {time_str} по Москве. 😊" if name else f"Я запомнил! Буду напоминать тебе о карте дня в {time_str} по Москве. 😊"
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        await logger.log_action(user_id, "reminder_set", {"time": time_str})
    except ValueError:
        await message.answer("Пожалуйста, укажи время в формате ЧЧ:ММ, например, 09:00.")
        await logger.log_action(user_id, "reminder_set_failed", {"reason": "invalid_format", "input": time_str})

async def cancel_reminder_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    await user_manager.set_reminder(user_id, None)
    text = f"{name}, я отключил напоминания. Ты всегда можешь включить их снова с помощью /reminder." if name else "Я отключил напоминания. Ты всегда можешь включить их снова с помощью /reminder."
    await message.answer(text, reply_markup=await get_main_menu(user_id, db))
    await state.clear()
    await logger.log_action(user_id, "cancel_reminder", {})

async def feedback_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    text = f"{name}, поделись, что думаешь о работе со мной? Что нравится, что можно улучшить?" if name else "Поделись, что думаешь о работе со мной? Что нравится, что можно улучшить?"
    await message.answer(text)
    await state.set_state(UserState.waiting_for_feedback)
    await logger.log_action(user_id, "feedback_command", {})

async def process_feedback(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    feedback_text = message.text.strip()
    name = db.get_user(user_id)["name"]
    if feedback_text:
        with db.conn:
            db.conn.execute(
                "INSERT INTO feedback (user_id, name, feedback, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, name, feedback_text, datetime.now(TIMEZONE).isoformat())
            )
        text = f"{name}, спасибо за твой отзыв! Это очень помогает мне становиться лучше. 😊" if name else "Спасибо за твой отзыв! Это очень помогает мне становиться лучше. 😊"
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        await state.clear()
        await logger.log_action(user_id, "feedback_submitted", {"feedback": feedback_text[:50] + "..." if len(feedback_text) > 50 else feedback_text})
    else:
        await message.answer("Пожалуйста, напиши свой отзыв.")
        await logger.log_action(user_id, "feedback_failed", {"reason": "empty_feedback"})

async def universe_advice_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = db.get_user(user_id)
    name = user_data["name"]
    if not user_data.get("bonus_available", False):
        text = f"{name}, эта возможность пока недоступна. Продолжай работать с картами, и я открою её для тебя!" if name else "Эта возможность пока недоступна. Продолжай работать с картами, и я открою её для тебя!"
        await message.answer(text, reply_markup=await get_main_menu(user_id, db))
        return
    advice = random.choice(UNIVERSE_ADVICE)
    text = f"{name}, вот подсказка от Вселенной: {advice}" if name else f"Вот подсказка от Вселенной: {advice}"
    await message.answer(text, reply_markup=await get_main_menu(user_id, db))
    await user_manager.set_bonus_available(user_id, False)
    await logger.log_action(user_id, "universe_advice", {"advice": advice})
    await state.clear()

async def share_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = db.get_user(user_id)["name"]
    text = (
        f"{name}, приглашай подруг к нам! 😊 Вот твоя уникальная ссылка: {BOT_LINK}?start={user_id}\n"
        "Поделись ею, и я открою тебе бонус — подсказку от Вселенной!"
        if name else
        f"Приглашай подруг к нам! 😊 Вот твоя уникальная ссылка: {BOT_LINK}?start={user_id}\n"
        "Поделись ею, и я открою тебе бонус — подсказку от Вселенной!"
    )
    await message.answer(text, reply_markup=await get_main_menu(user_id, db))
    await logger.log_action(user_id, "share_command", {"referral_link": f"{BOT_LINK}?start={user_id}"})
    await state.clear()

async def process_referral(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    args = message.get_args()
    if args and args.isdigit():
        referrer_id = int(args)
        if referrer_id != user_id:
            db.add_referral(referrer_id, user_id)
            await user_manager.set_bonus_available(referrer_id, True)
            referrer_name = db.get_user(referrer_id)["name"]
            await bot.send_message(
                referrer_id,
                f"{referrer_name}, твоя подруга присоединилась! 😊 Теперь тебе доступна подсказка Вселенной — выбери '💌 Подсказка Вселенной' в меню."
                if referrer_name else
                "Твоя подруга присоединилась! 😊 Теперь тебе доступна подсказка Вселенной — выбери '💌 Подсказка Вселенной' в меню."
            )
            await logger.log_action(user_id, "referral_added", {"referrer_id": referrer_id})
    await start_command(message, state)

# Регистрация обработчиков
dp.message.register(start_command, Command(commands=["start"]), StateFilter(None))
dp.message.register(process_referral, Command(commands=["start"]), lambda message: bool(message.get_args()))
dp.message.register(set_name_command, Command(commands=["name"]), StateFilter(None))
dp.message.register(process_name, StateFilter(UserState.waiting_for_name))
dp.message.register(set_reminder_command, Command(commands=["reminder"]), StateFilter(None))
dp.message.register(process_reminder_time, StateFilter(UserState.waiting_for_reminder_time))
dp.message.register(cancel_reminder_command, Command(commands=["cancel_reminder"]), StateFilter(None))
dp.message.register(feedback_command, Command(commands=["feedback"]), StateFilter(None))
dp.message.register(process_feedback, StateFilter(UserState.waiting_for_feedback))
dp.message.register(universe_advice_command, Command(commands=["universe"]), StateFilter(None))
dp.message.register(share_command, Command(commands=["share"]), StateFilter(None))
dp.message.register(send_survey, Command(commands=["survey"]), StateFilter(None))

# Обработчики для карты дня
dp.message.register(handle_card_request, lambda message: message.text == "✨ Карта дня", StateFilter(None))
dp.message.register(process_request_text, StateFilter(UserState.waiting_for_request_text))
dp.message.register(process_initial_response, StateFilter(UserState.waiting_for_initial_response))
dp.message.register(process_first_grok_response, StateFilter(UserState.waiting_for_first_grok_response))
dp.message.register(process_second_grok_response, StateFilter(UserState.waiting_for_second_grok_response))
dp.message.register(process_third_grok_response, StateFilter(UserState.waiting_for_third_grok_response))
dp.message.register(process_recovery_method, StateFilter(UserState.waiting_for_recovery_method))

# Обработчики для callback-запросов
dp.callback_query.register(process_initial_resource, lambda callback: callback.data.startswith("resource_initial_"))
dp.callback_query.register(process_scenario_choice, lambda callback: callback.data.startswith("scenario_"))
dp.callback_query.register(draw_card, lambda callback: callback.data.startswith("draw_card_"))
dp.callback_query.register(process_continue_choice, lambda callback: callback.data.startswith("scenario_"))
dp.callback_query.register(process_final_resource_response, lambda callback: callback.data.startswith("resource_final_"))
dp.callback_query.register(process_card_feedback, lambda callback: callback.data.startswith("feedback_"))
dp.callback_query.register(process_survey_response, lambda callback: callback.data.startswith("survey_"))

async def on_startup():
    logger_root.info("Bot is starting...")

async def on_shutdown():
    logger_root.info("Bot is shutting down...")
    db.conn.close()
    logger_root.info("Database connection closed.")

if __name__ == "__main__":
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    asyncio.run(dp.start_polling(bot))
