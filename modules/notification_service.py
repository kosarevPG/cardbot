import asyncio
from datetime import datetime
from config import TIMEZONE
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.running = False
        self.task = None
        logging.basicConfig(level=logging.INFO)

    async def start(self):
        """Запускает фоновую задачу для проверки напоминаний."""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self.check_reminders())
            logger.info("Notification service started")

    async def stop(self):
        """Останавливает фоновую задачу для проверки напоминаний."""
        if self.running:
            self.running = False
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            logger.info("Notification service stopped")

    async def check_reminders(self):
        """Проверяет и отправляет напоминания пользователям."""
        while self.running:
            try:
                now = datetime.now(TIMEZONE)
                current_time = now.strftime("%H:%M")
                today = now.date()
                for user_id, reminder_time in self.db.get_reminder_times().items():
                    if current_time == reminder_time and self.db.is_card_available(user_id, today):
                        name = self.db.get_user(user_id)["name"]
                        text = f"{name}, привет! Пришло время вытянуть свою карту дня. ✨" if name else "Привет! Пришло время вытянуть свою карту дня. ✨"
                        try:
                            await self.bot.send_message(user_id, text)
                            logger.info(f"Reminder sent to user {user_id} at {now}")
                        except Exception as e:
                            logger.error(f"Failed to send reminder to user {user_id}: {e}")
            except Exception as e:
                logger.error(f"Error in check_reminders loop: {e}")
            await asyncio.sleep(60)

    async def send_broadcast(self, broadcast_data):
        """Отправляет рассылку указанным получателям в заданное время."""
        logger.info(f"Starting broadcast with datetime: {broadcast_data['datetime']}, recipients: {broadcast_data['recipients']}")

        while True:
            try:
                now = datetime.now(TIMEZONE)
                logger.info(f"Current time: {now}, Target time: {broadcast_data['datetime']}")

                if now >= broadcast_data["datetime"]:
                    recipients = self.db.get_all_users() if broadcast_data["recipients"] == "all" else broadcast_data["recipients"]
                    for user_id in recipients:
                        name = self.db.get_user(user_id)["name"]
                        text = f"{name}, {broadcast_data['text']}" if name else broadcast_data["text"]
                        try:
                            await self.bot.send_message(user_id, text)
                            logger.info(f"Broadcast sent to user {user_id} at {now}")
                        except Exception as e:
                            logger.error(f"Failed to send broadcast to user {user_id}: {e}")
                    break
                else:
                    time_to_wait = (broadcast_data["datetime"] - now).total_seconds()
                    wait_seconds = min(time_to_wait, 60)
                    logger.info(f"Waiting {wait_seconds} seconds until broadcast time")
                    await asyncio.sleep(wait_seconds)
            except Exception as e:
                logger.error(f"Error in send_broadcast loop: {e}")
                break
