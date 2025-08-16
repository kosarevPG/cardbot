#!/usr/bin/env python3
"""
Проверка точности расчетов дашборда
"""

import requests
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

class DashboardVerifier:
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
    
    def verify_dau_calculation(self, days: int = 1):
        """Проверяет расчет DAU"""
        print(f"🔍 ПРОВЕРКА РАСЧЕТА DAU ЗА {days} ДЕНЬ(ДНЕЙ)")
        print("=" * 50)
        
        # Метод 1: Через таблицу daily_active_users
        sql_daily = f"""
        SELECT day, dau 
        FROM daily_active_users 
        WHERE day >= DATE('now', '-{days} days')
        ORDER BY day DESC
        """
        
        result_daily = self.execute_sql_query('daily_active_users', sql_daily)
        
        if result_daily and not result_daily.get('error'):
            if result_daily['rows']:
                print("📊 DAU из таблицы daily_active_users:")
                for row in result_daily['rows']:
                    day, dau = row
                    print(f"  • {day}: {dau}")
            else:
                print("❌ Нет данных в таблице daily_active_users")
        
        # Метод 2: Через user_scenarios (как в коде)
        sql_scenarios = f"""
        SELECT 
            DATE(started_at, '+3 hours') as date,
            COUNT(DISTINCT user_id) as dau
        FROM user_scenarios 
        WHERE started_at >= datetime('now', '-{days} days', '+3 hours')
        GROUP BY DATE(started_at, '+3 hours')
        ORDER BY date DESC
        """
        
        result_scenarios = self.execute_sql_query('user_scenarios', sql_scenarios)
        
        if result_scenarios and not result_scenarios.get('error'):
            if result_scenarios['rows']:
                print("📊 DAU из таблицы user_scenarios:")
                for row in result_scenarios['rows']:
                    date, dau = row
                    print(f"  • {date}: {dau}")
            else:
                print("❌ Нет данных в таблице user_scenarios")
        
        # Метод 3: Через actions
        sql_actions = f"""
        SELECT 
            DATE(timestamp) as date,
            COUNT(DISTINCT user_id) as dau
        FROM actions 
        WHERE timestamp >= datetime('now', '-{days} days')
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        """
        
        result_actions = self.execute_sql_query('actions', sql_actions)
        
        if result_actions and not result_actions.get('error'):
            if result_actions['rows']:
                print("📊 DAU из таблицы actions:")
                for row in result_actions['rows']:
                    date, dau = row
                    print(f"  • {date}: {dau}")
            else:
                print("❌ Нет данных в таблице actions")
        
        return result_daily, result_scenarios, result_actions
    
    def verify_scenario_stats(self, scenario: str, days: int = 1):
        """Проверяет статистику сценария"""
        print(f"\n🔍 ПРОВЕРКА СТАТИСТИКИ СЦЕНАРИЯ '{scenario}' ЗА {days} ДЕНЬ(ДНЕЙ)")
        print("=" * 60)
        
        # Метод 1: Через user_scenarios (как в коде)
        sql_starts = f"""
        SELECT COUNT(*) as total_starts
        FROM user_scenarios 
        WHERE scenario = '{scenario}' 
        AND started_at >= datetime('now', '-{days} days')
        """
        
        result_starts = self.execute_sql_query('user_scenarios', sql_starts)
        
        if result_starts and not result_starts.get('error'):
            if result_starts['rows']:
                total_starts = result_starts['rows'][0][0]
                print(f"📊 Запусков (user_scenarios): {total_starts}")
        
        # Метод 2: Через scenario_logs
        sql_logs_starts = f"""
        SELECT COUNT(DISTINCT user_id) as total_starts
        FROM scenario_logs 
        WHERE scenario = '{scenario}' 
        AND step = 'started'
        AND timestamp >= datetime('now', '-{days} days')
        """
        
        result_logs_starts = self.execute_sql_query('scenario_logs', sql_logs_starts)
        
        if result_logs_starts and not result_logs_starts.get('error'):
            if result_logs_starts['rows']:
                total_starts_logs = result_logs_starts['rows'][0][0]
                print(f"📊 Запусков (scenario_logs): {total_starts_logs}")
        
        # Завершения
        sql_completed = f"""
        SELECT COUNT(*) as total_completions
        FROM user_scenarios 
        WHERE scenario = '{scenario}' 
        AND status = 'completed'
        AND started_at >= datetime('now', '-{days} days')
        """
        
        result_completed = self.execute_sql_query('user_scenarios', sql_completed)
        
        if result_completed and not result_completed.get('error'):
            if result_completed['rows']:
                total_completed = result_completed['rows'][0][0]
                print(f"📊 Завершений: {total_completed}")
                
                if total_starts and int(total_starts) > 0:
                    completion_rate = (int(total_completed) / int(total_starts)) * 100
                    print(f"📈 Процент завершения: {completion_rate:.1f}%")
        
        # Среднее количество шагов
        sql_avg_steps = f"""
        SELECT AVG(steps_count) as avg_steps
        FROM user_scenarios 
        WHERE scenario = '{scenario}' 
        AND status = 'completed'
        AND started_at >= datetime('now', '-{days} days')
        """
        
        result_avg_steps = self.execute_sql_query('user_scenarios', sql_avg_steps)
        
        if result_avg_steps and not result_avg_steps.get('error'):
            if result_avg_steps['rows']:
                avg_steps = result_avg_steps['rows'][0][0]
                if avg_steps and avg_steps != 'None':
                    print(f"📊 Среднее количество шагов: {float(avg_steps):.1f}")
        
        return result_starts, result_logs_starts, result_completed, result_avg_steps
    
    def verify_retention_calculation(self, days: int = 1):
        """Проверяет расчет retention"""
        print(f"\n🔍 ПРОВЕРКА РАСЧЕТА RETENTION ЗА {days} ДЕНЬ(ДНЕЙ)")
        print("=" * 50)
        
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # D1 Retention
        sql_d1 = f"""
        SELECT 
            COUNT(DISTINCT CASE WHEN DATE(timestamp) = '{yesterday}' THEN user_id END) as yesterday_users,
            COUNT(DISTINCT CASE WHEN DATE(timestamp) = '{today}' THEN user_id END) as today_users
        FROM actions 
        WHERE DATE(timestamp) IN ('{yesterday}', '{today}')
        """
        
        result_d1 = self.execute_sql_query('actions', sql_d1)
        
        if result_d1 and not result_d1.get('error'):
            if result_d1['rows']:
                yesterday_users, today_users = result_d1['rows'][0]
                print(f"📊 Пользователей вчера: {yesterday_users}")
                print(f"📊 Пользователей сегодня: {today_users}")
                
                if yesterday_users and int(yesterday_users) > 0:
                    d1_retention = (int(today_users) / int(yesterday_users)) * 100
                    print(f"📈 D1 Retention: {d1_retention:.1f}%")
        
        return result_d1
    
    def verify_value_metrics(self, days: int = 1):
        """Проверяет метрики ценности"""
        print(f"\n🔍 ПРОВЕРКА МЕТРИК ЦЕННОСТИ ЗА {days} ДЕНЬ(ДНЕЙ)")
        print("=" * 50)
        
        # Положительная динамика ресурса
        sql_resource = f"""
        SELECT COUNT(*) as positive_resource
        FROM user_profiles 
        WHERE DATE(last_updated) >= DATE('now', '-{days} days')
        AND final_resource > initial_resource
        """
        
        result_resource = self.execute_sql_query('user_profiles', sql_resource)
        
        if result_resource and not result_resource.get('error'):
            if result_resource['rows']:
                positive_resource = result_resource['rows'][0][0]
                print(f"📊 Положительная динамика ресурса: {positive_resource}")
        
        # Feedback Score
        sql_feedback = f"""
        SELECT COUNT(*) as feedback_count
        FROM feedback 
        WHERE DATE(timestamp) >= DATE('now', '-{days} days')
        """
        
        result_feedback = self.execute_sql_query('feedback', sql_feedback)
        
        if result_feedback and not result_feedback.get('error'):
            if result_feedback['rows']:
                feedback_count = result_feedback['rows'][0][0]
                print(f"📊 Feedback за период: {feedback_count}")
        
        return result_resource, result_feedback
    
    def run_full_verification(self):
        """Запускает полную проверку расчетов"""
        print("🔍 ПРОВЕРКА ТОЧНОСТИ РАСЧЕТОВ ДАШБОРДА")
        print("=" * 60)
        print(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Проверяем DAU
        self.verify_dau_calculation(1)
        
        # Проверяем статистику карты дня
        self.verify_scenario_stats('card_of_day', 1)
        
        # Проверяем статистику вечерней рефлексии
        self.verify_scenario_stats('evening_reflection', 1)
        
        # Проверяем retention
        self.verify_retention_calculation(1)
        
        # Проверяем метрики ценности
        self.verify_value_metrics(1)
        
        print("\n" + "="*60)
        print("📋 ВЫВОДЫ:")
        print("• Сравните результаты с данными на скриншоте")
        print("• Проверьте корректность временных фильтров")
        print("• Убедитесь в правильности исключения пользователей")

def main():
    """Основная функция"""
    verifier = DashboardVerifier()
    verifier.run_full_verification()

if __name__ == "__main__":
    main() 