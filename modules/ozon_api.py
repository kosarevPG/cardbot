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
        self.api_key = os.getenv("OZON_API_KEY", "")  # API ключ из переменной окружения
        self.client_id = os.getenv("OZON_CLIENT_ID", "")  # Client ID для Ozon
        self.base_url = "https://api-seller.ozon.ru"
        
        # Правильные эндпоинты для Ozon API согласно актуальной документации
        self.endpoints = {
            "product_list": "/v3/product/list",           # Получение product_id по offer_id (v3 согласно документации)
            "analytics": "/v1/analytics/data",            # Аналитика (продажи, выручка) - v1 согласно документации
            "stocks": "/v2/product/info/stocks",          # Остатки на складе (v2 согласно документации)
            "product_info": "/v3/product/list"            # Общая информация о товарах
        }
        
        self.headers = {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        if not self.api_key:
            logger.error("Ozon API ключ не найден в переменной окружения OZON_API_KEY")
            raise ValueError("API ключ Ozon не настроен")
        
        if not self.client_id:
            logger.error("Ozon Client ID не найден в переменной окружения OZON_CLIENT_ID")
            raise ValueError("Client ID Ozon не настроен")
    
    async def get_product_mapping(self, page_size: int = 1000, page: int = 1) -> Dict[str, Union[bool, str, Dict]]:
        """
        Получение product_id по offer_id - метод POST /v3/product/list
        Строит словарь соответствия offer_id → product_id согласно документации v3
        """
        try:
            # Согласно документации v3: используем filter, limit, last_id
            payload = {
                "filter": {},
                "limit": page_size,
                "last_id": ""
            }
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoints['product_list']}",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    products = data.get("result", {}).get("items", [])
                    
                    # Строим словарь offer_id → product_id
                    mapping = {}
                    for p in products:
                        offer_id = p.get("offer_id")
                        product_id = p.get("product_id")
                        if offer_id and product_id:
                            mapping[offer_id] = product_id
                    
                    logger.info(f"Получено {len(mapping)} соответствий offer_id → product_id")
                    
                    return {
                        "success": True,
                        "mapping": mapping,
                        "total_count": len(mapping),
                        "page": page,
                        "page_size": page_size
                    }
                else:
                    logger.error(f"Ошибка API при получении product_mapping: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения product_mapping: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_analytics(self, product_ids: List[int], date_from: str = None, date_to: str = None) -> Dict[str, Union[bool, str, Dict]]:
        """
        Получение аналитики (продажи, выручка) - метод POST /v1/analytics/data согласно документации
        """
        try:
            # Если даты не указаны, берем последние 7 дней
            if not date_from:
                date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            if not date_to:
                date_to = datetime.now().strftime("%Y-%m-%d")
            
            # Согласно документации v1: правильная структура запроса с product_id
            payload = {
                "date_from": date_from,
                "date_to": date_to,
                "metrics": ["ordered_units", "revenue"],
                "dimension": "product_id",
                "filters": [
                    {
                        "key": "product_id",
                        "op": "IN",
                        "value": product_ids
                    }
                ],
                "limit": 1000
            }
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoints['analytics']}",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Получена аналитика для {len(product_ids)} товаров за период {date_from} - {date_to}")
                    
                    return {
                        "success": True,
                        "data": data,
                        "period": f"{date_from} - {date_to}",
                        "product_count": len(product_ids)
                    }
                else:
                    logger.error(f"Ошибка API при получении аналитики: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения аналитики: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_stocks(self, product_id: int) -> Dict[str, Union[bool, str, Dict]]:
        """
        Остатки на складе - метод POST /v2/product/info/stocks согласно документации
        """
        try:
            # Согласно документации v2: передаем массив product_id
            payload = {
                "product_id": [product_id]
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.endpoints['stocks']}",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Согласно документации v2: result содержит массив с данными по каждому product_id
                    result_items = data.get("result", [])
                    
                    if result_items and len(result_items) > 0:
                        # Берем первый элемент (наш product_id)
                        item = result_items[0]
                        stocks = item.get("stocks", [])
                        
                        # Считаем общий остаток по всем складам
                        total_present = sum(int(wh.get("present", 0)) for wh in stocks)
                        
                        logger.info(f"Получены остатки для product_id {product_id}: {total_present}")
                        
                        return {
                            "success": True,
                            "product_id": product_id,
                            "total_stock": total_present,
                            "warehouse_stocks": stocks,
                            "raw_data": data
                        }
                    else:
                        return {
                            "success": True,
                            "product_id": product_id,
                            "total_stock": 0,
                            "warehouse_stocks": [],
                            "raw_data": data
                        }
                else:
                    logger.error(f"Ошибка API при получении остатков для product_id {product_id}: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения остатков для product_id {product_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_stocks_batch(self, product_ids: List[int]) -> Dict[str, Union[bool, str, Dict]]:
        """
        Получение остатков для нескольких товаров
        """
        try:
            results = {}
            errors = []
            
            for product_id in product_ids:
                stock_result = await self.get_stocks(product_id)
                if stock_result["success"]:
                    results[product_id] = stock_result
                else:
                    errors.append({"product_id": product_id, "error": stock_result["error"]})
            
            return {
                "success": True,
                "stocks": results,
                "errors": errors,
                "total_processed": len(product_ids),
                "successful": len(results),
                "failed": len(errors)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения остатков для batch: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_complete_product_data(self, offer_ids: List[str]) -> Dict[str, Union[bool, str, Dict]]:
        """
        Полный цикл получения данных: offer_id → product_id → аналитика + остатки
        """
        try:
            # 1. Получаем соответствие offer_id → product_id
            mapping_result = await self.get_product_mapping()
            if not mapping_result["success"]:
                return mapping_result
            
            mapping = mapping_result["mapping"]
            
            # 2. Фильтруем только нужные product_id
            target_product_ids = []
            offer_to_product = {}
            
            for offer_id in offer_ids:
                if offer_id in mapping:
                    product_id = mapping[offer_id]
                    target_product_ids.append(product_id)
                    offer_to_product[offer_id] = product_id
                else:
                    logger.warning(f"offer_id {offer_id} не найден в mapping")
            
            if not target_product_ids:
                return {
                    "success": False,
                    "error": "Не найдено ни одного соответствия offer_id → product_id"
                }
            
            # 3. Получаем аналитику
            analytics_result = await self.get_analytics(target_product_ids)
            
            # 4. Получаем остатки
            stocks_result = await self.get_stocks_batch(target_product_ids)
            
            return {
                "success": True,
                "mapping": offer_to_product,
                "analytics": analytics_result,
                "stocks": stocks_result,
                "summary": {
                    "total_offers": len(offer_ids),
                    "found_products": len(target_product_ids),
                    "analytics_success": analytics_result["success"],
                    "stocks_success": stocks_result["success"]
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения полных данных: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_connection(self) -> Dict[str, Union[bool, str]]:
        """Тестирует подключение к Ozon API"""
        try:
            # Простой тест - получаем список товаров
            result = await self.get_product_mapping(page_size=1, page=1)
            
            if result["success"]:
                return {"success": True, "message": "Подключение к Ozon API успешно"}
            else:
                return {"success": False, "message": result["error"]}
                
        except Exception as e:
            logger.error(f"Ошибка подключения к Ozon API: {e}")
            return {"success": False, "message": f"Ошибка подключения: {str(e)}"}

# Функции для удобного использования
async def get_ozon_product_mapping(page_size: int = 1000) -> Dict:
    """Получает соответствие offer_id → product_id"""
    try:
        ozon_api = OzonAPI()
        return await ozon_api.get_product_mapping(page_size=page_size)
    except Exception as e:
        return {"success": False, "error": str(e)}

async def get_ozon_analytics(product_ids: List[int], days: int = 7) -> Dict:
    """Получает аналитику продаж и выручки"""
    try:
        ozon_api = OzonAPI()
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        return await ozon_api.get_analytics(product_ids, date_from, date_to)
    except Exception as e:
        return {"success": False, "error": str(e)}

async def get_ozon_stocks(product_id: int) -> Dict:
    """Получает остатки товара на складе"""
    try:
        ozon_api = OzonAPI()
        return await ozon_api.get_stocks(product_id)
    except Exception as e:
        return {"success": False, "error": str(e)}

async def get_ozon_complete_data(offer_ids: List[str]) -> Dict:
    """Получает полные данные по товарам: аналитику + остатки"""
    try:
        ozon_api = OzonAPI()
        return await ozon_api.get_complete_product_data(offer_ids)
    except Exception as e:
        return {"success": False, "error": str(e)}

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
    """Получает краткую сводку по Ozon для использования в командах бота"""
    try:
        ozon_api = OzonAPI()
        
        # Получаем соответствие offer_id → product_id
        mapping_result = await ozon_api.get_product_mapping(page_size=100, page=1)
        
        if not mapping_result["success"]:
            return f"❌ Ошибка получения данных: {mapping_result.get('error', 'Неизвестная ошибка')}"
        
        mapping = mapping_result["mapping"]
        total_products = len(mapping)
        
        if total_products == 0:
            return "📭 **Сводка Ozon**\n\n⚠️ Товары не найдены (возможно, нет товаров в аккаунте)"
        
        # Формируем краткую сводку
        summary = f"📊 **Сводка Ozon**\n\n"
        summary += f"📦 **Всего товаров:** {total_products}\n"
        
        # Показываем первые 5 товаров
        summary += f"\n📋 **Первые товары:**\n"
        for i, (offer_id, product_id) in enumerate(list(mapping.items())[:5], 1):
            summary += f"{i}. `{offer_id}` → ID: `{product_id}`\n"
        
        if total_products > 5:
            summary += f"\n... и еще {total_products - 5} товаров"
        
        # Пытаемся получить аналитику за последние 7 дней для первых 3 товаров
        if total_products >= 3:
            try:
                first_product_ids = list(mapping.values())[:3]
                analytics_result = await ozon_api.get_analytics(first_product_ids, days=7)
                
                if analytics_result["success"]:
                    summary += f"\n\n📈 **Аналитика за 7 дней:**\n"
                    summary += f"✅ Данные получены для {analytics_result['product_count']} товаров\n"
                    summary += f"📅 Период: {analytics_result['period']}"
                else:
                    summary += f"\n\n📈 **Аналитика:** ❌ Ошибка получения"
            except Exception as e:
                summary += f"\n\n📈 **Аналитика:** ⚠️ Не удалось получить"
        
        return summary
        
    except Exception as e:
        return f"❌ Ошибка получения сводки: {str(e)}"

async def get_ozon_products() -> Dict:
    """Получает список товаров Ozon для использования в командах бота"""
    try:
        ozon_api = OzonAPI()
        return await ozon_api.get_product_mapping(page_size=100, page=1)
    except Exception as e:
        return {"success": False, "error": str(e)}

async def get_ozon_stocks() -> Dict:
    """Получает остатки товаров Ozon для использования в командах бота"""
    try:
        ozon_api = OzonAPI()
        
        # Сначала получаем список товаров
        products_result = await ozon_api.get_product_mapping(page_size=100, page=1)
        if not products_result["success"]:
            return products_result
        
        mapping = products_result["mapping"]
        if not mapping:
            return {"success": True, "data": {"result": {"items": [], "total": 0}}}
        
        # Получаем остатки для первых 10 товаров
        first_product_ids = list(mapping.values())[:10]
        stocks_result = await ozon_api.get_stocks_batch(first_product_ids)
        
        if not stocks_result["success"]:
            return stocks_result
        
        # Формируем ответ в том же формате, что ожидает marketplace_commands
        items = []
        for offer_id, product_id in list(mapping.items())[:10]:
            stock_info = stocks_result["stocks"].get(product_id, {})
            total_stock = stock_info.get("total_stock", 0) if stock_info else 0
            
            items.append({
                "offer_id": offer_id,
                "product_id": product_id,
                "has_fbo_stocks": total_stock > 0,
                "has_fbs_stocks": total_stock > 0,
                "archived": False,
                "stock": total_stock
            })
        
        return {
            "success": True,
            "data": {
                "result": {
                    "items": items,
                    "total": len(items)
                }
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
