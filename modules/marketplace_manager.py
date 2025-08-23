# DEPLOY_TRIGGER 2025-08-22
# Единый модуль управления маркетплейсами (Ozon + Wildberries)
import httpx
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
import os
from .google_sheets import GoogleSheetsAPI

logger = logging.getLogger(__name__)

class MarketplaceManager:
    """Единый менеджер для работы с маркетплейсами Ozon и Wildberries"""
    
    def __init__(self):
        # Ozon API настройки
        self.ozon_api_key = os.getenv("OZON_API_KEY", "")
        self.ozon_client_id = os.getenv("OZON_CLIENT_ID", "")
        self.ozon_base_url = "https://api-seller.ozon.ru"
        
        # Wildberries API настройки
        self.wb_api_key = os.getenv("WB_API_KEY", "")
        self.wb_base_url = "https://suppliers-api.wildberries.ru"
        
        # Google Sheets настройки
        self.sheets_api = GoogleSheetsAPI()
        self.spreadsheet_id = "1RoWWv9BgiwlSu9H-KJNsFItQxlUVhG1WMbyB0eFxzYM"
        self.sheet_name = "marketplaces"
        
        # Структура таблицы для Ozon
        self.ozon_columns = {
            "offer_id": "D",      # Арт. Ozon
            "stock": "F",         # Остаток Ozon
            "sales": "H",         # Продажи Ozon
            "revenue": "J"        # Выручка Ozon
        }
        
        # Структура таблицы для Wildberries
        self.wb_columns = {
            "nm_id": "B",         # Артикул WB
            "stock": "E",         # Остаток WB
            "sales": "G",         # Продажи WB
            "revenue": "I"        # Выручка WB
        }
        
        # Ozon API эндпоинты
        self.ozon_endpoints = {
            "product_list": "/v3/product/list",
            "analytics": "/v1/analytics/data",
            "stocks": "/v4/product/info/stocks",
            "product_info": "/v3/product/list"
        }
        
        # Проверка настроек
        self._validate_config()
    
    def _validate_config(self):
        """Проверяет корректность настроек API"""
        if not self.ozon_api_key or not self.ozon_client_id:
            logger.warning("Ozon API не настроен - функции Ozon будут недоступны")
        
        if not self.wb_api_key:
            logger.warning("Wildberries API не настроен - функции WB будут недоступны")
    
    # ==================== OZON API МЕТОДЫ ====================
    
    def _get_ozon_headers(self) -> Dict[str, str]:
        """Возвращает заголовки для Ozon API"""
        return {
            "Client-Id": self.ozon_client_id,
            "Api-Key": self.ozon_api_key,
            "Content-Type": "application/json"
        }
    
    async def get_ozon_product_mapping(self, page_size: int = 1000) -> Dict[str, Union[bool, str, Dict]]:
        """Получение соответствия offer_id → product_id для Ozon"""
        if not self.ozon_api_key or not self.ozon_client_id:
            return {"success": False, "error": "Ozon API не настроен"}
        
        try:
            last_id = ""
            mapping = {}
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                while True:
                    payload = {
                        "filter": {},
                        "limit": page_size,
                        "last_id": last_id
                    }
                    
                    response = await client.post(
                        f"{self.ozon_base_url}{self.ozon_endpoints['product_list']}",
                        headers=self._get_ozon_headers(),
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        products = data.get("result", {}).get("items", [])
                        
                        for product in products:
                            offer_id = product.get("offer_id")
                            product_id = product.get("product_id")
                            if offer_id and product_id:
                                mapping[offer_id] = product_id
                        
                        last_id = data.get("result", {}).get("last_id", "")
                        if not last_id or len(products) < page_size:
                            break
                    else:
                        logger.error(f"Ошибка Ozon API: {response.status_code} - {response.text}")
                        return {
                            "success": False,
                            "error": f"Ошибка API: {response.status_code}",
                            "details": response.text
                        }
                
                logger.info(f"Получено {len(mapping)} соответствий Ozon offer_id → product_id")
                return {
                    "success": True,
                    "mapping": mapping,
                    "total_count": len(mapping)
                }
                    
        except Exception as e:
            logger.error(f"Ошибка получения Ozon product_mapping: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_ozon_stocks(self, product_ids: List[int]) -> Dict[str, Union[bool, str, Dict]]:
        """Получение остатков товаров Ozon по product_id"""
        if not self.ozon_api_key or not self.ozon_client_id:
            return {"success": False, "error": "Ozon API не настроен"}
        
        # Проверяем, что список product_ids не пустой
        if not product_ids:
            return {"success": False, "error": "Список product_ids пустой"}
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Формируем правильный запрос согласно документации Ozon API
                payload = {
                    "product_id": product_ids,
                    "limit": 1000,  # Добавляем обязательное поле limit
                    "filter": {}     # Добавляем обязательное поле filter
                }
                response = await client.post(
                    f"{self.ozon_base_url}{self.ozon_endpoints['stocks']}",
                    headers=self._get_ozon_headers(),
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    stocks_data = {}
                    
                    for item in data.get("result", []):
                        product_id = item.get("product_id")
                        stocks = item.get("stocks", [])
                        total_present = sum(int(wh.get("present", 0)) for wh in stocks)
                        stocks_data[str(product_id)] = total_present
                    
                    return {
                        "success": True,
                        "stocks": stocks_data
                    }
                else:
                    logger.error(f"Ошибка получения Ozon stocks: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения Ozon stocks: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_ozon_analytics(self, date_from: str, date_to: str) -> Dict[str, Union[bool, str, Dict]]:
        """Получение аналитики Ozon (продажи, выручка)"""
        if not self.ozon_api_key or not self.ozon_client_id:
            return {"success": False, "error": "Ozon API не настроен"}
        
        try:
            payload = {
                "date_from": date_from,
                "date_to": date_to,
                "metrics": ["revenue", "orders_count"],
                "dimensions": ["sku"],  # Используем "sku" вместо "offer_id" согласно документации
                "limit": 1000          # Добавляем обязательное поле limit
            }
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.ozon_base_url}{self.ozon_endpoints['analytics']}",
                    headers=self._get_ozon_headers(),
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "analytics": data.get("result", {}).get("data", [])
                    }
                else:
                    logger.error(f"Ошибка получения Ozon analytics: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения Ozon analytics: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== WILDBERRIES API МЕТОДЫ ====================
    
    def _get_wb_headers(self) -> Dict[str, str]:
        """Возвращает заголовки для Wildberries API"""
        return {
            "Authorization": self.wb_api_key,
            "Content-Type": "application/json"
        }
    
    async def get_wb_stocks(self) -> Dict[str, Union[bool, str, Dict]]:
        """Получение остатков товаров Wildberries"""
        if not self.wb_api_key:
            return {"success": False, "error": "Wildberries API не настроен"}
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.wb_base_url}/api/v3/supplies/stocks",
                    headers=self._get_wb_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "stocks": data.get("stocks", [])
                    }
                else:
                    logger.error(f"Ошибка получения WB stocks: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения WB stocks: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_wb_analytics(self, date_from: str, date_to: str) -> Dict[str, Union[bool, str, Dict]]:
        """Получение аналитики Wildberries"""
        if not self.wb_api_key:
            return {"success": False, "error": "Wildberries API не настроен"}
        
        try:
            params = {
                "dateFrom": date_from,
                "dateTo": date_to
            }
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{self.wb_base_url}/api/v1/supplier/reportDetailByPeriod",
                    headers=self._get_wb_headers(),
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "analytics": data
                    }
                else:
                    logger.error(f"Ошибка получения WB analytics: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка получения WB analytics: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== СИНХРОНИЗАЦИЯ С GOOGLE SHEETS ====================
    
    async def sync_ozon_data(self) -> Dict[str, Union[bool, str, Dict]]:
        """Синхронизация данных Ozon с Google таблицами"""
        try:
            # Получаем mapping offer_id → product_id
            mapping_result = await self.get_ozon_product_mapping()
            if not mapping_result["success"]:
                return mapping_result
            
            offer_map = mapping_result["mapping"]
            
            # Получаем остатки
            product_ids = list(offer_map.values())
            stocks_result = await self.get_ozon_stocks(product_ids)
            if not stocks_result["success"]:
                return stocks_result
            
            stocks = stocks_result["stocks"]
            
            # Получаем аналитику за последние 30 дней
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            analytics_result = await self.get_ozon_analytics(date_from, date_to)
            
            # Подготавливаем данные для таблицы
            table_data = []
            for offer_id, product_id in offer_map.items():
                stock = stocks.get(str(product_id), 0)
                
                # Здесь можно добавить логику получения продаж и выручки из analytics
                # Пока оставляем пустыми
                sales = 0
                revenue = 0
                
                table_data.append({
                    "offer_id": offer_id,
                    "stock": stock,
                    "sales": sales,
                    "revenue": revenue
                })
            
            # Обновляем Google таблицу
            await self._update_ozon_sheet(table_data)
            
            return {
                "success": True,
                "message": f"Синхронизировано {len(table_data)} товаров Ozon",
                "data": table_data
            }
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации Ozon: {e}")
            return {"success": False, "error": str(e)}
    
    async def sync_wb_data(self) -> Dict[str, Union[bool, str, Dict]]:
        """Синхронизация данных Wildberries с Google таблицами"""
        try:
            # Получаем остатки
            stocks_result = await self.get_wb_stocks()
            if not stocks_result["success"]:
                return stocks_result
            
            stocks = stocks_result["stocks"]
            
            # Получаем аналитику
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            analytics_result = await self.get_wb_analytics(date_from, date_to)
            
            # Подготавливаем данные для таблицы
            table_data = []
            for stock_item in stocks:
                nm_id = stock_item.get("nmId")
                stock = stock_item.get("quantity", 0)
                
                # Здесь можно добавить логику получения продаж и выручки
                sales = 0
                revenue = 0
                
                table_data.append({
                    "nm_id": nm_id,
                    "stock": stock,
                    "sales": sales,
                    "revenue": revenue
                })
            
            # Обновляем Google таблицу
            await self._update_wb_sheet(table_data)
            
            return {
                "success": True,
                "message": f"Синхронизировано {len(table_data)} товаров Wildberries",
                "data": table_data
            }
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации Wildberries: {e}")
            return {"success": False, "error": str(e)}
    
    async def sync_all_marketplaces(self) -> Dict[str, Union[bool, str, Dict]]:
        """Синхронизация всех маркетплейсов"""
        results = {}
        
        # Синхронизируем Ozon
        if self.ozon_api_key and self.ozon_client_id:
            results["ozon"] = await self.sync_ozon_data()
        else:
            results["ozon"] = {"success": False, "error": "API не настроен"}
        
        # Синхронизируем Wildberries
        if self.wb_api_key:
            results["wildberries"] = await self.sync_wb_data()
        else:
            results["wildberries"] = {"success": False, "error": "API не настроен"}
        
        return results
    
    async def _update_ozon_sheet(self, data: List[Dict[str, Any]]) -> None:
        """Обновляет лист Ozon в Google таблице"""
        try:
            # Подготавливаем данные для записи
            rows = []
            for item in data:
                rows.append([
                    item["offer_id"],  # Колонка D
                    "",               # Колонка E (пустая)
                    item["stock"],    # Колонка F
                    "",               # Колонка G (пустая)
                    item["sales"],    # Колонка H
                    "",               # Колонка I (пустая)
                    item["revenue"]   # Колонка J
                ])
            
            # Записываем в таблицу
            await self.sheets_api.write_data(
                self.spreadsheet_id,
                f"{self.sheet_name}!D2:J{len(rows)+1}",
                rows
            )
            
            logger.info(f"Обновлен лист Ozon: {len(rows)} строк")
            
        except Exception as e:
            logger.error(f"Ошибка обновления листа Ozon: {e}")
    
    async def _update_wb_sheet(self, data: List[Dict[str, Any]]) -> None:
        """Обновляет лист Wildberries в Google таблице"""
        try:
            # Подготавливаем данные для записи
            rows = []
            for item in data:
                rows.append([
                    item["nm_id"],    # Колонка B
                    "",               # Колонка C (пустая)
                    "",               # Колонка D (пустая)
                    item["stock"],    # Колонка E
                    "",               # Колонка F (пустая)
                    item["sales"],    # Колонка G
                    "",               # Колонка H (пустая)
                    item["revenue"]   # Колонка I
                ])
            
            # Записываем в таблицу
            await self.sheets_api.write_data(
                self.spreadsheet_id,
                f"{self.sheet_name}!B2:I{len(rows)+1}",
                rows
            )
            
            logger.info(f"Обновлен лист Wildberries: {len(rows)} строк")
            
        except Exception as e:
            logger.error(f"Ошибка обновления листа Wildberries: {e}")
    
    # ==================== УТИЛИТЫ ====================
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус всех API"""
        return {
            "ozon": {
                "configured": bool(self.ozon_api_key and self.ozon_client_id),
                "api_key": bool(self.ozon_api_key),
                "client_id": bool(self.ozon_client_id)
            },
            "wildberries": {
                "configured": bool(self.wb_api_key),
                "api_key": bool(self.wb_api_key)
            },
            "google_sheets": {
                "configured": True  # Google Sheets всегда доступен
            }
        }
    
    async def test_connections(self) -> Dict[str, Union[bool, str]]:
        """Тестирует подключения ко всем API"""
        results = {}
        
        # Тест Ozon
        if self.ozon_api_key and self.ozon_client_id:
            try:
                test_result = await self.get_ozon_product_mapping(page_size=1)
                results["ozon"] = test_result["success"]
            except Exception as e:
                results["ozon"] = f"Ошибка: {str(e)}"
        else:
            results["ozon"] = "API не настроен"
        
        # Тест Wildberries
        if self.wb_api_key:
            try:
                test_result = await self.get_wb_stocks()
                results["wildberries"] = test_result["success"]
            except Exception as e:
                results["wildberries"] = f"Ошибка: {str(e)}"
        else:
            results["wildberries"] = "API не настроен"
        
        # Тест Google Sheets
        try:
            # Простая проверка - пытаемся прочитать заголовки
            await self.sheets_api.read_data(self.spreadsheet_id, f"{self.sheet_name}!A1:Z1")
            results["google_sheets"] = True
        except Exception as e:
            results["google_sheets"] = f"Ошибка: {str(e)}"
        
        return results
