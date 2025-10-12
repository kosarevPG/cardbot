# код/user_management.py
from aiogram.fsm.state import State, StatesGroup
import logging

logger = logging.getLogger(__name__)

class UserState(StatesGroup):
    # Стандартные состояния
    waiting_for_name = State()
    # waiting_for_reminder_time = State() # Старое состояние - больше не используем
    waiting_for_feedback = State()

    # --- Новые состояния для напоминаний ---
    waiting_for_morning_reminder_time = State()
    waiting_for_evening_reminder_time = State()
    # ------------------------------------

    # --- Флоу Карты Дня ---
    waiting_for_deck_choice = State()  # выбор колоды
    waiting_for_initial_resource = State()
    waiting_for_request_type_choice = State()
    waiting_for_request_text_input = State()
    waiting_for_initial_response = State()
    waiting_for_emotion_choice = State()
    waiting_for_custom_response = State()
    waiting_for_exploration_choice = State()
    waiting_for_first_grok_response = State()
    waiting_for_second_grok_response = State()
    waiting_for_third_grok_response = State()
    waiting_for_final_resource = State()
    waiting_for_recharge_method = State()
    waiting_for_recharge_method_choice = State()

    # --- Состояния для Итога Дня ---
    waiting_for_good_moments = State()
    waiting_for_gratitude = State()
    waiting_for_hard_moments = State()


# --- Состояния для обучающего модуля "Как разговаривать с картой" ---
class LearnCardsFSM(StatesGroup):
    # Входной опросник
    entry_poll_q1 = State()  # Вопрос 1: Что знаешь о МАК
    entry_poll_q2 = State()  # Вопрос 2: Как формулируешь запрос
    entry_poll_q3 = State()  # Вопрос 3: Ожидания
    entry_poll_q4 = State()  # Вопрос 4: Что ближе
    
    # Основное обучение
    intro = State()  # Вступление
    choice_menu = State()  # Выбор: теория или тренажер
    theory_1 = State()  # Что такое МАК-карты
    theory_2 = State()  # Зачем нужен запрос
    theory_3 = State()  # Типичные ошибки
    steps = State()  # Три шага к живому запросу
    trainer_intro = State()  # Подготовка к практике
    trainer_examples = State()  # Примеры запросов
    trainer_user_input = State()  # Ввод запроса пользователем
    trainer_feedback = State()  # Анализ ИИ
    trainer_user_retry = State()  # Переформулировка
    
    # Выходной опросник
    exit_poll_q1 = State()  # Вопрос 1: Насколько понятно
    exit_poll_q2 = State()  # Вопрос 2: Что изменилось
    exit_poll_q3 = State()  # Вопрос 3: Как чувствуешь себя
    exit_feedback_invite = State()  # Приглашение на фидбек
    training_done = State()  # Завершение


class UserManager:
    # --- Код UserManager остается БЕЗ ИЗМЕНЕНИЙ ---
    def __init__(self, db):
        self.db = db

    async def set_name(self, user_id, name):
        user_data = self.db.get_user(user_id)
        if not user_data: logger.warning(f"UserManager: User {user_id} not found when trying to set name...")
        self.db.update_user(user_id, {"name": name})

    async def set_reminder(self, user_id, morning_time, evening_time): # Уже принимает оба времени
        """Устанавливает утреннее и вечернее время напоминания."""
        user_data = self.db.get_user(user_id)
        if not user_data: logger.warning(f"UserManager: User {user_id} not found when trying to set reminder.")
        self.db.update_user(user_id, {
            "reminder_time": morning_time, # Может быть None
            "reminder_time_evening": evening_time # Может быть None
        })

    async def clear_reminders(self, user_id):
        """Сбрасывает оба времени напоминания."""
        user_data = self.db.get_user(user_id)
        if not user_data: logger.warning(f"UserManager: User {user_id} not found when trying to clear reminders.")
        self.db.update_user(user_id, {"reminder_time": None, "reminder_time_evening": None})

    async def set_bonus_available(self, user_id, value):
        user_data = self.db.get_user(user_id)
        if not user_data: logger.warning(f"UserManager: User {user_id} not found when trying to set bonus.")
        self.db.update_user(user_id, {"bonus_available": value})
