import logging
import logging.handlers
import os
from datetime import datetime
try:
    from config_local import TIMEZONE
except ImportError:
    from config import TIMEZONE

class LoggingService:
    def __init__(self, log_dir='logs'):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # Убираем basicConfig отсюда, настройка должна быть в main.py
        # logging.basicConfig(level=logging.INFO)
        
        # Настройка основного логгера
        self.logger = logging.getLogger('app_logger')
        self.logger.setLevel(logging.INFO)

    async def log_action(self, user_id, action, details=None):
        try:
            chat = await self.db.bot.get_chat(user_id)
            username = chat.username or ""
        except Exception as e:
            logging.warning(f"Could not get chat info for user {user_id}: {e}")
            username = ""
        
        try:
            user_data = self.db.get_user(user_id)
            name = user_data.get("name", "Unknown") if user_data else "Unknown"
        except Exception as e:
            logging.warning(f"Could not get user data for user {user_id}: {e}")
            name = "Unknown"
        
        timestamp = datetime.now(TIMEZONE).isoformat()
        self.db.save_action(user_id, username, name, action, details or {}, timestamp)
        logging.info(f"User {user_id}: {action}, details: {details}")

    def get_logs_for_today(self):
        today = datetime.now(TIMEZONE).date()
        logs = self.db.get_actions()
        return [log for log in logs if datetime.fromisoformat(log["timestamp"]).astimezone(TIMEZONE).date() == today]
