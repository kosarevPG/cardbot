"""
Модуль управления постами и рассылками для админской панели.
"""
import logging
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from database.db import Database
from modules.logging_service import LoggingService

logger = logging.getLogger(__name__)


async def show_admin_posts(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает меню управления постами."""
    # Проверяем права администратора
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("❌ У вас нет доступа к этой функции.", parse_mode="HTML")
            return
    except ImportError as e:
        logger.error(f"Failed to import ADMIN_IDS: {e}")
        await message.edit_text("❌ Ошибка проверки прав доступа.", parse_mode="HTML")
        return
    
    try:
        # Получаем PostManager из диспетчера
        post_manager = None
        scheduler = None
        
        # Пытаемся получить из диспетчера
        if hasattr(message.bot, '_dispatcher') and message.bot._dispatcher:
            post_manager = message.bot._dispatcher.get("post_manager")
            scheduler = message.bot._dispatcher.get("scheduler")
        
        # Если не получилось, создаем временный
        if not post_manager:
            from modules.post_management import PostManager
            post_manager = PostManager(db, message.bot, logger_service)
        
        # Получаем последние посты и рассылки
        posts = post_manager.get_all_posts(limit=5)
        mailings = post_manager.get_all_mailings(limit=5)
        
        text = "📝 <b>УПРАВЛЕНИЕ ПОСТАМИ</b>\n\n"
        
        # Статистика
        text += f"📊 <b>Статистика:</b>\n"
        text += f"• Постов: {len(posts)}\n"
        text += f"• Рассылок: {len(mailings)}\n\n"
        
        # Последние посты
        if posts:
            text += "📝 <b>Последние посты:</b>\n"
            for post in posts[:3]:
                preview = post_manager.format_post_preview(post, max_length=50)
                text += f"• {preview}\n\n"
        else:
            text += "📝 <b>Постов пока нет</b>\n\n"
        
        # Последние рассылки
        if mailings:
            text += "📤 <b>Последние рассылки:</b>\n"
            for mailing in mailings[:3]:
                preview = post_manager.format_mailing_preview(mailing)
                text += f"• {preview}\n\n"
        else:
            text += "📤 <b>Рассылок пока нет</b>\n\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Создать пост", callback_data="admin_create_post")],
            [types.InlineKeyboardButton(text="📋 Список постов", callback_data="admin_list_posts")],
            [types.InlineKeyboardButton(text="📤 Список рассылок", callback_data="admin_list_mailings")],
            [types.InlineKeyboardButton(text="🔄 Обработать рассылки", callback_data="admin_process_mailings")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing admin posts: {e}", exc_info=True)
        text = "❌ Ошибка при получении данных о постах"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_posts")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        await message.edit_text(text, reply_markup=keyboard)


async def start_post_creation(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Начинает процесс создания поста."""
    try:
        text = """📝 <b>СОЗДАНИЕ НОВОГО ПОСТА</b>

Введите заголовок поста (максимум 100 символов):"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="❌ Отмена", callback_data="admin_posts")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
        # Логируем действие
        await logger_service.log_action(user_id, "admin_post_creation_started", {})
        
    except Exception as e:
        logger.error(f"Error starting post creation: {e}", exc_info=True)
        await message.answer("❌ Ошибка при создании поста")


async def show_posts_list(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает список всех постов."""
    try:
        # Получаем PostManager
        post_manager = None
        if hasattr(message.bot, '_dispatcher') and message.bot._dispatcher:
            post_manager = message.bot._dispatcher.get("post_manager")
        
        if not post_manager:
            from modules.post_management import PostManager
            post_manager = PostManager(db, message.bot, logger_service)
        
        posts = post_manager.get_all_posts(limit=20)
        
        if not posts:
            text = "📝 <b>СПИСОК ПОСТОВ</b>\n\nПостов пока нет."
        else:
            text = "📝 <b>СПИСОК ПОСТОВ</b>\n\n"
            for i, post in enumerate(posts, 1):
                preview = post_manager.format_post_preview(post, max_length=80)
                text += f"{i}. {preview}\n\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_posts")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing posts list: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении списка постов")


async def show_mailings_list(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает список всех рассылок."""
    try:
        # Получаем PostManager
        post_manager = None
        if hasattr(message.bot, '_dispatcher') and message.bot._dispatcher:
            post_manager = message.bot._dispatcher.get("post_manager")
        
        if not post_manager:
            from modules.post_management import PostManager
            post_manager = PostManager(db, message.bot, logger_service)
        
        mailings = post_manager.get_all_mailings(limit=20)
        
        if not mailings:
            text = "📤 <b>СПИСОК РАССЫЛОК</b>\n\nРассылок пока нет."
        else:
            text = "📤 <b>СПИСОК РАССЫЛОК</b>\n\n"
            for i, mailing in enumerate(mailings, 1):
                preview = post_manager.format_mailing_preview(mailing)
                stats = post_manager.get_mailing_stats(mailing['id'])
                text += f"{i}. {preview}\n"
                text += f"📊 Отправлено: {stats['sent_count']}, Ошибок: {stats['failed_count']}\n\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_posts")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing mailings list: {e}", exc_info=True)
        await message.answer("❌ Ошибка при получении списка рассылок")


async def process_mailings_now(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Принудительно обрабатывает все ожидающие рассылки."""
    try:
        # Получаем Scheduler из диспетчера
        scheduler = None
        try:
            # В aiogram 3.x диспетчер доступен через message.bot._dispatcher
            if hasattr(message.bot, '_dispatcher'):
                scheduler = message.bot._dispatcher.get("scheduler")
        except:
            pass
        
        if not scheduler:
            # Попробуем создать новый планировщик
            try:
                from modules.post_management import PostManager
                from modules.scheduler import MailingScheduler
                post_manager = PostManager(db, message.bot, logger_service)
                scheduler = MailingScheduler(post_manager, check_interval=60)
                await scheduler.start()
            except Exception as e:
                logger.error(f"Failed to create scheduler: {e}")
                await message.answer("❌ Планировщик недоступен")
                return
        
        # Показываем сообщение о начале обработки
        await message.edit_text("🔄 Обрабатываю рассылки...", parse_mode="HTML")
        
        # Обрабатываем рассылки
        result = await scheduler.process_mailings_now()
        
        # Показываем результат
        text = f"""✅ <b>ОБРАБОТКА РАССЫЛОК ЗАВЕРШЕНА</b>

📊 <b>Результат:</b>
• Обработано рассылок: {result['processed']}
• Отправлено сообщений: {result['sent']}
• Ошибок: {result['failed']}"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📤 Список рассылок", callback_data="admin_list_mailings")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_posts")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error processing mailings: {e}", exc_info=True)
        text = "❌ Ошибка при обработке рассылок"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_posts")]
        ])
        await message.edit_text(text, reply_markup=keyboard)

