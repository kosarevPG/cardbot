from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    waiting_for_name = State()
    waiting_for_reminder_time = State()
    # ... остальные состояния

class UserManager:
    def __init__(self, db):
        self.db = db

    async def set_name(self, user_id, name):
        self.db.update_user(user_id, {"name": name})

    async def set_reminder(self, user_id, time):
        self.db.update_user(user_id, {"reminder_time": time})
