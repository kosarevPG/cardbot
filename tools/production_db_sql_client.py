#!/usr/bin/env python3
"""
Клиент для выполнения SQL-запросов к продакшн БД
"""

import requests
import re
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

class ProductionSQLClient:
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
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                print("✅ Подключение к продакшн БД успешно!")
                return True
            else:
                print(f"❌ Ошибка подключения: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def execute_sql_query(self, sql_query: str) -> Optional[Dict[str, Any]]:
        """Выполняет SQL-запрос"""
        url = f"{self.base_url}/actions/query/"
        
        try:
            data = {'sql': sql_query}
            response = self.session.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                return self.parse_query_results(response.text)
            else:
                print(f"❌ Ошибка выполнения запроса: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    def parse_query_results(self, html_content: str) -> Dict[str, Any]:
        """Парсит результаты SQL-запроса из HTML"""
        try:
            result = {
                'headers': [],
                'rows': [],
                'total_rows': 0,
                'error': None
            }
            
            # Проверяем на ошибки SQL
            if 'error' in html_content.lower() or 'exception' in html_content.lower():
                error_match = re.search(r'<div[^>]*class="[^"]*error[^"]*"[^>]*>(.*?)</div>', html_content, re.IGNORECASE | re.DOTALL)
                if error_match:
                    result['error'] = error_match.group(1).strip()
                    return result
            
            # Ищем таблицу с результатами
            table_pattern = r'<table[^>]*class="[^"]*table[^"]*"[^>]*>(.*?)</table>'
            table_match = re.search(table_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            if table_match:
                table_html = table_match.group(1)
                
                # Извлекаем заголовки
                headers = []
                header_pattern = r'<th[^>]*>(.*?)</th>'
                for match in re.findall(header_pattern, table_html, re.DOTALL):
                    header_text = re.sub(r'<[^>]+>', '', match).strip()
                    headers.append(header_text)
                result['headers'] = headers
                
                # Извлекаем строки данных
                rows = []
                row_pattern = r'<tr[^>]*>(.*?)</tr>'
                for row_match in re.findall(row_pattern, table_html, re.DOTALL):
                    cell_pattern = r'<td[^>]*>(.*?)</td>'
                    cells = []
                    for cell_match in re.findall(cell_pattern, row_match, re.DOTALL):
                        cell_text = re.sub(r'<[^>]+>', '', cell_match).strip()
                        cells.append(cell_text)
                    if cells and len(cells) == len(headers):
                        rows.append(cells)
                result['rows'] = rows
                result['total_rows'] = len(rows)
            
            return result
            
        except Exception as e:
            return {'error': str(e)}
    
    def check_total_actions(self):
        """Проверяет общее количество действий"""
        print("\n📊 ПРОВЕРКА ОБЩЕЙ СТАТИСТИКИ")
        print("=" * 50)
        
        sql = "SELECT COUNT(*) as total_actions FROM actions"
        
        results = self.execute_sql_query(sql)
        
        if results and not results.get('error'):
            if results['rows']:
                total_actions = results['rows'][0][0]
                print(f"📊 Всего записей в таблице actions: {total_actions}")
                return int(total_actions)
            else:
                print("ℹ️ Записей не найдено")
                return 0
        else:
            print(f"❌ Ошибка выполнения запроса: {results.get('error', 'Неизвестная ошибка')}")
            return 0
    
    def check_admin_actions(self):
        """Проверяет админские действия"""
        print("\n🔍 ПРОВЕРКА АДМИНСКИХ ДЕЙСТВИЙ")
        print("=" * 50)
        
        # ТОЛЬКО ОДИН АДМИНИСТРАТОР
        admin_ids = ['6682555021']
        
        sql = """
        SELECT user_id, username, name, action, timestamp, COUNT(*) as action_count
        FROM actions 
        WHERE action LIKE 'admin_%'
        GROUP BY user_id, username, name, action, timestamp
        ORDER BY timestamp DESC
        LIMIT 20
        """
        
        results = self.execute_sql_query(sql)
        
        if results and not results.get('error'):
            if results['rows']:
                print(f"📊 Найдено админских действий: {len(results['rows'])}")
                print()
                
                for row in results['rows']:
                    if len(row) >= 6:
                        user_id, username, name, action, timestamp, action_count = row
                        
                        if user_id in admin_ids:
                            status = "✅ ЛЕГИТИМНЫЙ АДМИН"
                        else:
                            status = "🚨 НЕСАНКЦИОНИРОВАННЫЙ ДОСТУП"
                        
                        print(f"User: {user_id} ({name}) | Action: {action} | Status: {status}")
                        print(f"Time: {timestamp} | Count: {action_count}")
                        print("-" * 50)
            else:
                print("ℹ️ Админских действий не найдено")
        else:
            print(f"❌ Ошибка выполнения запроса: {results.get('error', 'Неизвестная ошибка')}")
    
    def check_specific_user(self, user_id: str):
        """Проверяет действия конкретного пользователя"""
        print(f"\n👤 ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ {user_id}")
        print("=" * 50)
        
        sql = f"""
        SELECT action, timestamp, details
        FROM actions 
        WHERE user_id = {user_id}
        ORDER BY timestamp DESC
        LIMIT 10
        """
        
        results = self.execute_sql_query(sql)
        
        if results and not results.get('error'):
            if results['rows']:
                print(f"📊 Найдено действий пользователя: {len(results['rows'])}")
                print()
                
                for row in results['rows']:
                    if len(row) >= 3:
                        action, timestamp, details = row
                        print(f"Action: {action}")
                        print(f"Time: {timestamp}")
                        if details and details != 'None':
                            print(f"Details: {details[:100]}...")
                        print("-" * 30)
            else:
                print("ℹ️ Действий пользователя не найдено")
        else:
            print(f"❌ Ошибка выполнения запроса: {results.get('error', 'Неизвестная ошибка')}")
    
    def run_full_analysis(self):
        """Запускает полный анализ"""
        print("🔍 АНАЛИЗ PRODUCTION БД")
        print("=" * 60)
        print(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Тест подключения
        if not self.test_connection():
            print("❌ Не удалось подключиться к продакшн БД")
            return
        
        # Проверка общей статистики
        total_actions = self.check_total_actions()
        
        # Проверка админских действий
        self.check_admin_actions()
        
        # Проверка подозрительных пользователей
        print("\n🔍 ПРОВЕРКА ПОДОЗРИТЕЛЬНЫХ ПОЛЬЗОВАТЕЛЕЙ")
        print("=" * 50)
        
        suspicious_users = ['865377684', '1159751971', '1853568101']
        
        for user_id in suspicious_users:
            self.check_specific_user(user_id)
        
        print("\n" + "="*60)
        print("📋 ВЫВОДЫ:")
        print(f"• Всего действий в БД: {total_actions}")
        print("• Проверьте все админские действия на легитимность")
        print("• Мониторьте активность подозрительных пользователей")

def main():
    """Основная функция"""
    client = ProductionSQLClient()
    client.run_full_analysis()

if __name__ == "__main__":
    main() 