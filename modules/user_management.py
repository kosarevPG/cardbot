# код/user_management.py
from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    # Existing states
    waiting_for_name = State()
    waiting_for_reminder_time = State()
    waiting_for_feedback = State() # General feedback state

    # Card flow states (renamed/added for clarity)
    waiting_for_initial_resource = State()    # NEW: Step 1 - Resource check
    waiting_for_request_type_choice = State() # NEW: Step 2 - Mental/Typed request choice
    waiting_for_request_text_input = State()  # Step 3a - If Typed request chosen
    waiting_for_initial_response = State()    # Step 4 - After card is shown, user association
    waiting_for_exploration_choice = State()  # NEW: Step 5 - Explore further?
    waiting_for_first_grok_response = State() # Step 6a - If exploring, waiting for response to Q1
    waiting_for_second_grok_response = State()# Step 6b - Waiting for response to Q2
    waiting_for_third_grok_response = State() # Step 6c - Waiting for response to Q3
    waiting_for_final_resource = State()      # NEW: Step 7 - Final resource check
    waiting_for_recharge_method = State()     # NEW: Step 8 - If final resource low

class UserManager:
    def __init__(self, db):
        self.db = db

    async def set_name(self, user_id, name):
        # Ensure user exists before updating
        user_data = self.db.get_user(user_id)
        if user_data:
            self.db.update_user(user_id, {"name": name})
        else:
            # This case should be less likely now with get_user creating defaults
            logger.warning(f"UserManager: Attempted to set name for non-existent user {user_id}")


    async def set_reminder(self, user_id, time):
        user_data = self.db.get_user(user_id)
        if user_data:
            self.db.update_user(user_id, {"reminder_time": time})
        else:
            logger.warning(f"UserManager: Attempted to set reminder for non-existent user {user_id}")

    async def set_bonus_available(self, user_id, value):
        user_data = self.db.get_user(user_id)
        if user_data:
            self.db.update_user(user_id, {"bonus_available": value})
        else:
            logger.warning(f"UserManager: Attempted to set bonus for non-existent user {user_id}")

    # NEW: Helper to update profile resource/recharge info
    async def update_profile_data(self, user_id, data_to_update):
        """Updates specific fields in the user profile."""
        # It's generally better to update profile via build_user_profile
        # But for single fields like resource status, a direct update might be okay
        # Let's stick to logging for now and let build_user_profile handle the update
        # based on logs later. If direct update is needed:
        # current_profile = self.db.get_user_profile(user_id) or {"user_id": user_id}
        # current_profile.update(data_to_update)
        # self.db.update_user_profile(user_id, current_profile)
        pass # For now, just log actions, profile rebuild will pick it up.
