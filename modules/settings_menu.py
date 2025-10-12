"""
Модуль меню "Настройки" - дополнительные настройки и функции
"""
import logging
from aiogram import types
from aiogram.fsm.context import FSMContext
from database.db import Database

logger = logging.getLogger(__name__)


async def show_settings_menu(message: types.Message, db: Database, user_id: int):
    """
    Показывает меню "Настройки" с дополнительными настройками.
    
    Структура:
    - 👤 Профиль
    - 🔔 Напоминания
    - 📣 Поделиться ботом
    - 💬 Отзыв и идеи
    - 🛍️ Купить МАК-колоду
    - ℹ️ О боте
    - ⬅️ Назад
    """
    try:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="👤 Профиль", callback_data="settings_profile")],
            [types.InlineKeyboardButton(text="🔔 Напоминания", callback_data="settings_reminders")],
            [types.InlineKeyboardButton(text="📣 Поделиться ботом", callback_data="settings_invite")],
            [types.InlineKeyboardButton(text="💬 Отзыв и идеи", callback_data="settings_feedback")],
            [types.InlineKeyboardButton(text="🛍️ Купить МАК-колоду", callback_data="settings_purchase")],
            [types.InlineKeyboardButton(text="ℹ️ О боте", callback_data="settings_about")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back")]
        ])
        
        text = (
            "⚙️ <b>Дополнительные настройки</b>\n\n"
            "Здесь ты можешь управлять своим профилем, настроить напоминания "
            "и узнать больше о боте."
        )
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"Settings menu shown to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error showing settings menu to user {user_id}: {e}", exc_info=True)
        await message.answer("Произошла ошибка при открытии меню настроек.")


async def handle_settings_callback(callback: types.CallbackQuery, db: Database, logger_service):
    """
    Обрабатывает callback'и из меню "Настройки".
    """
    try:
        user_id = callback.from_user.id
        action = callback.data
        
        if action == "settings_profile":
            # Показываем профиль пользователя
            user_data = db.get_user(user_id) or {}
            name = user_data.get('name', 'Не указано')
            username = user_data.get('username', 'Не указано')
            first_seen = user_data.get('first_seen', 'Неизвестно')
            
            text = (
                f"👤 <b>Твой профиль</b>\n\n"
                f"👋 Имя: {name}\n"
                f"🆔 Username: @{username}\n"
                f"📅 С нами с: {first_seen}\n\n"
                f"Используй /name, чтобы изменить имя."
            )
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="← Назад", callback_data="settings_menu")]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            
        elif action == "settings_reminders":
            # Меню напоминаний
            text = (
                "🔔 <b>Настройка напоминаний</b>\n\n"
                "Используй команды:\n"
                "• /remind - настроить напоминания\n"
                "• /remind_off - выключить все напоминания"
            )
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="← Назад", callback_data="settings_menu")]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            
        elif action == "settings_invite":
            # Поделиться ботом
            text = (
                "🎁 <b>Пригласи друга!</b>\n\n"
                "Поделись ботом с друзьями и получи бонус!\n\n"
                "Используй команду /share, чтобы получить реферальную ссылку."
            )
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="← Назад", callback_data="settings_menu")]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            
        elif action == "settings_feedback":
            # Отзыв и идеи
            text = (
                "💬 <b>Отзыв и идеи</b>\n\n"
                "Мы будем рады услышать твои идеи и пожелания!\n\n"
                "Используй команду /feedback, чтобы оставить отзыв."
            )
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="← Назад", callback_data="settings_menu")]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            
        elif action == "settings_purchase":
            # Перенаправляем на меню покупки МАК
            from modules.purchase_menu import handle_purchase_menu
            await callback.answer()
            await handle_purchase_menu(callback.message, db, logger_service)
            
        elif action == "settings_about":
            # О боте
            text = (
                "ℹ️ <b>О боте</b>\n\n"
                "Этот бот помогает тебе работать с МАК-картами для самопознания и рефлексии.\n\n"
                "🌙 Получай карты дня\n"
                "📝 Проводи вечерние рефлексии\n"
                "🎓 Учись разговаривать с картой\n\n"
                "Создатель: @TopPsyGame"
            )
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="← Назад", callback_data="settings_menu")]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            
        elif action == "settings_menu":
            # Возвращаемся в меню настроек
            await show_settings_menu(callback.message, db, user_id)
            await callback.answer()
            
        elif action == "settings_back":
            # Возвращаемся в главное меню
            from modules.card_of_the_day import get_main_menu
            text = "Вы вернулись в главное меню."
            await callback.message.edit_text(text)
            await callback.message.answer("Выбери действие:", reply_markup=await get_main_menu(user_id, db))
            await callback.answer()
        
    except Exception as e:
        logger.error(f"Error handling settings callback for user {user_id}: {e}", exc_info=True)
        await callback.answer("Произошла ошибка.", show_alert=True)

