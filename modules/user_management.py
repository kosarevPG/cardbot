# код/user_management.py
from aiogram.fsm.state import State, StatesGroup
import logging # Добавим логирование

# Настраиваем логгер для этого модуля
logger = logging.getLogger(__name__)

class UserState(StatesGroup):
    # Стандартные состояния
    waiting_for_name = State()
    waiting_for_reminder_time = State()
    waiting_for_feedback = State() # Общий фидбек

    # === Новый флоу Карты Дня ===
    # Шаг 1: Ожидание выбора начального ресурса
    waiting_for_initial_resource = State()
    # Шаг 2: Ожидание выбора типа запроса (в уме / написать)
    waiting_for_request_type_choice = State()
    # Шаг 3а: Ожидание ввода текста запроса (если выбран)
    waiting_for_request_text_input = State()
    # Шаг 4: Ожидание первой ассоциации на карту
    waiting_for_initial_response = State()
    # Шаг 5: Ожидание выбора: исследовать дальше или завершить
    waiting_for_exploration_choice = State()
    # Шаг 6: Исследование с Grok (если выбрано)
    waiting_for_first_grok_response = State() # Ожидание ответа на 1й вопрос Grok
    waiting_for_second_grok_response = State()# Ожидание ответа на 2й вопрос Grok
    waiting_for_third_grok_response = State() # Ожидание ответа на 3й вопрос Grok
    # Шаг 7: Ожидание выбора конечного ресурса
    waiting_for_final_resource = State()
    # Шаг 8: Ожидание ввода способа восстановления (если ресурс низкий)
    waiting_for_recharge_method = State()

class UserManager:
    def __init__(self, db):
        self.db = db

    async def set_name(self, user_id, name):
        # Убедимся, что пользователь существует, перед обновлением
        # get_user теперь создает пользователя, если его нет, так что проверка не так критична,
        # но оставим лог на всякий случай
        user_data = self.db.get_user(user_id)
        if not user_data:
             logger.warning(f"UserManager: User {user_id} not found when trying to set name (should have been created).")
        self.db.update_user(user_id, {"name": name})


    async def set_reminder(self, user_id, time):
        user_data = self.db.get_user(user_id)
        if not user_data:
             logger.warning(f"UserManager: User {user_id} not found when trying to set reminder.")
        self.db.update_user(user_id, {"reminder_time": time})

    async def set_bonus_available(self, user_id, value):
        user_data = self.db.get_user(user_id)
        if not user_data:
             logger.warning(f"UserManager: User {user_id} not found when trying to set bonus.")
        self.db.update_user(user_id, {"bonus_available": value})

    # Прямое обновление профиля убрано, т.к. лучше делать через build_user_profile
    # на основе логов для консистентности.
