# Google Sheets API модуль
import gspread
from google.oauth2.service_account import Credentials
import logging
import os
from typing import Dict, List, Optional, Union
import json

logger = logging.getLogger(__name__)

class GoogleSheetsAPI:
    """Класс для работы с Google Sheets API"""
    
    def __init__(self):
        # Настройки Google Sheets API
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Путь к файлу сервисного аккаунта (будет загружен из переменной окружения)
        self.service_account_info = self._get_service_account_info()
        
        if not self.service_account_info:
            raise ValueError("Информация о сервисном аккаунте не найдена")
        
        # Создаем учетные данные
        self.creds = Credentials.from_service_account_info(
            self.service_account_info, 
            scopes=self.scope
        )
        
        # Создаем клиент
        self.client = gspread.authorize(self.creds)
        
        logger.info("Google Sheets API клиент успешно инициализирован")
    
    def _get_service_account_info(self) -> Optional[Dict]:
        """Получает информацию о сервисном аккаунте из переменной окружения"""
        try:
            # Пытаемся получить из переменной окружения GOOGLE_SERVICE_ACCOUNT_BASE64
            service_account_base64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")
            
            if service_account_base64:
                # Декодируем base64 и парсим JSON
                import base64
                service_account_json = base64.b64decode(service_account_base64).decode('utf-8')
                return json.loads(service_account_json)
            
            # Пытаемся получить из переменной окружения GOOGLE_SERVICE_ACCOUNT (обычный JSON)
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
            
            if service_account_json:
                # Парсим JSON из переменной окружения
                return json.loads(service_account_json)
            
            # Альтернативно, можно попробовать получить из файла
            service_account_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH")
            if service_account_path and os.path.exists(service_account_path):
                with open(service_account_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            logger.error("Переменные GOOGLE_SERVICE_ACCOUNT_BASE64, GOOGLE_SERVICE_ACCOUNT или GOOGLE_SERVICE_ACCOUNT_PATH не настроены")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о сервисном аккаунте: {e}")
            return None
    
    async def test_connection(self) -> Dict[str, Union[bool, str]]:
        """Тестирует подключение к Google Sheets API"""
        try:
            # Пытаемся получить список таблиц
            spreadsheets = self.client.list_spreadsheet_files()
            
            return {
                "success": True, 
                "message": f"Подключение к Google Sheets API успешно. Доступно таблиц: {len(spreadsheets)}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка подключения к Google Sheets API: {e}")
            return {
                "success": False, 
                "message": f"Ошибка подключения: {str(e)}"
            }
    
    async def open_spreadsheet(self, spreadsheet_id: str) -> Optional[gspread.Spreadsheet]:
        """Открывает таблицу по ID"""
        try:
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            logger.info(f"Таблица {spreadsheet.title} успешно открыта")
            return spreadsheet
        except Exception as e:
            logger.error(f"Ошибка открытия таблицы {spreadsheet_id}: {e}")
            return None
    
    async def get_sheet_data(self, spreadsheet_id: str, sheet_name: str = None, range_name: str = None) -> Dict:
        """Получает данные из таблицы"""
        try:
            spreadsheet = await self.open_spreadsheet(spreadsheet_id)
            if not spreadsheet:
                return {"success": False, "error": "Не удалось открыть таблицу"}
            
            # Если указано имя листа, открываем его
            if sheet_name:
                worksheet = spreadsheet.worksheet(sheet_name)
            else:
                # Иначе берем первый лист
                worksheet = spreadsheet.worksheet(0)
            
            # Получаем данные
            if range_name:
                data = worksheet.get(range_name)
            else:
                data = worksheet.get_all_values()
            
            return {
                "success": True,
                "data": data,
                "spreadsheet_title": spreadsheet.title,
                "sheet_name": worksheet.title,
                "rows": len(data),
                "columns": len(data[0]) if data else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения данных из таблицы: {e}")
            return {"success": False, "error": str(e)}
    
    async def write_data(self, spreadsheet_id: str, sheet_name: str, data: List[List], start_cell: str = "A1") -> Dict:
        """Записывает данные в таблицу"""
        try:
            spreadsheet = await self.open_spreadsheet(spreadsheet_id)
            if not spreadsheet:
                return {"success": False, "error": "Не удалось открыть таблицу"}
            
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Записываем данные
            worksheet.update(start_cell, data)
            
            return {
                "success": True,
                "message": f"Данные успешно записаны в {sheet_name} начиная с {start_cell}",
                "rows_written": len(data),
                "columns_written": len(data[0]) if data else 0
            }
            
        except Exception as e:
            logger.error(f"Ошибка записи данных в таблицу: {e}")
            return {"success": False, "error": str(e)}
    
    async def append_data(self, spreadsheet_id: str, sheet_name: str, data: List[List]) -> Dict:
        """Добавляет данные в конец таблицы"""
        try:
            spreadsheet = await self.open_spreadsheet(spreadsheet_id)
            if not spreadsheet:
                return {"success": False, "error": "Не удалось открыть таблицу"}
            
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Добавляем данные в конец
            worksheet.append_rows(data)
            
            return {
                "success": True,
                "message": f"Данные успешно добавлены в {sheet_name}",
                "rows_added": len(data)
            }
            
        except Exception as e:
            logger.error(f"Ошибка добавления данных в таблицу: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_sheet_info(self, spreadsheet_id: str) -> Dict:
        """Получает информацию о таблице и листах"""
        try:
            spreadsheet = await self.open_spreadsheet(spreadsheet_id)
            if not spreadsheet:
                return {"success": False, "error": "Не удалось открыть таблицу"}
            
            # Получаем информацию о листах
            worksheets = spreadsheet.worksheets()
            sheets_info = []
            
            for ws in worksheets:
                sheets_info.append({
                    "title": ws.title,
                    "id": ws.id,
                    "row_count": ws.row_count,
                    "col_count": ws.col_count
                })
            
            return {
                "success": True,
                "spreadsheet_title": spreadsheet.title,
                "spreadsheet_id": spreadsheet_id,
                "sheets_count": len(worksheets),
                "sheets": sheets_info
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о таблице: {e}")
            return {"success": False, "error": str(e)}
    
    async def batch_update_values(self, spreadsheet_id: str, sheet_name: str = None, updates: List[tuple]) -> Dict:
        """Пакетное обновление значений в таблице
        
        Args:
            spreadsheet_id: ID таблицы
            sheet_name: Имя листа (если None, то range должен содержать полный путь)
            updates: Список кортежей (range, [[value]])
        
        Returns:
            Dict с результатом операции
        """
        try:
            spreadsheet = await self.open_spreadsheet(spreadsheet_id)
            if not spreadsheet:
                return {"success": False, "error": "Не удалось открыть таблицу"}
            
            # Если sheet_name не указан, берем первый лист
            if sheet_name is None:
                worksheet = spreadsheet.worksheet(0)
                sheet_name = worksheet.title
            else:
                worksheet = spreadsheet.worksheet(sheet_name)
            
            # Подготавливаем данные для batch update
            batch_data = []
            for range_name, values in updates:
                # Если range_name уже содержит имя листа, используем как есть
                if "!" in range_name:
                    final_range = range_name
                else:
                    final_range = f"{sheet_name}!{range_name}"
                
                batch_data.append({
                    "range": final_range,
                    "values": values
                })
            
            # Выполняем пакетное обновление
            worksheet.batch_update(batch_data)
            
            return {
                "success": True,
                "message": f"Пакетное обновление выполнено для {len(updates)} ячеек",
                "cells_updated": len(updates)
            }
            
        except Exception as e:
            logger.error(f"Ошибка пакетного обновления: {e}")
            return {"success": False, "error": str(e)}

# Функции для удобного использования
async def test_google_sheets_connection() -> str:
    """Тестирует подключение к Google Sheets API и возвращает сообщение"""
    try:
        sheets_api = GoogleSheetsAPI()
        result = await sheets_api.test_connection()
        
        if result["success"]:
            return f"✅ {result['message']}"
        else:
            return f"❌ {result['message']}"
            
    except Exception as e:
        return f"❌ Критическая ошибка: {str(e)}"

async def get_sheets_info(spreadsheet_id: str) -> Dict:
    """Получает информацию о таблице"""
    try:
        sheets_api = GoogleSheetsAPI()
        return await sheets_api.get_sheet_info(spreadsheet_id)
    except Exception as e:
        return {"success": False, "error": str(e)}

async def read_sheet_data(spreadsheet_id: str, sheet_name: str = None) -> Dict:
    """Читает данные из таблицы"""
    try:
        sheets_api = GoogleSheetsAPI()
        return await sheets_api.get_sheet_data(spreadsheet_id, sheet_name)
    except Exception as e:
        return {"success": False, "error": str(e)}
