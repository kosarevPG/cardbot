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
    
    async def get_ozon_stock(self, offer_id: str) -> Optional[int]:
        """Получает остаток товара по offer_id"""
        try:
            payload = {
                "offer_id": offer_id
            }
            
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.ozon_api.base_url}/v3/product/info/stocks",
                    headers=self.ozon_api.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data and "stocks" in data["result"]:
                        stocks = data["result"]["stocks"]
                        if stocks:
                            # Суммируем все остатки по складам
                            total_stock = sum(stock.get("present", 0) for stock in stocks)
                            return total_stock
                
                logger.warning(f"Не удалось получить остаток для {offer_id}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения остатка для {offer_id}: {e}")
            return None
    
    async def get_ozon_analytics(self, offer_id: str, date_from: str, date_to: str) -> Dict:
        """Получает аналитику продаж и выручки по offer_id"""
        try:
            payload = {
                "date_from": date_from,
                "date_to": date_to,
                "metrics": [
                    "ordered_units",
                    "revenue"
                ],
                "dimension": "sku",
                "filters": [
                    {
                        "key": "offer_id",
                        "value": offer_id
                    }
                ],
                "limit": 1000
            }
            
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.ozon_api.base_url}/v3/analytics/data",
                    headers=self.ozon_api.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data and data["result"]:
                        result = data["result"][0]
                        return {
                            "ordered_units": result.get("ordered_units", 0),
                            "revenue": result.get("revenue", 0.0)
                        }
                
                logger.warning(f"Не удалось получить аналитику для {offer_id}")
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
                # Извлекаем offer_id из данных, убираем пустые строки
                offer_ids = []
                for row in data:
                    if row and row[0] and row[0].strip():  # Проверяем, что ячейка не пустая
                        offer_ids.append(row[0].strip())
                
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
            updates = [
                [stock],      # Колонка E - остаток
                [sales],      # Колонка F - продажи
                [revenue]     # Колонка G - выручка
            ]
            
            # Обновляем каждую колонку отдельно
            for i, (col, value) in enumerate(zip(['E', 'F', 'G'], updates)):
                cell_range = f"{col}{row_index}"
                update_result = await self.sheets_api.write_data(
                    self.spreadsheet_id,
                    self.sheet_name,
                    value,
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
            
            # Получаем остаток
            stock = await self.get_ozon_stock(offer_id)
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
        """Синхронизирует данные для всех offer_id из таблицы"""
        try:
            logger.info("Начинаю синхронизацию всех offer_id")
            
            # Читаем offer_id из таблицы
            offer_ids = await self.read_offer_ids_from_sheet()
            
            if not offer_ids:
                return {
                    "success": False,
                    "error": "Не удалось прочитать offer_id из таблицы"
                }
            
            # Синхронизируем каждый offer_id
            results = []
            for offer_id in offer_ids:
                result = await self.sync_single_offer(offer_id)
                results.append(result)
                
                # Небольшая задержка между запросами
                await asyncio.sleep(0.5)
            
            # Подсчитываем статистику
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
