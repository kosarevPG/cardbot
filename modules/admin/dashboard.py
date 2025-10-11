"""
Модуль дашбордов и метрик для админской панели.
Содержит функции отображения различных метрик и статистики.
"""
import logging
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from database.db import Database
from modules.logging_service import LoggingService

try:
    from config_local import NO_LOGS_USERS, TIMEZONE
except ImportError:
    from config import NO_LOGS_USERS, TIMEZONE

logger = logging.getLogger(__name__)


async def show_admin_dashboard(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, days: int = 7):
    """Показывает главный дашборд с ключевыми метриками."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin dashboard")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем сводку метрик (оптимизировано - все данные в одном запросе)
        summary = db.get_admin_dashboard_summary(days)
        
        if not summary:
            text = "❌ Ошибка при получении данных дашборда"
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_dashboard")],
                [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
            ])
            await message.edit_text(text, reply_markup=keyboard)
            return
        
        # Определяем период для отображения
        period_text = "Сегодня" if days == 1 else f"{days} дней"
        
        # Используем данные из summary (устраняем дублирование)
        dau_metrics = summary['dau']
        retention_metrics = summary['retention']
        
        # Формируем текст дашборда
        text = f"""🔍 <b>ГЛАВНЫЙ ДАШБОРД</b> ({period_text})

👥 <b>DAU:</b>
• Сегодня: {dau_metrics['dau_today']}
• Вчера: {dau_metrics['dau_yesterday']}
• 7 дней: {dau_metrics['dau_7']}
• 30 дней: {dau_metrics['dau_30']}

📈 <b>Retention:</b>
• D1: {retention_metrics.get('d1_retention', 0):.1f}%
• D7: {retention_metrics.get('d7_retention', 0):.1f}%

🔄 <b>Карта дня:</b>
• Запусков: {summary['card_stats']['total_starts']}
• Завершено: {summary['card_stats']['total_completions']} ({summary['card_stats']['completion_rate']:.1f}%)
• Среднее шагов: {summary['card_stats']['avg_steps']}

🌙 <b>Итог дня:</b>
• Запусков: {summary['evening_stats']['total_starts']}
• Завершено: {summary['evening_stats']['total_completions']} ({summary['evening_stats']['completion_rate']:.1f}%)

💎 <b>Ценность:</b>
• Положительная динамика ресурса: {summary['value']['resource_lift']['positive_pct']}%
• Feedback Score: {summary['value']['feedback_score']}%

🃏 <b>Колоды:</b>
• 🌿 Природа: {summary['deck_popularity']['decks'].get('nature', {}).get('percentage', 0)}%
• 💌 Весточка: {summary['deck_popularity']['decks'].get('message', {}).get('percentage', 0)}%"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Сегодня", callback_data="admin_dashboard_1"),
                types.InlineKeyboardButton(text="7 дней", callback_data="admin_dashboard_7"),
                types.InlineKeyboardButton(text="30 дней", callback_data="admin_dashboard_30")
            ],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_dashboard_{days}")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_dashboard_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin dashboard: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке дашборда"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise


async def show_admin_retention(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает метрики удержания."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin retention")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем все метрики одним запросом (оптимизировано)
        summary = db.get_admin_dashboard_summary(7)
        retention = summary['retention']
        dau = summary['dau']
        
        text = f"""📈 <b>МЕТРИКИ УДЕРЖАНИЯ</b> (за 7 дней)

🎯 <b>D1 Retention:</b>
• {retention['d1_retention']}% ({retention['d1_returned_users']}/{retention['d1_total_users']})
• Цель: >30%

📅 <b>D7 Retention:</b>
• {retention['d7_retention']}% ({retention['d7_returned_users']}/{retention['d7_total_users']})
• Цель: >25%

👥 <b>DAU:</b>
• Вчера: {dau['dau_yesterday']}
• Среднее за 7 дней: {dau['dau_7']}
• Среднее за 30 дней: {dau['dau_30']}"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_retention")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_retention_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin retention: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке метрик удержания"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise


async def show_admin_funnel(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, days: int = 7):
    """Показывает воронку сценария 'Карта дня'."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin funnel")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем все метрики одним запросом (оптимизировано)
        summary = db.get_admin_dashboard_summary(days)
        funnel = summary['funnel']
        
        period_text = {
            1: "сегодня",
            7: "7 дней", 
            30: "30 дней"
        }.get(days, f"{days} дней")
        
        text = f"""🔄 <b>ВОРОНКА 'КАРТА ДНЯ'</b> (за {period_text})

📊 <b>Completion Rate: {funnel['completion_rate']}%</b>
Цель: >60%

📈 <b>Детальная воронка:</b>
1️⃣ Начали сессию: {funnel['step1']['count']} ({funnel['step1']['pct']}%)
2️⃣ Выбрали ресурс: {funnel['step2']['count']} ({funnel['step2']['pct']}%)
3️⃣ Выбрали тип запроса: {funnel['step3']['count']} ({funnel['step3']['pct']}%)
4️⃣ Вытянули карту: {funnel['step4']['count']} ({funnel['step4']['pct']}%)
5️⃣ Написали ассоциацию: {funnel['step5']['count']} ({funnel['step5']['pct']}%)
6️⃣ Выбрали углубляющий диалог: {funnel['step6']['count']} ({funnel['step6']['pct']}%)
7️⃣ Завершили сценарий: {funnel['step7']['count']} ({funnel['step7']['pct']}%)"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📅 Сегодня", callback_data="admin_funnel_1")],
            [types.InlineKeyboardButton(text="📅 7 дней", callback_data="admin_funnel_7")],
            [types.InlineKeyboardButton(text="📅 30 дней", callback_data="admin_funnel_30")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_funnel_{days}")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_funnel_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin funnel: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке воронки"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise


async def show_admin_value(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, days: int = 7):
    """Показывает метрики ценности."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin value metrics")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем все метрики одним запросом (оптимизировано)
        summary = db.get_admin_dashboard_summary(days)
        value = summary['value']
        
        # Определяем период для отображения
        period_text = "Сегодня" if days == 1 else f"{days} дней"
        
        text = f"""💎 <b>МЕТРИКИ ЦЕННОСТИ</b> ({period_text})

📈 <b>Resource Lift:</b>
• Положительная динамика: {value['resource_lift']['positive_pct']}%
• Отрицательная динамика: {value['resource_lift']['negative_pct']}%
• Всего сессий: {value['resource_lift']['total_sessions']}

👍 <b>Feedback Score:</b>
• Позитивные отзывы: {value['feedback_score']}%
• Всего отзывов: {value['total_feedback']}
• Цель: ≥50%"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Сегодня", callback_data="admin_value_1"),
                types.InlineKeyboardButton(text="7 дней", callback_data="admin_value_7"),
                types.InlineKeyboardButton(text="30 дней", callback_data="admin_value_30")
            ],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_value_{days}")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_value_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin value: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке метрик ценности"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise


async def show_admin_decks(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, days: int = 7):
    """Показывает статистику по колодам карт."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin decks")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем метрики популярности колод
        deck_metrics = db.get_deck_popularity_metrics(days)
        
        if not deck_metrics or not deck_metrics.get('decks'):
            text = "❌ Нет данных о колодах за указанный период"
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
            ])
            await message.edit_text(text, reply_markup=keyboard)
            return
        
        # Определяем период для отображения
        period_text = "Сегодня" if days == 1 else f"{days} дней"
        
        decks_data = deck_metrics['decks']
        total_draws = deck_metrics['total_draws']
        
        # Маппинг названий колод
        deck_names = {
            'nature': '🌿 Ресурсы природы',
            'message': '💌 Ресурсная весточка'
        }
        
        text = f"""🃏 <b>СТАТИСТИКА КОЛОД</b> ({period_text})

📊 <b>Всего вытянуто карт:</b> {total_draws}

"""
        
        # Добавляем статистику по каждой колоде
        for deck_key in ['nature', 'message']:
            deck_info = decks_data.get(deck_key, {'total_draws': 0, 'unique_users': 0, 'percentage': 0})
            deck_name = deck_names.get(deck_key, deck_key)
            
            text += f"""<b>{deck_name}:</b>
• Выбрано: {deck_info['total_draws']} раз ({deck_info['percentage']}%)
• Уникальных пользователей: {deck_info['unique_users']}

"""
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Сегодня", callback_data="admin_decks_1"),
                types.InlineKeyboardButton(text="7 дней", callback_data="admin_decks_7"),
                types.InlineKeyboardButton(text="30 дней", callback_data="admin_decks_30")
            ],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_decks_{days}")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_decks_viewed", {"days": days})
        
    except Exception as e:
        logger.error(f"Error showing admin decks: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке статистики колод"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise


async def show_admin_reflections(message: types.Message, db: Database, logger_service: LoggingService, user_id: int, days: int = 7):
    """Показывает метрики вечерней рефлексии."""
    # ЖЕСТКАЯ ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
    try:
        from config import ADMIN_IDS
        if str(user_id) not in ADMIN_IDS:
            await message.edit_text("🚫 ДОСТУП ЗАПРЕЩЕН! У вас нет прав администратора.", parse_mode="HTML")
            logger.warning(f"BLOCKED: User {user_id} attempted to access admin reflections")
            return
    except ImportError as e:
        logger.error(f"CRITICAL: Failed to import ADMIN_IDS: {e}")
        await message.edit_text("🚫 КРИТИЧЕСКАЯ ОШИБКА БЕЗОПАСНОСТИ", parse_mode="HTML")
        return
    
    try:
        # Получаем метрики вечерней рефлексии
        metrics = db.get_evening_reflection_metrics(days)
        
        if not metrics:
            text = "❌ Нет данных о рефлексиях за указанный период"
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
            ])
            await message.edit_text(text, reply_markup=keyboard)
            return
        
        # Определяем период для отображения
        period_text = "Сегодня" if days == 1 else f"{days} дней"
        
        text = f"""🌙 <b>ВЕЧЕРНЯЯ РЕФЛЕКСИЯ</b> ({period_text})

📊 <b>Общая статистика:</b>
• Всего рефлексий: {metrics['total_reflections']}
• Уникальных пользователей: {metrics['unique_users']}
• AI-резюме сгенерировано: {metrics['ai_summaries_count']} ({metrics['ai_summary_rate']}%)

📝 <b>Средняя длина ответов:</b>
• Хорошие моменты: {metrics['avg_good_length']} символов
• Благодарность: {metrics['avg_gratitude_length']} символов
• Сложности: {metrics['avg_hard_length']} символов

👥 <b>Топ-5 активных пользователей:</b>
"""
        
        # Добавляем топ пользователей
        for i, user in enumerate(metrics['top_users'][:5], 1):
            text += f"{i}. {user['name']} — {user['reflection_count']} рефлексий\n"
        
        if not metrics['top_users']:
            text += "Нет данных\n"
        
        text += "\n💡 Нажмите кнопку ниже, чтобы увидеть последние рефлексии"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Сегодня", callback_data="admin_reflections_1"),
                types.InlineKeyboardButton(text="7 дней", callback_data="admin_reflections_7"),
                types.InlineKeyboardButton(text="30 дней", callback_data="admin_reflections_30")
            ],
            [types.InlineKeyboardButton(text="📋 Последние рефлексии", callback_data=f"admin_recent_reflections_{days}")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_reflections_{days}")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        try:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        await logger_service.log_action(user_id, "admin_reflections_viewed", {"days": days})
        
    except Exception as e:
        logger.error(f"Error showing admin reflections: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке метрик рефлексии"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise


async def show_admin_logs(message: types.Message, db: Database, logger_service: LoggingService, user_id: int):
    """Показывает детальные логи."""
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
        # Получаем последние логи
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
        
        cursor = db.conn.execute(f"""
            SELECT scenario, step, COUNT(*) as count
            FROM scenario_logs 
            WHERE timestamp >= datetime('now', '-7 days')
            {excluded_condition}
            GROUP BY scenario, step
            ORDER BY count DESC
            LIMIT 10
        """, list(excluded_users) if excluded_users else [])
        
        logs = cursor.fetchall()
        
        text = """📋 <b>ДЕТАЛЬНЫЕ ЛОГИ</b> (за 7 дней)

🔍 <b>Топ-10 шагов по частоте:</b>"""
        
        for i, log in enumerate(logs, 1):
            text += f"\n{i}. {log['scenario']} → {log['step']}: {log['count']}"
        
        text += "\n\n🔧 <b>Действия:</b>\n• /scenario_stats - статистика сценариев\n• /logs - все логи"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📊 Статистика сценариев", callback_data="admin_scenario_stats")],
            [types.InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_logs")],
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        
        await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await logger_service.log_action(user_id, "admin_logs_viewed", {})
        
    except Exception as e:
        logger.error(f"Error showing admin logs: {e}", exc_info=True)
        text = "❌ Ошибка при загрузке логов"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="← Назад", callback_data="admin_back")]
        ])
        await message.edit_text(text, reply_markup=keyboard)

