# код/modules/post_management.py

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pytz
from aiogram import Bot, types
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.enums import ParseMode
import logging

logger = logging.getLogger(__name__)

# Московское время
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

class PostManager:
    """Менеджер для работы с постами и рассылками."""
    
    def __init__(self, db, bot: Bot, logger_service):
        self.db = db
        self.bot = bot
        self.logger_service = logger_service
    
    def create_post(self, title: str, content: str, created_by: int, media_file_id: str = None) -> int:
        """Создает новый пост."""
        return self.db.create_post(title, content, created_by, media_file_id)
    
    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Получает пост по ID."""
        return self.db.get_post(post_id)
    
    def get_all_posts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получает все активные посты."""
        return self.db.get_all_posts(limit)
    
    def update_post(self, post_id: int, title: str = None, content: str = None, media_file_id: str = None) -> bool:
        """Обновляет пост."""
        return self.db.update_post(post_id, title, content, media_file_id)
    
    def delete_post(self, post_id: int) -> bool:
        """Удаляет пост."""
        return self.db.delete_post(post_id)
    
    def create_mailing(self, post_id: int, title: str, send_to_all: bool, created_by: int,
                      target_user_ids: List[int] = None, scheduled_at: str = None) -> int:
        """Создает новую рассылку."""
        # Конвертируем московское время в UTC перед сохранением в базу
        if scheduled_at:
            scheduled_at = self._convert_moscow_to_utc(scheduled_at)
        
        return self.db.create_mailing(post_id, title, send_to_all, created_by, target_user_ids, scheduled_at)
    
    def get_mailing(self, mailing_id: int) -> Optional[Dict[str, Any]]:
        """Получает рассылку по ID."""
        return self.db.get_mailing(mailing_id)
    
    def get_all_mailings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получает все рассылки."""
        return self.db.get_all_mailings(limit)
    
    def get_mailing_stats(self, mailing_id: int) -> Dict[str, Any]:
        """Получает статистику рассылки."""
        return self.db.get_mailing_stats(mailing_id)
    
    def _convert_moscow_to_utc(self, moscow_datetime: str) -> str:
        """Конвертирует московское время в UTC."""
        try:
            # Парсим московское время
            dt = datetime.strptime(moscow_datetime, "%Y-%m-%d %H:%M")
            moscow_dt = MOSCOW_TZ.localize(dt)
            utc_dt = moscow_dt.astimezone(pytz.UTC)
            return utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.error(f"Error converting Moscow time to UTC: {e}")
            return moscow_datetime
    
    def _convert_utc_to_moscow(self, utc_datetime: str) -> str:
        """Конвертирует UTC время в московское."""
        try:
            # Пробуем разные форматы времени
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
                try:
                    dt = datetime.strptime(utc_datetime, fmt)
                    utc_dt = pytz.UTC.localize(dt)
                    moscow_dt = utc_dt.astimezone(MOSCOW_TZ)
                    return moscow_dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    continue
            
            # Если ни один формат не подошел
            logger.error(f"Could not parse datetime format: {utc_datetime}")
            return utc_datetime
        except Exception as e:
            logger.error(f"Error converting UTC time to Moscow: {e}")
            return utc_datetime
    
    async def send_post_to_user(self, user_id: int, post: Dict[str, Any], mailing_id: int = None) -> bool:
        """Отправляет пост конкретному пользователю."""
        try:
            content = post['content']
            
            # Если есть медиа, отправляем с медиа
            if post.get('media_file_id'):
                await self.bot.send_photo(
                    chat_id=user_id,
                    photo=post['media_file_id'],
                    caption=content,
                    parse_mode=ParseMode.HTML
                )
            else:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=content,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
            
            # Логируем успешную отправку
            if mailing_id:
                self.db.log_mailing_result(mailing_id, user_id, 'sent')
            
            return True
            
        except TelegramAPIError as e:
            error_msg = str(e)
            if "bot was blocked" in error_msg.lower() or "user is deactivated" in error_msg.lower():
                status = 'blocked'
            else:
                status = 'failed'
            
            if mailing_id:
                self.db.log_mailing_result(mailing_id, user_id, status, error_msg)
            
            logger.error(f"Failed to send post to user {user_id}: {e}")
            return False
            
        except Exception as e:
            if mailing_id:
                self.db.log_mailing_result(mailing_id, user_id, 'failed', str(e))
            logger.error(f"Unexpected error sending post to user {user_id}: {e}")
            return False
    
    async def process_mailing(self, mailing: Dict[str, Any]) -> Dict[str, int]:
        """Обрабатывает рассылку - отправляет сообщения всем получателям."""
        mailing_id = mailing['id']
        post = {
            'content': mailing['post_content'],
            'media_file_id': mailing.get('media_file_id')
        }
        
        # Обновляем статус на "в процессе"
        self.db.update_mailing_status(mailing_id, 'in_progress')
        
        # Определяем список получателей
        if mailing['send_to_all']:
            users = self.db.get_all_users()
            target_user_ids = users  # get_all_users() уже возвращает список user_id
        else:
            target_user_ids = mailing.get('target_user_ids', [])
        
        if not target_user_ids:
            self.db.update_mailing_status(mailing_id, 'failed')
            return {'sent': 0, 'failed': 0, 'total': 0}
        
        # Отправляем сообщения
        sent_count = 0
        failed_count = 0
        
        for user_id in target_user_ids:
            success = await self.send_post_to_user(user_id, post, mailing_id)
            if success:
                sent_count += 1
            else:
                failed_count += 1
            
            # Небольшая задержка между отправками
            await asyncio.sleep(0.05)
        
        # Обновляем статус и счетчики
        status = 'completed' if failed_count == 0 else 'completed'
        self.db.update_mailing_status(mailing_id, status, sent_count, failed_count)
        
        return {
            'sent': sent_count,
            'failed': failed_count,
            'total': len(target_user_ids)
        }
    
    async def process_pending_mailings(self) -> Dict[str, int]:
        """Обрабатывает все ожидающие рассылки."""
        pending_mailings = self.db.get_pending_mailings()
        
        if not pending_mailings:
            return {'processed': 0, 'total_sent': 0, 'total_failed': 0}
        
        total_sent = 0
        total_failed = 0
        
        for mailing in pending_mailings:
            result = await self.process_mailing(mailing)
            total_sent += result['sent']
            total_failed += result['failed']
        
        return {
            'processed': len(pending_mailings),
            'total_sent': total_sent,
            'total_failed': total_failed
        }
    
    def format_post_preview(self, post: Dict[str, Any], max_length: int = 100) -> str:
        """Форматирует превью поста для отображения в админке."""
        content = post['content']
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return f"📝 {post['title']}\n{content}"
    
    def format_mailing_preview(self, mailing: Dict[str, Any]) -> str:
        """Форматирует превью рассылки для отображения в админке."""
        status_emoji = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅',
            'failed': '❌'
        }
        
        emoji = status_emoji.get(mailing['status'], '❓')
        target = "всем пользователям" if mailing['send_to_all'] else f"{len(mailing.get('target_user_ids', []))} пользователям"
        
        scheduled_text = ""
        if mailing.get('scheduled_at'):
            moscow_time = self._convert_utc_to_moscow(mailing['scheduled_at'])
            scheduled_text = f"\n📅 Запланировано на: {moscow_time}"
        
        return f"{emoji} {mailing['title']}\n👥 {target}{scheduled_text}"
    
    def validate_post_data(self, title: str, content: str) -> Dict[str, Any]:
        """Валидирует данные поста."""
        errors = []
        
        if not title or not title.strip():
            errors.append("Заголовок не может быть пустым")
        
        if not content or not content.strip():
            errors.append("Содержание поста не может быть пустым")
        
        if len(title) > 100:
            errors.append("Заголовок слишком длинный (максимум 100 символов)")
        
        if len(content) > 4096:
            errors.append("Содержание поста слишком длинное (максимум 4096 символов)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_mailing_data(self, send_to_all: bool, target_user_ids: List[int] = None, 
                            scheduled_at: str = None) -> Dict[str, Any]:
        """Валидирует данные рассылки."""
        errors = []
        
        if not send_to_all and (not target_user_ids or len(target_user_ids) == 0):
            errors.append("Необходимо указать хотя бы одного получателя")
        
        if scheduled_at:
            try:
                # Проверяем, что время в будущем
                scheduled_dt = datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M")
                now = datetime.now()
                if scheduled_dt <= now:
                    errors.append("Время отправки должно быть в будущем")
            except ValueError:
                errors.append("Неверный формат времени (используйте YYYY-MM-DD HH:MM)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        } 