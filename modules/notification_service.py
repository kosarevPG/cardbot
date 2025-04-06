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
                    name = self.db.get_user(user_id)["name"]
                    text = f"{name}, привет! Пришло время вытянуть свою карту дня. ✨" if name else "Привет! Пришло время вытянуть свою карту дня. ✨"
                    await self.bot.send_message(user_id, text)
            await asyncio.sleep(60)

    async def send_broadcast(self, broadcast_data):
        now = datetime.now(TIMEZONE)
        if now >= broadcast_data["datetime"]:
            recipients = self.db.get_all_users() if broadcast_data["recipients"] == "all" else broadcast_data["recipients"]
            for user_id in recipients:
                name = self.db.get_user(user_id)["name"]
                text = f"{name}, {broadcast_data['text']}" if name else broadcast_data["text"]
                await self.bot.send_message(user_id, text)
