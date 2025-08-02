#!/usr/bin/env python3
"""
Скрипт для проверки состояния аутентификации
"""

import os
import requests
from requests.auth import HTTPBasicAuth

def check_auth_status():
    """Проверяет состояние аутентификации"""
    url = "https://cardbot-1-kosarevpg.amvera.io/"
    
    print("🔐 Проверка состояния аутентификации")
    print("=" * 50)
    
    # Проверяем переменные окружения
    username = os.environ.get('SQLITE_WEB_USERNAME', 'admin')
    password = os.environ.get('SQLITE_WEB_PASSWORD', 'root')
    
    print(f"📋 Переменные окружения:")
    print(f"   SQLITE_WEB_USERNAME: {username}")
    print(f"   SQLITE_WEB_PASSWORD: {'*' * len(password)}")
    print()
    
    # Тест 1: Доступ без аутентификации
    print("🔒 Тест 1: Доступ без аутентификации")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 401:
            print("   ✅ Аутентификация работает - доступ заблокирован")
        else:
            print(f"   ❌ Аутентификация не работает - статус: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Ошибка подключения: {e}")
    print()
    
    # Тест 2: Доступ с правильными учетными данными
    print("🔑 Тест 2: Доступ с правильными учетными данными")
    try:
        auth = HTTPBasicAuth(username, password)
        response = requests.get(url, auth=auth, timeout=10)
        if response.status_code == 200:
            print("   ✅ Аутентификация работает - доступ предоставлен")
        else:
            print(f"   ❌ Ошибка доступа: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Ошибка подключения: {e}")
    print()
    
    # Тест 3: Доступ с неправильными учетными данными
    print("🚫 Тест 3: Доступ с неправильными учетными данными")
    try:
        auth = HTTPBasicAuth("wrong_user", "wrong_pass")
        response = requests.get(url, auth=auth, timeout=10)
        if response.status_code == 401:
            print("   ✅ Аутентификация работает - неправильные данные отклонены")
        else:
            print(f"   ❌ Аутентификация не работает - статус: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Ошибка подключения: {e}")
    print()
    
    print("=" * 50)
    print("📝 Рекомендации:")
    print("   1. Если все тесты пройдены ✅ - аутентификация работает корректно")
    print("   2. Если есть ошибки ❌ - проверьте конфигурацию Procfile")
    print("   3. Для изменения пароля обновите переменную SQLITE_WEB_PASSWORD в Amvera")
    print("   4. После изменения переменных перезапустите приложение")

if __name__ == '__main__':
    check_auth_status() 