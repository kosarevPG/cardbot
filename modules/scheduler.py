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