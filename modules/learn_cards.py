# modules/learn_cards.py
# Модуль обучения "Как разговаривать с картой"

import logging
import json
import uuid
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from datetime import datetime

try:
    from config_local import TIMEZONE
except ImportError:
    from config import TIMEZONE

from modules.user_management import LearnCardsFSM
from modules.ai_service import analyze_request
from modules.training_logger import TrainingLogger
from database.db import Database

logger = logging.getLogger(__name__)

# === КОНСТАНТЫ ===

# Тексты обучающего модуля
TEXTS = {
    "intro": (
        "🌿 Добро пожаловать в мини-практику «Как разговаривать с картой».\n\n"
        "МАК-карта не предсказывает будущее — она помогает услышать тебя.\n"
        "Но чтобы карта «заговорила», нужен живой, осознанный запрос.\n\n"
        "Хочешь узнать, как такой запрос формулировать — просто и точно?"
    ),
    "theory_1": (
        "🌀 <b>Что такое МАК-карты</b>\n\n"
        "Это метод самопознания через образы.\n"
        "Каждая карта — это повод заглянуть внутрь, распознать чувства, заметить скрытое.\n\n"
        "Через образы говорит твое бессознательное.\n"
        "<i>Первая мысль, ощущение, впечатление — часто самое чистое послание карты.</i>"
    ),
    "theory_2": (
        "🔮 <b>Зачем нужен запрос</b>\n\n"
        "Запрос — это как фонарик: он освещает нужное внутри.\n"
        "Когда ты задаёшь вопрос от себя, карта отвечает языком твоей интуиции.\n\n"
        "Без запроса — просто красивая картинка. С запросом — <b>отклик и инсайт</b>."
    ),
    "theory_3": (
        "⚠️ <b>Типичные ошибки</b>\n\n"
        "🧩 Запросы «наружу» не работают:\n"
        "• \"Что будет?\"\n"
        "• \"Почему он так делает?\"\n"
        "• \"Как всё сложится?\"\n\n"
        "🌿 Лучше повернуться внутрь:\n"
        "• \"Что я сейчас чувствую в этой ситуации?\"\n"
        "• \"Что мне важно заметить о себе?\"\n"
        "• \"Как я могу поддержать себя, пока жду перемен?\""
    ),
    "steps": (
        "✨ <b>Как сделать запрос живым и точным</b>\n\n"
        "1️⃣ <b>Ситуация</b>: что происходит?\n"
        "2️⃣ <b>Чувство</b>: что ты ощущаешь?\n"
        "3️⃣ <b>Намерение</b>: чего ты хочешь — понять, отпустить, укрепить?\n\n"
        "✖️ \"Когда всё получится?\"\n"
        "✅ \"Что поможет мне сохранить уверенность, пока я иду к цели?\""
    ),
    "trainer_intro": (
        "Сейчас ты потренируешься формулировать запрос.\n\n"
        "Я покажу примеры, а потом — твоя очередь."
    ),
    "trainer_examples": (
        "💡 <b>Примеры переформулировки</b>\n\n"
        "✦ \"Почему у меня ничего не получается?\"\n"
        "→ 🌿 \"Что поможет мне поверить в себя и сделать первый шаг?\"\n\n"
        "✦ \"Когда всё наладится?\"\n"
        "→ 🌿 \"Как я могу поддержать себя, пока всё меняется?\"\n\n"
        "Фокус смещается с <i>мира</i> — на <b>себя</b>. Это и есть ресурсный запрос."
    ),
    "trainer_input": (
        "Теперь твоя очередь! ✍️\n\n"
        "Сформулируй свой запрос к карте — так, как ты его чувствуешь.\n"
        "Не бойся ошибок: я помогу, если что."
    ),
    "choice_menu": (
        "Хочешь освежить теорию или сразу потренироваться?"
    ),
    # Вопросы входного опросника
    "entry_poll_q1": "🧭 Что ты знаешь о МАК-картах?",
    "entry_poll_q2": "🧠 Как ты обычно формулируешь запрос?",
    "entry_poll_q3": "🔮 С какими ожиданиями ты приходишь?",
    "entry_poll_q4": "💭 Что тебе ближе прямо сейчас?",
    # Вопросы выходного опросника
    "exit_poll_q1": "🔍 Насколько понятным был материал?",
    "exit_poll_q2": "✨ Что изменилось в твоём понимании запроса?",
    "exit_poll_q3": "💬 Как ты теперь чувствуешь себя перед работой с картой?",
    "exit_feedback_invite": (
        "💌 Если хочешь поделиться мыслями или пожеланиями — мне будет очень ценно услышать тебя. "
        "Просто набери команду /feedback"
    )
}

# Примеры запросов для быстрой помощи
EXAMPLE_TEMPLATES = [
    "Что я чувствую в ситуации [название]?",
    "Что поможет мне справиться с этим по-доброму?",
    "Как я могу поддержать себя в теме [название]?"
]

# Варианты ответов для входного опросника
ENTRY_POLL_OPTIONS = {
    "q1": [
        "Ничего / слышала, но не использовала",
        "Немного практиковала",
        "Работаю с ними регулярно"
    ],
    "q2": [
        "Просто задаю вопрос в голове",
        "Пишу, что чувствую",
        "Я не уверена, как это делать"
    ],
    "q3": [
        "Хочу получить ответ от карты",
        "Хочу лучше понять себя",
        "Просто интересно попробовать"
    ],
    "q4": [
        "Хочу разобраться, как работают МАК",
        "Хочу научиться формулировать запрос",
        "Просто интересно, что это",
        "Не знаю, но что-то потянуло сюда"
    ]
}

# Варианты ответов для выходного опросника
EXIT_POLL_OPTIONS = {
    "q1": [
        "Всё чётко",
        "Немного запуталась",
        "Было сложно"
    ],
    "q2": [
        "Стало яснее, как и зачем его формулировать",
        "Поняла, что делала раньше не так",
        "Ничего нового"
    ],
    "q3": [
        "Увереннее",
        "Любопытно",
        "Всё ещё не уверена"
    ]
}


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def create_inline_keyboard(buttons_data):
    """
    Создает инлайн-клавиатуру из списка кнопок.
    
    Args:
        buttons_data: Список кортежей (text, callback_data) или список списков для рядов
    """
    if not buttons_data:
        return None
    
    keyboard = []
    for item in buttons_data:
        if isinstance(item, list):
            # Если это список, создаем ряд кнопок
            row = [types.InlineKeyboardButton(text=text, callback_data=callback) for text, callback in item]
            keyboard.append(row)
        else:
            # Иначе создаем одну кнопку в ряду
            text, callback = item
            keyboard.append([types.InlineKeyboardButton(text=text, callback_data=callback)])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


async def get_or_create_progress(db: Database, user_id: int) -> dict:
    """
    Получает или создает прогресс обучения для пользователя.
    
    Args:
        db: Экземпляр базы данных
        user_id: ID пользователя
        
    Returns:
        dict: Данные прогресса обучения
    """
    progress = db.get_training_progress(user_id)
    if not progress:
        db.init_training_progress(user_id)
        progress = db.get_training_progress(user_id)
    return progress


# === ОБРАБОТЧИКИ ОПРОСНИКОВ ===

async def show_entry_poll_q1(message: types.Message, state: FSMContext):
    """Показывает первый вопрос входного опросника."""
    keyboard = create_inline_keyboard([
        (opt, f"entry_q1_{i}") for i, opt in enumerate(ENTRY_POLL_OPTIONS["q1"])
    ])
    question_text = f"<b>Вопрос 1/4</b>\n\n{TEXTS['entry_poll_q1']}"
    await message.answer(question_text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.entry_poll_q1)


async def handle_entry_poll_q1(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает ответ на вопрос 1."""
    answer_index = int(callback.data.split("_")[-1])
    answer_text = ENTRY_POLL_OPTIONS["q1"][answer_index]
    
    # Сохраняем ответ
    data = await state.get_data()
    entry_answers = data.get("entry_poll_answers", {})
    entry_answers["q1"] = answer_text
    await state.update_data(entry_poll_answers=entry_answers)
    
    await callback.answer()
    
    # Переходим к вопросу 2
    keyboard = create_inline_keyboard([
        (opt, f"entry_q2_{i}") for i, opt in enumerate(ENTRY_POLL_OPTIONS["q2"])
    ])
    question_text = f"<b>Вопрос 2/4</b>\n\n{TEXTS['entry_poll_q2']}"
    await callback.message.edit_text(question_text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.entry_poll_q2)


async def handle_entry_poll_q2(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает ответ на вопрос 2."""
    answer_index = int(callback.data.split("_")[-1])
    answer_text = ENTRY_POLL_OPTIONS["q2"][answer_index]
    
    # Сохраняем ответ
    data = await state.get_data()
    entry_answers = data.get("entry_poll_answers", {})
    entry_answers["q2"] = answer_text
    await state.update_data(entry_poll_answers=entry_answers)
    
    await callback.answer()
    
    # Переходим к вопросу 3
    keyboard = create_inline_keyboard([
        (opt, f"entry_q3_{i}") for i, opt in enumerate(ENTRY_POLL_OPTIONS["q3"])
    ])
    question_text = f"<b>Вопрос 3/4</b>\n\n{TEXTS['entry_poll_q3']}"
    await callback.message.edit_text(question_text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.entry_poll_q3)


async def handle_entry_poll_q3(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает ответ на вопрос 3."""
    answer_index = int(callback.data.split("_")[-1])
    answer_text = ENTRY_POLL_OPTIONS["q3"][answer_index]
    
    # Сохраняем ответ
    data = await state.get_data()
    entry_answers = data.get("entry_poll_answers", {})
    entry_answers["q3"] = answer_text
    await state.update_data(entry_poll_answers=entry_answers)
    
    await callback.answer()
    
    # Переходим к вопросу 4
    keyboard = create_inline_keyboard([
        (opt, f"entry_q4_{i}") for i, opt in enumerate(ENTRY_POLL_OPTIONS["q4"])
    ])
    question_text = f"<b>Вопрос 4/4</b>\n\n{TEXTS['entry_poll_q4']}"
    await callback.message.edit_text(question_text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.entry_poll_q4)


async def handle_entry_poll_q4(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Обрабатывает ответ на вопрос 4 и завершает входной опросник."""
    answer_index = int(callback.data.split("_")[-1])
    answer_text = ENTRY_POLL_OPTIONS["q4"][answer_index]
    
    # Сохраняем ответ
    data = await state.get_data()
    entry_answers = data.get("entry_poll_answers", {})
    entry_answers["q4"] = answer_text
    await state.update_data(entry_poll_answers=entry_answers)
    
    # Логируем входной опросник
    user_id = callback.from_user.id
    session_id = data.get("session_id")
    training_logger = TrainingLogger(db)
    training_logger.log_training_step(
        user_id=user_id,
        training_type="card_conversation",
        step="entry_poll_completed",
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        session_id=session_id,
        details={"entry_poll": entry_answers}
    )
    
    await callback.answer()
    
    # Переходим к вступлению
    keyboard = create_inline_keyboard([
        ("Да, хочу 🌙", "learn_intro_yes"),
        ("Пока нет", "learn_intro_no")
    ])
    await callback.message.edit_text(TEXTS["intro"], reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.intro)


async def show_exit_poll_q1(message: types.Message, state: FSMContext):
    """Показывает первый вопрос выходного опросника."""
    keyboard = create_inline_keyboard([
        (opt, f"exit_q1_{i}") for i, opt in enumerate(EXIT_POLL_OPTIONS["q1"])
    ])
    question_text = f"<b>Вопрос 1/3</b>\n\n{TEXTS['exit_poll_q1']}"
    await message.answer(question_text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.exit_poll_q1)


async def handle_exit_poll_q1(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает ответ на выходной вопрос 1."""
    answer_index = int(callback.data.split("_")[-1])
    answer_text = EXIT_POLL_OPTIONS["q1"][answer_index]
    
    # Сохраняем ответ
    data = await state.get_data()
    exit_answers = data.get("exit_poll_answers", {})
    exit_answers["q1"] = answer_text
    await state.update_data(exit_poll_answers=exit_answers)
    
    await callback.answer()
    
    # Переходим к вопросу 2
    keyboard = create_inline_keyboard([
        (opt, f"exit_q2_{i}") for i, opt in enumerate(EXIT_POLL_OPTIONS["q2"])
    ])
    question_text = f"<b>Вопрос 2/3</b>\n\n{TEXTS['exit_poll_q2']}"
    await callback.message.edit_text(question_text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.exit_poll_q2)


async def handle_exit_poll_q2(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает ответ на выходной вопрос 2."""
    answer_index = int(callback.data.split("_")[-1])
    answer_text = EXIT_POLL_OPTIONS["q2"][answer_index]
    
    # Сохраняем ответ
    data = await state.get_data()
    exit_answers = data.get("exit_poll_answers", {})
    exit_answers["q2"] = answer_text
    await state.update_data(exit_poll_answers=exit_answers)
    
    await callback.answer()
    
    # Переходим к вопросу 3
    keyboard = create_inline_keyboard([
        (opt, f"exit_q3_{i}") for i, opt in enumerate(EXIT_POLL_OPTIONS["q3"])
    ])
    question_text = f"<b>Вопрос 3/3</b>\n\n{TEXTS['exit_poll_q3']}"
    await callback.message.edit_text(question_text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.exit_poll_q3)


async def handle_exit_poll_q3(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Обрабатывает ответ на выходной вопрос 3 и завершает выходной опросник."""
    answer_index = int(callback.data.split("_")[-1])
    answer_text = EXIT_POLL_OPTIONS["q3"][answer_index]
    
    # Сохраняем ответ
    data = await state.get_data()
    exit_answers = data.get("exit_poll_answers", {})
    exit_answers["q3"] = answer_text
    entry_answers = data.get("entry_poll_answers", {})
    session_id = data.get("session_id")
    
    await state.update_data(exit_poll_answers=exit_answers)
    
    # Логируем выходной опросник и завершение обучения
    user_id = callback.from_user.id
    training_logger = TrainingLogger(db)
    
    # Логируем выходной опросник
    training_logger.log_training_step(
        user_id=user_id,
        training_type="card_conversation",
        step="exit_poll_completed",
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        session_id=session_id,
        details={"exit_poll": exit_answers}
    )
    
    # Логируем завершение всего обучения с полными данными
    training_logger.log_training_step(
        user_id=user_id,
        training_type="card_conversation",
        step="completed",
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        session_id=session_id,
        details={
            "entry_poll": entry_answers,
            "exit_poll": exit_answers
        }
    )
    
    await callback.answer()
    
    # Показываем приглашение на фидбек
    keyboard = create_inline_keyboard([
        ("Оставить отзыв 💌", "learn_feedback"),
        ("Завершить обучение ✨", "learn_finish_final")
    ])
    await callback.message.edit_text(TEXTS["exit_feedback_invite"], reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.exit_feedback_invite)


# === ОБРАБОТЧИКИ КОМАНД ===

async def start_learning(message: types.Message, state: FSMContext, db: Database):
    """
    Точка входа /learn_cards - начало обучения.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Генерируем session_id для всего обучения
    session_id = f"learn_{user_id}_{int(datetime.now().timestamp())}"
    
    # Сохраняем session_id в состоянии
    await state.update_data(session_id=session_id, entry_poll_answers={}, exit_poll_answers={})
    
    # Логируем начало обучения
    training_logger = TrainingLogger(db)
    training_logger.log_training_step(
        user_id=user_id,
        training_type="card_conversation",
        step="started",
        username=username,
        first_name=first_name,
        session_id=session_id
    )
    
    # Получаем или создаем прогресс
    progress = await get_or_create_progress(db, user_id)
    
    # Проверяем, проходил ли пользователь теорию
    if progress and progress.get('theory_passed'):
        # Пользователь уже проходил обучение, предлагаем выбор
        keyboard = create_inline_keyboard([
            ("🔁 С входным опросом", "learn_with_poll"),
            ("🔁 Теория заново", "learn_theory"),
            ("🧪 Сразу к практике", "learn_practice")
        ])
        await message.answer(
            "Ты уже проходил обучение раньше.\nХочешь повторить?",
            reply_markup=keyboard
        )
        await state.set_state(LearnCardsFSM.choice_menu)
    else:
        # Первый раз - начинаем с входного опросника
        await show_entry_poll_q1(message, state)


async def start_practice_command(message: types.Message, state: FSMContext, db: Database):
    """
    Команда /practice - быстрая практика без теории.
    """
    user_id = message.from_user.id
    
    # Инициализируем прогресс если нужно
    await get_or_create_progress(db, user_id)
    
    # Стартуем сессию обучения
    session_id = db.start_training_session(user_id)
    await state.update_data(
        session_id=session_id,
        attempts_count=0,
        max_attempts=9999,  # неограниченное число попыток
        is_practice_mode=True
    )
    
    await message.answer(
        "🧪 <b>Быстрая практика</b>\n\n"
        "Давай сразу попробуем! Сформулируй ресурсный запрос.",
        parse_mode="HTML"
    )
    
    # Переходим сразу к примерам
    await handle_trainer_examples(message, state, db, from_callback=False)


# === ОБРАБОТЧИКИ ТЕОРЕТИЧЕСКОЙ ЧАСТИ ===

async def handle_intro_yes(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Обработка нажатия 'Да, хочу' во вступлении."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    keyboard = create_inline_keyboard([("Далее ➡️", "learn_theory_1")])
    await callback.message.answer(TEXTS["theory_1"], reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.theory_1)


async def handle_intro_no(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Обработка нажатия 'Пока нет' во вступлении."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Хорошо, возвращайся, когда будешь готова! 🌙\n\n"
        "Команда /learn_cards всегда доступна."
    )
    await state.clear()


async def handle_theory_1(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Обработка перехода к теории 2."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    keyboard = create_inline_keyboard([("Далее ➡️", "learn_theory_2")])
    await callback.message.answer(TEXTS["theory_2"], reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.theory_2)


async def handle_theory_2(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Обработка перехода к теории 3."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    keyboard = create_inline_keyboard([("Далее ➡️", "learn_theory_3")])
    await callback.message.answer(TEXTS["theory_3"], reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.theory_3)


async def handle_theory_3(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Обработка перехода к шагам."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    keyboard = create_inline_keyboard([("Попробовать на практике 🎓", "learn_steps")])
    await callback.message.answer(TEXTS["steps"], reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.steps)


async def handle_steps(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Обработка завершения теории и перехода к практике."""
    user_id = callback.from_user.id
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Отмечаем теорию как пройденную
    db.update_training_progress(user_id, {"theory_passed": True})
    
    # Стартуем сессию обучения
    session_id = db.start_training_session(user_id)
    await state.update_data(
        session_id=session_id,
        attempts_count=0,
        is_practice_mode=False
    )
    
    keyboard = create_inline_keyboard([("Давай! 💫", "learn_trainer_intro")])
    await callback.message.answer(TEXTS["trainer_intro"], reply_markup=keyboard)
    await state.set_state(LearnCardsFSM.trainer_intro)


# === ОБРАБОТЧИКИ ПРАКТИЧЕСКОЙ ЧАСТИ ===

async def handle_trainer_intro(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Переход к примерам."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await handle_trainer_examples(callback.message, state, db, from_callback=True)


async def handle_trainer_examples(message: types.Message, state: FSMContext, db: Database, from_callback: bool = True):
    """Показ примеров и переход к вводу запроса."""
    keyboard = create_inline_keyboard([
        ("Попробовать самой ✍️", "learn_trainer_input"),
        ("Не знаю, с чего начать 🤔", "learn_show_templates")
    ])
    
    await message.answer(TEXTS["trainer_examples"], reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.trainer_examples)


async def handle_show_templates(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Показ шаблонов запросов."""
    await callback.answer()
    
    templates_text = "💡 <b>Шаблоны для начала:</b>\n\n" + "\n".join(
        [f"{i+1}. {template}" for i, template in enumerate(EXAMPLE_TEMPLATES)]
    )
    templates_text += "\n\n<i>Подставь свою ситуацию и попробуй!</i>"
    
    await callback.message.answer(templates_text, parse_mode="HTML")
    # Переходим в состояние ожидания ввода запроса от пользователя
    await state.set_state(LearnCardsFSM.trainer_user_input)


async def handle_trainer_input(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Переход к вводу запроса пользователем."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await callback.message.answer(TEXTS["trainer_input"])
    await state.set_state(LearnCardsFSM.trainer_user_input)


async def handle_user_request_input(message: types.Message, state: FSMContext, db: Database):
    """
    Обработка введенного пользователем запроса.
    Анализирует запрос через ИИ и дает обратную связь.
    """
    user_id = message.from_user.id
    request_text = message.text.strip()
    
    # Валидация
    if not request_text:
        await message.answer("Пожалуйста, напиши свой запрос текстом.")
        return
    
    if len(request_text) < 5:
        await message.answer("Попробуй сформулировать запрос чуть подробнее (хотя бы 5 символов).")
        return
    
    # Показываем, что обрабатываем
    processing_msg = await message.answer("Анализирую твой запрос... ⏳")
    
    try:
        # Анализируем запрос через ИИ
        analysis = await analyze_request(request_text)
        
        # Удаляем сообщение о загрузке
        await processing_msg.delete()
        
        # Получаем данные сессии
        data = await state.get_data()
        session_id = data.get('session_id')
        attempts_count = data.get('attempts_count', 0) + 1
        is_practice_mode = data.get('is_practice_mode', False)
        max_attempts = data.get('max_attempts', 999)
        
        # Обновляем счетчик попыток
        await state.update_data(
            attempts_count=attempts_count,
            last_request=request_text,
            last_analysis=analysis
        )
        
        # Обновляем сессию в БД
        if session_id:
            # Получаем текущую сессию для сохранения всех оценок
            current_session = db.get_training_session(session_id)
            ai_feedback = current_session.get('ai_feedback', {}) if current_session else {}
            
            # Добавляем новую оценку
            if isinstance(ai_feedback, dict):
                ai_feedback[f'attempt_{attempts_count}'] = analysis
            else:
                ai_feedback = {f'attempt_{attempts_count}': analysis}
            
            # Обновляем best_score если текущая оценка лучше
            best_score = max(analysis['score'], current_session.get('best_score', 0)) if current_session else analysis['score']
            
            db.update_training_session(session_id, {
                'attempts': attempts_count,
                'best_score': best_score,
                'final_tone': analysis['tone'],
                'ai_feedback': ai_feedback
            })
        
        # Формируем ответ в зависимости от тона
        response_text = f"<b>Твой запрос:</b>\n<i>\"{request_text}\"</i>\n\n"
        
        if analysis['tone'] == 'resourceful':
            response_text += f"🌿 {analysis['message']}\n\n<b>Оценка: {analysis['score']}/100</b>"
            buttons = [
                ("Отлично! Что дальше? ✨", "learn_complete_success")
            ]
        elif analysis['tone'] == 'neutral':
            response_text += f"💫 {analysis['message']}\n\n<b>Оценка: {analysis['score']}/100</b>"
            buttons = [
                ("Попробовать иначе 🔄", "learn_retry"),
                ("Оставить так 🌿", "learn_complete_neutral")
            ]
        else:  # external
            response_text += f"🌒 {analysis['message']}\n\n<b>Оценка: {analysis['score']}/100</b>"
            
            # Проверяем, не закончились ли попытки в режиме практики
            if is_practice_mode and attempts_count >= max_attempts:
                response_text += "\n\n<i>Это была твоя последняя попытка в быстрой практике.</i>"
                buttons = [
                    ("Завершить 🌙", "learn_complete_external")
                ]
            else:
                buttons = [
                    ("Попробовать ещё ✍️", "learn_retry"),
                    ("Завершить 🌙", "learn_complete_external")
                ]
        
        keyboard = create_inline_keyboard(buttons)
        await message.answer(response_text, reply_markup=keyboard, parse_mode="HTML")
        await state.set_state(LearnCardsFSM.trainer_feedback)
        
    except Exception as e:
        logger.error(f"Error analyzing user request for user {user_id}: {e}", exc_info=True)
        await processing_msg.delete()
        await message.answer(
            "Произошла ошибка при анализе запроса. Попробуй еще раз или напиши /learn_cards для начала заново."
        )


async def handle_show_examples_again(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Повторный показ примеров."""
    await callback.answer()
    
    await callback.message.answer(TEXTS["trainer_examples"], parse_mode="HTML")
    await callback.message.answer(
        "Попробуй еще раз! Напиши свой запрос, используя примеры как ориентир.",
    )
    await state.set_state(LearnCardsFSM.trainer_user_input)


async def handle_retry(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Обработка повторной попытки."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await callback.message.answer(
        "Отлично! Попробуй переформулировать свой запрос, чтобы он стал ближе к тебе.\n\n"
        "Вспомни:\n"
        "• Используй 'я', 'мне', 'мой'\n"
        "• Спрашивай о своих чувствах\n"
        "• Избегай 'почему', 'когда', 'будет ли'"
    )
    await state.set_state(LearnCardsFSM.trainer_user_retry)


async def handle_user_retry_input(message: types.Message, state: FSMContext, db: Database):
    """Обработка переформулированного запроса (та же логика, что и первая попытка)."""
    # Используем ту же логику, что и для первого ввода
    await handle_user_request_input(message, state, db)


# === ОБРАБОТЧИКИ ЗАВЕРШЕНИЯ ===

async def handle_complete_success(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Завершение с ресурсным запросом."""
    await handle_training_done(callback, state, db, success_level='resourceful')


async def handle_complete_neutral(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Завершение с нейтральным запросом."""
    await handle_training_done(callback, state, db, success_level='neutral')


async def handle_complete_external(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Завершение с внешним запросом."""
    await handle_training_done(callback, state, db, success_level='external')


async def handle_training_done(callback: types.CallbackQuery, state: FSMContext, db: Database, success_level: str = 'neutral'):
    """
    Общий обработчик завершения обучения.
    
    Args:
        callback: Callback query
        state: FSM контекст
        db: База данных
        success_level: Уровень успеха ('resourceful', 'neutral', 'external')
    """
    user_id = callback.from_user.id
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Получаем данные сессии
    data = await state.get_data()
    session_id = data.get('session_id')
    last_analysis = data.get('last_analysis', {})
    
    # Завершаем сессию
    if session_id:
        now = datetime.now(TIMEZONE).isoformat()
        db.update_training_session(session_id, {
            'finished_at': now
        })
        
        # Обновляем общий прогресс
        current_progress = db.get_training_progress(user_id)
        if current_progress:
            sessions_completed = current_progress.get('sessions_completed', 0) + 1
            best_score = max(last_analysis.get('score', 0), current_progress.get('best_score', 0))
            
            # Обновляем consecutive_resourceful
            if success_level == 'resourceful':
                consecutive = current_progress.get('consecutive_resourceful', 0) + 1
            else:
                consecutive = 0
            
            db.update_training_progress(user_id, {
                'sessions_completed': sessions_completed,
                'best_score': best_score,
                'consecutive_resourceful': consecutive,
                'last_session_at': now
            })
    
    # Финальное сообщение
    congrats_text = ""
    if success_level == 'resourceful':
        congrats_text = (
            "🌙 Отлично! Теперь ты знаешь, как говорить с картой.\n\n"
            "Твой запрос направлен внутрь, и карта сможет откликнуться на него глубоко и точно."
        )
    elif success_level == 'neutral':
        congrats_text = (
            "🌙 Хорошая работа! Ты на правильном пути.\n\n"
            "С практикой твои запросы будут становиться все более глубокими и ресурсными."
        )
    else:
        congrats_text = (
            "🌙 Спасибо за практику!\n\n"
            "Формулировать ресурсные запросы — это навык. Чем больше практики, тем легче будет."
        )
    
    # Вместо финального сообщения показываем выходной опросник
    await callback.message.answer(congrats_text)
    
    # Переходим к выходному опроснику
    await show_exit_poll_q1(callback.message, state)


async def handle_draw_card(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Переход к вытягиванию карты дня."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Очищаем состояние обучения
    data = await state.get_data()
    last_request = data.get('last_request', '')
    
    await state.clear()
    
    # Импортируем функцию для карты дня
    from modules.card_of_the_day import handle_card_request
    
    # Устанавливаем флаг, что пришли из обучения
    await state.update_data(from_learning=True, learning_request=last_request)
    
    await callback.message.answer(
        "Отлично! Сейчас вытянем для тебя карту. ✨"
    )
    
    # Вызываем флоу карты дня
    await handle_card_request(callback.message, state, db, logger)


async def handle_feedback_choice(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Предлагает оставить фидбек через /feedback."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await callback.message.answer(
        "💌 Отлично! Набери команду /feedback, чтобы поделиться своими мыслями.\n\n"
        "Спасибо за прохождение обучения! 🌿\n\n"
        "Команды:\n"
        "/learn_cards — полное обучение\n"
        "/practice — быстрая практика"
    )
    
    await state.clear()


async def handle_finish_final(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Финальное завершение обучения после опросника."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await callback.message.answer(
        "🌿 Спасибо за прохождение обучения!\n\n"
        "Теперь ты знаешь, как формулировать запросы к карте.\n"
        "Возвращайся к практике, когда захочешь.\n\n"
        "Команды:\n"
        "/learn_cards — полное обучение\n"
        "/practice — быстрая практика"
    )
    
    await state.clear()


async def handle_finish(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Завершение без вытягивания карты."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await callback.message.answer(
        "Отлично! Возвращайся к практике когда захочешь.\n\n"
        "Команды:\n"
        "/learn_cards — полное обучение\n"
        "/practice — быстрая практика"
    )
    
    await state.clear()


# === ОБРАБОТЧИКИ ВЫБОРА (ТЕОРИЯ/ПРАКТИКА) ===

async def handle_choice_with_poll(callback: types.CallbackQuery, state: FSMContext):
    """Выбор прохождения с входным опросом."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Начинаем с входного опросника
    await show_entry_poll_q1(callback.message, state)


async def handle_choice_theory(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Выбор повторного прохождения теории."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Начинаем теорию с самого начала
    keyboard = create_inline_keyboard([("Далее ➡️", "learn_theory_1")])
    await callback.message.answer(TEXTS["theory_1"], reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(LearnCardsFSM.theory_1)


async def handle_choice_practice(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Выбор сразу практики."""
    user_id = callback.from_user.id
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Стартуем сессию обучения
    session_id = db.start_training_session(user_id)
    await state.update_data(
        session_id=session_id,
        attempts_count=0,
        is_practice_mode=False
    )
    
    await handle_trainer_examples(callback.message, state, db, from_callback=True)


# === РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ===

def register_learn_cards_handlers(dp, db: Database, logger_service, user_manager):
    """
    Регистрирует все обработчики модуля обучения.
    
    Args:
        dp: Dispatcher
        db: Database instance
        logger_service: Logging service
        user_manager: User manager
    """
    # Создаем partial функции с db
    from functools import partial
    
    # Команды
    dp.message.register(
        partial(start_learning, db=db),
        Command("learn_cards")
    )
    
    dp.message.register(
        partial(start_practice_command, db=db),
        Command("practice")
    )
    
    # Обработчики входного опросника
    dp.callback_query.register(
        handle_entry_poll_q1,
        F.data.startswith("entry_q1_")
    )
    
    dp.callback_query.register(
        handle_entry_poll_q2,
        F.data.startswith("entry_q2_")
    )
    
    dp.callback_query.register(
        handle_entry_poll_q3,
        F.data.startswith("entry_q3_")
    )
    
    dp.callback_query.register(
        partial(handle_entry_poll_q4, db=db),
        F.data.startswith("entry_q4_")
    )
    
    # Обработчики выходного опросника
    dp.callback_query.register(
        handle_exit_poll_q1,
        F.data.startswith("exit_q1_")
    )
    
    dp.callback_query.register(
        handle_exit_poll_q2,
        F.data.startswith("exit_q2_")
    )
    
    dp.callback_query.register(
        partial(handle_exit_poll_q3, db=db),
        F.data.startswith("exit_q3_")
    )
    
    # Обработчики финальных кнопок после выходного опросника
    dp.callback_query.register(
        partial(handle_feedback_choice, db=db),
        F.data == "learn_feedback"
    )
    
    dp.callback_query.register(
        partial(handle_finish_final, db=db),
        F.data == "learn_finish_final"
    )
    
    # Обработчики callback'ов теоретической части
    dp.callback_query.register(
        partial(handle_intro_yes, db=db),
        F.data == "learn_intro_yes"
    )
    
    dp.callback_query.register(
        partial(handle_intro_no, db=db),
        F.data == "learn_intro_no"
    )
    
    dp.callback_query.register(
        partial(handle_theory_1, db=db),
        F.data == "learn_theory_1"
    )
    
    dp.callback_query.register(
        partial(handle_theory_2, db=db),
        F.data == "learn_theory_2"
    )
    
    dp.callback_query.register(
        partial(handle_theory_3, db=db),
        F.data == "learn_theory_3"
    )
    
    dp.callback_query.register(
        partial(handle_steps, db=db),
        F.data == "learn_steps"
    )
    
    # Обработчики практической части
    dp.callback_query.register(
        partial(handle_trainer_intro, db=db),
        F.data == "learn_trainer_intro"
    )
    
    dp.callback_query.register(
        partial(handle_trainer_input, db=db),
        F.data == "learn_trainer_input"
    )
    
    dp.callback_query.register(
        partial(handle_show_templates, db=db),
        F.data == "learn_show_templates"
    )
    
    dp.callback_query.register(
        partial(handle_show_examples_again, db=db),
        F.data == "learn_show_examples_again"
    )
    
    dp.callback_query.register(
        partial(handle_retry, db=db),
        F.data == "learn_retry"
    )
    
    # Обработчики завершения
    dp.callback_query.register(
        partial(handle_complete_success, db=db),
        F.data == "learn_complete_success"
    )
    
    dp.callback_query.register(
        partial(handle_complete_neutral, db=db),
        F.data == "learn_complete_neutral"
    )
    
    dp.callback_query.register(
        partial(handle_complete_external, db=db),
        F.data == "learn_complete_external"
    )
    
    dp.callback_query.register(
        partial(handle_draw_card, db=db),
        F.data == "learn_draw_card"
    )
    
    dp.callback_query.register(
        partial(handle_finish, db=db),
        F.data == "learn_finish"
    )
    
    # Обработчики выбора теория/практика
    dp.callback_query.register(
        handle_choice_with_poll,
        F.data == "learn_with_poll"
    )
    
    dp.callback_query.register(
        partial(handle_choice_theory, db=db),
        F.data == "learn_theory"
    )
    
    dp.callback_query.register(
        partial(handle_choice_practice, db=db),
        F.data == "learn_practice"
    )
    
    # Обработчики текстового ввода
    dp.message.register(
        partial(handle_user_request_input, db=db),
        LearnCardsFSM.trainer_user_input
    )
    
    dp.message.register(
        partial(handle_user_retry_input, db=db),
        LearnCardsFSM.trainer_user_retry
    )
    
    logger.info("Learn cards handlers registered successfully")

