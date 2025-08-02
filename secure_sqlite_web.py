#!/usr/bin/env python3
"""
Безопасный запуск sqlite_web с аутентификацией через кастомное Flask приложение
"""

import os
import sys
import sqlite3
from flask import Flask, request, Response, redirect, url_for
from flask_basicauth import BasicAuth
import werkzeug

# Получаем учетные данные из переменных окружения
USERNAME = os.environ.get('SQLITE_WEB_USERNAME', 'admin')
PASSWORD = os.environ.get('SQLITE_WEB_PASSWORD', 'root')

# Путь к базе данных
DB_PATH = "/data/bot.db"

# Проверяем существование базы данных
if not os.path.exists(DB_PATH):
    print(f"Ошибка: База данных не найдена по пути {DB_PATH}")
    sys.exit(1)

# Создаем Flask приложение
app = Flask(__name__)

# Настройка Basic Auth
app.config['BASIC_AUTH_USERNAME'] = USERNAME
app.config['BASIC_AUTH_PASSWORD'] = PASSWORD
app.config['BASIC_AUTH_FORCE'] = True

# Инициализируем Basic Auth
basic_auth = BasicAuth(app)

# Импортируем sqlite_web после настройки аутентификации
import sqlite_web

# Получаем приложение sqlite_web
sqlite_app = sqlite_web.app

# Создаем WSGI приложение с аутентификацией
def application(environ, start_response):
    """WSGI приложение с аутентификацией"""
    
    # Создаем Flask request объект
    with app.request_context(environ):
        # Проверяем аутентификацию
        auth = request.authorization
        if not auth or not basic_auth.check_credentials(auth.username, auth.password):
            return basic_auth.challenge()(environ, start_response)
        
        # Если аутентификация прошла, передаем запрос в sqlite_web
        return sqlite_app(environ, start_response)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 80))
    host = "0.0.0.0"
    
    print(f"Запуск защищенного sqlite_web на {host}:{port}")
    print(f"Логин: {USERNAME}")
    print(f"База данных: {DB_PATH}")
    
    # Запускаем через Werkzeug
    werkzeug.serving.run_simple(host, port, application, use_reloader=False, use_debugger=False) 