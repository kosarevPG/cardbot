#!/usr/bin/env python3
"""
Простой скрипт для проверки подключения к БД
"""

import requests

def test_connection():
    """Тестирует подключение к веб-интерфейсу БД"""
    print("🔍 ТЕСТ ПОДКЛЮЧЕНИЯ К БД")
    print("=" * 30)
    
    url = "https://cardbot-1-kosarevpg.amvera.io/actions/content/"
    
    try:
        print(f"Подключаюсь к: {url}")
        response = requests.get(url, timeout=10)
        
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Подключение успешно!")
            print(f"Размер ответа: {len(response.text)} символов")
            
            # Проверяем, есть ли в ответе данные о действиях
            if "admin_requests_viewed" in response.text:
                print("🔍 Найдены упоминания admin_requests_viewed")
            else:
                print("ℹ️ admin_requests_viewed не найдено в текущей странице")
                
        else:
            print(f"❌ Ошибка подключения: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_connection() 