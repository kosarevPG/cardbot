#!/usr/bin/env python3
"""
Расчет DAU из таблицы user_scenarios с московским временем
"""
import requests
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

class DAUCalculator:
    def __init__(self):
        self.base_url = "https://cardbot-1-kosarevpg.amvera.io"
        self.session = requests.Session()
        self.username = "admin"
        self.password = "root"
        self.session.auth = (self.username, self.password)
        
    def execute_sql_query(self, sql_query: str) -> Optional[Dict[str, Any]]:
        """Выполняет SQL-запрос"""
        url = f"{self.base_url}/actions/query/"
        try:
            data = {'sql': sql_query}
            response = self.session.post(url, data=data, timeout=30)
            if response.status_code == 200:
                return self.parse_query_results(response.text)
            else:
                print(f"❌ HTTP {response.status_code}")
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
            
            if 'error' in html_content.lower() or 'exception' in html_content.lower():
                error_match = re.search(r'<div[^>]*class="[^"]*error[^"]*"[^>]*>(.*?)</div>', html_content, re.IGNORECASE | re.DOTALL)
                if error_match:
                    result['error'] = error_match.group(1).strip()
                    return result
            
            table_pattern = r'<table[^>]*class="[^"]*table[^"]*"[^>]*>(.*?)</table>'
            table_match = re.search(table_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            if table_match:
                table_html = table_match.group(1)
                
                # Парсим заголовки
                headers = []
                header_pattern = r'<th[^>]*>(.*?)</th>'
                for match in re.findall(header_pattern, table_html, re.DOTALL):
                    header_text = re.sub(r'<[^>]+>', '', match).strip()
                    headers.append(header_text)
                result['headers'] = headers
                
                # Парсим строки
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
    
    def calculate_dau_today(self):
        """DAU за сегодня (30 июля)"""
        print("🔍 DAU ЗА СЕГОДНЯ (30 июля)")
        print("=" * 40)
        
        sql = """
        SELECT COUNT(DISTINCT user_id) as dau_today
        FROM user_scenarios 
        WHERE DATE(started_at, '+3 hours') = '2025-07-30'
        AND user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985, 999999999)
        """
        
        result = self.execute_sql_query(sql)
        if result and not result.get('error'):
            if result['rows']:
                dau = result['rows'][0][0]
                print(f"📊 DAU за сегодня: {dau}")
                return int(dau)
            else:
                print("❌ Нет данных за сегодня")
                return 0
        else:
            print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            return 0
    
    def calculate_dau_yesterday(self):
        """DAU за вчера (29 июля)"""
        print("\n🔍 DAU ЗА ВЧЕРА (29 июля)")
        print("=" * 40)
        
        sql = """
        SELECT COUNT(DISTINCT user_id) as dau_yesterday
        FROM user_scenarios 
        WHERE DATE(started_at, '+3 hours') = '2025-07-29'
        AND user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985, 999999999)
        """
        
        result = self.execute_sql_query(sql)
        if result and not result.get('error'):
            if result['rows']:
                dau = result['rows'][0][0]
                print(f"📊 DAU за вчера: {dau}")
                return int(dau)
            else:
                print("❌ Нет данных за вчера")
                return 0
        else:
            print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            return 0
    
    def calculate_dau_7_days(self):
        """Средний DAU за 7 дней"""
        print("\n🔍 СРЕДНИЙ DAU ЗА 7 ДНЕЙ")
        print("=" * 40)
        
        sql = """
        SELECT 
            DATE(started_at, '+3 hours') as date,
            COUNT(DISTINCT user_id) as daily_dau
        FROM user_scenarios 
        WHERE DATE(started_at, '+3 hours') >= '2025-07-24'
        AND user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985, 999999999)
        GROUP BY DATE(started_at, '+3 hours')
        ORDER BY date DESC
        """
        
        result = self.execute_sql_query(sql)
        if result and not result.get('error'):
            if result['rows']:
                print("📋 DAU по дням:")
                total_dau = 0
                days_count = 0
                for row in result['rows']:
                    date, dau = row
                    print(f"  • {date}: {dau}")
                    total_dau += int(dau)
                    days_count += 1
                
                avg_dau = total_dau / days_count if days_count > 0 else 0
                print(f"\n📊 Средний DAU за 7 дней: {avg_dau:.1f}")
                return avg_dau
            else:
                print("❌ Нет данных за 7 дней")
                return 0
        else:
            print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            return 0
    
    def calculate_dau_30_days(self):
        """Средний DAU за 30 дней"""
        print("\n🔍 СРЕДНИЙ DAU ЗА 30 ДНЕЙ")
        print("=" * 40)
        
        sql = """
        SELECT 
            DATE(started_at, '+3 hours') as date,
            COUNT(DISTINCT user_id) as daily_dau
        FROM user_scenarios 
        WHERE DATE(started_at, '+3 hours') >= '2025-07-01'
        AND user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985, 999999999)
        GROUP BY DATE(started_at, '+3 hours')
        ORDER BY date DESC
        """
        
        result = self.execute_sql_query(sql)
        if result and not result.get('error'):
            if result['rows']:
                print("📋 DAU по дням (первые 10):")
                total_dau = 0
                days_count = 0
                for i, row in enumerate(result['rows']):
                    date, dau = row
                    if i < 10:  # Показываем только первые 10 дней
                        print(f"  • {date}: {dau}")
                    total_dau += int(dau)
                    days_count += 1
                
                if days_count > 10:
                    print(f"  • ... и еще {days_count - 10} дней")
                
                avg_dau = total_dau / days_count if days_count > 0 else 0
                print(f"\n📊 Средний DAU за 30 дней: {avg_dau:.1f}")
                print(f"📊 Всего дней с данными: {days_count}")
                return avg_dau
            else:
                print("❌ Нет данных за 30 дней")
                return 0
        else:
            print(f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            return 0
    
    def run_full_calculation(self):
        """Запускает полный расчет DAU"""
        print("🔍 РАСЧЕТ DAU ИЗ USER_SCENARIOS")
        print("=" * 60)
        print(f"Время расчета: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Московское время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        today_dau = self.calculate_dau_today()
        yesterday_dau = self.calculate_dau_yesterday()
        avg_7_days = self.calculate_dau_7_days()
        avg_30_days = self.calculate_dau_30_days()
        
        print("\n" + "=" * 60)
        print("📋 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
        print(f"• Сегодня (30 июля): {today_dau}")
        print(f"• Вчера (29 июля): {yesterday_dau}")
        print(f"• Среднее за 7 дней: {avg_7_days:.1f}")
        print(f"• Среднее за 30 дней: {avg_30_days:.1f}")
        print("=" * 60)

def main():
    """Основная функция"""
    calculator = DAUCalculator()
    calculator.run_full_calculation()

if __name__ == "__main__":
    main() 