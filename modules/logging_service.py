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

    async def log_action(self, user_id, action, details=None, username=None):
        """
        Записывает действие пользователя.

        Раньше здесь на КАЖДОЕ действие делался запрос bot.get_chat(user_id) — только
        чтобы узнать username. Это лишний round-trip к Telegram в каждом хендлере, а при
        проблемах со связью он вешал обработку апдейта на таймаут в 60 секунд.
        Username и так есть в таблице users (обновляется в обработчике /start), и его же
        можно передать из апдейта параметром. К Telegram больше не ходим.
        """
        name = "Unknown"
        db_username = ""
        try:
            user_data = self.db.get_user(user_id)
            if user_data:
                name = user_data.get("name") or "Unknown"
                db_username = user_data.get("username") or ""
        except Exception as e:
            logging.warning(f"Could not get user data for user {user_id}: {e}")

        timestamp = datetime.now(TIMEZONE).isoformat()
        self.db.save_action(
            user_id,
            username if username is not None else db_username,
            name, action, details or {}, timestamp,
        )
        logging.info(f"User {user_id}: {action}, details: {details}")

    def get_logs_for_today(self):
        today = datetime.now(TIMEZONE).date()
        logs = self.db.get_actions()
        return [log for log in logs if datetime.fromisoformat(log["timestamp"]).astimezone(TIMEZONE).date() == today]
