"""
Модуль управления пользователями для админской панели.
Содержит функции просмотра пользователей и их запросов.
"""
import logging
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime
from database.db import Database
from modules.logging_service import LoggingService
from modules.ai_service import build_user_profile
from modules.constants import BOT_INITIATED_ACTIONS

try:
    from config_local import NO_LOGS_USERS, TIMEZONE, ADMIN_IDS
except ImportError:
    from config import NO_LOGS_USERS, TIMEZONE, ADMIN_IDS

logger = logging.getLogger(__name__)


def make_admin_user_profile_handler(db, logger_service):
    async def wrapped_handler(message: types.Message):
        user_id = message.from_user.id
        if str(user_id) not in ADMIN_IDS:
            await message.answer("Эта команда доступна только администратору.")
            return
        
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Укажи ID пользователя: /admin_user_profile <user_id>")
            return
        
        try:
            target_user_id = int(args[1])
        except ValueError:
            await message.answer("ID пользователя должен быть числом.")
            return
        
        user_info = db.get_user(target_user_id)
        if not user_info:
            await message.answer(f"Пользователь с ID {target_user_id} не найден в таблице users.")
            return
        
        profile = await build_user_profile(target_user_id, db)
        name = user_info.get("name", "N/A")
        username = user_info.get("username", "N/A")
        mood = profile.get("mood", "N/A")
        mood_trend_list = [m for m in profile.get("mood_trend", []) if m != "unknown"]
        mood_trend = " → ".join(mood_trend_list) if mood_trend_list else "N/A"
        themes_list = profile.get("themes", [])
        themes = ", ".join(themes_list) if themes_list and themes_list != ["не определено"] else "N/A"
        initial_resource = profile.get("initial_resource") or "N/A"
        final_resource = profile.get("final_resource") or "N/A"
        recharge_method = profile.get("recharge_method") or "N/A"
        last_reflection_date = profile.get("last_reflection_date") or "N/A"
        reflection_count = profile.get("reflection_count", 0)
        response_count = profile.get("response_count", 0)
        days_active = profile.get("days_active", 0)
        total_cards_drawn = profile.get("total_cards_drawn", 0)
        last_updated_dt = profile.get("last_updated")
        last_updated = last_updated_dt.astimezone(TIMEZONE).strftime("%Y-%m-%d %H:%M") if isinstance(last_updated_dt, datetime) and TIMEZONE else "N/A"
        
        text = (
            f"👤 <b>Профиль пользователя:</b> <code>{target_user_id}</code> | @{username} | {name}\n\n"
            f"<b>Состояние & Темы:</b>\n  Настроение: {mood}\n  Тренд: {mood_trend}\n  Темы: {themes}\n\n"
            f"<b>Ресурс (последний 'Карта дня'):</b>\n  Начало: {initial_resource}\n  Конец: {final_resource}\n  Восстановление: {recharge_method}\n\n"
             f"<b>Итог дня:</b>\n  Последний итог: {last_reflection_date}\n  Всего итогов: {reflection_count}\n\n"
            f"<b>Статистика Активности:</b>\n  Ответов (карта): {response_count}\n  Карт вытянуто: {total_cards_drawn}\n  Дней актив.: {days_active}\n\n"
            f"<b>Обновлено:</b> {last_updated} МСК"
        )
        await message.answer(text)
        await logger_service.log_action(user_id, "admin_user_profile_viewed", {"target_user_id": target_user_id})
    
    return wrapped_handler


async def show_admin_users(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает меню управления пользователями."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin users")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем базовую статистику пользователей
        all_users = db.get_all_users()
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        filtered_users = [uid for uid in all_users if uid not in excluded_users]
        total_users = len(filtered_users)
        
        # Активные пользователи за последние 7 дней (из scenario_logs)
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
        
        # Используем VIEW v_events для подсчета активных пользователей
        excluded_condition_view = ""
        params_view = []
        if excluded_users:
            excluded_condition_view = "AND user_id NOT IN ({})".format(','.join('?' * len(excluded_users)))
            params_view = list(excluded_users)
        
        cursor = db.conn.execute(f"""
            SELECT COUNT(DISTINCT user_id) as active_users
            FROM v_events 
            WHERE d_local >= date('now', '+3 hours', '-7 days')
            {excluded_condition_view}
        """, params_view)
        active_users = cursor.fetchone()['active_users']
        
        activity_pct = (active_users/total_users*100) if total_users > 0 else 0
        
        # Получаем статистику по новым пользователям
        new_users_stats = db.get_new_users_stats(7)
        
        text = f"""👥 <b>ПОЛЬЗОВАТЕЛИ</b>

📊 <b>Общая статистика:</b>
• Всего пользователей: {total_users}
• Активных за 7 дней: {active_users}
• Процент активности: {activity_pct:.1f}%

🆕 <b>Новые пользователи (7 дней):</b>
• Всего новых: {new_users_stats['total_new_users']}
• С меткой first_seen: {new_users_stats['users_with_first_seen']}
• Без метки: {new_users_stats['users_without_first_seen']}

🔧 <b>Действия:</b>
• /users - список всех пользователей
• /user_profile [ID] - профиль пользователя"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔥 Сегменты и ядро", callback_data="admin_user_segments")],
            [types.InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users_list")],
            [types.InlineKeyboardButton(text="💬 Запросы пользователей", callback_data="admin_requests")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_users_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin users: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке данных пользователей"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise


async def show_admin_users_list(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, page: int = 0):
    """Показывает список всех пользователей."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin users list")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем всех пользователей
        all_users = db.get_all_users()
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        filtered_users = [uid for uid in all_users if uid not in excluded_users]
        
        if not filtered_users:
            text = "👥 <b>СПИСОК ПОЛЬЗОВАТЕЛЕЙ</b>\n\nПока нет пользователей в базе данных."
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users_list")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
            ])
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            return
        
        # Формируем список пользователей
        text = f"👥 <b>СПИСОК ПОЛЬЗОВАТЕЛЕЙ</b> ({len(filtered_users)})\n\n"
        
        # Получаем данные пользователей
        user_list = []
        for uid in filtered_users:
            user_data = db.get_user(uid)
            if user_data:
                name = user_data.get("name", "Без имени")
                username = user_data.get("username", "")
                last_action_time = "Нет действий"
                
                # Получаем последнее действие ЧЕЛОВЕКА: отправку напоминания и показ
                # приглашения инициирует бот, и без фильтра у всех адресатов утренней
                # рассылки «последним действием» становится одно и то же время.
                user_actions = [
                    a for a in db.get_actions(uid)
                    if a.get("action") not in BOT_INITIATED_ACTIONS
                ]
                if user_actions:
                    last_action = user_actions[-1]
                    raw_timestamp = last_action.get("timestamp")
                    try:
                        if isinstance(raw_timestamp, datetime):
                            last_action_dt = raw_timestamp.astimezone(TIMEZONE) if raw_timestamp.tzinfo and TIMEZONE else raw_timestamp
                            last_action_time = last_action_dt.strftime("%Y-%m-%d %H:%M")
                        elif isinstance(raw_timestamp, str):
                            last_action_dt = datetime.fromisoformat(raw_timestamp.replace('Z', '+00:00')).astimezone(TIMEZONE)
                            last_action_time = last_action_dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        last_action_time = "Ошибка даты"
                
                username_display = f"@{username}" if username else "без username"
                user_list.append({
                    'uid': uid,
                    'name': name,
                    'username': username_display,
                    'last_action_time': last_action_time
                })
        
        # Сортируем по времени последнего действия
        try:
            user_list.sort(key=lambda x: x['last_action_time'], reverse=True)
        except Exception as sort_err:
            logger.warning(f"Error sorting user list by timestamp: {sort_err}. List may be unsorted.")
        
        # Формируем текст списка с ограничением длины
        max_users_per_page = 15  # Максимум пользователей на страницу
        current_page = page
        start_idx = current_page * max_users_per_page
        end_idx = start_idx + max_users_per_page
        
        # Показываем только часть пользователей для избежания MESSAGE_TOO_LONG
        visible_users = user_list[start_idx:end_idx]
        
        for i, user in enumerate(visible_users, start_idx + 1):
            text += f"{i}. <code>{user['uid']}</code> | {user['username']} | {user['name']}\n"
            text += f"   Последнее действие: {user['last_action_time']}\n\n"
        
        # Добавляем информацию о пагинации
        total_pages = (len(user_list) + max_users_per_page - 1) // max_users_per_page
        current_page_display = current_page + 1
        
        if total_pages > 1:
            text += f"\n📄 Страница {current_page_display} из {total_pages}\n"
            text += f"Показано {len(visible_users)} из {len(user_list)} пользователей"
        else:
            text += f"\n📄 Всего пользователей: {len(user_list)}"
        
        # Создаем клавиатуру с навигацией
        keyboard_buttons = []
        
        # Кнопки навигации
        if total_pages > 1:
            nav_buttons = []
            if current_page > 0:
                nav_buttons.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_page_{current_page-1}"))
            nav_buttons.append(types.InlineKeyboardButton(text=f"{current_page_display}/{total_pages}", callback_data="admin_users_list"))
            if current_page < total_pages - 1:
                nav_buttons.append(types.InlineKeyboardButton(text="➡️", callback_data=f"admin_users_page_{current_page+1}"))
            keyboard_buttons.append(nav_buttons)
        
        # Основные кнопки
        keyboard_buttons.extend([
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users_list")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_users_list_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin users list: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке списка пользователей"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise


async def show_admin_requests(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает запросы пользователей к картам."""
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
        # Получаем статистику запросов
        requests_stats = db.get_user_requests_stats(7, user_id)
        requests_sample = db.get_user_requests_sample(5, 7, user_id)
        
        text = f"""💬 <b>ЗАПРОСЫ ПОЛЬЗОВАТЕЛЕЙ</b> (за 7 дней)

📊 <b>Статистика:</b>
• Всего запросов: {requests_stats.get('total_requests', 0)}
• Уникальных пользователей: {requests_stats.get('unique_users', 0)}
• Средняя длина: {requests_stats.get('avg_length', 0)} символов
• Минимум: {requests_stats.get('min_length', 0)} символов
• Максимум: {requests_stats.get('max_length', 0)} символов

📝 <b>Последние запросы:</b>"""
        
        if requests_sample:
            for i, req in enumerate(requests_sample, 1):
                req_user_id = req.get('user_id', 'N/A')
                user_name = req.get('user_name', 'Аноним')
                username = req.get('user_username', '')
                timestamp = req.get('timestamp', '')
                request_text = req['request_text']
                
                # Форматируем дату
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_date = timestamp
                
                # Форматируем username
                username_display = f"@{username}" if username else "без username"
                
                # Показываем полный текст без обрезки
                display_text = request_text
                
                text += f"\n{i}. <b>{formatted_date}</b>"
                text += f"\n   <i>«{display_text}»</i>"
                text += f"\n   👤 <code>{req_user_id}</code> | {username_display} | {user_name}"
                text += f"\n"
        else:
            text += "\nПока нет запросов"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📋 Все запросы", callback_data="admin_requests_full")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_requests")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_requests_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin requests: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке запросов"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise


async def show_admin_requests_full(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает полные запросы пользователей с детальной информацией."""
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
        # Получаем больше запросов для детального просмотра
        requests_sample = db.get_user_requests_sample(20, 7, user_id)
        
        text = f"""📋 <b>ПОЛНЫЕ ЗАПРОСЫ ПОЛЬЗОВАТЕЛЕЙ</b> (за 7 дней)

📊 <b>Всего запросов:</b> {len(requests_sample)}

📝 <b>Детальная информация:</b>"""
        
        if requests_sample:
            for i, req in enumerate(requests_sample, 1):
                req_user_id = req.get('user_id', 'N/A')
                user_name = req.get('user_name', 'Аноним')
                username = req.get('user_username', '')
                timestamp = req.get('timestamp', '')
                request_text = req['request_text']
                card_number = req.get('card_number', 'N/A')
                
                # Форматируем дату
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_date = timestamp
                
                # Форматируем username
                username_display = f"@{username}" if username else "без username"
                
                text += f"\n\n<b>{i}. {formatted_date}</b>"
                text += f"\n🎴 Карта: {card_number}"
                text += f"\n👤 <b>Пользователь:</b> <code>{req_user_id}</code> | {username_display} | {user_name}"
                text += f"\n💬 <b>Запрос:</b>"
                text += f"\n   «{request_text}»"
                text += f"\n{'─' * 40}"
        else:
            text += "\n\nПока нет запросов"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📊 Краткая статистика", callback_data="admin_requests")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_requests_full")],
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_requests_full_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin requests full: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке полных запросов"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

