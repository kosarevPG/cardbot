import asyncio
from datetime import datetime
from config import TIMEZONE

class NotificationService:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    async def check_reminders(self):
        while True:
            now = datetime.now(TIMEZONE)
            current_time = now.strftime("%H:%M")
            today = now.date()
            for user_id, reminder_time in self.db.get_reminder_times().items():
                if current_time == reminder_time and self.db.is_card_available(user_id, today):
                    await self.bot.send_message(user_id, "Пришло время вытянуть карту дня! ✨")
            await asyncio.sleep(60)

    async def send_broadcast(self, broadcast_data):
        recipients = self.db.get_all_users() if broadcast_data["recipients"] == "all" else broadcast_data["recipients"]
        for user_id in recipients:
            await self.bot.send_message(user_id, broadcast_data["text"])
