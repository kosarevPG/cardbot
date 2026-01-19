@echo off
chcp 65001 >nul
title Telegram Bot - Локальный запуск

echo.
echo 🚀 Запуск Telegram бота локально...
echo 📱 Бот будет доступен для пользователей
echo ⏰ Время: %date% %time%
echo.

:check_python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.8+
    echo 💡 Скачать: https://www.python.org/downloads/
    pause
    exit /b 1
)

:check_env
if not exist ".env" (
    echo ⚠️  Файл .env не найден!
    echo 📝 Создайте файл .env с токеном бота
    echo 💡 Пример содержимого:
    echo    BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
    echo.
    echo 🔧 Создаю пример .env файла...
    
    echo # Токен вашего бота > .env
    echo BOT_TOKEN=YOUR_BOT_TOKEN_HERE >> .env
    echo # ID канала >> .env
    echo CHANNEL_ID=@your_channel >> .env
    echo # Ссылка на бота >> .env
    echo BOT_LINK=https://t.me/your_bot >> .env
    echo # ID администратора >> .env
    echo ADMIN_ID=123456789 >> .env
    
    echo ✅ Файл .env создан! Отредактируйте его и запустите снова.
    echo.
    pause
    exit /b 1
)

:check_deps
echo 🔍 Проверяю зависимости...
pip show aiogram >nul 2>&1
if errorlevel 1 (
    echo 📦 Устанавливаю зависимости...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Ошибка установки зависимостей!
        pause
        exit /b 1
    )
)

:start_bot
echo.
echo 🎯 Запускаю бота...
echo 💡 Для остановки нажмите Ctrl+C
echo 📊 Логи сохраняются в bot_local.log
echo.

:loop
python local_main.py
if errorlevel 1 (
    echo.
    echo ❌ Бот остановлен с ошибкой!
    echo 🔄 Перезапуск через 10 секунд...
    echo.
    timeout /t 10 /nobreak >nul
    goto loop
) else (
    echo.
    echo 🛑 Бот остановлен пользователем
    echo 🔄 Перезапуск через 5 секунд...
    echo.
    timeout /t 5 /nobreak >nul
    goto loop
)
