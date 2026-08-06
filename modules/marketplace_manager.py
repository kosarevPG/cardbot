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

# Уровень логирования настраивается централизованно в main.py (env LOG_LEVEL).
# Модуль не трогает root-логгер: раньше он принудительно включал DEBUG всему приложению.

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
    
    def __init__(self, google_creds=None):
        # Ozon API настройки
        self.ozon_api_key = os.getenv("OZON_API_KEY", "")
        self.ozon_client_id = os.getenv("OZON_CLIENT_ID", "")
        self.ozon_base_url = "https://api-seller.ozon.ru"
        
        # Wildberries API настройки
        self.wb_api_key = os.getenv("WB_API_KEY", "")

        # С января 2025 WB заменил suppliers-api.wildberries.ru на новые домены:
        #   marketplace-api.wildberries.ru  – заказы/склады/остатки
        #   content-api.wildberries.ru      – карточки/контент
        # Базы можно переопределить через переменные окружения
        self.wb_marketplace_base = os.getenv(
            "WB_MARKETPLACE_BASE", "https://marketplace-api.wildberries.ru")
        self.wb_content_base = os.getenv(
            "WB_CONTENT_BASE", "https://content-api.wildberries.ru")
        
        # Google Sheets настройки
        self.sheets_api = GoogleSheetsAPI(service_account_info=google_creds)
        self.spreadsheet_id = "1RoWWv9BgiwlSu9H-KJNsFItQxlUVhG1WMbyB0eFxzYM"
        self.sheet_name = "marketplaces"
        
        # Структура таблицы для Ozon (соответствует "Форбс.Учет 2.0")
        self.ozon_columns = {
            "offer_id": "D",      # Арт. Ozon (колонка D)
            "stock": "I",         # Остаток Ozon, всего (колонка I)
            "stock_fbo": "J",     # Остаток Ozon, FBO (колонка J)
            "stock_fbs": "K",     # Остаток Ozon, FBS (колонка K)
            "sales": "M",         # Продажи Ozon (колонка M)
            "revenue": "O",       # Выручка Ozon (колонка O)
            "price": "Q"          # Цена Ozon (колонка Q)
        }
        
        # Структура таблицы для Wildberries (соответствует "Форбс.Учет 2.0")
        self.wb_columns = {
            "nm_id": "C",        # Баркод WB (колонка C)
            "stock": "F",        # Остаток WB (всего) (колонка F)
            "sales": "L",        # Продажи WB (колонка L)
            "revenue": "N",      # Выручка WB (колонка N)
            "price": "P"         # Цена WB (колонка P)
        }
        
        # Ozon API эндпоинты
        # ⚠️ ВАЖНО: filter.visibility обязателен для /v3/product/list
        self.ozon_endpoints = {
            "product_list": "/v3/product/list",     # ✅ Список товаров (требует visibility)
            "analytics": "/v1/analytics/data",      # ✅ Аналитика
            "stocks": "/v4/product/info/stocks",    # ✅ Остатки конкретных товаров
            "product_info": "/v3/product/list",     # ✅ Информация о товарах (требует visibility)
            "product_info_list": "/v3/product/info/list",  # ✅ Полная информация о товаре (включая name, price, stocks)
            "prices": "/v1/product/info/attributes" # ✅ Информация о товарах (включая цены)
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

    async def _ozon_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Выполняет запрос к Ozon API"""
        import httpx
        
        url = f"{self.ozon_base_url}{endpoint}"
        headers = self._get_ozon_headers()
        
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=data)
                else:
                    response = await client.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Ozon API error {response.status_code}: {response.text}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Ошибка запроса к Ozon API: {e}")
            return {}
    
    async def get_ozon_product_mapping(self, page_size: int = 1000, max_pages: int = 100) -> Dict[str, Union[bool, str, Dict]]:
        """Получение соответствия offer_id → product_id для Ozon
        
        Args:
            page_size: Размер страницы (по умолчанию 1000)
            max_pages: Максимальное количество страниц для защиты от зависания (по умолчанию 100)
        """
        if not self.ozon_api_key or not self.ozon_client_id:
            logger.error(f"Ozon API не настроен: api_key={bool(self.ozon_api_key)}, client_id={bool(self.ozon_client_id)}")
            return {"success": False, "error": "Ozon API не настроен"}
        
        try:
            last_id = ""
            mapping = {}
            page_count = 0
            
            # Логируем детали запроса
            logger.info(f"Запрос к Ozon API: {self.ozon_base_url}{self.ozon_endpoints['product_list']}")
            logger.info(f"API ключ: {'***' + self.ozon_api_key[-4:] if self.ozon_api_key else 'НЕТ'}")
            logger.info(f"Client ID: {'***' + self.ozon_client_id[-4:] if self.ozon_client_id else 'НЕТ'}")
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                while page_count < max_pages:
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
                        page_count += 1
                        
                        if not last_id or len(products) < page_size:
                            break
                
                    if page_count >= max_pages:
                        logger.warning(f"Достигнут лимит страниц ({max_pages}), возможно есть еще товары")
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
    
    async def get_ozon_products_simple(self, page_size: int = 1000, max_pages: int = 100) -> Dict[str, Union[bool, str, List]]:
        """Простое получение списка товаров Ozon без остатков (только для тестирования)
        
        Args:
            page_size: Размер страницы (по умолчанию 1000)
            max_pages: Максимальное количество страниц для защиты от зависания (по умолчанию 100)
        """
        if not self.ozon_api_key or not self.ozon_client_id:
            logger.error(f"Ozon API не настроен: api_key={bool(self.ozon_api_key)}, client_id={bool(self.ozon_client_id)}")
            return {"success": False, "error": "Ozon API не настроен"}
        
        try:
            last_id = ""
            products = []
            page_count = 0
            
            # Логируем детали запроса
            logger.info(f"Простой запрос к Ozon API: {self.ozon_base_url}{self.ozon_endpoints['product_list']}")
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                while page_count < max_pages:
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
                        page_count += 1
                        
                        if not last_id or len(items) < page_size:
                            break
                
                    if page_count >= max_pages:
                        logger.warning(f"Достигнут лимит страниц ({max_pages}) для простого запроса")
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
    def _get_wb_headers(self, bearer: bool = False) -> Dict[str, str]:
        """Формирует заголовки для Wildberries API.

        Для большинства supplier-эндпоинтов передаётся токен без префикса.
        Для content-api требуется префикс «Bearer ». Задаём его через
        параметр bearer=True.
        """
        token = f"Bearer {self.wb_api_key}" if bearer else self.wb_api_key
        return {
            "Authorization": token,
            "Content-Type": "application/json"
        }
    
    async def _wb_request(self, path: str, *, suppliers: bool = True, method: str = "GET", bearer: bool = False, **kwargs):
        """Делает запрос к WB.

        path – строка вроде "/api/v3/warehouses"
        suppliers=True  → marketplace-api.wildberries.ru
        bearer=True     → добавляем префикс "Bearer " в Authorization
        
        Note: Fallback на IP удален, так как переменные wb_suppliers_ip и wb_content_ip не инициализированы.
        """
        base = self.wb_marketplace_base if suppliers else self.wb_content_base
        url = f"{base}{path}"
        headers = kwargs.pop("headers", self._get_wb_headers(bearer=bearer))
        
        try:
            async with httpx.AsyncClient(timeout=20.0, verify=True) as client:
                resp = await client.request(method, url, headers=headers, **kwargs)
                return resp
        except httpx.ConnectError as e:
            logger.error(f"WB connection error for {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"WB request error for {url}: {e}")
            raise

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
                    f"{self.wb_marketplace_base}/api/v1/supplier/reportDetailByPeriod",
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
            # Кеш offer_id → sku наполняется ниже в get_ozon_stocks_by_offer.
            # Сбрасываем его, чтобы общий экземпляр вёл себя так же, как свежесозданный,
            # и в таблицу не попал sku, оставшийся от предыдущей синхронизации.
            self.offer_id_to_sku = {}

            # Получаем mapping offer_id → product_id
            mapping_result = await self.get_ozon_product_mapping()
            if not mapping_result["success"]:
                return mapping_result
            
            offer_map = mapping_result["mapping"]
            
            # Получаем остатки через offer_id
            offer_ids = list(offer_map.keys())
            stocks_result = await self.get_ozon_stocks_by_offer(offer_ids)
            if not stocks_result["success"]:
                return stocks_result
            
            stocks_by_offer_id = stocks_result["stocks"]
            
            logger.info(f"[DIAGNOSTIC] Stocks data before processing loop: {stocks_by_offer_id}")

            # Получаем аналитику за последние 30 дней
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            analytics_result = await self.get_ozon_analytics(date_from, date_to)
            
            # Подготавливаем данные для таблицы
            table_data = {}
            for offer_id, product_id in offer_map.items():
                stock_info = stocks_by_offer_id.get(offer_id, {})
                
                logger.info(f"[DEBUG] Processing offer_id={offer_id}. Found stock_info: {stock_info}")

                total_stock = stock_info.get("total", 0)
                fbo_stock = sum(s['stock'] for s in stock_info.get("warehouses", []) if s.get("name") == "fbo")
                fbs_stock = sum(s['stock'] for s in stock_info.get("warehouses", []) if s.get("name") == "fbs")
                
                logger.info(f"Обновляем строку offer_id={offer_id}: total={total_stock}, fbo={fbo_stock}, fbs={fbs_stock}")
                
                sales = 0
                revenue = 0
                
                table_data[offer_id] = {
                    "total_stock": total_stock,
                    "fbo_stock": fbo_stock,
                    "fbs_stock": fbs_stock,
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

    # ===== Новый метод: синхронизация остатков WB в колонке F-H =====
    async def sync_wb_stock_to_sheet(self) -> Dict[str, Union[bool, str, int]]:
        """Записывает остаток WB (total/FBO/FBS) в столбцы F,G,H таблицы."""
        if not self.wb_api_key:
            return {"success": False, "error": "WB_API_KEY not set"}

        try:
            # 1. Склады
            wh_res = await self.get_wb_warehouses()
            if not wh_res.get("success"):
                return {"success": False, "error": wh_res.get("error", "warehouses fail")}
            warehouses = wh_res.get("warehouses", [])
            if not warehouses:
                return {"success": False, "error": "warehouses empty"}

            # 2. Все barcodes
            bc_res = await self.get_wb_product_barcodes()
            if not bc_res.get("success"):
                return {"success": False, "error": bc_res.get("error", "barcodes fail")}
            barcodes = bc_res.get("barcodes", [])
            if not barcodes:
                return {"success": False, "error": "no barcodes"}

            # 3. Аггрегируем остатки по всем складам
            from collections import defaultdict
            agg: Dict[str, Dict[str,int]] = defaultdict(lambda: {"total":0,"fbo":0,"fbs":0})
            for wh in warehouses:
                wid = wh["id"]
                stocks_res = await self.get_wb_stocks(wid, barcodes)
                if not stocks_res.get("success"):
                    continue
                for item in stocks_res["stocks"].get("stocks", []):
                    sku = str(item.get("sku"))
                    qty = int(item.get("amount",0))
                    delivery_type = wh.get("deliveryType")
                    wh_type = "fbo" if delivery_type == 1 else "fbs"
                    agg[sku][wh_type]+=qty
                    agg[sku]["total"]+=qty

            if not agg:
                return {"success": False, "error": "stocks empty"}

            # 4. Читаем колонку C (nm_id)
            sheet_vals = await self.sheets_api.read_data(self.spreadsheet_id, f"{self.sheet_name}!C:C")
            sku_to_row={row[0]:idx+1 for idx,row in enumerate(sheet_vals) if row}

            updates=[]
            for sku,data in agg.items():
                row=sku_to_row.get(sku)
                if not row:
                    continue
                updates.append({"range":f"F{row}","values":[[data["total"]]]})
                updates.append({"range":f"G{row}","values":[[data["fbo"]]]})
                updates.append({"range":f"H{row}","values":[[data["fbs"]]]})

            if updates:
                ws= (await self.sheets_api.open_spreadsheet(self.spreadsheet_id)).worksheet(self.sheet_name)
                ws.batch_update(updates)
            return {"success": True, "updated": len(updates)//3}
        except Exception as e:
            logger.exception("sync_wb_stock_to_sheet error")
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
            # Читаем весь лист, чтобы правильно сопоставить товары
            sheet_data = await self.sheets_api.read_data(self.spreadsheet_id, self.sheet_name)
            if not sheet_data or len(sheet_data) < 2:
                logger.warning("⚠️ Нет данных в таблице для обновления Ozon")
                return
            
            # Создаем mapping: offer_id -> номер строки (пропускаем заголовок)
            offer_to_row = {}
            for i, row in enumerate(sheet_data[1:], start=2):  # Пропускаем заголовок, начинаем с строки 2
                if len(row) > 3 and row[3]:  # Колонка D (Арт. Ozon)
                    offer_id = row[3].strip()
                    offer_to_row[offer_id] = i
            
            logger.info(f"📋 Найдено {len(offer_to_row)} товаров в таблице: {list(offer_to_row.keys())}")
            logger.info(f"📦 Данных для обновления: {list(data.keys())}")
            
            # Подготавливаем данные для пакетного обновления
            updates = []
            matched_count = 0
            
            for offer_id, info in data.items():
                if offer_id in offer_to_row:
                    row = offer_to_row[offer_id]
                    matched_count += 1
                    
                    logger.info(f"📦 Обновляю товар {offer_id} в строке {row}: остаток={info.get('total_stock', 0)}")
                    
                    # Обновляем остатки, продажи, выручку
                    updates.append({
                        "range": f"{self.ozon_columns['stock']}{row}",
                        "values": [[info.get("total_stock", 0)]]
                    })
                    updates.append({
                        "range": f"{self.ozon_columns['stock_fbo']}{row}",
                        "values": [[info.get("fbo_stock", 0)]]
                    })
                    updates.append({
                        "range": f"{self.ozon_columns['stock_fbs']}{row}",
                        "values": [[info.get("fbs_stock", 0)]]
                    })
                    
                    # Also update sales and revenue if they are available
                    if "sales" in info:
                        updates.append({
                            "range": f"{self.ozon_columns['sales']}{row}",
                            "values": [[info.get("sales", 0)]]
                        })
                    if "revenue" in info:
                        updates.append({
                            "range": f"{self.ozon_columns['revenue']}{row}",
                            "values": [[info.get("revenue", 0)]]
                        })
                else:
                    logger.warning(f"⚠️ Товар {offer_id} не найден в таблице")
            
            logger.info(f"✅ Сопоставлено {matched_count} из {len(data)} товаров")

            # Выполняем пакетное обновление
            if updates:
                spreadsheet = await self.sheets_api.open_spreadsheet(self.spreadsheet_id)
                if spreadsheet:
                    worksheet = spreadsheet.worksheet(self.sheet_name)
                    worksheet.batch_update(updates)
                    logger.info(f"Обновлен лист Ozon: {len(updates)} ячеек")
                else:
                    logger.error("Не удалось открыть таблицу для обновления")
            else:
                logger.warning("Нет данных для обновления Ozon")
                
        except Exception as e:
            logger.error(f"Ошибка обновления листа Ozon: {e}", exc_info=True)
    
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
            await self.sheets_api.write_data_range(
                self.spreadsheet_id,
                f"{self.sheet_name}!{self.wb_columns['nm_id']}2:{self.wb_columns['nm_id']}{len(rows)+1}",
                [[item["nm_id"]] for item in data]
            )
            await self.sheets_api.write_data_range(
                self.spreadsheet_id,
                f"{self.sheet_name}!{self.wb_columns['stock']}2:{self.wb_columns['stock']}{len(rows)+1}",
                [[item["stock"]] for item in data]
            )
            await self.sheets_api.write_data_range(
                self.spreadsheet_id,
                f"{self.sheet_name}!{self.wb_columns['sales']}2:{self.wb_columns['sales']}{len(rows)+1}",
                [[item["sales"]] for item in data]
            )
            await self.sheets_api.write_data_range(
                self.spreadsheet_id,
                f"{self.sheet_name}!{self.wb_columns['revenue']}2:{self.wb_columns['revenue']}{len(rows)+1}",
                [[item["revenue"]] for item in data]
            )
            
            logger.info(f"Обновлен лист Wildberries: {len(rows)} строк")
            
        except Exception as e:
            logger.error(f"Ошибка обновления листа Wildberries: {e}")
    
    async def get_ozon_prices(self, offer_ids: List[str] = None) -> Dict[str, Dict]:
        """
        Получает цены товаров с Ozon (заглушка - цены не доступны через API).
        
        Args:
            offer_ids: Список offer_id для получения цен (если None - все товары)
            
        Returns:
            Dict[str, Dict]: Словарь {offer_id: {price: float, currency: str}}
        """
        logger.info("💰 Получение цен товаров Ozon...")
        
        try:
            # Если не указаны конкретные товары, получаем все
            if not offer_ids:
                result = await self.get_ozon_products_simple()
                if result.get("success") and "products" in result:
                    products = result["products"]
                    offer_ids = [p["offer_id"] for p in products if p.get("offer_id")]
                else:
                    logger.warning("⚠️ Не удалось получить список товаров Ozon")
                    return {}
            
            if not offer_ids:
                logger.warning("⚠️ Нет товаров для получения цен")
                return {}
            
            # Временная заглушка - цены Ozon не доступны через текущий API
            # Возвращаем пустые цены для всех товаров
            prices_data = {}
            for offer_id in offer_ids:
                prices_data[offer_id] = {
                    "price": 0,
                    "currency": "RUB",
                    "old_price": None,
                    "premium_price": None,
                    "auto_action_enabled": False,
                    "note": "Цены Ozon недоступны через API"
                }
            
            logger.info(f"⚠️ Возвращены заглушки цен для {len(prices_data)} товаров Ozon")
            return prices_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения цен Ozon: {e}", exc_info=True)
            return {}

    async def get_wb_prices(self, nm_ids: List[int] = None) -> Dict[int, Dict]:
        """
        Получает цены товаров с Wildberries.
        
        Args:
            nm_ids: Список nm_id для получения цен (если None - все товары)
            
        Returns:
            Dict[int, Dict]: Словарь {nm_id: {price: float, currency: str}}
        """
        logger.info("💰 Получение цен товаров Wildberries...")
        
        try:
            # Если не указаны конкретные товары, получаем все
            if not nm_ids:
                # Получаем список товаров из Google Sheets
                result = await self.sheets_api.get_sheet_data(self.spreadsheet_id, self.sheet_name)
                if result.get("success"):
                    sheet_data = result["data"]
                else:
                    logger.warning("⚠️ Не удалось получить данные из таблицы")
                    return {}
                if not sheet_data or len(sheet_data) < 2:
                    logger.warning("⚠️ Нет данных в таблице для получения цен")
                    return {}
                
                # Извлекаем nm_id из колонки C (Баркод WB)
                nm_ids = []
                for row in sheet_data[1:]:  # Пропускаем заголовок
                    if len(row) > 2 and row[2]:  # Колонка C
                        try:
                            nm_id = int(row[2])
                            nm_ids.append(nm_id)
                        except (ValueError, IndexError):
                            continue
            
            if not nm_ids:
                logger.warning("⚠️ Нет товаров для получения цен")
                return {}
            
            # Получаем цены через API WB
            prices_data = {}
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                for nm_id in nm_ids:
                    try:
                        # API для получения информации о товаре (включая цену)
                        response = await client.get(
                            f"{self.wb_content_base}/content/v1/cards/filter",
                            headers={
                                "Authorization": self.wb_api_key,
                                "Content-Type": "application/json"
                            },
                            params={
                                "nm": nm_id
                            }
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data and "data" in data and data["data"]:
                                product = data["data"][0]
                                prices_data[nm_id] = {
                                    "price": product.get("price", 0),
                                    "currency": "RUB",
                                    "old_price": product.get("old_price"),
                                    "sale_price": product.get("sale_price")
                                }
                        
                        # Небольшая пауза между запросами
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        logger.error(f"❌ Ошибка получения цены для nm_id {nm_id}: {e}")
                        continue
            
            logger.info(f"✅ Получены цены для {len(prices_data)} товаров WB")
            return prices_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения цен WB: {e}", exc_info=True)
            return {}

    async def update_prices_in_sheets(self) -> Dict:
        """
        Обновляет цены товаров в Google Sheets.
        
        Returns:
            Dict: Результат обновления цен
        """
        logger.info("💰 Обновление цен в Google Sheets...")
        
        try:
            # Получаем цены Ozon
            ozon_prices = await self.get_ozon_prices()
            
            # Получаем цены WB
            wb_prices = await self.get_wb_prices()
            
            # Обновляем цены в таблице
            await self._update_prices_sheet(ozon_prices, wb_prices)
            
            logger.info("✅ Цены обновлены успешно")
            return {
                "success": True,
                "ozon_prices_count": len(ozon_prices),
                "wb_prices_count": len(wb_prices),
                # Отдаём данные вызывающему коду (например, /get_prices), чтобы можно было показать пользователю список цен.
                # Это не используется на фронте таблицы, только для вывода в Telegram.
                "ozon_prices": ozon_prices,
                "wb_prices": wb_prices,
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления цен: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _update_prices_sheet(self, ozon_prices: Dict[str, Dict], wb_prices: Dict[int, Dict]):
        """
        Обновляет цены в Google Sheets.
        
        Args:
            ozon_prices: Цены товаров Ozon {offer_id: {price: float}}
            wb_prices: Цены товаров WB {nm_id: {price: float}}
        """
        try:
            # Читаем данные из таблицы
            result = await self.sheets_api.get_sheet_data(self.spreadsheet_id, self.sheet_name)
            if result.get("success"):
                sheet_data = result["data"]
            else:
                logger.warning("⚠️ Не удалось получить данные из таблицы")
                return
            if not sheet_data or len(sheet_data) < 2:
                logger.warning("⚠️ Нет данных в таблице")
                return
            
            # Обновляем цены Ozon (колонка Q)
            ozon_price_updates = []
            wb_price_updates = []
            
            for i, row in enumerate(sheet_data[1:], start=2):  # Пропускаем заголовок, начинаем с строки 2
                if len(row) > 3:  # Проверяем наличие колонки D (Арт. Ozon)
                    offer_id = row[3].strip() if len(row) > 3 and row[3] else None
                    nm_id = row[2].strip() if len(row) > 2 and row[2] else None
                    
                    # Цена Ozon
                    if offer_id and offer_id in ozon_prices:
                        price = ozon_prices[offer_id]["price"]
                        ozon_price_updates.append([price])
                        logger.debug(f"💰 Цена Ozon для {offer_id}: {price}")
                    else:
                        ozon_price_updates.append([""])
                    
                    # Цена WB
                    if nm_id:
                        try:
                            nm_id_int = int(nm_id)
                            if nm_id_int in wb_prices:
                                price = wb_prices[nm_id_int]["price"]
                                wb_price_updates.append([price])
                                logger.debug(f"💰 Цена WB для {nm_id}: {price}")
                            else:
                                wb_price_updates.append([""])
                        except (ValueError, TypeError):
                            wb_price_updates.append([""])
                    else:
                        wb_price_updates.append([""])
            
            # Записываем цены Ozon в колонку Q
            if ozon_price_updates:
                await self.sheets_api.write_data_range(
                    self.spreadsheet_id,
                    f"{self.sheet_name}!{self.ozon_columns['price']}2:{self.ozon_columns['price']}{len(ozon_price_updates)+1}",
                    ozon_price_updates
                )
            
            # Записываем цены WB в колонку P
            if wb_price_updates:
                await self.sheets_api.write_data_range(
                    self.spreadsheet_id,
                    f"{self.sheet_name}!{self.wb_columns['price']}2:{self.wb_columns['price']}{len(wb_price_updates)+1}",
                    wb_price_updates
                )
            
            logger.info(f"✅ Обновлены цены: Ozon - {len(ozon_price_updates)}, WB - {len(wb_price_updates)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления цен в таблице: {e}", exc_info=True)

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
                    # Сначала пробуем получить через /v3/product/list
                    payload = {
                        "filter": {
                            "product_id": [product_id],
                            "visibility": "ALL"
                        },
                        "limit": 1000
                    }
                    
                    response = await client.post(
                        f"{self.ozon_base_url}{self.ozon_endpoints['product_list']}",
                        headers=self._get_ozon_headers(),
                        json=payload
                    )
                    
                    product_name = None
                    product_data = {}
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("result", {}).get("items"):
                            item = data["result"]["items"][0]
                            
                            # Логируем все доступные ключи для отладки
                            logger.debug(f"Доступные ключи в ответе /v3/product/list для product_id {product_id}: {list(item.keys())}")
                            
                            # Пробуем получить название из разных полей (title имеет приоритет)
                            product_name = item.get("title") or item.get("name")
                            
                            if product_name:
                                logger.info(f"Название получено из /v3/product/list для product_id {product_id}: {product_name}")
                            
                            product_data = {
                                "archived": item.get("archived", False),
                                "has_fbo_stocks": item.get("has_fbo_stocks", False),
                                "has_fbs_stocks": item.get("has_fbs_stocks", False),
                                "is_discounted": item.get("is_discounted", False),
                                "offer_id": item.get("offer_id", ""),
                                "product_id": item.get("product_id", 0),
                                "quants": item.get("quants", [])
                            }
                        else:
                            logger.warning(f"Нет items в ответе /v3/product/list для product_id {product_id}")
                    else:
                        logger.warning(f"Ошибка /v3/product/list для product_id {product_id}: {response.status_code} - {response.text}")
                    
                    # Всегда пробуем получить name через /v3/product/info/list (полная информация о товаре)
                    try:
                        info_response = await client.post(
                            f"{self.ozon_base_url}{self.ozon_endpoints['product_info_list']}",
                            headers=self._get_ozon_headers(),
                            json={"product_id": [product_id]}
                        )
                        
                        if info_response.status_code == 200:
                            info_data = info_response.json()
                            logger.debug(f"Ответ /v3/product/info/list для product_id {product_id}: {info_data}")
                            
                            if info_data.get("result"):
                                result_items = info_data["result"]
                                if isinstance(result_items, list) and len(result_items) > 0:
                                    result_item = result_items[0]
                                    
                                    # Логируем доступные ключи
                                    if isinstance(result_item, dict):
                                        logger.debug(f"Доступные ключи в /v3/product/info/list: {list(result_item.keys())}")
                                    
                                    # Получаем name из /v3/product/info/list (имеет приоритет)
                                    name_from_info = result_item.get("name")
                                    
                                    # Используем name из /v3/product/info/list, если он есть
                                    if name_from_info:
                                        product_name = name_from_info
                                        logger.info(f"Название получено через /v3/product/info/list для product_id {product_id}: {product_name}")
                                else:
                                    logger.warning(f"Пустой результат в /v3/product/info/list для product_id {product_id}")
                            else:
                                logger.warning(f"Нет result в ответе /v3/product/info/list для product_id {product_id}")
                        else:
                            logger.warning(f"Ошибка /v3/product/info/list для product_id {product_id}: {info_response.status_code} - {info_response.text}")
                    except Exception as e:
                        logger.warning(f"Не удалось получить название через /v3/product/info/list для product_id {product_id}: {e}", exc_info=True)
                    
                    # Если название все еще не получено, используем offer_id
                    if not product_name:
                        product_name = product_data.get("offer_id", "Без названия")
                        logger.warning(f"Название не найдено для product_id {product_id}, используется offer_id: {product_name}")
                    
                    product_data["name"] = product_name
                    products[str(product_id)] = product_data
                
                return {
                    "success": True,
                    "products": products,
                    "total": len(products)
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения детальной информации о продуктах: {e}")
            return {"success": False, "error": str(e)}
    
    async def fill_ozon_product_by_id(self, product_identifier: str) -> Dict[str, Any]:
        """
        Автозаполнение данных товара Ozon по offer_id или product_id.
        Заполняет название, остатки, цены в таблице.
        
        Args:
            product_identifier: offer_id (например, "KU-3-PVK") или product_id (например, "2343897353")
        
        Returns:
            Dict с результатами:
            - success: bool
            - offer_id: str
            - product_id: int
            - name: str
            - row: int - номер строки в таблице
            - error: str (если success=False)
        """
        if not self.ozon_api_key or not self.ozon_client_id:
            return {"success": False, "error": "Ozon API не настроен"}
        
        try:
            # Определяем, это offer_id или product_id
            # Если это число - вероятно product_id, иначе - offer_id
            offer_id = None
            product_id = None
            
            try:
                # Пробуем как product_id (число)
                product_id = int(product_identifier)
                # Если успешно - это product_id, нужно найти offer_id
                mapping_result = await self.get_ozon_product_mapping()
                if mapping_result.get("success"):
                    mapping = mapping_result["mapping"]
                    # Ищем offer_id по product_id
                    reverse_mapping = {v: k for k, v in mapping.items()}
                    offer_id = reverse_mapping.get(product_id)
                    if not offer_id:
                        return {"success": False, "error": f"Товар с product_id {product_id} не найден в Ozon"}
            except ValueError:
                # Это не число, значит offer_id
                offer_id = product_identifier
                # Находим product_id по offer_id
                mapping_result = await self.get_ozon_product_mapping()
                if mapping_result.get("success"):
                    mapping = mapping_result["mapping"]
                    product_id = mapping.get(offer_id)
                    if not product_id:
                        return {"success": False, "error": f"Товар с offer_id {offer_id} не найден в Ozon"}
            
            if not offer_id or not product_id:
                return {"success": False, "error": "Не удалось определить offer_id и product_id"}
            
            logger.info(f"🔍 Заполняю данные для товара: offer_id={offer_id}, product_id={product_id}")
            
            # 1. Получаем название товара
            detailed_result = await self.get_ozon_products_detailed([product_id])
            if not detailed_result.get("success"):
                return {"success": False, "error": f"Не удалось получить данные о товаре: {detailed_result.get('error')}"}
            
            product_info = detailed_result["products"].get(str(product_id), {})
            product_name = product_info.get("name", "Без названия")
            
            # 2. Получаем остатки
            stocks_result = await self.get_ozon_stocks_by_offer([offer_id])
            if not stocks_result.get("success"):
                logger.warning(f"Не удалось получить остатки: {stocks_result.get('error')}")
                stocks_data = {"total": 0, "fbo": 0, "fbs": 0}
            else:
                stocks = stocks_result.get("stocks", {}).get(offer_id, {})
                total_stock = stocks.get("total", 0)
                warehouses = stocks.get("warehouses", [])
                fbo_stock = sum(w.get("stock", 0) for w in warehouses if w.get("name", "").lower() == "fbo")
                fbs_stock = sum(w.get("stock", 0) for w in warehouses if w.get("name", "").lower() == "fbs")
                stocks_data = {
                    "total": total_stock,
                    "fbo": fbo_stock,
                    "fbs": fbs_stock
                }
            
            # 3. Получаем цены из quants
            price = None
            quants = product_info.get("quants", [])
            for quant in quants:
                price_str = quant.get("price") or quant.get("marketing_price", {}).get("price") or quant.get("seller_price")
                if price_str:
                    try:
                        price = float(str(price_str).replace(",", "."))
                        break
                    except (ValueError, TypeError):
                        continue
            
            # 4. Находим или создаем строку в таблице
            sheet_data = await self.sheets_api.get_sheet_data(self.spreadsheet_id, self.sheet_name)
            if not sheet_data.get("success"):
                return {"success": False, "error": "Не удалось прочитать таблицу"}
            
            data_rows = sheet_data.get("data", [])
            if not data_rows or len(data_rows) < 2:
                return {"success": False, "error": "Таблица пуста или содержит только заголовок"}
            
            # Ищем строку по offer_id (колонка D, индекс 3)
            row_number = None
            for i, row in enumerate(data_rows[1:], start=2):  # Пропускаем заголовок
                if len(row) > 3 and str(row[3]).strip() == offer_id:
                    row_number = i
                    break
            
            # Если строка не найдена, создаем новую
            if not row_number:
                # Добавляем новую строку в конец
                new_row = [
                    str(product_id),  # Колонка A: SKU
                    product_name,     # Колонка B: Название
                    "",               # Колонка C: Баркод WB
                    offer_id,         # Колонка D: Арт. Ozon
                    "",               # Колонка E: Остаток Всего
                    "",               # Колонка F: Остаток WB
                    "",               # Колонка G: Остаток WB, FBO
                    "",               # Колонка H: Остаток WB, FBS
                    stocks_data["total"],  # Колонка I: Остаток Ozon, всего
                    stocks_data["fbo"],    # Колонка J: Остаток Ozon, FBO
                    stocks_data["fbs"],   # Колонка K: Остаток Ozon, FBS
                    "",               # Колонка L: Продажи WB
                    "",               # Колонка M: Продажи Ozon
                    "",               # Колонка N: Выручка WB
                    "",               # Колонка O: Выручка Ozon
                    "",               # Колонка P: Цена WB
                    price if price else "",  # Колонка Q: Цена Ozon
                ]
                
                append_result = await self.sheets_api.append_data(self.spreadsheet_id, self.sheet_name, [new_row])
                if not append_result.get("success"):
                    return {"success": False, "error": f"Не удалось добавить новую строку: {append_result.get('error')}"}
                
                # Получаем номер новой строки (последняя строка)
                updated_sheet = await self.sheets_api.get_sheet_data(self.spreadsheet_id, self.sheet_name)
                if updated_sheet.get("success"):
                    row_number = len(updated_sheet.get("data", []))
                else:
                    row_number = len(data_rows) + 1
            else:
                # Обновляем существующую строку
                updates = []
                
                # Обновляем название (колонка B)
                if len(data_rows[row_number - 1]) <= 1 or not data_rows[row_number - 1][1]:
                    updates.append({
                        "range": f"B{row_number}",
                        "values": [[product_name]]
                    })
                
                # Обновляем SKU (колонка A), если пусто
                if len(data_rows[row_number - 1]) == 0 or not data_rows[row_number - 1][0]:
                    updates.append({
                        "range": f"A{row_number}",
                        "values": [[str(product_id)]]
                    })
                
                # Обновляем offer_id (колонка D), если пусто
                if len(data_rows[row_number - 1]) <= 3 or not data_rows[row_number - 1][3]:
                    updates.append({
                        "range": f"D{row_number}",
                        "values": [[offer_id]]
                    })
                
                # Обновляем остатки (колонки I, J, K)
                updates.append({
                    "range": f"I{row_number}",
                    "values": [[stocks_data["total"]]]
                })
                updates.append({
                    "range": f"J{row_number}",
                    "values": [[stocks_data["fbo"]]]
                })
                updates.append({
                    "range": f"K{row_number}",
                    "values": [[stocks_data["fbs"]]]
                })
                
                # Обновляем цену (колонка Q), если получена
                if price:
                    updates.append({
                        "range": f"Q{row_number}",
                        "values": [[price]]
                    })
                
                # Выполняем пакетное обновление
                if updates:
                    spreadsheet = await self.sheets_api.open_spreadsheet(self.spreadsheet_id)
                    if spreadsheet:
                        worksheet = spreadsheet.worksheet(self.sheet_name)
                        worksheet.batch_update(updates)
                        logger.info(f"Обновлено {len(updates)} ячеек для товара {offer_id}")
                    else:
                        return {"success": False, "error": "Не удалось открыть таблицу для обновления"}
            
            return {
                "success": True,
                "offer_id": offer_id,
                "product_id": product_id,
                "name": product_name,
                "stock": stocks_data["total"],
                "stock_fbo": stocks_data["fbo"],
                "stock_fbs": stocks_data["fbs"],
                "price": price,
                "row": row_number
            }
            
        except Exception as e:
            logger.error(f"Ошибка автозаполнения товара: {e}", exc_info=True)
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
                test_result = await self.get_wb_warehouses()
                results["wildberries"] = test_result.get("success", False)
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
        """Получает список складов WB (API v3)"""
        if not self.wb_api_key:
            return {"success": False, "error": "Wildberries API не настроен"}

        try:
            resp = await self._wb_request("/api/v3/warehouses", suppliers=True)
            if resp.status_code == 200:
                return {"success": True, "warehouses": resp.json()}
            return {"success": False, "error": f"{resp.status_code} - {resp.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_wb_product_barcodes(self) -> Dict[str, Union[bool, str, List[str]]]:
        """Получает список баркодов (sku) всех карточек WB через Content-API v2."""
        if not self.wb_api_key:
            return {"success": False, "error": "Wildberries API не настроен"}

        try:
            barcodes: List[str] = []

            cursor_updated_at: Optional[str] = None
            cursor_nm_id: Optional[int] = None
            total: Optional[int] = None

            while True:
                cursor_payload: Dict[str, Any] = {"limit": 100}
                if cursor_updated_at and cursor_nm_id is not None:
                    cursor_payload.update({
                        "updatedAt": cursor_updated_at,
                        "nmID": int(cursor_nm_id)
                    })

                payload = {
                    "settings": {
                        "cursor": cursor_payload,
                        "filter": {"withPhoto": -1}
                    }
                }

                resp = await self._wb_request(
                    "/content/v2/get/cards/list",
                    suppliers=False,
                    method="POST",
                    bearer=True,
                    json=payload,
                )

                if resp.status_code != 200:
                    logger.error("WB content API err %s: %s", resp.status_code, resp.text)
                    return {"success": False, "error": f"{resp.status_code} - {resp.text}"}

                data = resp.json()
                cards = data.get("cards", []) or []
                cursor_obj = data.get("cursor", {}) or {}

                for card in cards:
                    for sz in card.get("sizes", []) or []:
                        barcodes.extend(sz.get("skus", []) or [])

                cursor_updated_at = cursor_obj.get("updatedAt")
                cursor_nm_id = cursor_obj.get("nmID")
                total = cursor_obj.get("total", total)

                if not cards or cursor_updated_at is None or cursor_nm_id is None:
                    break

            return {"success": True, "barcodes": barcodes, "total": len(barcodes)}

        except Exception as e:
            logger.exception("Ошибка get_wb_product_barcodes")
            return {"success": False, "error": str(e)}

    async def get_wb_stocks(self, warehouse_id: int, barcodes: List[str]) -> Dict[str, Union[bool, str, Dict]]:
        """Получение остатков товаров на складе WB"""
        if not self.wb_api_key:
            return {"success": False, "error": "Wildberries API не настроен"}

        try:
            resp = await self._wb_request(
                f"/api/v3/stocks/{warehouse_id}",
                suppliers=True,
                method="POST",
                json={"skus": barcodes},
            )
            if resp.status_code == 200:
                return {"success": True, "stocks": resp.json()}
            return {"success": False, "error": f"{resp.status_code} - {resp.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Ранее здесь логировалось значение WB_API_KEY — секрет попадал в логи Amvera при
# каждом импорте модуля. Для диагностики достаточно факта наличия ключа: см. _validate_config().


_manager_instance: Optional["MarketplaceManager"] = None


def get_manager() -> "MarketplaceManager":
    """
    Возвращает общий экземпляр MarketplaceManager.

    Конструктор авторизует service-account Google Sheets (сетевой запрос), поэтому
    создавать его заново в каждой из ~20 команд — лишний round-trip перед началом работы.
    Экземпляр кешируется только при успешном создании: если ключи не настроены,
    исключение прокидывается наверх, и следующий вызов попробует снова.
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MarketplaceManager()
        logger.info("MarketplaceManager инициализирован (общий экземпляр)")
    return _manager_instance
