import random
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile  # Добавляем FSInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import asyncio

# Настройки
TOKEN = "8054930534:AAFDdyp5_xiX0ZPQnSEZKpfOhk2PCdchKvg"
CHANNEL_ID = "@TopPsyGame"

# Инициализация бота
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Логирование
logging.basicConfig(level=logging.INFO)

# Middleware для проверки подписки
class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            try:
                user_status = await bot.get_chat_member(CHANNEL_ID, user_id)
                if user_status.status not in ["member", "administrator", "creator"]:
                    await event.answer(
                        "Для начала подпишись на <a href='https://t.me/TopPsyGame'>канал</a>",
                        disable_web_page_preview=True
                    )
                    return
            except Exception as e:
                logging.error(f"Ошибка проверки подписки: {e}")
                await event.answer("Произошла ошибка. Попробуй позже.")
                return
        return await handler(event, data)

# Регистрация middleware
dp.message.middleware(SubscriptionMiddleware())

# Команда /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Карта дня", callback_data="draw_card")]
    ])
    await message.answer(
        "Вы подписаны! Нажмите кнопку, чтобы вытянуть карту.",
        reply_markup=keyboard,
        protect_content=True
    )

# Обработка кнопки "Карта дня"
@dp.callback_query(lambda c: c.data == "draw_card")
async def send_card(callback_query: types.CallbackQuery):
    try:
        card_numbers = list(range(1, 61))
        random.shuffle(card_numbers)
        card_number = card_numbers[0]
        card_path = f"cards/card_{card_number}.jpg"
        # Используем FSInputFile вместо открытого файла
        photo = FSInputFile(card_path)
        await bot.send_photo(
            callback_query.from_user.id,
            photo,
            protect_content=True
        )
        await callback_query.answer("Вот твоя карта дня!")
    except FileNotFoundError:
        await bot.send_message(
            callback_query.from_user.id,
            "Ошибка: карта не найдена. Свяжитесь с создателем бота.",
            protect_content=True
        )
        await callback_query.answer()
    except Exception as e:
        logging.error(f"Ошибка при отправке карты: {e}")
        await bot.send_message(
            callback_query.from_user.id,
            "Произошла ошибка. Попробуй позже.",
            protect_content=True
        )
        await callback_query.answer()

# Запуск бота
async def main():
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())