#!/usr/bin/env python3
"""
Скрипт для проверки продакшн данных через API
"""

import requests
import json
from datetime import datetime

def check_production_via_web():
    """Проверяет продакшн данные через веб-интерфейс"""
    print("🔍 ПРОВЕРКА PRODUCTION ДАННЫХ ЧЕРЕЗ WEB")
    print("=" * 50)
    
    # URL продакшн бота
    base_url = "https://cardbot-kosarevpg.amvera.io"
    
    try:
        # Пробуем подключиться к веб-интерфейсу SQLite
        response = requests.get(base_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Веб-интерфейс доступен")
            print(f"📊 URL: {base_url}")
            print("🔍 Откройте этот URL в браузере для просмотра БД")
        else:
            print(f"❌ Веб-интерфейс недоступен (код: {response.status_code})")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения: {e}")
        print("💡 Возможные причины:")
        print("   - Бот не запущен")
        print("   - Неправильный URL")
        print("   - Проблемы с сетью")

def check_bot_status():
    """Проверяет статус бота"""
    print("\n🤖 ПРОВЕРКА СТАТУСА БОТА")
    print("=" * 30)
    
    # Проверяем, отвечает ли бот на команды
    # Это можно сделать только если у бота есть webhook или web endpoint
    
    print("ℹ️ Для проверки статуса бота:")
    print("   1. Отправьте команду /start боту")
    print("   2. Проверьте, отвечает ли он")
    print("   3. Попробуйте команду /admin (должна быть заблокирована для не-админов)")

def generate_sql_queries():
    """Генерирует SQL-запросы для проверки безопасности"""
    print("\n📋 SQL-ЗАПРОСЫ ДЛЯ ПРОВЕРКИ БЕЗОПАСНОСТИ")
    print("=" * 50)
    
    queries = [
        {
            "name": "Проверка админских действий",
            "sql": """
                SELECT 
                    user_id,
                    username,
                    name,
                    action,
                    timestamp,
                    CASE 
                        WHEN user_id IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985) 
                        THEN 'LEGITIMATE_ADMIN' 
                        ELSE 'UNAUTHORIZED_ACCESS' 
                    END as access_type
                FROM actions 
                WHERE action LIKE 'admin_%'
                ORDER BY timestamp DESC
                LIMIT 20
            """
        },
        {
            "name": "Проверка пользователя 865377684",
            "sql": """
                SELECT 
                    user_id,
                    username,
                    name,
                    action,
                    timestamp
                FROM actions 
                WHERE user_id = 865377684
                ORDER BY timestamp DESC
            """
        },
        {
            "name": "Статистика безопасности",
            "sql": """
                SELECT 
                    COUNT(*) as total_admin_actions,
                    COUNT(CASE WHEN user_id IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985) THEN 1 END) as legitimate_actions,
                    COUNT(CASE WHEN user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985) THEN 1 END) as unauthorized_actions
                FROM actions 
                WHERE action LIKE 'admin_%'
            """
        }
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{i}. {query['name']}:")
        print("   SQL:")
        print(query['sql'])
        print()

def main():
    """Основная функция"""
    print("🔍 ПРОВЕРКА PRODUCTION ДАННЫХ")
    print("=" * 50)
    print(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Проверка 1: Веб-интерфейс
    check_production_via_web()
    
    # Проверка 2: Статус бота
    check_bot_status()
    
    # Проверка 3: SQL-запросы
    generate_sql_queries()
    
    print("\n📋 ИНСТРУКЦИИ ДЛЯ ПРОВЕРКИ:")
    print("1. Откройте https://cardbot-kosarevpg.amvera.io в браузере")
    print("2. Найдите таблицу 'actions'")
    print("3. Выполните SQL-запросы выше")
    print("4. Проверьте, есть ли действия пользователя 865377684")
    print("5. Проверьте, есть ли несанкционированные админские действия")
    
    print("\n🚨 ЕСЛИ ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
    print("- Немедленно проверьте деплой в Amvera")
    print("- Принудительно перезапустите бота")
    print("- Проверьте логи на предмет ошибок")

if __name__ == "__main__":
    main() 