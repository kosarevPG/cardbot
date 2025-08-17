# Модуль автоматической синхронизации Ozon с Google таблицами
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from .ozon_api import OzonAPI
from .google_sheets import GoogleSheetsAPI

logger = logging.getLogger(__name__)

class OzonDataSync:
    """Класс для автоматической синхронизации данных Ozon с Google таблицами"""
    
    def __init__(self):
        self.ozon_api = OzonAPI()
        self.sheets_api = GoogleSheetsAPI()
        
        # ID таблицы и имя листа из документации
        self.spreadsheet_id = "1RoWWv9BgiwlSu9H-KJNsFItQxlUVhG1WMbyB0eFxzYM"
        self.sheet_name = "marketplaces"
        
        # Структура таблицы
        self.columns = {
            "offer_id": "D",      # Арт. Ozon (колонка D)
            "stock": "E",         # Остаток Ozon (колонка E)
            "sales": "F",         # Продажи Ozon (колонка F)
            "revenue": "G"        # Выручка Ozon (колонка G)
        }
    
    async def get_ozon_stock(self, offer_id: str, offer_map: dict[str, int]) -> Optional[int]:
        """Получает остаток товара по offer_id используя настоящий эндпоинт"""
        try:
            import httpx, asyncio, random
            
            body = {"product_id": offer_map[offer_id]} if offer_id in offer_map else {"offer_id": offer_id}
            
            for attempt in range(3):
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r = await client.post(
                        f"{self.ozon_api.base_url}/v3/product/info/stocks",
                        headers=self.ozon_api.headers,
                        json=body
                    )
                    
                    if r.status_code in (429, 500, 502, 503, 504):
                        await asyncio.sleep((2** attempt) + random.random())
                        continue
                    
                    if r.status_code == 404:
                        logger.warning(f"Stocks 404 for {offer_id} (body={body})")
                        return None
                    
                    r.raise_for_status()
                    
                    res = r.json().get("result", {})
                    total_present = sum(int(wh.get("present", 0)) for wh in res.get("stocks", []))
                    return total_present
            
            return None
                
        except Exception as e:
            logger.error(f"Ошибка получения остатка для {offer_id}: {e}")
            return None
    
    async def build_offer_map(self) -> dict[str, int]:
        """Строит карту offer_id -> product_id"""
        try:
            # Берём все товары — пагинация при необходимости
            payload = {"filter": {}, "limit": 1000, "last_id": ""}
            offer_map = {}
            
            import httpx
            async with httpx.AsyncClient(timeout=20.0) as client:
                while True:
                    r = await client.post(
                        f"{self.ozon_api.base_url}/v3/product/list",
                        headers=self.ozon_api.headers,
                        json=payload
                    )
                    r.raise_for_status()
                    
                    data = r.json()["result"]
                    for it in data.get("items", []):
                        offer = it.get("offer_id")
                        pid = it.get("product_id")
                        
                        if not pid:
                            continue
                        
                        if isinstance(offer, str) and offer:
                            offer_map[offer] = pid
                        elif isinstance(offer, list):
                            for o in offer:
                                if o:
                                    offer_map[str(o)] = pid
                    
                    last_id = data.get("last_id")
                    if not last_id:
                        break
                    payload["last_id"] = last_id
            
            logger.info(f"Построена карта для {len(offer_map)} товаров")
            return offer_map
            
        except Exception as e:
            logger.error(f"Ошибка построения карты offer_id: {e}")
            return {}

    async def get_ozon_analytics(self, offer_id: str, date_from: str, date_to: str) -> Dict:
        """Получает аналитику продаж и выручки по offer_id"""
        try:
            import httpx, asyncio, random
            
            body = {
                "date_from": date_from,
                "date_to": date_to,
                "metrics": ["ordered_units", "revenue"],
                "dimension": "offer_id",
                "filters": [{"key": "offer_id", "op": "IN", "value": [offer_id]}],
                "limit": 1000
            }
            
            for attempt in range(3):
                async with httpx.AsyncClient(timeout=20.0) as client:
                    r = await client.post(
                        f"{self.ozon_api.base_url}/v3/analytics/data",
                        headers=self.ozon_api.headers,
                        json=body
                    )
                    
                    if r.status_code in (429, 500, 502, 503, 504):
                        await asyncio.sleep((2** attempt) + random.random())
                        continue
                    
                    if r.status_code == 404:
                        logger.warning(f"Analytics 404 for {offer_id} (body={body})")
                        return {"ordered_units": 0, "revenue": 0.0}
                    
                    r.raise_for_status()
                    
                    rows = r.json().get("result", [])
                    if not rows:
                        return {"ordered_units": 0, "revenue": 0.0}
                    
                    row = rows[0]
                    return {
                        "ordered_units": int(row.get("ordered_units", 0)),
                        "revenue": float(row.get("revenue", 0.0))
                    }
            
            return {"ordered_units": 0, "revenue": 0.0}
                
        except Exception as e:
            logger.error(f"Ошибка получения аналитики для {offer_id}: {e}")
            return {"ordered_units": 0, "revenue": 0.0}
    
    async def read_offer_ids_from_sheet(self) -> List[str]:
        """Читает offer_id из колонки D таблицы"""
        try:
            # Читаем данные из колонки D (начиная со строки 2)
            range_name = f"{self.columns['offer_id']}2:{self.columns['offer_id']}"
            
            result = await self.sheets_api.get_sheet_data(
                self.spreadsheet_id, 
                self.sheet_name, 
                range_name
            )
            
            if result["success"]:
                data = result["data"]
                # Извлекаем offer_id из данных, убираем пустые строки и нормализуем
                offer_ids = []
                for row in data:
                    if row and row[0] and row[0].strip():  # Проверяем, что ячейка не пустая
                        normalized_id = row[0].strip().upper()  # Нормализуем через .strip() и .upper()
                        offer_ids.append(normalized_id)
                
                logger.info(f"Прочитано {len(offer_ids)} offer_id из таблицы")
                return offer_ids
            else:
                logger.error(f"Ошибка чтения данных из таблицы: {result.get('error')}")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка чтения offer_id из таблицы: {e}")
            return []
    
    async def update_sheet_data(self, offer_id: str, stock: int, sales: int, revenue: float) -> bool:
        """Обновляет данные в таблице для конкретного offer_id"""
        try:
            # Находим строку с нужным offer_id
            result = await self.sheets_api.get_sheet_data(
                self.spreadsheet_id, 
                self.sheet_name
            )
            
            if not result["success"]:
                logger.error(f"Не удалось прочитать таблицу для поиска {offer_id}")
                return False
            
            data = result["data"]
            row_index = None
            
            # Ищем строку с нужным offer_id (колонка D)
            for i, row in enumerate(data):
                if len(row) > 3 and row[3] == offer_id:  # Колонка D (индекс 3)
                    row_index = i + 1  # +1 потому что индексация в Google Sheets начинается с 1
                    break
            
            if row_index is None:
                logger.warning(f"Offer_id {offer_id} не найден в таблице")
                return False
            
            # Обновляем данные в соответствующих колонках
            # Google Sheets требует двумерный массив [[value]]
            updates = [
                (stock if stock is not None else 0),      # Колонка E - остаток
                (sales if sales is not None else 0),      # Колонка F - продажи
                (revenue if revenue is not None else 0.0) # Колонка G - выручка
            ]
            
            # Обновляем каждую колонку отдельно
            for i, (col, value) in enumerate(zip(['E', 'F', 'G'], updates)):
                cell_range = f"{col}{row_index}"
                # Форматируем значение как двумерный массив [[value]]
                formatted_value = [[value]]
                
                update_result = await self.sheets_api.write_data(
                    self.spreadsheet_id,
                    self.sheet_name,
                    formatted_value,
                    cell_range
                )
                
                if not update_result["success"]:
                    logger.error(f"Ошибка обновления {col}{row_index}: {update_result.get('error')}")
                    return False
            
            logger.info(f"Данные для {offer_id} успешно обновлены")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления данных для {offer_id}: {e}")
            return False
    
    async def sync_single_offer(self, offer_id: str) -> Dict:
        """Синхронизирует данные для одного offer_id"""
        try:
            logger.info(f"Синхронизация данных для {offer_id}")
            
            # Строим карту offer_id -> product_id
            offer_map = await self.build_offer_map()
            
            # Получаем остаток
            stock = await self.get_ozon_stock(offer_id, offer_map)
            if stock is None:
                stock = 0
            
            # Получаем аналитику за последние 7 дней
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            analytics = await self.get_ozon_analytics(offer_id, date_from, date_to)
            sales = analytics["ordered_units"]
            revenue = analytics["revenue"]
            
            # Обновляем таблицу
            success = await self.update_sheet_data(offer_id, stock, sales, revenue)
            
            return {
                "offer_id": offer_id,
                "success": success,
                "stock": stock,
                "sales": sales,
                "revenue": revenue
            }
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации {offer_id}: {e}")
            return {
                "offer_id": offer_id,
                "success": False,
                "error": str(e)
            }
    
    async def sync_all_offers(self) -> Dict:
        """Синхронизирует данные для всех offer_id из таблицы (оптимизированная версия)"""
        try:
            logger.info("Начинаю синхронизацию всех offer_id")
            
            # Читаем offer_id из таблицы
            offer_ids = await self.read_offer_ids_from_sheet()
            
            if not offer_ids:
                return {
                    "success": False,
                    "error": "Не удалось прочитать offer_id из таблицы"
                }
            
            # карта offer_id -> product_id
            offer_map = await self.build_offer_map()
            
            # распарсим все строки разом (чтобы знать, в каких строках писать)
            sheet_rows = await self.sheets_api.get_sheet_data(
                self.spreadsheet_id, 
                self.sheet_name
            )
            
            if not sheet_rows["success"]:
                return {
                    "success": False,
                    "error": "Не удалось прочитать лист целиком"
                }
            
            data = sheet_rows["data"]
            # индекс строки по offer_id (D-колонка) - нормализуем для поиска
            row_by_offer: dict[str, int] = {}
            for i, row in enumerate(data, start=1):
                if len(row) > 3 and row[3]:
                    normalized_id = row[3].strip().upper()  # Нормализуем для поиска
                    row_by_offer[normalized_id] = i
            
            updates = []  # (range, [[value]])
            results = []
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            for offer_id in offer_ids:
                # Нормализуем offer_id для поиска в таблице
                normalized_offer_id = offer_id.upper()
                row_index = row_by_offer.get(normalized_offer_id)
                if not row_index:
                    logger.warning(f"{offer_id} нет в листе - пропускаю")
                    results.append({"offer_id": offer_id, "success": False, "error": "not in sheet"})
                    continue
                
                stock = await self.get_ozon_stock(offer_id, offer_map)
                if stock is None:
                    stock = 0
                
                analytics = await self.get_ozon_analytics(offer_id, date_from, date_to)
                sales = analytics["ordered_units"]
                revenue = analytics["revenue"]
                
                updates += [
                    (f"E{row_index}", [[stock]]),
                    (f"F{row_index}", [[sales]]),
                    (f"G{row_index}", [[revenue]])
                ]
                
                results.append({"offer_id": offer_id, "success": True, "stock": stock, "sales": sales, "revenue": revenue})
                await asyncio.sleep(0.2)  # чуть разгрузим RPS
            
            # единым batch-запросом
            ok = await self.sheets_api.batch_update_values(self.spreadsheet_id, self.sheet_name, updates)
            if not ok["success"]:
                logger.error(f"Ошибка записи данных в таблицу: {ok.get('error')}")
                # можно fallback'ом писать по одной ячейке
            
            successful = sum(1 for r in results if r["success"])
            failed = len(results) - successful
            
            return {
                "success": True,
                "total_offers": len(offer_ids),
                "successful": successful,
                "failed": failed,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации всех offer_id: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Функции для удобного использования
async def sync_ozon_data() -> str:
    """Синхронизирует данные Ozon с Google таблицей и возвращает сообщение"""
    try:
        sync = OzonDataSync()
        result = await sync.sync_all_offers()
        
        if result["success"]:
            return f"✅ Синхронизация завершена!\n\n📊 **Статистика:**\n• Всего товаров: {result['total_offers']}\n• Успешно: {result['successful']}\n• Ошибок: {result['failed']}"
        else:
            return f"❌ Ошибка синхронизации: {result.get('error', 'Неизвестная ошибка')}"
            
    except Exception as e:
        return f"❌ Критическая ошибка: {str(e)}"

async def sync_single_ozon_offer(offer_id: str) -> str:
    """Синхронизирует данные для одного offer_id"""
    try:
        sync = OzonDataSync()
        result = await sync.sync_single_offer(offer_id)
        
        if result["success"]:
            return f"✅ Данные для {offer_id} обновлены!\n\n📊 **Результат:**\n• Остаток: {result['stock']} шт.\n• Продажи (7 дней): {result['sales']} шт.\n• Выручка (7 дней): {result['revenue']} ₽"
        else:
            return f"❌ Ошибка синхронизации {offer_id}: {result.get('error', 'Неизвестная ошибка')}"
            
    except Exception as e:
        return f"❌ Критическая ошибка: {str(e)}"
