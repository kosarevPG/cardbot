# modules/learn_cards.py
# Модуль обучения "Как разговаривать с картой"

import logging
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
from database.db import Database

logger = logging.getLogger(__name__)

# === КОНСТАНТЫ ===

# Тексты обучающего модуля
TEXTS = {
    "intro": (
        "🌿 Добро пожаловать в практику \"Как разговаривать с картой\".\n\n"
        "Карта — не ответ, а зеркало. Чтобы она заговорила, важно задать живой вопрос.\n\n"
        "Хочешь узнать, как это делать?"
    ),
    "theory_1": (
        "🌀 <b>Что такое МАК-карты</b>\n\n"
        "Карты отражают твои внутренние состояния через образы.\n\n"
        "Здесь нет правильных ответов — есть только отклики."
    ),
    "theory_2": (
        "🔮 <b>Зачем нужен запрос</b>\n\n"
        "Запрос — это луч внимания внутрь.\n\n"
        "Без него карта молчит. С ним — она говорит."
    ),
    "theory_3": (
        "⚠️ <b>Типичные ошибки</b>\n\n"
        "Самые частые ошибки:\n"
        "• \"Почему он так делает?\"\n"
        "• \"Будет ли у меня успех?\"\n"
        "• \"Мне плохо.\"\n\n"
        "🌿 Лучше спросить:\n"
        "• \"Что я чувствую, когда он так делает?\"\n"
        "• \"Что помогает мне понять, что со мной происходит?\""
    ),
    "steps": (
        "✨ <b>Три шага к живому запросу</b>\n\n"
        "1️⃣ От ситуации — что со мной происходит?\n\n"
        "2️⃣ К чувству — что я сейчас чувствую?\n\n"
        "3️⃣ К намерению — что я хочу понять, отпустить или принять?"
    ),
    "trainer_intro": (
        "Сейчас ты потренируешься формулировать запрос.\n\n"
        "Я покажу примеры, а потом — твоя очередь."
    ),
    "trainer_examples": (
        "Посмотри на эти примеры:\n\n"
        "✦ <i>\"Почему он не звонит?\"</i> → 🔄 <i>\"Что я чувствую, когда он молчит?\"</i>\n\n"
        "✦ <i>\"Когда я стану успешной?\"</i> → 🔄 <i>\"Что помогает мне почувствовать успех уже сейчас?\"</i>\n\n"
        "Видишь разницу? Фокус смещается с внешнего на внутреннее, с \"они\" на \"я\"."
    ),
    "trainer_input": (
        "Теперь твоя очередь! ✍️\n\n"
        "Напиши свой запрос к карте. Не бойся ошибок — я помогу, если нужно."
    ),
    "choice_menu": (
        "Хочешь освежить теорию или сразу потренироваться?"
    ),
}

# Примеры запросов для быстрой помощи
EXAMPLE_TEMPLATES = [
    "Что я чувствую в отношении [ситуация]?",
    "Что помогает мне понять [что происходит]?",
    "Что мне важно сейчас про [тема]?"
]


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


# === ОБРАБОТЧИКИ КОМАНД ===

async def start_learning(message: types.Message, state: FSMContext, db: Database):
    """
    Точка входа /learn_cards - начало обучения.
    """
    user_id = message.from_user.id
    
    # Получаем или создаем прогресс
    progress = await get_or_create_progress(db, user_id)
    
    # Проверяем, проходил ли пользователь теорию
    if progress and progress.get('theory_passed'):
        # Пользователь уже проходил обучение, предлагаем выбор
        keyboard = create_inline_keyboard([
            ("🔁 Теория заново", "learn_theory"),
            ("🧪 Сразу к практике", "learn_practice")
        ])
        await message.answer(TEXTS["choice_menu"], reply_markup=keyboard)
    else:
        # Первый раз - показываем вступление
        keyboard = create_inline_keyboard([
            ("Да, хочу 🌙", "learn_intro_yes"),
            ("Пока нет", "learn_intro_no")
        ])
        await message.answer(TEXTS["intro"], reply_markup=keyboard)
        await state.set_state(LearnCardsFSM.intro)


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
        max_attempts=2,  # Для /practice лимит 2 попытки
        is_practice_mode=True
    )
    
    await message.answer(
        "🧪 <b>Быстрая практика</b>\n\n"
        "Давай сразу попробуем! У тебя будет 2 попытки сформулировать ресурсный запрос.",
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
                    ("Попробовать снова 🔄", "learn_retry"),
                    ("Посмотреть примеры 👀", "learn_show_examples_again")
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
    
    congrats_text += "\n\nХочешь проверить, как карта откликнется на твой запрос?"
    
    keyboard = create_inline_keyboard([
        ("Да, вытянуть карту 🔮", "learn_draw_card"),
        ("Позже 🌙", "learn_finish")
    ])
    
    await callback.message.answer(congrats_text, reply_markup=keyboard)
    await state.set_state(LearnCardsFSM.training_done)


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


async def handle_finish(callback: types.CallbackQuery, state: FSMContext, db: Database):
    """Завершение без вытягивания карты."""
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await callback.message.answer(
        "Отлично! Возвращайся к практике когда захочешь.\n\n"
        "Команды:\n"
        "/learn_cards — полное обучение\n"
        "/practice — быстрая практика (2 попытки)"
    )
    
    await state.clear()


# === ОБРАБОТЧИКИ ВЫБОРА (ТЕОРИЯ/ПРАКТИКА) ===

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

