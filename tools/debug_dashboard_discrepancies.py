#!/usr/bin/env python3
"""
Детальный анализ расхождений в статистике дашборда
"""

import requests
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

class DashboardDiscrepancyAnalyzer:
    def __init__(self):
        self.base_url = "https://cardbot-1-kosarevpg.amvera.io"
        self.session = requests.Session()
        
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
    
    def analyze_card_of_day_discrepancy(self):
        """Анализирует расхождения в статистике карты дня"""
        print("🔍 АНАЛИЗ РАСХОЖДЕНИЙ В СТАТИСТИКЕ КАРТЫ ДНЯ")
        print("=" * 60)
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 1. Подсчет через user_scenarios (как в коде)
        sql_user_scenarios = f"""
        SELECT COUNT(*) as total_starts
        FROM user_scenarios 
        WHERE scenario = 'card_of_day' 
        AND started_at >= datetime('now', '-1 days')
        """
        
        result_user_scenarios = self.execute_sql_query('user_scenarios', sql_user_scenarios)
        
        if result_user_scenarios and not result_user_scenarios.get('error'):
            if result_user_scenarios['rows']:
                total_user_scenarios = result_user_scenarios['rows'][0][0]
                print(f"📊 Запусков через user_scenarios: {total_user_scenarios}")
        
        # 2. Подсчет через scenario_logs
        sql_scenario_logs = f"""
        SELECT COUNT(DISTINCT user_id) as total_starts
        FROM scenario_logs 
        WHERE scenario = 'card_of_day' 
        AND step = 'started'
        AND timestamp >= datetime('now', '-1 days')
        """
        
        result_scenario_logs = self.execute_sql_query('scenario_logs', sql_scenario_logs)
        
        if result_scenario_logs and not result_scenario_logs.get('error'):
            if result_scenario_logs['rows']:
                total_scenario_logs = result_scenario_logs['rows'][0][0]
                print(f"📊 Запусков через scenario_logs: {total_scenario_logs}")
        
        # 3. Детальный анализ user_scenarios
        sql_detailed_user_scenarios = f"""
        SELECT 
            user_id,
            started_at,
            status,
            steps_count
        FROM user_scenarios 
        WHERE scenario = 'card_of_day' 
        AND started_at >= datetime('now', '-1 days')
        ORDER BY started_at DESC
        """
        
        result_detailed = self.execute_sql_query('user_scenarios', sql_detailed_user_scenarios)
        
        if result_detailed and not result_detailed.get('error'):
            if result_detailed['rows']:
                print(f"\n📋 Детальные данные user_scenarios:")
                for row in result_detailed['rows']:
                    user_id, started_at, status, steps_count = row
                    print(f"  • User {user_id}: {started_at} - {status} ({steps_count} шагов)")
        
        # 4. Детальный анализ scenario_logs
        sql_detailed_logs = f"""
        SELECT 
            user_id,
            timestamp,
            step
        FROM scenario_logs 
        WHERE scenario = 'card_of_day' 
        AND step = 'started'
        AND timestamp >= datetime('now', '-1 days')
        ORDER BY timestamp DESC
        """
        
        result_detailed_logs = self.execute_sql_query('scenario_logs', sql_detailed_logs)
        
        if result_detailed_logs and not result_detailed_logs.get('error'):
            if result_detailed_logs['rows']:
                print(f"\n📋 Детальные данные scenario_logs:")
                for row in result_detailed_logs['rows']:
                    user_id, timestamp, step = row
                    print(f"  • User {user_id}: {timestamp} - {step}")
        
        return result_user_scenarios, result_scenario_logs, result_detailed, result_detailed_logs
    
    def analyze_evening_reflection_discrepancy(self):
        """Анализирует расхождения в статистике вечерней рефлексии"""
        print("\n🔍 АНАЛИЗ РАСХОЖДЕНИЙ В СТАТИСТИКЕ ВЕЧЕРНЕЙ РЕФЛЕКСИИ")
        print("=" * 60)
        
        # 1. Подсчет через user_scenarios
        sql_user_scenarios = f"""
        SELECT COUNT(*) as total_starts
        FROM user_scenarios 
        WHERE scenario = 'evening_reflection' 
        AND started_at >= datetime('now', '-1 days')
        """
        
        result_user_scenarios = self.execute_sql_query('user_scenarios', sql_user_scenarios)
        
        if result_user_scenarios and not result_user_scenarios.get('error'):
            if result_user_scenarios['rows']:
                total_user_scenarios = result_user_scenarios['rows'][0][0]
                print(f"📊 Запусков через user_scenarios: {total_user_scenarios}")
        
        # 2. Подсчет через scenario_logs
        sql_scenario_logs = f"""
        SELECT COUNT(DISTINCT user_id) as total_starts
        FROM scenario_logs 
        WHERE scenario = 'evening_reflection' 
        AND step = 'started'
        AND timestamp >= datetime('now', '-1 days')
        """
        
        result_scenario_logs = self.execute_sql_query('scenario_logs', sql_scenario_logs)
        
        if result_scenario_logs and not result_scenario_logs.get('error'):
            if result_scenario_logs['rows']:
                total_scenario_logs = result_scenario_logs['rows'][0][0]
                print(f"📊 Запусков через scenario_logs: {total_scenario_logs}")
        
        # 3. Детальный анализ
        sql_detailed = f"""
        SELECT 
            user_id,
            started_at,
            status,
            steps_count
        FROM user_scenarios 
        WHERE scenario = 'evening_reflection' 
        AND started_at >= datetime('now', '-1 days')
        ORDER BY started_at DESC
        """
        
        result_detailed = self.execute_sql_query('user_scenarios', sql_detailed)
        
        if result_detailed and not result_detailed.get('error'):
            if result_detailed['rows']:
                print(f"\n📋 Детальные данные evening_reflection:")
                for row in result_detailed['rows']:
                    user_id, started_at, status, steps_count = row
                    print(f"  • User {user_id}: {started_at} - {status} ({steps_count} шагов)")
        
        return result_user_scenarios, result_scenario_logs, result_detailed
    
    def analyze_timezone_issues(self):
        """Анализирует проблемы с часовыми поясами"""
        print("\n🔍 АНАЛИЗ ПРОБЛЕМ С ЧАСОВЫМИ ПОЯСАМИ")
        print("=" * 50)
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Без часового пояса
        sql_no_timezone = f"""
        SELECT COUNT(*) as count
        FROM user_scenarios 
        WHERE scenario = 'card_of_day' 
        AND DATE(started_at) = '{today}'
        """
        
        result_no_timezone = self.execute_sql_query('user_scenarios', sql_no_timezone)
        
        if result_no_timezone and not result_no_timezone.get('error'):
            if result_no_timezone['rows']:
                count_no_timezone = result_no_timezone['rows'][0][0]
                print(f"📊 Без часового пояса: {count_no_timezone}")
        
        # С московским временем (+3 часа)
        sql_moscow_time = f"""
        SELECT COUNT(*) as count
        FROM user_scenarios 
        WHERE scenario = 'card_of_day' 
        AND DATE(started_at, '+3 hours') = '{today}'
        """
        
        result_moscow_time = self.execute_sql_query('user_scenarios', sql_moscow_time)
        
        if result_moscow_time and not result_moscow_time.get('error'):
            if result_moscow_time['rows']:
                count_moscow_time = result_moscow_time['rows'][0][0]
                print(f"📊 С московским временем (+3): {count_moscow_time}")
        
        # С UTC
        sql_utc_time = f"""
        SELECT COUNT(*) as count
        FROM user_scenarios 
        WHERE scenario = 'card_of_day' 
        AND DATE(started_at, '-3 hours') = '{today}'
        """
        
        result_utc_time = self.execute_sql_query('user_scenarios', sql_utc_time)
        
        if result_utc_time and not result_utc_time.get('error'):
            if result_utc_time['rows']:
                count_utc_time = result_utc_time['rows'][0][0]
                print(f"📊 С UTC (-3): {count_utc_time}")
        
        return result_no_timezone, result_moscow_time, result_utc_time
    
    def analyze_excluded_users(self):
        """Анализирует влияние исключенных пользователей"""
        print("\n🔍 АНАЛИЗ ИСКЛЮЧЕННЫХ ПОЛЬЗОВАТЕЛЕЙ")
        print("=" * 50)
        
        # Получаем всех пользователей
        sql_all_users = """
        SELECT COUNT(DISTINCT user_id) as total_users
        FROM user_scenarios 
        WHERE scenario = 'card_of_day' 
        AND started_at >= datetime('now', '-1 days')
        """
        
        result_all_users = self.execute_sql_query('user_scenarios', sql_all_users)
        
        if result_all_users and not result_all_users.get('error'):
            if result_all_users['rows']:
                total_users = result_all_users['rows'][0][0]
                print(f"📊 Всего пользователей: {total_users}")
        
        # Проверяем конкретных пользователей
        sql_user_details = """
        SELECT 
            user_id,
            COUNT(*) as sessions
        FROM user_scenarios 
        WHERE scenario = 'card_of_day' 
        AND started_at >= datetime('now', '-1 days')
        GROUP BY user_id
        ORDER BY sessions DESC
        """
        
        result_user_details = self.execute_sql_query('user_scenarios', sql_user_details)
        
        if result_user_details and not result_user_details.get('error'):
            if result_user_details['rows']:
                print(f"\n📋 Пользователи по количеству сессий:")
                for row in result_user_details['rows']:
                    user_id, sessions = row
                    print(f"  • User {user_id}: {sessions} сессий")
        
        return result_all_users, result_user_details
    
    def run_full_analysis(self):
        """Запускает полный анализ расхождений"""
        print("🔍 ДЕТАЛЬНЫЙ АНАЛИЗ РАСХОЖДЕНИЙ В СТАТИСТИКЕ ДАШБОРДА")
        print("=" * 70)
        print(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Анализ карты дня
        self.analyze_card_of_day_discrepancy()
        
        # Анализ вечерней рефлексии
        self.analyze_evening_reflection_discrepancy()
        
        # Анализ часовых поясов
        self.analyze_timezone_issues()
        
        # Анализ исключенных пользователей
        self.analyze_excluded_users()
        
        print("\n" + "="*70)
        print("📋 ВЫВОДЫ:")
        print("• Проанализированы возможные причины расхождений")
        print("• Проверьте влияние часовых поясов")
        print("• Убедитесь в корректности исключения пользователей")
        print("• Сравните с логикой в коде дашборда")

def main():
    """Основная функция"""
    analyzer = DashboardDiscrepancyAnalyzer()
    analyzer.run_full_analysis()

if __name__ == "__main__":
    main() 