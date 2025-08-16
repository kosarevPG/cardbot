#!/usr/bin/env python3
"""
Скрипт для диагностики ошибок в дашборде
"""

import sqlite3
import json
from datetime import datetime, timedelta
import os

def check_database_connection():
    """Проверяет подключение к базе данных"""
    print("🔍 Проверка подключения к базе данных")
    print("=" * 50)
    
    try:
        # Пробуем подключиться к базе данных
        db_path = "/data/bot.db"
        if not os.path.exists(db_path):
            print(f"❌ База данных не найдена по пути: {db_path}")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем основные таблицы
        tables = ['users', 'user_scenarios', 'scenario_logs', 'user_requests', 'posts', 'mailings']
        missing_tables = []
        
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                missing_tables.append(table)
        
        if missing_tables:
            print(f"❌ Отсутствуют таблицы: {missing_tables}")
            return False
        else:
            print("✅ Все основные таблицы найдены")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        return False

def test_dashboard_queries():
    """Тестирует запросы дашборда"""
    print("\n🔍 Тестирование запросов дашборда")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect("/data/bot.db")
        cursor = conn.cursor()
        
        # Тест 1: DAU метрики
        print("📊 Тест 1: DAU метрики")
        try:
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as dau_yesterday
                FROM user_scenarios 
                WHERE DATE(started_at, '+3 hours') = DATE('now', '+3 hours', '-1 day')
            """)
            result = cursor.fetchone()
            print(f"   DAU вчера: {result[0] if result else 0}")
        except Exception as e:
            print(f"   ❌ Ошибка DAU: {e}")
        
        # Тест 2: Retention метрики
        print("📈 Тест 2: Retention метрики")
        try:
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as d1_users
                FROM user_scenarios 
                WHERE DATE(started_at, '+3 hours') >= DATE('now', '+3 hours', '-1 day')
            """)
            result = cursor.fetchone()
            print(f"   D1 пользователей: {result[0] if result else 0}")
        except Exception as e:
            print(f"   ❌ Ошибка Retention: {e}")
        
        # Тест 3: Сценарий статистика
        print("🎯 Тест 3: Статистика сценариев")
        try:
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as total_starts
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = 'started'
                AND timestamp >= datetime('now', '-7 days', '+3 hours')
            """)
            result = cursor.fetchone()
            print(f"   Запусков карты дня: {result[0] if result else 0}")
        except Exception as e:
            print(f"   ❌ Ошибка статистики сценариев: {e}")
        
        # Тест 4: Value метрики
        print("💎 Тест 4: Value метрики")
        try:
            cursor.execute("""
                SELECT COUNT(*) as total_feedback
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = 'usefulness_rating'
                AND timestamp >= datetime('now', '-7 days', '+3 hours')
            """)
            result = cursor.fetchone()
            print(f"   Всего отзывов: {result[0] if result else 0}")
        except Exception as e:
            print(f"   ❌ Ошибка value метрик: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Общая ошибка тестирования: {e}")

def check_admin_config():
    """Проверяет конфигурацию администраторов"""
    print("\n🔍 Проверка конфигурации администраторов")
    print("=" * 50)
    
    try:
        # Проверяем config.py
        try:
            from config import ADMIN_IDS
            print(f"✅ ADMIN_IDS найдены: {ADMIN_IDS}")
        except ImportError as e:
            print(f"❌ Ошибка импорта ADMIN_IDS: {e}")
        
        # Проверяем config_local.py
        try:
            from config_local import ADMIN_IDS
            print(f"✅ ADMIN_IDS в config_local: {ADMIN_IDS}")
        except ImportError:
            print("ℹ️  config_local.py не найден (это нормально)")
        
    except Exception as e:
        print(f"❌ Ошибка проверки конфигурации: {e}")

def check_logs():
    """Проверяет логи на наличие ошибок"""
    print("\n🔍 Проверка логов")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect("/data/bot.db")
        cursor = conn.cursor()
        
        # Проверяем последние ошибки в логах
        cursor.execute("""
            SELECT timestamp, user_id, action, details
            FROM actions 
            WHERE action LIKE '%error%' OR action LIKE '%fail%'
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        
        errors = cursor.fetchall()
        if errors:
            print("⚠️  Найдены ошибки в логах:")
            for error in errors:
                print(f"   {error[0]}: {error[2]} - {error[3]}")
        else:
            print("✅ Ошибок в логах не найдено")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка проверки логов: {e}")

def main():
    """Основная функция диагностики"""
    print("🚀 Диагностика дашборда")
    print("=" * 50)
    
    # Проверяем подключение к БД
    if not check_database_connection():
        print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Не удается подключиться к базе данных")
        return
    
    # Тестируем запросы
    test_dashboard_queries()
    
    # Проверяем конфигурацию
    check_admin_config()
    
    # Проверяем логи
    check_logs()
    
    print("\n" + "=" * 50)
    print("📝 Рекомендации:")
    print("1. Если есть ошибки в запросах - проверьте структуру таблиц")
    print("2. Если проблемы с ADMIN_IDS - проверьте config.py")
    print("3. Если ошибки в логах - проверьте последние действия пользователей")
    print("4. Перезапустите приложение после исправлений")

if __name__ == '__main__':
    main() 