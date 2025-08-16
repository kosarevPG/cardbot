# код/modules/scheduler.py

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import pytz

logger = logging.getLogger(__name__)

class MailingScheduler:
    """Планировщик для обработки запланированных рассылок."""
    
    def __init__(self, post_manager, check_interval: int = 60):
        """
        Инициализация планировщика.
        
        Args:
            post_manager: Экземпляр PostManager
            check_interval: Интервал проверки в секундах (по умолчанию 60)
        """
        self.post_manager = post_manager
        self.check_interval = check_interval
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Запускает планировщик."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info(f"Mailing scheduler started with {self.check_interval}s interval")
    
    async def stop(self):
        """Останавливает планировщик."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Mailing scheduler stopped")
    
    async def _run_scheduler(self):
        """Основной цикл планировщика."""
        while self.is_running:
            try:
                # Обрабатываем ожидающие рассылки
                result = await self.post_manager.process_pending_mailings()
                
                if result['processed'] > 0:
                    logger.info(f"Processed {result['processed']} mailings: "
                              f"{result['total_sent']} sent, {result['total_failed']} failed")
                
                # Ждем следующей проверки
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.info("Scheduler task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # Ждем немного перед повторной попыткой
                await asyncio.sleep(min(self.check_interval, 10))
    
    async def process_mailings_now(self) -> dict:
        """Принудительно обрабатывает все ожидающие рассылки."""
        try:
            result = await self.post_manager.process_pending_mailings()
            logger.info(f"Manual processing completed: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in manual processing: {e}", exc_info=True)
            return {'processed': 0, 'total_sent': 0, 'total_failed': 0, 'error': str(e)}
    
    def get_status(self) -> dict:
        """Возвращает статус планировщика."""
        return {
            'is_running': self.is_running,
            'check_interval': self.check_interval,
            'task_running': self.task is not None and not self.task.done()
        }

# --- НОВЫЙ КЛАСС: Планировщик еженедельного анализа рефлексий ---
class ReflectionAnalysisScheduler:
    """Планировщик для еженедельного анализа рефлексий пользователей."""
    
    def __init__(self, bot, db, check_interval: int = 3600):  # Проверяем каждый час
        """
        Инициализация планировщика анализа рефлексий.
        
        Args:
            bot: Экземпляр бота для отправки сообщений
            db: Экземпляр базы данных
            check_interval: Интервал проверки в секундах (по умолчанию 1 час)
        """
        self.bot = bot
        self.db = db
        self.check_interval = check_interval
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Запускает планировщик."""
        if self.is_running:
            logger.warning("Reflection analysis scheduler is already running")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info(f"Reflection analysis scheduler started with {self.check_interval}s interval")
    
    async def stop(self):
        """Останавливает планировщик."""
        if not self.is_running:
            logger.warning("Reflection analysis scheduler is not running")
            return
        
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Reflection analysis scheduler stopped")
    
    async def _run_scheduler(self):
        """Основной цикл планировщика."""
        while self.is_running:
            try:
                # Проверяем, нужно ли запустить еженедельный анализ
                await self._check_weekly_analysis()
                
                # Ждем следующей проверки
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.info("Reflection analysis scheduler task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in reflection analysis scheduler loop: {e}", exc_info=True)
                # Ждем немного перед повторной попыткой
                await asyncio.sleep(min(self.check_interval, 10))
    
    async def _check_weekly_analysis(self):
        """Проверяет, нужно ли запустить еженедельный анализ."""
        try:
            now = datetime.now()
            
            # Запускаем анализ каждое воскресенье в 20:00
            if now.weekday() == 6 and now.hour == 20 and now.minute < 5:  # Воскресенье, 20:00-20:05
                logger.info("It's Sunday 20:00, starting weekly reflection analysis...")
                await self._run_weekly_analysis()
                
        except Exception as e:
            logger.error(f"Error checking weekly analysis schedule: {e}", exc_info=True)
    
    async def _run_weekly_analysis(self):
        """Запускает еженедельный анализ для всех пользователей."""
        try:
            # Получаем пользователей с рефлексиями за последнюю неделю
            user_ids = self.db.get_users_with_recent_reflections(days=7)
            logger.info(f"Starting weekly analysis for {len(user_ids)} users")
            
            # Запускаем анализ для каждого пользователя
            for user_id in user_ids:
                try:
                    await self._send_weekly_analysis(user_id)
                    # Небольшая задержка между пользователями
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error sending weekly analysis to user {user_id}: {e}", exc_info=True)
            
            logger.info(f"Weekly analysis completed for {len(user_ids)} users")
            
        except Exception as e:
            logger.error(f"Error running weekly analysis: {e}", exc_info=True)
    
    async def _send_weekly_analysis(self, user_id: int):
        """Отправляет еженедельный анализ конкретному пользователю."""
        try:
            # Получаем рефлексии за неделю
            reflections = self.db.get_reflections_for_last_n_days(user_id, days=7)
            
            if len(reflections) >= 3:  # Минимум 3 записи для анализа
                # Импортируем здесь, чтобы избежать циклических импортов
                from .ai_service import get_weekly_analysis
                
                # Генерируем анализ
                analysis = await get_weekly_analysis(reflections)
                
                # Отправляем пользователю
                await self.bot.send_message(
                    user_id,
                    f"🌙 **Еженедельный анализ твоих рефлексий**\n\n{analysis}",
                    parse_mode="Markdown"
                )
                
                logger.info(f"Weekly analysis sent to user {user_id}")
            else:
                logger.info(f"User {user_id} has only {len(reflections)} reflections, skipping weekly analysis")
                
        except Exception as e:
            logger.error(f"Error sending weekly analysis to user {user_id}: {e}", exc_info=True)
    
    def get_status(self) -> dict:
        """Возвращает статус планировщика."""
        return {
            'is_running': self.is_running,
            'check_interval': self.check_interval,
            'task_running': self.task is not None and not self.task.done()
        }

# --- КОНЕЦ НОВОГО КЛАССА --- 