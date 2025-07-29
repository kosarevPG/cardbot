#!/usr/bin/env python3
"""
Клиент для работы с БД с аутентификацией
"""

import requests
import re
import json
from datetime import datetime

class AuthenticatedDBClient:
    def __init__(self):
        self.base_url = "https://cardbot-1-kosarevpg.amvera.io"
        self.username = "admin"
        self.password = "root"
        self.session = requests.Session()
        
        # Настраиваем аутентификацию
        self.session.auth = (self.username, self.password)
        
    def test_connection(self):
        """Тестирует подключение с аутентификацией"""
        print("🔍 ТЕСТ ПОДКЛЮЧЕНИЯ С АУТЕНТИФИКАЦИЕЙ")
        print("=" * 50)
        
        url = f"{self.base_url}/actions/content/"
        
        try:
            print(f"Подключаюсь к: {url}")
            print(f"Логин: {self.username}")
            print(f"Пароль: {self.password}")
            
            response = self.session.get(url, timeout=15)
            
            print(f"Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Подключение успешно!")
                print(f"Размер ответа: {len(response.text)} символов")
                return True
            elif response.status_code == 401:
                print("❌ Ошибка аутентификации (401)")
                return False
            else:
                print(f"❌ Ошибка подключения: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def execute_sql_query(self, sql_query):
        """Выполняет SQL-запрос с аутентификацией"""
        print(f"🔍 ВЫПОЛНЕНИЕ SQL-ЗАПРОСА")
        print("=" * 40)
        print(f"SQL: {sql_query}")
        print()
        
        url = f"{self.base_url}/actions/query/"
        
        try:
            data = {
                'sql': sql_query
            }
            
            response = self.session.post(url, data=data, timeout=15)
            
            print(f"Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Запрос выполнен успешно!")
                return self.parse_query_results(response.text)
            else:
                print(f"❌ Ошибка выполнения запроса: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    def parse_query_results(self, html_content):
        """Парсит результаты SQL-запроса"""
        try:
            # Ищем таблицу с результатами
            table_pattern = r'<table[^>]*>(.*?)</table>'
            table_match = re.search(table_pattern, html_content, re.DOTALL)
            
            if table_match:
                table_html = table_match.group(1)
                
                # Извлекаем заголовки
                headers = []
                header_pattern = r'<th[^>]*>(.*?)</th>'
                for match in re.findall(header_pattern, table_html):
                    headers.append(match.strip())
                
                # Извлекаем строки данных
                rows = []
                row_pattern = r'<tr[^>]*>(.*?)</tr>'
                for row_match in re.findall(row_pattern, table_html):
                    cell_pattern = r'<td[^>]*>(.*?)</td>'
                    cells = []
                    for cell_match in re.findall(cell_pattern, row_match):
                        cells.append(cell_match.strip())
                    if cells:
                        rows.append(cells)
                
                return {
                    'headers': headers,
                    'rows': rows
                }
            else:
                print("❌ Не удалось найти таблицу с результатами")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка парсинга результатов: {e}")
            return None
    
    def check_admin_requests_viewed(self):
        """Проверяет действия admin_requests_viewed"""
        print("🔍 ПРОВЕРКА ДЕЙСТВИЙ admin_requests_viewed")
        print("=" * 50)
        
        sql = """
        SELECT id, user_id, username, name, action, timestamp, details
        FROM actions 
        WHERE action = 'admin_requests_viewed'
        ORDER BY id DESC
        """
        
        results = self.execute_sql_query(sql)
        
        if results and results['rows']:
            print(f"📊 Найдено записей: {len(results['rows'])}")
            print()
            
            for row in results['rows']:
                if len(row) >= 7:
                    id_val, user_id, username, name, action, timestamp, details = row
                    
                    # Проверяем, является ли пользователь админом
                    admin_ids = ['6682555021', '392141189', '239719200', '7494824111', '171507422', '138192985']
                    
                    if user_id in admin_ids:
                        status = "✅ ЛЕГИТИМНЫЙ АДМИН"
                    else:
                        status = "🚨 НЕСАНКЦИОНИРОВАННЫЙ ДОСТУП"
                    
                    print(f"ID: {id_val}")
                    print(f"User ID: {user_id}")
                    print(f"Username: {username}")
                    print(f"Name: {name}")
                    print(f"Action: {action}")
                    print(f"Timestamp: {timestamp}")
                    print(f"Status: {status}")
                    print("-" * 30)
        else:
            print("ℹ️ Действий admin_requests_viewed не найдено")
    
    def check_user_actions(self, user_id):
        """Проверяет действия конкретного пользователя"""
        print(f"🔍 ПРОВЕРКА ДЕЙСТВИЙ ПОЛЬЗОВАТЕЛЯ {user_id}")
        print("=" * 50)
        
        sql = f"""
        SELECT id, user_id, username, name, action, timestamp, details
        FROM actions 
        WHERE user_id = {user_id}
        ORDER BY id DESC
        LIMIT 20
        """
        
        results = self.execute_sql_query(sql)
        
        if results and results['rows']:
            print(f"📊 Найдено записей: {len(results['rows'])}")
            print()
            
            for row in results['rows']:
                if len(row) >= 7:
                    id_val, user_id, username, name, action, timestamp, details = row
                    print(f"ID: {id_val} | Action: {action} | Time: {timestamp}")
        else:
            print("ℹ️ Действий пользователя не найдено")

def main():
    """Основная функция"""
    print("🔍 КЛИЕНТ С АУТЕНТИФИКАЦИЕЙ ДЛЯ РАБОТЫ С БД")
    print("=" * 60)
    
    client = AuthenticatedDBClient()
    
    # Тест подключения
    if client.test_connection():
        print("\n" + "="*50 + "\n")
        
        # Проверка admin_requests_viewed
        client.check_admin_requests_viewed()
        
        print("\n" + "="*50 + "\n")
        
        # Проверка действий пользователя 865377684
        client.check_user_actions(865377684)
    else:
        print("❌ Не удалось подключиться к БД")

if __name__ == "__main__":
    main() 