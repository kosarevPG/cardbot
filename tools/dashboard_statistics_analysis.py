#!/usr/bin/env python3
"""
Анализ логики подсчета статистики дашборда за сегодня
"""

import requests
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

class DashboardStatisticsAnalyzer:
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
    
    def analyze_dau_today(self):
        """Анализирует DAU за сегодня"""
        print("🔍 АНАЛИЗ DAU ЗА СЕГОДНЯ")
        print("=" * 50)
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Проверяем таблицу daily_active_users
        sql = f"""
        SELECT day, dau 
        FROM daily_active_users 
        WHERE day = '{today}'
        """
        
        result = self.execute_sql_query('daily_active_users', sql)
        
        if result and not result.get('error'):
            if result['rows']:
                for row in result['rows']:
                    day, dau = row
                    print(f"📊 DAU за {day}: {dau}")
            else:
                print(f"❌ Нет данных DAU за {today}")
        
        # Проверяем активных пользователей через actions
        sql_actions = f"""
        SELECT COUNT(DISTINCT user_id) as active_users
        FROM actions 
        WHERE DATE(timestamp) = '{today}'
        """
        
        result_actions = self.execute_sql_query('actions', sql_actions)
        
        if result_actions and not result_actions.get('error'):
            if result_actions['rows']:
                active_users = result_actions['rows'][0][0]
                print(f"📊 Активных пользователей через actions: {active_users}")
        
        return result, result_actions
    
    def analyze_card_of_day_today(self):
        """Анализирует статистику карты дня за сегодня"""
        print("\n🔍 АНАЛИЗ КАРТЫ ДНЯ ЗА СЕГОДНЯ")
        print("=" * 50)
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Подсчет запусков карты дня
        sql_launches = f"""
        SELECT COUNT(*) as launches
        FROM scenario_logs 
        WHERE scenario = 'card_of_day' 
        AND DATE(timestamp) = '{today}'
        AND step = 'started'
        """
        
        result_launches = self.execute_sql_query('scenario_logs', sql_launches)
        
        if result_launches and not result_launches.get('error'):
            if result_launches['rows']:
                launches = result_launches['rows'][0][0]
                print(f"📊 Запусков карты дня: {launches}")
        
        # Подсчет завершений карты дня
        sql_completed = f"""
        SELECT COUNT(*) as completed
        FROM user_scenarios 
        WHERE scenario = 'card_of_day' 
        AND DATE(started_at) = '{today}'
        AND status = 'completed'
        """
        
        result_completed = self.execute_sql_query('user_scenarios', sql_completed)
        
        if result_completed and not result_completed.get('error'):
            if result_completed['rows']:
                completed = result_completed['rows'][0][0]
                print(f"📊 Завершено карт дня: {completed}")
                
                if launches and int(launches) > 0:
                    completion_rate = (int(completed) / int(launches)) * 100
                    print(f"📈 Процент завершения: {completion_rate:.1f}%")
        
        # Среднее количество шагов
        sql_avg_steps = f"""
        SELECT AVG(steps_count) as avg_steps
        FROM user_scenarios 
        WHERE scenario = 'card_of_day' 
        AND DATE(started_at) = '{today}'
        AND status = 'completed'
        """
        
        result_avg_steps = self.execute_sql_query('user_scenarios', sql_avg_steps)
        
        if result_avg_steps and not result_avg_steps.get('error'):
            if result_avg_steps['rows']:
                avg_steps = result_avg_steps['rows'][0][0]
                if avg_steps and avg_steps != 'None':
                    print(f"📊 Среднее количество шагов: {float(avg_steps):.1f}")
        
        return result_launches, result_completed, result_avg_steps
    
    def analyze_evening_reflection_today(self):
        """Анализирует статистику вечерней рефлексии за сегодня"""
        print("\n🔍 АНАЛИЗ ВЕЧЕРНЕЙ РЕФЛЕКСИИ ЗА СЕГОДНЯ")
        print("=" * 50)
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Подсчет запусков вечерней рефлексии
        sql_launches = f"""
        SELECT COUNT(*) as launches
        FROM scenario_logs 
        WHERE scenario = 'evening_reflection' 
        AND DATE(timestamp) = '{today}'
        AND step = 'started'
        """
        
        result_launches = self.execute_sql_query('scenario_logs', sql_launches)
        
        if result_launches and not result_launches.get('error'):
            if result_launches['rows']:
                launches = result_launches['rows'][0][0]
                print(f"📊 Запусков вечерней рефлексии: {launches}")
        
        # Подсчет завершений вечерней рефлексии
        sql_completed = f"""
        SELECT COUNT(*) as completed
        FROM user_scenarios 
        WHERE scenario = 'evening_reflection' 
        AND DATE(started_at) = '{today}'
        AND status = 'completed'
        """
        
        result_completed = self.execute_sql_query('user_scenarios', sql_completed)
        
        if result_completed and not result_completed.get('error'):
            if result_completed['rows']:
                completed = result_completed['rows'][0][0]
                print(f"📊 Завершено вечерних рефлексий: {completed}")
                
                if launches and int(launches) > 0:
                    completion_rate = (int(completed) / int(launches)) * 100
                    print(f"📈 Процент завершения: {completion_rate:.1f}%")
        
        return result_launches, result_completed
    
    def analyze_value_metrics_today(self):
        """Анализирует метрики ценности за сегодня"""
        print("\n🔍 АНАЛИЗ МЕТРИК ЦЕННОСТИ ЗА СЕГОДНЯ")
        print("=" * 50)
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Положительная динамика ресурса
        sql_resource = f"""
        SELECT COUNT(*) as positive_resource
        FROM user_profiles 
        WHERE DATE(last_updated) = '{today}'
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
        WHERE DATE(timestamp) = '{today}'
        """
        
        result_feedback = self.execute_sql_query('feedback', sql_feedback)
        
        if result_feedback and not result_feedback.get('error'):
            if result_feedback['rows']:
                feedback_count = result_feedback['rows'][0][0]
                print(f"📊 Feedback за сегодня: {feedback_count}")
        
        return result_resource, result_feedback
    
    def analyze_retention_today(self):
        """Анализирует retention за сегодня"""
        print("\n🔍 АНАЛИЗ RETENTION ЗА СЕГОДНЯ")
        print("=" * 50)
        
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
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
                if yesterday_users and int(yesterday_users) > 0:
                    d1_retention = (int(today_users) / int(yesterday_users)) * 100
                    print(f"📊 D1 Retention: {d1_retention:.1f}%")
        
        # D7 Retention
        sql_d7 = f"""
        SELECT 
            COUNT(DISTINCT CASE WHEN DATE(timestamp) = '{week_ago}' THEN user_id END) as week_ago_users,
            COUNT(DISTINCT CASE WHEN DATE(timestamp) = '{today}' THEN user_id END) as today_users
        FROM actions 
        WHERE DATE(timestamp) IN ('{week_ago}', '{today}')
        """
        
        result_d7 = self.execute_sql_query('actions', sql_d7)
        
        if result_d7 and not result_d7.get('error'):
            if result_d7['rows']:
                week_ago_users, today_users = result_d7['rows'][0]
                if week_ago_users and int(week_ago_users) > 0:
                    d7_retention = (int(today_users) / int(week_ago_users)) * 100
                    print(f"📊 D7 Retention: {d7_retention:.1f}%")
        
        return result_d1, result_d7
    
    def run_full_analysis(self):
        """Запускает полный анализ статистики дашборда"""
        print("🔍 АНАЛИЗ СТАТИСТИКИ ДАШБОРДА ЗА СЕГОДНЯ")
        print("=" * 60)
        print(f"Время анализа: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Анализ DAU
        self.analyze_dau_today()
        
        # Анализ карты дня
        self.analyze_card_of_day_today()
        
        # Анализ вечерней рефлексии
        self.analyze_evening_reflection_today()
        
        # Анализ метрик ценности
        self.analyze_value_metrics_today()
        
        # Анализ retention
        self.analyze_retention_today()
        
        print("\n" + "="*60)
        print("📋 ВЫВОДЫ:")
        print("• Проверена логика подсчета всех метрик дашборда")
        print("• Сравните результаты с данными на скриншоте")
        print("• Убедитесь в корректности временных фильтров")

def main():
    """Основная функция"""
    analyzer = DashboardStatisticsAnalyzer()
    analyzer.run_full_analysis()

if __name__ == "__main__":
    main() 