from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    waiting_for_name = State()
    waiting_for_reminder_time = State()
    waiting_for_feedback = State()
    waiting_for_request_text = State()
    waiting_for_initial_response = State()
    waiting_for_first_grok_response = State()
    waiting_for_second_grok_response = State()
    waiting_for_third_grok_response = State()
    waiting_for_initial_resource = State()
    waiting_for_scenario_choice = State()
    waiting_for_card_draw = State()
    waiting_for_continue_choice = State()
    waiting_for_final_resource = State()
    waiting_for_recovery_method = State()
    waiting_for_card_feedback = State()

class UserManager:
    def __init__(self, db):
        self.db = db

    async def set_name(self, user_id, name):
        self.db.update_user(user_id, {"name": name})

    async def set_reminder(self, user_id, time):
        self.db.update_user(user_id, {"reminder_time": time})

    async def set_bonus_available(self, user_id, value):
        self.db.update_user(user_id, {"bonus_available": value})
