# код/modules/scheduler.py

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import pytz

logger = logging.getLogger(__name__)

class PeriodicProcessor:
    """
    Общий цикл периодической обработки: раз в check_interval вызывает переданный
    обработчик и не падает от его ошибок.

    Выделен из MailingScheduler, когда у бота появился второй такой цикл
    (касания кампании знакомства с платформой). Логика запуска, остановки и
    устойчивости к ошибкам у них одна и та же, и расходиться ей незачем.
    """

    def __init__(self, process, name: str, check_interval: int = 60,
                 describe=None):
        """
        Args:
            process: корутина без аргументов — один проход обработки
            name: имя для логов
            check_interval: интервал проверки в секундах
            describe: функция, превращающая результат прохода в строку для лога
                      (None — ничего не логируем)
        """
        self._process = process
        self.name = name
        self.check_interval = check_interval
        self._describe = describe
        self.is_running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Запускает планировщик."""
        if self.is_running:
            logger.warning(f"{self.name} scheduler is already running")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info(f"{self.name} scheduler started with {self.check_interval}s interval")

    async def stop(self):
        """Останавливает планировщик."""
        if not self.is_running:
            logger.warning(f"{self.name} scheduler is not running")
            return

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info(f"{self.name} scheduler stopped")

    async def _run_scheduler(self):
        """Основной цикл планировщика."""
        while self.is_running:
            try:
                result = await self._process()

                if self._describe:
                    message = self._describe(result)
                    if message:
                        logger.info(f"[{self.name}] {message}")

                # Ждем следующей проверки
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.info(f"{self.name} scheduler task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in {self.name} scheduler loop: {e}", exc_info=True)
                # Ждем немного перед повторной попыткой
                await asyncio.sleep(min(self.check_interval, 10))

    def get_status(self) -> dict:
        """Возвращает статус планировщика."""
        return {
            'is_running': self.is_running,
            'check_interval': self.check_interval,
            'task_running': self.task is not None and not self.task.done()
        }


def _describe_mailings(result: dict) -> Optional[str]:
    if result.get('processed'):
        return (f"Processed {result['processed']} mailings: "
                f"{result['total_sent']} sent, {result['total_failed']} failed")
    return None


class MailingScheduler(PeriodicProcessor):
    """Планировщик для обработки запланированных рассылок."""

    def __init__(self, post_manager, check_interval: int = 60):
        """
        Инициализация планировщика.

        Args:
            post_manager: Экземпляр PostManager
            check_interval: Интервал проверки в секундах (по умолчанию 60)
        """
        super().__init__(post_manager.process_pending_mailings, "Mailing",
                         check_interval, describe=_describe_mailings)
        self.post_manager = post_manager

    async def process_mailings_now(self) -> dict:
        """Принудительно обрабатывает все ожидающие рассылки."""
        try:
            result = await self.post_manager.process_pending_mailings()
            logger.info(f"Manual processing completed: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in manual processing: {e}", exc_info=True)
            return {'processed': 0, 'total_sent': 0, 'total_failed': 0, 'error': str(e)}


def _describe_platform_campaign(result: dict) -> Optional[str]:
    """
    Что писать в лог по итогам прохода кампании. Молчим, когда ничего не
    происходит: тик идёт часто, а выключенная кампания — норма, а не событие.
    """
    if not result.get('enabled'):
        return None
    counts = {k: result.get(k, 0) for k in ('sent', 'failed', 'deferred', 'skipped')}
    if not any(counts.values()):
        return None
    return (f"follow-ups: sent={counts['sent']}, failed={counts['failed']}, "
            f"deferred={counts['deferred']}, skipped={counts['skipped']}")


class PlatformCampaignScheduler(PeriodicProcessor):
    """
    Планировщик касаний кампании знакомства с платформой.

    Сам по себе ничего не отправляет: пока администратор не включил кампанию,
    проход возвращает «disabled» и выходит. Интервал пять минут — касания
    привязаны к дням, минута точности здесь не нужна.
    """

    def __init__(self, campaign, check_interval: int = 300):
        super().__init__(campaign.process_due_followups, "PlatformCampaign",
                         check_interval, describe=_describe_platform_campaign)
        self.campaign = campaign


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