"""
Модуль для логирования обучения пользователей
"""
import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from database.db import Database

logger = logging.getLogger(__name__)

class TrainingLogger:
    """Класс для логирования прохождения обучения"""
    
    def __init__(self, db: Database):
        self.db = db
        
    def log_training_step(self, user_id: int, training_type: str, step: str, 
                          username: str = None, first_name: str = None, last_name: str = None,
                          session_id: str = None, details: Dict = None):
        """
        Логирует шаг обучения пользователя
        
        Args:
            user_id: ID пользователя
            training_type: Тип обучения (например, 'card_conversation')
            step: Шаг ('started', 'completed', 'abandoned')
            username: Имя пользователя в Telegram
            first_name: Имя
            last_name: Фамилия
            session_id: ID сессии для группировки
            details: Дополнительные данные в виде словаря
        """
        try:
            # Проверяем, включено ли логирование обучения
            cursor = self.db.conn.execute("SELECT value FROM settings WHERE key = ?", ('training_logs_enabled',))
            result = cursor.fetchone()
            settings = {'value': result['value']} if result else None
            if settings and settings.get('value') != 'true':
                return
                
            # Проверяем, исключать ли админов
            cursor = self.db.conn.execute("SELECT value FROM settings WHERE key = ?", ('training_exclude_admins',))
            result = cursor.fetchone()
            exclude_admins = {'value': result['value']} if result else None
            if exclude_admins and exclude_admins.get('value') == 'true':
                # Проверяем, является ли пользователь админом
                try:
                    from config_local import NO_LOGS_USERS
                except ImportError:
                    from config import NO_LOGS_USERS
                if user_id in NO_LOGS_USERS:
                    logger.debug(f"Пропускаем логирование обучения для админа {user_id}")
                    return
            
            # Подготавливаем данные для вставки
            details_json = json.dumps(details) if details else None
            
            # Вставляем запись в базу данных
            query = """
            INSERT INTO training_logs 
            (user_id, username, first_name, last_name, training_type, step, details, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            with self.db.conn:
                self.db.conn.execute(query, (
                    user_id, username, first_name, last_name, 
                    training_type, step, details_json, session_id
                ))
            
            logger.info(f"Записан лог обучения: user_id={user_id}, training={training_type}, step={step}")
            
        except Exception as e:
            logger.error(f"Ошибка логирования обучения: {e}", exc_info=True)
    
    def get_training_stats(self, training_type: str = None, days: int = 30) -> Dict:
        """
        Получает статистику обучения
        
        Args:
            training_type: Тип обучения (если None - все типы)
            days: Количество дней для анализа
            
        Returns:
            Dict с статистикой
        """
        try:
            # Базовый запрос
            where_conditions = ["timestamp >= datetime('now', '-{} days')".format(days)]
            params = []
            
            if training_type:
                where_conditions.append("training_type = ?")
                params.append(training_type)
            
            where_clause = " AND ".join(where_conditions)
            
            # Общая статистика
            query = f"""
            SELECT 
                training_type,
                step,
                COUNT(*) as count,
                COUNT(DISTINCT user_id) as unique_users
            FROM training_logs 
            WHERE {where_clause}
            GROUP BY training_type, step
            ORDER BY training_type, step
            """
            
            cursor = self.db.conn.execute(query, params)
            stats = cursor.fetchall()
            
            # Статистика по дням
            daily_query = f"""
            SELECT 
                DATE(timestamp) as date,
                training_type,
                COUNT(*) as count,
                COUNT(DISTINCT user_id) as unique_users
            FROM training_logs 
            WHERE {where_clause}
            GROUP BY DATE(timestamp), training_type
            ORDER BY date DESC
            """
            
            cursor = self.db.conn.execute(daily_query, params)
            daily_stats = cursor.fetchall()
            
            return {
                "success": True,
                "period_days": days,
                "training_type": training_type,
                "overall_stats": stats,
                "daily_stats": daily_stats
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики обучения: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_training_users(self, training_type: str = None, step: str = None, 
                           limit: int = 100) -> List[Dict]:
        """
        Получает список пользователей, проходивших обучение
        
        Args:
            training_type: Тип обучения
            step: Шаг обучения
            limit: Максимальное количество записей
            
        Returns:
            List[Dict] с данными пользователей
        """
        try:
            where_conditions = []
            params = []
            
            if training_type:
                where_conditions.append("training_type = ?")
                params.append(training_type)
                
            if step:
                where_conditions.append("step = ?")
                params.append(step)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            query = f"""
            SELECT 
                user_id,
                username,
                first_name,
                last_name,
                training_type,
                step,
                timestamp,
                session_id
            FROM training_logs 
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
            """
            
            params.append(limit)
            
            cursor = self.db.conn.execute(query, params)
            users = cursor.fetchall()
            
            return users
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователей обучения: {e}", exc_info=True)
            return []
    
    def get_user_training_history(self, user_id: int) -> List[Dict]:
        """
        Получает историю обучения конкретного пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[Dict] с историей обучения
        """
        try:
            query = """
            SELECT 
                training_type,
                step,
                timestamp,
                session_id,
                details
            FROM training_logs 
            WHERE user_id = ?
            ORDER BY timestamp DESC
            """
            
            cursor = self.db.conn.execute(query, (user_id,))
            history = cursor.fetchall()
            
            return history
            
        except Exception as e:
            logger.error(f"Ошибка получения истории обучения пользователя {user_id}: {e}", exc_info=True)
            return []
