#!/usr/bin/env python3
"""
Мониторинг безопасности в реальном времени
"""

import requests
import re
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

class SecurityMonitor:
    def __init__(self):
        self.base_url = "https://cardbot-1-kosarevpg.amvera.io"
        self.session = requests.Session()
        
        # ТОЛЬКО ОДИН АДМИНИСТРАТОР
        self.admin_ids = ['6682555021']
        
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
    
    def check_admin_actions(self):
        """Проверяет админские действия"""
        print("🔍 ПРОВЕРКА АДМИНСКИХ ДЕЙСТВИЙ")
        print("=" * 50)
        
        sql = """
        SELECT 
            COUNT(CASE WHEN user_id IN (6682555021) THEN 1 END) as legitimate_actions,
            COUNT(CASE WHEN user_id NOT IN (6682555021) THEN 1 END) as unauthorized_actions
        FROM actions 
        WHERE action LIKE 'admin_%'
        """
        
        results = self.execute_sql_query(sql)
        
        if results and not results.get('error'):
            if results['rows']:
                row = results['rows'][0]
                if len(row) >= 2:
                    legitimate = int(row[0])
                    unauthorized = int(row[1])
                    
                    print(f"✅ Легитимных действий: {legitimate}")
                    print(f"🚨 Несанкционированных действий: {unauthorized}")
                    
                    if unauthorized > 0:
                        print("🚨 ВНИМАНИЕ: Обнаружены несанкционированные админские действия!")
                        
                        # Получаем детали несанкционированных действий
                        sql_details = """
                        SELECT user_id, username, name, action, timestamp
                        FROM actions 
                        WHERE action LIKE 'admin_%' AND user_id NOT IN (6682555021)
                        ORDER BY timestamp DESC
                        LIMIT 10
                        """
                        
                        details_results = self.execute_sql_query(sql_details)
                        
                        if details_results and not details_results.get('error'):
                            if details_results['rows']:
                                print("\n🚨 ПОСЛЕДНИЕ НЕСАНКЦИОНИРОВАННЫЕ ДЕЙСТВИЯ:")
                                for detail_row in details_results['rows']:
                                    if len(detail_row) >= 5:
                                        user_id, username, name, action, timestamp = detail_row
                                        print(f"   User: {user_id} ({name}) | Action: {action} | Time: {timestamp}")
                    else:
                        print("✅ Все админские действия легитимны")
            else:
                print("ℹ️ Админских действий не найдено")
        else:
            print(f"❌ Ошибка выполнения запроса: {results.get('error', 'Неизвестная ошибка')}")
    
    def check_suspicious_users(self):
        """Проверяет подозрительных пользователей"""
        print("\n🔍 ПРОВЕРКА ПОДОЗРИТЕЛЬНЫХ ПОЛЬЗОВАТЕЛЕЙ")
        print("=" * 50)
        
        sql = """
        SELECT user_id, username, name, COUNT(*) as admin_action_count
        FROM actions 
        WHERE action LIKE 'admin_%' AND user_id NOT IN (6682555021)
        GROUP BY user_id, username, name
        ORDER BY admin_action_count DESC
        """
        
        results = self.execute_sql_query(sql)
        
        if results and not results.get('error'):
            if results['rows']:
                print(f"🚨 Найдено подозрительных пользователей: {len(results['rows'])}")
                print()
                
                for row in results['rows']:
                    if len(row) >= 4:
                        user_id, username, name, action_count = row
                        print(f"🚨 User ID: {user_id}")
                        print(f"   Username: {username}")
                        print(f"   Name: {name}")
                        print(f"   Admin actions: {action_count}")
                        print("-" * 30)
            else:
                print("✅ Подозрительных пользователей не найдено")
        else:
            print(f"❌ Ошибка выполнения запроса: {results.get('error', 'Неизвестная ошибка')}")
    
    def run_security_check(self):
        """Запускает полную проверку безопасности"""
        print("🔍 МОНИТОР БЕЗОПАСНОСТИ В РЕАЛЬНОМ ВРЕМЕНИ")
        print("=" * 60)
        print(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Проверка админских действий
        self.check_admin_actions()
        
        # Проверка подозрительных пользователей
        self.check_suspicious_users()
        
        print("\n" + "="*60)
        print("📋 РЕКОМЕНДАЦИИ:")
        print("1. Если обнаружены несанкционированные действия - немедленно заблокировать доступ")
        print("2. Мониторить активность подозрительных пользователей")
        print("3. Регулярно проверять логи безопасности")

def main():
    """Основная функция"""
    monitor = SecurityMonitor()
    monitor.run_security_check()

if __name__ == "__main__":
    main() 