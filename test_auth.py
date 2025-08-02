#!/usr/bin/env python3
"""
Скрипт для тестирования аутентификации sqlite_web
"""

import os
import requests
from requests.auth import HTTPBasicAuth

# URL для тестирования
URL = "https://cardbot-1-kosarevpg.amvera.io/"

# Учетные данные
USERNAME = os.environ.get('SQLITE_WEB_USERNAME', 'admin')
PASSWORD = os.environ.get('SQLITE_WEB_PASSWORD', 'root')

def test_auth():
    """Тестирует аутентификацию"""
    print(f"Тестирование аутентификации для {URL}")
    print(f"Логин: {USERNAME}")
    print(f"Пароль: {PASSWORD}")
    
    # Тест без аутентификации
    print("\n1. Тест без аутентификации:")
    try:
        response = requests.get(URL, timeout=10)
        print(f"Статус: {response.status_code}")
        if response.status_code == 401:
            print("✅ Аутентификация работает - доступ заблокирован")
        else:
            print("❌ Аутентификация не работает - доступ открыт")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Тест с правильными учетными данными
    print("\n2. Тест с правильными учетными данными:")
    try:
        auth = HTTPBasicAuth(USERNAME, PASSWORD)
        response = requests.get(URL, auth=auth, timeout=10)
        print(f"Статус: {response.status_code}")
        if response.status_code == 200:
            print("✅ Аутентификация работает - доступ предоставлен")
        else:
            print(f"❌ Ошибка доступа: {response.status_code}")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    # Тест с неправильными учетными данными
    print("\n3. Тест с неправильными учетными данными:")
    try:
        auth = HTTPBasicAuth("wrong_user", "wrong_pass")
        response = requests.get(URL, auth=auth, timeout=10)
        print(f"Статус: {response.status_code}")
        if response.status_code == 401:
            print("✅ Аутентификация работает - неправильные данные отклонены")
        else:
            print("❌ Аутентификация не работает - неправильные данные приняты")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    test_auth() 