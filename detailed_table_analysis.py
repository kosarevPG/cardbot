#!/usr/bin/env python3
"""
Детальный анализ всех таблиц БД
"""

import requests
import re
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

class DetailedTableAnalyzer:
    def __init__(self):
        self.base_url = "https://cardbot-1-kosarevpg.amvera.io"
        self.session = requests.Session()
        
        # Список всех таблиц
        self.tables = [
            'actions',
            'card_feedback', 
            'daily_active_users',
            'evening_reflections',
            'feedback',
            'mailing_logs',
            'mailings',
            'posts',
            'referrals',
            'resource_states',
            'scenario_logs',
            'sqlite_sequence',
            'user_cards',
            'user_profiles',
            'user_recharge_methods',
            'user_requests',
            'user_scenarios',
            'users'
        ]
        
    def execute_sql_query(self, table_name: str, sql_query: str) -> Optional[Dict[str, Any]]:
        """Выполняет SQL-запрос для конкретной таблицы"""
        url = f"{self.base_url}/{table_name}/query/"
        
        try:
            data = {'sql': sql_query}
            response = self.session.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                return self.parse_query_results(response.text)
            else:
                print(f"❌ HTTP {response.status_code} для таблицы {table_name}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка для таблицы {table_name}: {e}")
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
    
    def analyze_table(self, table_name: str):
        """Анализирует конкретную таблицу"""
        print(f"\n🔍 АНАЛИЗ ТАБЛИЦЫ: {table_name}")
        print("=" * 50)
        
        # 1. Подсчет записей
        count_sql = f"SELECT COUNT(*) as total FROM {table_name}"
        count_result = self.execute_sql_query(table_name, count_sql)
        
        if count_result and not count_result.get('error'):
            if count_result['rows']:
                total_count = count_result['rows'][0][0]
                print(f"📊 Всего записей: {total_count}")
                
                # 2. Получение структуры таблицы
                structure_sql = f"PRAGMA table_info({table_name})"
                structure_result = self.execute_sql_query(table_name, structure_sql)
                
                if structure_result and not structure_result.get('error'):
                    if structure_result['rows']:
                        print(f"📋 Структура таблицы:")
                        for row in structure_result['rows']:
                            if len(row) >= 6:
                                cid, name, type_info, not_null, default_val, pk = row
                                print(f"  • {name} ({type_info})")
                
                # 3. Последние записи
                if int(total_count) > 0:
                    recent_sql = f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 3"
                    recent_result = self.execute_sql_query(table_name, recent_sql)
                    
                    if recent_result and not recent_result.get('error'):
                        if recent_result['rows']:
                            print(f"📋 Последние записи:")
                            for i, row in enumerate(recent_result['rows'], 1):
                                print(f"  {i}. {row}")
                
                return {
                    'table': table_name,
                    'total_records': total_count,
                    'accessible': True,
                    'error': None
                }
            else:
                print(f"❌ Нет данных в таблице {table_name}")
                return {
                    'table': table_name,
                    'total_records': 0,
                    'accessible': False,
                    'error': 'Нет данных'
                }
        else:
            error = count_result.get('error', 'Неизвестная ошибка') if count_result else 'Нет доступа'
            print(f"❌ Ошибка доступа к таблице {table_name}: {error}")
            return {
                'table': table_name,
                'total_records': 0,
                'accessible': False,
                'error': error
            }
    
    def analyze_all_tables(self):
        """Анализирует все таблицы"""
        print("🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ВСЕХ ТАБЛИЦ БД")
        print("=" * 60)
        print(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        results = []
        
        for table in self.tables:
            result = self.analyze_table(table)
            results.append(result)
        
        # Итоговая статистика
        print("\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        print("=" * 60)
        
        accessible_tables = [r for r in results if r['accessible']]
        inaccessible_tables = [r for r in results if not r['accessible']]
        
        total_records = sum(int(r['total_records']) for r in accessible_tables)
        
        print(f"✅ Доступных таблиц: {len(accessible_tables)}")
        print(f"❌ Недоступных таблиц: {len(inaccessible_tables)}")
        print(f"📈 Процент доступности: {(len(accessible_tables)/(len(accessible_tables)+len(inaccessible_tables))*100):.1f}%")
        print(f"📊 Общее количество записей: {total_records}")
        
        if accessible_tables:
            print(f"\n✅ ДОСТУПНЫЕ ТАБЛИЦЫ:")
            for result in accessible_tables:
                print(f"  • {result['table']}: {result['total_records']} записей")
        
        if inaccessible_tables:
            print(f"\n❌ НЕДОСТУПНЫЕ ТАБЛИЦЫ:")
            for result in inaccessible_tables:
                print(f"  • {result['table']}: {result['error']}")
        
        return results

def main():
    """Основная функция"""
    analyzer = DetailedTableAnalyzer()
    analyzer.analyze_all_tables()

if __name__ == "__main__":
    main() 