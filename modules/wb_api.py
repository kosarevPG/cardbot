# Wildberries API модуль
import httpx
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import os

logger = logging.getLogger(__name__)

class WildberriesAPI:
    """Класс для работы с Wildberries API"""
    
    def __init__(self):
        self.api_key = os.getenv("W", "")  # API ключ из переменной окружения
        self.base_url = "https://suppliers-api.wildberries.ru"
        # Альтернативные URL если основной не работает
        self.fallback_urls = [
            "https://suppliers-api.wildberries.ru",
            "https://suppliers-api.wildberries.ru:443",
            "https://suppliers-api.wildberries.ru/api"
        ]
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        if not self.api_key:
            logger.error("Wildberries API ключ не найден в переменной окружения W")
            raise ValueError("API ключ Wildberries не настроен")
    
    async def test_connection(self) -> Dict[str, Union[bool, str]]:
        """Тестирует подключение к WB API"""
        # Сначала пробуем основной URL
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/supplies",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "Подключение к WB API успешно"}
                else:
                    return {"success": False, "message": f"Ошибка API: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Ошибка подключения к WB API (основной URL): {e}")
            
            # Если основная ошибка DNS, пробуем fallback URL
            if "Name or service not known" in str(e):
                logger.info("Пробуем fallback URL для WB API...")
                return await self._test_fallback_connection()
            elif "401" in str(e):
                return {"success": False, "message": "Ошибка авторизации: проверьте API ключ в переменной W"}
            else:
                return {"success": False, "message": f"Ошибка подключения: {str(e)}"}
    
    async def _test_fallback_connection(self) -> Dict[str, Union[bool, str]]:
        """Тестирует подключение с fallback URL"""
        for fallback_url in self.fallback_urls:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(
                        f"{fallback_url}/api/v1/supplies",
                        headers=self.headers
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"Успешное подключение через fallback URL: {fallback_url}")
                        return {"success": True, "message": f"Подключение к WB API успешно через {fallback_url}"}
                    else:
                        logger.warning(f"Fallback URL {fallback_url} вернул статус {response.status_code}")
                        
            except Exception as e:
                logger.warning(f"Fallback URL {fallback_url} не сработал: {e}")
                continue
        
        return {"success": False, "message": "Ошибка DNS: не удается подключиться ни к одному URL. Проверьте интернет-соединение и доступность WB API."}
    
    async def get_sales_stats(self, date_from: str = None, date_to: str = None) -> Dict:
        """Получает статистику продаж"""
        try:
            # Если даты не указаны, берем последние 7 дней
            if not date_from:
                date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            if not date_to:
                date_to = datetime.now().strftime("%Y-%m-%d")
            
            params = {
                "dateFrom": date_from,
                "dateTo": date_to
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/supplier/sales",
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "data": data,
                        "period": f"{date_from} - {date_to}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения статистики продаж: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_orders(self, date_from: str = None, date_to: str = None) -> Dict:
        """Получает список заказов"""
        try:
            if not date_from:
                date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            if not date_to:
                date_to = datetime.now().strftime("%Y-%m-%d")
            
            params = {
                "dateFrom": date_from,
                "dateTo": date_to
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/supplier/orders",
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "data": data,
                        "period": f"{date_from} - {date_to}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения заказов: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_products(self) -> Dict:
        """Получает список товаров"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/supplier/cards",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "data": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения товаров: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_stocks(self) -> Dict:
        """Получает остатки товаров"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/supplier/stocks",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "data": data
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения остатков: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_daily_stats(self) -> Dict:
        """Получает дневную статистику"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Получаем продажи за сегодня
            sales = await self.get_sales_stats(today, today)
            # Получаем заказы за сегодня
            orders = await self.get_orders(today, today)
            
            return {
                "success": True,
                "date": today,
                "sales": sales,
                "orders": orders
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения дневной статистики: {e}")
            return {"success": False, "error": str(e)}

# Функции для удобного использования
async def test_wb_connection() -> str:
    """Тестирует подключение к WB API и возвращает сообщение"""
    try:
        wb_api = WildberriesAPI()
        result = await wb_api.test_connection()
        
        if result["success"]:
            return "✅ Подключение к Wildberries API успешно установлено!"
        else:
            return f"❌ Ошибка подключения к WB API: {result['message']}"
            
    except Exception as e:
        return f"❌ Критическая ошибка: {str(e)}"

async def get_wb_summary() -> str:
    """Получает краткую сводку по WB"""
    try:
        wb_api = WildberriesAPI()
        
        # Получаем дневную статистику
        daily_stats = await wb_api.get_daily_stats()
        
        if not daily_stats["success"]:
            return f"❌ Ошибка получения статистики: {daily_stats.get('error', 'Неизвестная ошибка')}"
        
        # Формируем краткую сводку
        summary = f"📊 **Сводка Wildberries за {daily_stats['date']}**\n\n"
        
        # Добавляем информацию о продажах
        if daily_stats["sales"]["success"]:
            sales_data = daily_stats["sales"]["data"]
            if isinstance(sales_data, list) and len(sales_data) > 0:
                summary += f"💰 Продажи: {len(sales_data)} записей\n"
            else:
                summary += "💰 Продажи: нет данных\n"
        else:
            summary += f"💰 Продажи: ошибка получения\n"
        
        # Добавляем информацию о заказах
        if daily_stats["orders"]["success"]:
            orders_data = daily_stats["orders"]["data"]
            if isinstance(orders_data, list) and len(orders_data) > 0:
                summary += f"📦 Заказы: {len(orders_data)} записей\n"
            else:
                summary += "📦 Заказы: нет данных\n"
        else:
            summary += f"📦 Заказы: ошибка получения\n"
        
        return summary
        
    except Exception as e:
        return f"❌ Ошибка получения сводки: {str(e)}"
