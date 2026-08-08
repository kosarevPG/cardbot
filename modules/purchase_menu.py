from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.db import Database
from modules.card_of_the_day import get_main_menu # Для возврата в главное меню

# --- Клавиатура для Приобретения МАК ---
async def get_purchase_menu() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для выбора места приобретения МАК."""
    keyboard = [
        [InlineKeyboardButton(text="Приобрести на Ozon", url="https://www.ozon.ru/seller/makovaya-igropraktika-3033403/?miniapp=seller_3033403")],
        [InlineKeyboardButton(text="Приобрести на WB", url="https://www.wildberries.ru/brands/312187808-makovaya-igropraktika")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- Обработчик для кнопки "Приобрести МАК" ---
async def handle_purchase_menu(message: types.Message, db: Database, logging_service):
    """Отправляет меню для приобретения МАК."""
    await message.answer("Выберите, где приобрести МАК:", reply_markup=await get_purchase_menu())
    # Раздел был полной аналитической слепой зоной: нельзя было сказать даже,
    # открывает ли меню хоть кто-нибудь. Сам переход на Ozon/WB отследить нельзя —
    # это url-кнопки, Telegram не присылает по ним callback.
    if logging_service:
        try:
            await logging_service.log_action(message.from_user.id, "purchase_menu_opened", {})
        except Exception:
            pass

# --- Обработчик callback-ов меню "Приобрести МАК" ---
async def handle_purchase_callbacks(query: types.CallbackQuery, db: Database):
    """Обрабатывает callback-и от кнопок меню приобретения МАК."""
    if query.data == "back_to_main_menu":
        await query.message.edit_text("Главное меню:", reply_markup=await get_main_menu(query.from_user.id, db))
        await query.answer()
