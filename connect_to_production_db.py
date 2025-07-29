#!/usr/bin/env python3
"""
Скрипт для подключения к продакшн БД через веб-интерфейс
"""

import requests
import re
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

class ProductionDBClient:
    def __init__(self):
        self.base_url = "https://cardbot-1-kosarevpg.amvera.io"
        self.session = requests.Session()
        
        # Настройки для аутентификации (если требуется)
        self.username = "admin"
        self.password = "root"
        self.session.auth = (self.username, self.password)
        
    def test_connection(self) -> bool:
        """Тестирует подключение к продакшн БД"""
        print("🔍 ТЕСТ ПОДКЛЮЧЕНИЯ К PRODUCTION БД")
        print("=" * 50)
        
        url = f"{self.base_url}/actions/content/"
        
        try:
            print(f"Подключаюсь к: {url}")
            response = self.session.get(url, timeout=15)
            
            print(f"Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Подключение успешно!")
                print(f"Размер ответа: {len(response.text)} символов")
                return True
            elif response.status_code == 401:
                print("❌ Ошибка аутентификации (401)")
                print("Попробуйте без аутентификации...")
                # Пробуем без аутентификации
                self.session.auth = None
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    print("✅ Подключение успешно без аутентификации!")
                    return True
                else:
                    print(f"❌ Ошибка подключения без аутентификации: {response.status_code}")
                    return False
            else:
                print(f"❌ Ошибка подключения: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def get_table_content(self, table_name: str = "actions", page: int = 1) -> Optional[Dict[str, Any]]:
        """Получает содержимое таблицы"""
        print(f"🔍 ПОЛУЧЕНИЕ СОДЕРЖИМОГО ТАБЛИЦЫ {table_name}")
        print("=" * 50)
        
        url = f"{self.base_url}/{table_name}/content/"
        if page > 1:
            url += f"?page={page}"
        
        try:
            print(f"Запрос: {url}")
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                print("✅ Данные получены успешно!")
                return self.parse_table_content(response.text, table_name)
            else:
                print(f"❌ Ошибка получения данных: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    def parse_table_content(self, html_content: str, table_name: str) -> Dict[str, Any]:
        """Парсит содержимое таблицы из HTML"""
        try:
            # Извлекаем информацию о таблице
            result = {
                'table_name': table_name,
                'total_rows': 0,
                'current_page': 1,
                'total_pages': 1,
                'headers': [],
                'rows': []
            }
            
            # Ищем информацию о количестве записей
            rows_match = re.search(r'(\d+)\s+rows', html_content)
            if rows_match:
                result['total_rows'] = int(rows_match.group(1))
            
            # Ищем информацию о страницах
            page_match = re.search(r'Page\s+(\d+)\s+/\s+(\d+)', html_content)
            if page_match:
                result['current_page'] = int(page_match.group(1))
                result['total_pages'] = int(page_match.group(2))
            
            # Извлекаем заголовки таблицы
            headers = []
            header_pattern = r'<th[^>]*>(.*?)</th>'
            for match in re.findall(header_pattern, html_content):
                headers.append(match.strip())
            result['headers'] = headers
            
            # Извлекаем строки данных
            rows = []
            row_pattern = r'<tr[^>]*>(.*?)</tr>'
            for row_match in re.findall(row_pattern, html_content):
                cell_pattern = r'<td[^>]*>(.*?)</td>'
                cells = []
                for cell_match in re.findall(cell_pattern, row_match):
                    cells.append(cell_match.strip())
                if cells and len(cells) == len(headers):
                    rows.append(cells)
            result['rows'] = rows
            
            print(f"📊 Найдено записей: {len(rows)}")
            print(f"📄 Страница: {result['current_page']} из {result['total_pages']}")
            
            return result
            
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
            return {'error': str(e)}
    
    def search_actions(self, search_term: str) -> Optional[Dict[str, Any]]:
        """Ищет действия по ключевому слову"""
        print(f"🔍 ПОИСК ДЕЙСТВИЙ: {search_term}")
        print("=" * 40)
        
        # Получаем все действия и фильтруем
        actions_data = self.get_table_content("actions")
        
        if not actions_data or 'rows' not in actions_data:
            return None
        
        filtered_rows = []
        for row in actions_data['rows']:
            if len(row) >= 5:  # id, user_id, username, name, action, details, timestamp
                action = row[4] if len(row) > 4 else ""
                details = row[5] if len(row) > 5 else ""
                
                if search_term.lower() in action.lower() or search_term.lower() in details.lower():
                    filtered_rows.append(row)
        
        return {
            'search_term': search_term,
            'total_found': len(filtered_rows),
            'rows': filtered_rows,
            'headers': actions_data.get('headers', [])
        }
    
    def get_user_actions(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает действия конкретного пользователя"""
        print(f"🔍 ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ {user_id}")
        print("=" * 40)
        
        actions_data = self.get_table_content("actions")
        
        if not actions_data or 'rows' not in actions_data:
            return None
        
        user_actions = []
        for row in actions_data['rows']:
            if len(row) >= 2 and row[1] == str(user_id):
                user_actions.append(row)
        
        return {
            'user_id': user_id,
            'total_actions': len(user_actions),
            'rows': user_actions,
            'headers': actions_data.get('headers', [])
        }
    
    def get_recent_actions(self, limit: int = 20) -> Optional[Dict[str, Any]]:
        """Получает последние действия"""
        print(f"🔍 ПОСЛЕДНИЕ ДЕЙСТВИЯ (лимит: {limit})")
        print("=" * 40)
        
        actions_data = self.get_table_content("actions")
        
        if not actions_data or 'rows' not in actions_data:
            return None
        
        recent_actions = actions_data['rows'][:limit]
        
        return {
            'limit': limit,
            'total_found': len(recent_actions),
            'rows': recent_actions,
            'headers': actions_data.get('headers', [])
        }

def main():
    """Основная функция"""
    print("🔍 КЛИЕНТ ДЛЯ ПОДКЛЮЧЕНИЯ К PRODUCTION БД")
    print("=" * 60)
    print(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    client = ProductionDBClient()
    
    # Тест подключения
    if client.test_connection():
        print("\n" + "="*50 + "\n")
        
        # Получаем последние действия
        recent_actions = client.get_recent_actions(10)
        if recent_actions:
            print("📊 ПОСЛЕДНИЕ ДЕЙСТВИЯ:")
            for row in recent_actions['rows']:
                if len(row) >= 7:
                    id_val, user_id, username, name, action, details, timestamp = row
                    print(f"ID: {id_val} | User: {user_id} | Action: {action} | Time: {timestamp}")
        
        print("\n" + "="*50 + "\n")
        
        # Ищем действия admin_requests_viewed
        admin_actions = client.search_actions("admin_requests_viewed")
        if admin_actions and admin_actions['total_found'] > 0:
            print("🚨 НАЙДЕНЫ АДМИНСКИЕ ДЕЙСТВИЯ:")
            for row in admin_actions['rows']:
                if len(row) >= 7:
                    id_val, user_id, username, name, action, details, timestamp = row
                    print(f"ID: {id_val} | User: {user_id} | Action: {action} | Time: {timestamp}")
        else:
            print("✅ Админских действий не найдено")
        
        print("\n" + "="*50 + "\n")
        
        # Проверяем действия пользователя 865377684
        user_actions = client.get_user_actions(865377684)
        if user_actions and user_actions['total_actions'] > 0:
            print(f"📊 ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ 865377684 ({user_actions['total_actions']} записей):")
            for row in user_actions['rows']:
                if len(row) >= 7:
                    id_val, user_id, username, name, action, details, timestamp = row
                    print(f"ID: {id_val} | Action: {action} | Time: {timestamp}")
        else:
            print("ℹ️ Действий пользователя 865377684 не найдено")
        
        print("\n" + "="*50 + "\n")
        
        # Получаем общую статистику
        actions_data = client.get_table_content("actions")
        if actions_data:
            print("📊 ОБЩАЯ СТАТИСТИКА:")
            print(f"Всего записей в таблице actions: {actions_data['total_rows']}")
            print(f"Текущая страница: {actions_data['current_page']} из {actions_data['total_pages']}")
        
    else:
        print("❌ Не удалось подключиться к продакшн БД")
        print("\n💡 Возможные причины:")
        print("   - Бот не запущен на Amvera")
        print("   - Неправильный URL")
        print("   - Проблемы с сетью")
        print("   - Требуется аутентификация")

if __name__ == "__main__":
    main() 