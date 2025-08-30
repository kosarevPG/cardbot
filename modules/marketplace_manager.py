# FORCE RESTART 2025-08-24 - ИСПРАВЛЕНИЕ Any ИМПОРТА
# FORCE RESTART 2025-08-24 - ИСПРАВЛЕНИЕ ozon_stocks_detailed - теперь использует правильный метод
# FORCE RESTART 2025-08-24 - ИСПРАВЛЕНИЕ sync_ozon_data - теперь правильно записывает остатки в Google таблицу
# FORCE RESTART 2025-08-24 - ИСПРАВЛЕНИЕ _update_ozon_sheet - теперь использует SKU для маппинга строк
# FORCE RESTART 2025-08-24 - ИСПРАВЛЕНИЕ sync_ozon_data - теперь правильно суммирует FBO/FBS остатки по present
# FORCE RESTART 2025-08-24 - ИСПРАВЛЕНИЕ _update_ozon_sheet - теперь ищет строки по offer_id из колонки D
# Управление маркетплейсами (Ozon, Wildberries) и Google Sheets
import os
import json
import base64
import logging
import asyncio
from typing import Dict, List, Union, Optional, Any
# Дополнительный импорт для уверенности
from typing import Any as TypeAny
from datetime import datetime, timedelta
import httpx
import gspread
from google.oauth2.service_account import Credentials
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
        # ⚠️ ВАЖНО: filter.visibility обязателен для /v3/product/list
        self.ozon_endpoints = {
            "product_list": "/v3/product/list",     # ✅ Список товаров (требует visibility)
            "analytics": "/v1/analytics/data",      # ✅ Аналитика
            "stocks": "/v4/product/info/stocks",    # ✅ Остатки конкретных товаров
            "product_info": "/v3/product/list"      # ✅ Информация о товарах (требует visibility)
        }
        
        # Проверка настроек
        self._validate_config()
        
        # Добавляем словарь для сопоставления offer_id с SKU
        self.offer_id_to_sku = {}
    
    def _validate_config(self):
        """Проверяет корректность настроек API"""
        if not self.ozon_api_key or not self.ozon_client_id:
            logger.warning("Ozon API не настроен - функции Ozon будут недоступны")
        
        # Проверка наличия WB_API_KEY и логирование
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
            logger.error(f"Ozon API не настроен: api_key={bool(self.ozon_api_key)}, client_id={bool(self.ozon_client_id)}")
            return {"success": False, "error": "Ozon API не настроен"}
        
        try:
            last_id = ""
            mapping = {}
            
            # Логируем детали запроса
            logger.info(f"Запрос к Ozon API: {self.ozon_base_url}{self.ozon_endpoints['product_list']}")
            logger.info(f"API ключ: {'***' + self.ozon_api_key[-4:] if self.ozon_api_key else 'НЕТ'}")
            logger.info(f"Client ID: {'***' + self.ozon_client_id[-4:] if self.ozon_client_id else 'НЕТ'}")
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                while True:
                    payload = {
                        "filter": {
                            "visibility": "ALL"  # ✅ Обязательное поле согласно документации Ozon
                        },
                        "limit": page_size,
                        "last_id": last_id
                    }
                    
                    logger.info(f"Отправляем payload для /v3/product/list: {payload}")
                    
                    response = await client.post(
                        f"{self.ozon_base_url}{self.ozon_endpoints['product_list']}",
                        headers=self._get_ozon_headers(),
                        json=payload
                    )
                    
                    logger.info(f"Ответ Ozon API: статус {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Получен ответ от /v3/product/list: {data}")
                        
                        # Правильная структура для /v3/product/list
                        products = data.get("result", {}).get("items", [])
                        logger.info(f"Найдено товаров в ответе: {len(products)}")
                        
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
    
    async def get_ozon_products_simple(self, page_size: int = 1000) -> Dict[str, Union[bool, str, List]]:
        """Простое получение списка товаров Ozon без остатков (только для тестирования)"""
        if not self.ozon_api_key or not self.ozon_client_id:
            logger.error(f"Ozon API не настроен: api_key={bool(self.ozon_api_key)}, client_id={bool(self.ozon_client_id)}")
            return {"success": False, "error": "Ozon API не настроен"}
        
        try:
            last_id = ""
            products = []
            
            # Логируем детали запроса
            logger.info(f"Простой запрос к Ozon API: {self.ozon_base_url}{self.ozon_endpoints['product_list']}")
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                while True:
                    payload = {
                        "filter": {
                            "visibility": "ALL"  # ✅ Обязательное поле согласно документации Ozon
                        },
                        "limit": page_size,
                        "last_id": last_id
                    }
                    
                    logger.info(f"Отправляем простой payload: {payload}")
                    
                    response = await client.post(
                        f"{self.ozon_base_url}{self.ozon_endpoints['product_list']}",
                        headers=self._get_ozon_headers(),
                        json=payload
                    )
                    
                    logger.info(f"Простой ответ: статус {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Простой ответ от /v3/product/list: {data}")
                        
                        items = data.get("result", {}).get("items", [])
                        logger.info(f"Найдено товаров в простом ответе: {len(items)}")
                        
                        products.extend(items)
                        
                        last_id = data.get("result", {}).get("last_id", "")
                        if not last_id or len(items) < page_size:
                            break
                    else:
                        logger.error(f"Ошибка простого запроса: {response.status_code} - {response.text}")
                        return {
                            "success": False,
                            "error": f"Ошибка API: {response.status_code}",
                            "details": response.text
                        }
                
                logger.info(f"Получено {len(products)} товаров в простом запросе")
                return {
                    "success": True,
                    "products": products,
                    "total_count": len(products)
                }
                
        except Exception as e:
            logger.error(f"Ошибка при простом получении товаров Ozon: {e}")
            return {
                "success": False,
                "error": f"Ошибка: {str(e)}"
            }
    
    async def get_ozon_stocks(self, product_ids: List[int]) -> Dict[str, Union[bool, str, Dict]]:
        """
        Получает остатки товаров по списку product_id из Ozon Seller API.
        Возвращает словарь с данными или None при ошибке.
        """
        if not self.ozon_api_key or not self.ozon_client_id:
            return {"success": False, "error": "Ozon API не настроен"}

        if not product_ids:
            return {"success": False, "error": "Список product_ids пустой"}

        # Сначала получаем offer_id для каждого product_id
        mapping_result = await self.get_ozon_product_mapping()
        if not mapping_result["success"]:
            return {"success": False, "error": "Не удалось получить mapping товаров"}

        mapping = mapping_result["mapping"]
        # Инвертируем mapping: product_id -> offer_id
        reverse_mapping = {str(v): k for k, v in mapping.items()}
        
        # Получаем offer_id для запрошенных product_id
        offer_ids = []
        for product_id in product_ids:
            offer_id = reverse_mapping.get(str(product_id))
            if offer_id:
                offer_ids.append(offer_id)

        if not offer_ids:
            return {"success": False, "error": "Не найдены offer_id для указанных product_id"}

        # Теперь используем offer_id для получения остатков
        return await self.get_ozon_stocks_by_offer(offer_ids)
    
    async def get_ozon_stocks_by_offer(self, offer_ids: List[str]) -> Dict[str, Union[bool, str, Dict]]:
        """Получает остатки товаров по списку offer_id из Ozon Seller API"""
        if not self.ozon_api_key or not self.ozon_client_id:
            return {"success": False, "error": "Ozon API не настроен"}

        if not offer_ids:
            return {"success": False, "error": "Список offer_ids пустой"}

        url = f"{self.ozon_base_url}{self.ozon_endpoints['stocks']}"
        headers = self._get_ozon_headers()

        payload = {
            "filter": {
                "offer_id": offer_ids,
                "visibility": "ALL"
            },
            "limit": 100,
            "cursor": ""
        }

        logger.info(f"Отправляем payload для /v4/product/info/stocks (by offer_id): {payload}")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Получен ответ от /v4/product/info/stocks (by offer_id): {data}")

                    stocks_data = {}
                    items = data.get("items", [])

                    logger.info(f"Найдено товаров в ответе (by offer_id): {len(items)}")

                    for item in items:
                        offer_id = item.get("offer_id")
                        product_id = item.get("product_id")
                        stocks = item.get("stocks", [])

                        logger.info(f"Обрабатываем offer_id {offer_id} (product_id: {product_id}) с {len(stocks)} складами")

                        # Фильтруем склады с остатками
                        valid_stocks = [
                            stock for stock in stocks
                            if stock.get("present", 0) > 0 or stock.get("reserved", 0) > 0
                        ]
                        
                        if valid_stocks:
                            logger.info(f"Найдено {len(valid_stocks)} складов с остатками для {offer_id}")
                            logger.info(f"Склады с остатками: {valid_stocks}")
                            
                            # Общая сумма остатков
                            total_present = sum(int(wh.get("present", 0)) for wh in valid_stocks)

                            # Детальная информация по складам
                            warehouse_details = []
                            for warehouse in valid_stocks:
                                warehouse_type = warehouse.get("type", "Неизвестный склад")
                                present = int(warehouse.get("present", 0))
                                reserved = int(warehouse.get("reserved", 0))

                                warehouse_details.append({
                                    "name": warehouse_type,
                                    "stock": present,
                                    "reserved": reserved
                                })

                            stocks_data[str(offer_id)] = {
                                "product_id": product_id,
                                "total": total_present,
                                "warehouses": warehouse_details
                            }
                        else:
                            logger.info(f"У товара {offer_id} нет складов с остатками")
                            # Добавляем товар с нулевыми остатками
                            stocks_data[str(offer_id)] = {
                                "product_id": product_id,
                                "total": 0,
                                "warehouses": []
                            }

                        # Сохраняем SKU
                        if offer_id and "sku" in item:
                            self.offer_id_to_sku[offer_id] = item["sku"]

                    logger.info(f"Обработано товаров (by offer_id): {len(stocks_data)}")

                    return {
                        "success": True,
                        "stocks": stocks_data
                    }
                else:
                    logger.error(f"Ошибка получения Ozon stocks (by offer_id): {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Ошибка API: {response.status_code}",
                        "details": response.text
                    }

        except Exception as e:
            logger.error(f"Ошибка получения Ozon stocks (by offer_id): {e}")
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
            # Получаем все склады
            warehouses_result = await self.get_wb_warehouses()
            if not warehouses_result["success"]:
                return warehouses_result

            warehouses = warehouses_result.get("warehouses", [])
            if not warehouses:
                return {"success": False, "error": "Не удалось получить список складов Wildberries"}

            # Используем первый склад для получения остатков (можно добавить логику выбора)
            warehouse_id = warehouses[0].get("id")
            if not warehouse_id:
                return {"success": False, "error": "Не удалось получить ID склада Wildberries"}

            # Получаем все баркоды товаров
            barcodes_result = await self.get_wb_product_barcodes()
            if not barcodes_result["success"]:
                return barcodes_result

            barcodes = barcodes_result.get("barcodes", [])
            if not barcodes:
                return {"success": False, "error": "Не удалось получить список баркодов Wildberries"}

            # Теперь используем новый метод get_wb_stocks с warehouse_id и barcodes
            stocks_result = await self.get_wb_stocks_by_warehouse_and_barcodes(warehouse_id, barcodes)
            
            return stocks_result
                    
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
            
            # Получаем остатки через offer_id (правильный метод)
            offer_ids = list(offer_map.keys())
            stocks_result = await self.get_ozon_stocks_by_offer(offer_ids)
            if not stocks_result["success"]:
                return stocks_result
            
            stocks_by_offer_id = stocks_result.get("stocks", {})
            logger.info(f"[DEBUG] Stocks data received in sync_ozon_data: {stocks_by_offer_id}")

            # Получаем аналитику за последние 30 дней
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            analytics_result = await self.get_ozon_analytics(date_from, date_to)
            
            # Подготавливаем данные для таблицы
            table_data = {}
            for offer_id, product_id in offer_map.items():
                stock_info = stocks_by_offer_id.get(str(offer_id), {})
                logger.info(f"[DEBUG] Processing offer_id={offer_id}. Found stock_info: {stock_info}")

                # Исправляем подсчёт остатков, используя сумму всех складов по типу
                warehouses = stock_info.get("warehouses", [])
                fbo = sum(s.get('stock', 0) for s in warehouses if s.get("name") == "fbo")
                fbs = sum(s.get('stock', 0) for s in warehouses if s.get("name") == "fbs")
                
                total = stock_info.get("total", 0)
                
                logger.info(f"Обновляем строку offer_id={offer_id}: total={total}, fbo={fbo}, fbs={fbs}")
                
                # Здесь можно добавить логику получения продаж и выручки из analytics
                # Пока оставляем пустыми
                sales = 0
                revenue = 0
                
                table_data[offer_id] = {
                    "total_stock": total,
                    "fbo_stock": fbo,
                    "fbs_stock": fbs,
                    "sku": self.offer_id_to_sku.get(offer_id),
                    "sales": sales,
                    "revenue": revenue
                }
            
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
    
    async def _update_ozon_sheet(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Обновляет лист Ozon в Google таблице с помощью пакетного обновления"""
        try:
            # Читаем столбец с offer_id, чтобы найти номера строк
            offer_ids_in_sheet = await self.sheets_api.read_data(
                self.spreadsheet_id,
                f"{self.sheet_name}!{self.ozon_columns['offer_id']}:{self.ozon_columns['offer_id']}"
            )
            
            # Создаем mapping: offer_id -> номер строки
            offer_to_row = {
                offer[0]: i + 1 
                for i, offer in enumerate(offer_ids_in_sheet) 
                if offer
            }
            
            # Подготавливаем данные для пакетного обновления
            updates = []
            for offer_id, info in data.items():
                if offer_id in offer_to_row:
                    row = offer_to_row[offer_id]
                    
                    # Обновляем остатки, продажи, выручку
                    updates.append({
                        "range": f"{self.sheet_name}!{self.ozon_columns['stock']}{row}",
                        "values": [[info.get("total_stock", 0)]]
                    })
                    updates.append({
                        "range": f"{self.sheet_name}!{self.ozon_columns['sales']}{row}",
                        "values": [[info.get("sales", 0)]]
                    })
                    updates.append({
                        "range": f"{self.sheet_name}!{self.ozon_columns['revenue']}{row}",
                        "values": [[info.get("revenue", 0)]]
                    })
            
            # Выполняем пакетное обновление
            if updates:
                spreadsheet = await self.sheets_api.open_spreadsheet(self.spreadsheet_id)
                worksheet = spreadsheet.worksheet(self.sheet_name)
                worksheet.batch_update(updates)
                logger.info(f"Обновлен лист Ozon: {len(updates)} ячеек")
            else:
                logger.warning("Нет данных для обновления Ozon")
                
        except Exception as e:
            logger.error(f"Ошибка обновления листа Ozon: {e}")

    
    async def _update_wb_sheet(self, data: List[Dict[str, Any]]) -> None:
        """Обновляет лист Wildberries в Google таблице"""
        try:
            # Подготавливаем данные для записи
            rows = []
            for item in data:
                rows.append([
                    item["nm_id"],    # Колонка C: Арт. WB
                    item["stock"],    # Колонка E: Остаток WB
                    item["sales"],    # Колонка I: Продажи WB
                    item["revenue"]   # Колонка K: Выручка WB
                ])
            
            # Записываем в таблицу (колонки C, E, I, K)
            await self.sheets_api.write_data(
                self.spreadsheet_id,
                f"{self.sheet_name}!C2:C{len(rows)+1}",
                [[item["nm_id"]] for item in data]
            )
            await self.sheets_api.write_data(
                self.spreadsheet_id,
                f"{self.sheet_name}!E2:E{len(rows)+1}",
                [[item["stock"]] for item in data]
            )
            await self.sheets_api.write_data(
                self.spreadsheet_id,
                f"{self.sheet_name}!I2:I{len(rows)+1}",
                [[item["sales"]] for item in data]
            )
            await self.sheets_api.write_data(
                self.spreadsheet_id,
                f"{self.sheet_name}!K2:K{len(rows)+1}",
                [[item["revenue"]] for item in data]
            )
            
            logger.info(f"Обновлен лист Wildberries: {len(rows)} строк")
            
        except Exception as e:
            logger.error(f"Ошибка обновления листа Wildberries: {e}")
    
    # ==================== УТИЛИТЫ ====================
    
    async def get_ozon_products_detailed(self, product_ids: List[int]) -> Dict[str, Union[bool, str, Dict]]:
        """Получение детальной информации о продуктах Ozon"""
        if not self.ozon_api_key or not self.ozon_client_id:
            return {"success": False, "error": "Ozon API не настроен"}
        
        if not product_ids:
            return {"success": False, "error": "Список product_id пуст"}
        
        try:
            products = {}
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                # Получаем детальную информацию о каждом продукте
                for product_id in product_ids:
                    payload = {
                        "filter": {
                            "product_id": [product_id],
                            "visibility": "ALL"  # ✅ Обязательное поле согласно документации Ozon
                        },
                        "limit": 1000
                    }
                    
                    response = await client.post(
                        f"{self.ozon_base_url}{self.ozon_endpoints['product_list']}",
                        headers=self._get_ozon_headers(),
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("result", {}).get("items"):
                            item = data["result"]["items"][0]  # Берем первый (и единственный) продукт
                            products[str(product_id)] = {
                                "archived": item.get("archived", False),
                                "has_fbo_stocks": item.get("has_fbo_stocks", False),
                                "has_fbs_stocks": item.get("has_fbs_stocks", False),
                                "is_discounted": item.get("is_discounted", False),
                                "offer_id": item.get("offer_id", ""),
                                "product_id": item.get("product_id", 0),
                                "name": item.get("name", "Без названия"),  # Добавляем название продукта
                                "quants": item.get("quants", [])
                            }
                        else:
                            products[str(product_id)] = {}
                    else:
                        logger.warning(f"Ошибка API для product_id {product_id}: {response.status_code}")
                        products[str(product_id)] = {}
                
                return {
                    "success": True,
                    "products": products,
                    "total": len(products)
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения детальной информации о продуктах: {e}")
            return {"success": False, "error": str(e)}
    
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

async def get_wb_warehouses(self) -> Dict[str, Union[bool, str, List[Dict]]]:
    """Получение списка складов Wildberries"""
    if not self.wb_api_key:
        return {"success": False, "error": "Wildberries API не настроен"}
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.wb_base_url}/api/v3/warehouses",
                headers={"Authorization": f"Bearer {self.wb_api_key}"}
            )
            if response.status_code == 200:
                return {"success": True, "warehouses": response.json()}
            else:
                return {"success": False, "error": f"Ошибка при получении складов: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def get_wb_product_barcodes(self) -> Dict[str, Union[bool, str, List[str]]]:
    """Получение списка баркодов товаров Wildberries"""
    if not self.wb_api_key:
        return {"success": False, "error": "Wildberries API не настроен"}
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.wb_base_url}/content/v2/get/cards/list",
                headers={"Authorization": f"Bearer {self.wb_api_key}", "Content-Type": "application/json"},
                json={"settings": {"cursor": {"limit": 1000}}}
            )
            if response.status_code == 200:
                products = response.json().get("data", [])
                barcodes = [product["barcode"] for product in products]
                return {"success": True, "barcodes": barcodes}
            else:
                return {"success": False, "error": f"Ошибка при получении баркодов: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def get_wb_stocks_by_warehouse_and_barcodes(self, warehouse_id: int, barcodes: List[str]) -> Dict[str, Union[bool, str, Dict]]:
    """Получение остатков товаров на складе Wildberries по ID склада и баркодам"""
    if not self.wb_api_key:
        return {"success": False, "error": "Wildberries API не настроен"}
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.wb_base_url}/api/v3/stocks/{warehouse_id}",
                headers={"Authorization": f"Bearer {self.wb_api_key}", "Content-Type": "application/json"},
                json={"skus": barcodes}
            )
            if response.status_code == 200:
                return {"success": True, "stocks": response.json()}
            else:
                return {"success": False, "error": f"Ошибка при получении остатков: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Временное логирование для проверки загрузки WB_API_KEY
logger.info(f"WB_API_KEY: {os.getenv('WB_API_KEY')}")
