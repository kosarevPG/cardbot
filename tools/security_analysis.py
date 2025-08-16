#!/usr/bin/env python3
"""
Глубокий анализ безопасности продакшн БД
"""

import requests
import re
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

class SecurityAnalyzer:
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
    
    def analyze_admin_actions(self):
        """Анализирует все админские действия"""
        print("🔍 АНАЛИЗ АДМИНСКИХ ДЕЙСТВИЙ")
        print("=" * 50)
        
        sql = """
        SELECT id, user_id, username, name, action, timestamp, details
        FROM actions 
        WHERE action LIKE 'admin_%'
        ORDER BY id DESC
        """
        
        results = self.execute_sql_query(sql)
        
        if results and not results.get('error'):
            if results['rows']:
                print(f"📊 Найдено админских действий: {len(results['rows'])}")
                print()
                
                unauthorized_count = 0
                authorized_count = 0
                
                for row in results['rows']:
                    if len(row) >= 7:
                        id_val, user_id, username, name, action, timestamp, details = row
                        
                        if user_id in self.admin_ids:
                            status = "✅ ЛЕГИТИМНЫЙ АДМИН"
                            authorized_count += 1
                        else:
                            status = "🚨 НЕСАНКЦИОНИРОВАННЫЙ ДОСТУП"
                            unauthorized_count += 1
                        
                        print(f"ID: {id_val} | User: {user_id} | Action: {action} | Status: {status}")
                
                print(f"\n📊 СТАТИСТИКА:")
                print(f"✅ Легитимных действий: {authorized_count}")
                print(f"🚨 Несанкционированных действий: {unauthorized_count}")
                print(f"📈 Процент несанкционированных: {(unauthorized_count/(authorized_count+unauthorized_count)*100):.1f}%")
            else:
                print("ℹ️ Админских действий не найдено")
        else:
            print(f"❌ Ошибка выполнения запроса: {results.get('error', 'Неизвестная ошибка')}")
    
    def analyze_suspicious_users(self):
        """Анализирует подозрительных пользователей"""
        print("\n🔍 АНАЛИЗ ПОДОЗРИТЕЛЬНЫХ ПОЛЬЗОВАТЕЛЕЙ")
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
                print(f"📊 Найдено подозрительных пользователей: {len(results['rows'])}")
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
    
    def analyze_user_requests_table(self):
        """Анализирует таблицу user_requests"""
        print("\n🔍 АНАЛИЗ ТАБЛИЦЫ user_requests")
        print("=" * 50)
        
        # Проверяем существование таблицы
        sql = """
        SELECT COUNT(*) as total_requests
        FROM user_requests
        """
        
        results = self.execute_sql_query(sql)
        
        if results and not results.get('error'):
            if results['rows']:
                total_requests = results['rows'][0][0]
                print(f"📊 Всего запросов пользователей: {total_requests}")
                
                # Получаем последние запросы
                sql_recent = """
                SELECT user_id, request_text, created_at
                FROM user_requests
                ORDER BY created_at DESC
                LIMIT 10
                """
                
                recent_results = self.execute_sql_query(sql_recent)
                
                if recent_results and not recent_results.get('error'):
                    if recent_results['rows']:
                        print(f"\n📋 Последние запросы:")
                        for row in recent_results['rows']:
                            if len(row) >= 3:
                                user_id, request_text, created_at = row
                                print(f"User: {user_id} | Time: {created_at}")
                                print(f"Request: {request_text[:100]}...")
                                print("-" * 30)
            else:
                print("ℹ️ Таблица user_requests пуста или не существует")
        else:
            print(f"❌ Ошибка выполнения запроса: {results.get('error', 'Неизвестная ошибка')}")
    
    def analyze_table_structure(self):
        """Анализирует структуру всех таблиц"""
        print("\n🔍 АНАЛИЗ СТРУКТУРЫ ТАБЛИЦ")
        print("=" * 50)
        
        tables = ['actions', 'users', 'user_requests', 'user_cards', 'feedback', 'user_profiles']
        
        for table in tables:
            sql = f"""
            SELECT COUNT(*) as total_rows
            FROM {table}
            """
            
            results = self.execute_sql_query(sql)
            
            if results and not results.get('error'):
                if results['rows']:
                    total_rows = results['rows'][0][0]
                    print(f"📊 Таблица {table}: {total_rows} записей")
                else:
                    print(f"📊 Таблица {table}: 0 записей")
            else:
                print(f"❌ Таблица {table}: ошибка доступа")
    
    def generate_security_report(self):
        """Генерирует отчет по безопасности"""
        print("\n🔍 ОТЧЕТ ПО БЕЗОПАСНОСТИ")
        print("=" * 60)
        print(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Анализ админских действий
        self.analyze_admin_actions()
        
        # Анализ подозрительных пользователей
        self.analyze_suspicious_users()
        
        # Анализ таблицы user_requests
        self.analyze_user_requests_table()
        
        # Анализ структуры таблиц
        self.analyze_table_structure()
        
        print("\n" + "="*60)
        print("📋 РЕКОМЕНДАЦИИ ПО БЕЗОПАСНОСТИ:")
        print("1. Немедленно заблокировать доступ к админ-функциям")
        print("2. Добавить проверку прав доступа")
        print("3. Логировать все попытки несанкционированного доступа")
        print("4. Рассмотреть временную блокировку подозрительных пользователей")
        print("5. Регулярно мониторить активность в БД")

def main():
    """Основная функция"""
    print("🔍 АНАЛИЗАТОР БЕЗОПАСНОСТИ PRODUCTION БД")
    print("=" * 60)
    
    analyzer = SecurityAnalyzer()
    analyzer.generate_security_report()

if __name__ == "__main__":
    main() 