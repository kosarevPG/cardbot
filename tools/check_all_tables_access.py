#!/usr/bin/env python3
"""
Проверка доступа ко всем таблицам БД
"""

import requests
import re
import json
from datetime import datetime
from typing import Optional, Dict, List, Any

class TableAccessChecker:
    def __init__(self):
        self.base_url = "https://cardbot-1-kosarevpg.amvera.io"
        self.session = requests.Session()
        
        # Список всех таблиц из скриншота
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
        
    def check_table_access(self, table_name: str) -> bool:
        """Проверяет доступ к конкретной таблице"""
        url = f"{self.base_url}/{table_name}/query/"
        
        try:
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при проверке таблицы {table_name}: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о таблице"""
        url = f"{self.base_url}/{table_name}/query/"
        
        try:
            # Пробуем выполнить простой запрос
            sql_query = f"SELECT COUNT(*) as total FROM {table_name}"
            data = {'sql': sql_query}
            
            response = self.session.post(url, data=data, timeout=30)
            
            if response.status_code == 200:
                # Парсим результат
                result = self.parse_query_results(response.text)
                if result and not result.get('error'):
                    return {
                        'accessible': True,
                        'total_rows': result.get('total_rows', 0),
                        'error': None
                    }
                else:
                    return {
                        'accessible': False,
                        'total_rows': 0,
                        'error': result.get('error', 'Неизвестная ошибка')
                    }
            else:
                return {
                    'accessible': False,
                    'total_rows': 0,
                    'error': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                'accessible': False,
                'total_rows': 0,
                'error': str(e)
            }
    
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
    
    def check_all_tables(self):
        """Проверяет доступ ко всем таблицам"""
        print("🔍 ПРОВЕРКА ДОСТУПА КО ВСЕМ ТАБЛИЦАМ")
        print("=" * 60)
        print(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        accessible_tables = []
        inaccessible_tables = []
        
        for table in self.tables:
            print(f"🔍 Проверяю таблицу: {table}")
            
            info = self.get_table_info(table)
            
            if info and info['accessible']:
                print(f"✅ {table}: {info['total_rows']} записей")
                accessible_tables.append((table, info['total_rows']))
            else:
                error = info.get('error', 'Неизвестная ошибка') if info else 'Нет доступа'
                print(f"❌ {table}: {error}")
                inaccessible_tables.append((table, error))
            
            print("-" * 40)
        
        # Итоговая статистика
        print("\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        print("=" * 60)
        print(f"✅ Доступных таблиц: {len(accessible_tables)}")
        print(f"❌ Недоступных таблиц: {len(inaccessible_tables)}")
        print(f"📈 Процент доступности: {(len(accessible_tables)/(len(accessible_tables)+len(inaccessible_tables))*100):.1f}%")
        
        if accessible_tables:
            print(f"\n✅ ДОСТУПНЫЕ ТАБЛИЦЫ:")
            for table, count in accessible_tables:
                print(f"  • {table}: {count} записей")
        
        if inaccessible_tables:
            print(f"\n❌ НЕДОСТУПНЫЕ ТАБЛИЦЫ:")
            for table, error in inaccessible_tables:
                print(f"  • {table}: {error}")
        
        return accessible_tables, inaccessible_tables

def main():
    """Основная функция"""
    checker = TableAccessChecker()
    checker.check_all_tables()

if __name__ == "__main__":
    main() 