# Сервис уведомлений о событиях маркетплейсов (заказы, изменения цен)
import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from aiogram import Bot

from .marketplace_manager import MarketplaceManager

logger = logging.getLogger(__name__)


class MarketplaceNotificationService:
    """Сервис для отслеживания событий маркетплейсов и отправки уведомлений"""
    
    def __init__(self, bot: Bot, admin_ids: List[str], check_interval: int = 300):
        """
        Args:
            bot: Экземпляр бота для отправки уведомлений
            admin_ids: Список ID администраторов для отправки уведомлений
            check_interval: Интервал проверки в секундах (по умолчанию 5 минут)
        """
        self.bot = bot
        self.admin_ids = admin_ids
        self.check_interval = check_interval
        self.manager = MarketplaceManager()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Хранилище последних проверенных заказов (для отслеживания новых)
        self._last_ozon_order_ids: Set[str] = set()
        self._last_wb_order_ids: Set[str] = set()
        
        # Хранилище последних цен (для отслеживания изменений)
        self._last_prices: Dict[str, Dict[str, str]] = {
            "ozon": {},  # offer_id -> price
            "wb": {}     # nm_id -> price
        }
    
    async def start(self):
        """Запускает сервис polling"""
        if self._running:
            logger.warning("MarketplaceNotificationService уже запущен")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._polling_loop())
        logger.info(f"MarketplaceNotificationService запущен (интервал: {self.check_interval} сек)")
    
    async def stop(self):
        """Останавливает сервис polling"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("MarketplaceNotificationService остановлен")
    
    async def _polling_loop(self):
        """Основной цикл polling"""
        while self._running:
            try:
                await self._check_new_orders()
                await self._check_price_changes()
            except Exception as e:
                logger.error(f"Ошибка в polling loop: {e}", exc_info=True)
            
            # Ждём перед следующей проверкой
            await asyncio.sleep(self.check_interval)
    
    async def _check_new_orders(self):
        """Проверяет новые заказы и отправляет уведомления"""
        try:
            # Проверяем заказы Ozon
            if self.manager.ozon_api_key and self.manager.ozon_client_id:
                ozon_result = await self.manager.get_ozon_orders(
                    since=datetime.now() - timedelta(hours=1),  # Проверяем за последний час
                    limit=100
                )
                
                if ozon_result.get("success"):
                    orders = ozon_result.get("orders", [])
                    new_orders = []
                    
                    for order in orders:
                        order_id = str(order.get("posting_number", ""))
                        if order_id and order_id not in self._last_ozon_order_ids:
                            new_orders.append(order)
                            self._last_ozon_order_ids.add(order_id)
                    
                    # Отправляем уведомления о новых заказах
                    for order in new_orders:
                        await self._send_order_notification("Ozon", order)
            
            # Проверяем заказы Wildberries
            if self.manager.wb_api_key:
                wb_result = await self.manager.get_wb_orders(
                    date_from=datetime.now() - timedelta(hours=1),  # Проверяем за последний час
                    limit=100
                )
                
                if wb_result.get("success"):
                    orders = wb_result.get("orders", [])
                    new_orders = []
                    
                    for order in orders:
                        order_id = str(order.get("orderId", ""))
                        if order_id and order_id not in self._last_wb_order_ids:
                            new_orders.append(order)
                            self._last_wb_order_ids.add(order_id)
                    
                    # Отправляем уведомления о новых заказах
                    for order in new_orders:
                        await self._send_order_notification("Wildberries", order)
                        
        except Exception as e:
            logger.error(f"Ошибка проверки новых заказов: {e}", exc_info=True)
    
    async def _check_price_changes(self):
        """Проверяет изменения цен и отправляет уведомления"""
        try:
            # Читаем текущие цены из таблицы
            prices_result = await self.manager.read_prices_from_sheet()
            if not prices_result.get("success"):
                return
            
            # Проверяем изменения цен Ozon
            ozon_prices = prices_result.get("ozon_prices", [])
            for item in ozon_prices:
                offer_id = item.get("offer_id", "")
                current_price = item.get("price", "")
                name = item.get("name", offer_id)
                
                if offer_id and current_price:
                    last_price = self._last_prices["ozon"].get(offer_id)
                    if last_price and last_price != current_price:
                        # Цена изменилась
                        await self._send_price_change_notification(
                            "Ozon", name, offer_id, last_price, current_price
                        )
                    
                    # Обновляем последнюю цену
                    self._last_prices["ozon"][offer_id] = current_price
            
            # Проверяем изменения цен Wildberries
            wb_prices = prices_result.get("wb_prices", [])
            for item in wb_prices:
                nm_id = item.get("nm_id", "")
                current_price = item.get("price", "")
                name = item.get("name", nm_id)
                
                if nm_id and current_price:
                    last_price = self._last_prices["wb"].get(nm_id)
                    if last_price and last_price != current_price:
                        # Цена изменилась
                        await self._send_price_change_notification(
                            "Wildberries", name, nm_id, last_price, current_price
                        )
                    
                    # Обновляем последнюю цену
                    self._last_prices["wb"][nm_id] = current_price
                    
        except Exception as e:
            logger.error(f"Ошибка проверки изменений цен: {e}", exc_info=True)
    
    async def _send_order_notification(self, marketplace: str, order: Dict):
        """Отправляет уведомление о новом заказе"""
        try:
            # Формируем сообщение о заказе
            if marketplace == "Ozon":
                order_id = order.get("posting_number", "н/д")
                products = order.get("products", [])
                product_names = [p.get("name", "н/д") for p in products[:3]]  # Первые 3 товара
                total_price = order.get("financial_data", {}).get("products", [{}])[0].get("price", "н/д") if order.get("financial_data", {}).get("products") else "н/д"
                
                message = (
                    f"🛒 **Новый заказ {marketplace}!**\n\n"
                    f"📦 Номер заказа: `{order_id}`\n"
                    f"💰 Сумма: {total_price} ₽\n"
                    f"📋 Товары: {', '.join(product_names) if product_names else 'н/д'}"
                )
            else:  # Wildberries
                order_id = order.get("orderId", "н/д")
                skus = order.get("skus", [])
                total_price = order.get("totalPrice", "н/д")
                
                message = (
                    f"🛒 **Новый заказ {marketplace}!**\n\n"
                    f"📦 Номер заказа: `{order_id}`\n"
                    f"💰 Сумма: {total_price} ₽\n"
                    f"📋 SKU: {', '.join(str(s) for s in skus[:3]) if skus else 'н/д'}"
                )
            
            # Отправляем уведомление всем админам
            for admin_id in self.admin_ids:
                try:
                    await self.bot.send_message(
                        int(admin_id),
                        message,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка формирования уведомления о заказе: {e}", exc_info=True)
    
    async def _send_price_change_notification(self, marketplace: str, product_name: str, 
                                             product_id: str, old_price: str, new_price: str):
        """Отправляет уведомление об изменении цены"""
        try:
            message = (
                f"💰 **Изменилась цена!**\n\n"
                f"🛍️ Маркетплейс: {marketplace}\n"
                f"📦 Товар: {product_name}\n"
                f"🆔 ID: `{product_id}`\n"
                f"📉 Было: {old_price}\n"
                f"📈 Стало: {new_price}"
            )
            
            # Отправляем уведомление всем админам
            for admin_id in self.admin_ids:
                try:
                    await self.bot.send_message(
                        int(admin_id),
                        message,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка формирования уведомления об изменении цены: {e}", exc_info=True)
