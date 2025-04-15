import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class LoggingService:
    def __init__(self, db):
        self.db = db

    async def log_action(self, user_id, action, details):
        try:
            details_json = json.dumps(details, ensure_ascii=False)
            timestamp = datetime.now().isoformat()
            with self.db.conn:
                self.db.conn.execute(
                    "INSERT INTO logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                    (user_id, action, details_json, timestamp)
                )
            logger.info(f"Logged action for user {user_id}: {action}")
        except Exception as e:
            logger.error(f"Failed to log action for user {user_id}: {e}")
