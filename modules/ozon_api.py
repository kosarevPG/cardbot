# Ozon API модуль
import httpx
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import os

logger = logging.getLogger(__name__)

class OzonAPI:
    """Класс для работы с Ozon API"""
    
    def __init__(self):
        self.api_key = os.getenv("O", "")  # API ключ из переменной окружения
        self.client_id = os.getenv("OZON_CLIENT_ID", "")  # Client ID для Ozon
        self.base_url = "https://api-seller.ozon.ru"
        self.headers = {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        if not self.api_key:
            logger.error("Ozon API ключ не найден в переменной окружения O")
            raise ValueError("API ключ Ozon не настроен")
        
        if not self.client_id:
            logger.warning("Ozon Client ID не найден, некоторые функции могут не работать")
    
    async def test_connection(self) -> Dict[str, Union[bool, str]]:
        """Тестирует подключение к Ozon API"""
        try:
            # Простой тест - получаем информацию о продавце
            payload = {
                "method": "v2/info/list"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/v2/info/list",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "Подключение к Ozon API успешно"}
                else:
                    return {"success": False, "message": f"Ошибка API: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Ошибка подключения к Ozon API: {e}")
            return {"success": False, "message": f"Ошибка подключения: {str(e)}"}
    
    async def get_sales_stats(self, date_from: str = None, date_to: str = None) -> Dict:
        """Получает статистику продаж"""
        try:
            # Если даты не указаны, берем последние 7 дней
            if not date_from:
                date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            if not date_to:
                date_to = datetime.now().strftime("%Y-%m-%d")
            
            payload = {
                "method": "v3/product/info/list",
                "params": {
                    "filter": {
                        "date_from": date_from,
                        "date_to": date_to
                    }
                }
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/v3/product/info/list",
                    headers=self.headers,
                    json=payload
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
            
            payload = {
                "method": "v3/order/list",
                "params": {
                    "filter": {
                        "date_from": date_from,
                        "date_to": date_to
                    }
                }
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/v3/order/list",
                    headers=self.headers,
                    json=payload
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
            payload = {
                "method": "v2/product/list",
                "params": {
                    "limit": 100,
                    "offset": 0
                }
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/v2/product/list",
                    headers=self.headers,
                    json=payload
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
            payload = {
                "method": "v3/product/info/stocks",
                "params": {
                    "filter": {}
                }
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/v3/product/info/stocks",
                    headers=self.headers,
                    json=payload
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
async def test_ozon_connection() -> str:
    """Тестирует подключение к Ozon API и возвращает сообщение"""
    try:
        ozon_api = OzonAPI()
        result = await ozon_api.test_connection()
        
        if result["success"]:
            return "✅ Подключение к Ozon API успешно установлено!"
        else:
            return f"❌ Ошибка подключения к Ozon API: {result['message']}"
            
    except Exception as e:
        return f"❌ Критическая ошибка: {str(e)}"

async def get_ozon_summary() -> str:
    """Получает краткую сводку по Ozon"""
    try:
        ozon_api = OzonAPI()
        
        # Получаем дневную статистику
        daily_stats = await ozon_api.get_daily_stats()
        
        if not daily_stats["success"]:
            return f"❌ Ошибка получения статистики: {daily_stats.get('error', 'Неизвестная ошибка')}"
        
        # Формируем краткую сводку
        summary = f"📊 **Сводка Ozon за {daily_stats['date']}**\n\n"
        
        # Добавляем информацию о продажах
        if daily_stats["sales"]["success"]:
            sales_data = daily_stats["sales"]["data"]
            if isinstance(sales_data, dict) and "result" in sales_data:
                summary += f"💰 Продажи: данные получены\n"
            else:
                summary += "💰 Продажи: нет данных\n"
        else:
            summary += f"💰 Продажи: ошибка получения\n"
        
        # Добавляем информацию о заказах
        if daily_stats["orders"]["success"]:
            orders_data = daily_stats["orders"]["data"]
            if isinstance(orders_data, dict) and "result" in orders_data:
                summary += f"📦 Заказы: данные получены\n"
            else:
                summary += "📦 Заказы: нет данных\n"
        else:
            summary += f"📦 Заказы: ошибка получения\n"
        
        return summary
        
    except Exception as e:
        return f"❌ Ошибка получения сводки: {str(e)}"
