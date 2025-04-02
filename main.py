import logging
from aiogram import Bot
import asyncio

# Настройки
TOKEN = "8054930534:AAFDdyp5_xiX0ZPQnSEZKpfOhk2PCdchKvg"

# Инициализация бота
bot = Bot(token=TOKEN)

# Логирование
logging.basicConfig(level=logging.INFO)

async def main():
    logging.info("Bot starting...")
    try:
        await bot.send_message(6682555021, "Test message from Amvera")
        logging.info("Test message sent successfully")
    except Exception as e:
        logging.error(f"Failed to send test message: {e}")
    finally:
        await bot.session.close()
        logging.info("Bot session closed")

if __name__ == "__main__":
    asyncio.run(main())