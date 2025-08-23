#!/usr/bin/env python3
"""
Скрипт для создания .env файла с переменными окружения
"""

def create_env_file():
    """Создает .env файл с настройками бота"""
    
    env_content = """# ШАБЛОН локальных переменных окружения для Telegram бота
# Замените все значения на реальные!

# Основные настройки бота
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
CHANNEL_ID=@YOUR_CHANNEL
BOT_LINK=t.me/your_bot_name
ADMIN_ID=YOUR_ADMIN_ID

# Ozon API ключи
OZON_API_KEY=YOUR_OZON_API_KEY
OZON_CLIENT_ID=YOUR_OZON_CLIENT_ID

# Google Sheets API (base64 encoded service account JSON)
GOOGLE_SERVICE_ACCOUNT_BASE64=YOUR_GOOGLE_SERVICE_ACCOUNT_BASE64

# YandexGPT
YANDEX_API_KEY=YOUR_YANDEX_API_KEY
YANDEX_FOLDER_ID=YOUR_YANDEX_FOLDER_ID

# SQLite Web (опционально)
SQLITE_WEB_USERNAME=admin
SQLITE_WEB_PASSWORD=your_password
"""
    
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ Файл .env успешно создан!")
        print("📝 Содержит все необходимые переменные окружения:")
        print("   • BOT_TOKEN - токен Telegram бота")
        print("   • OZON_API_KEY - ключ Ozon API")
        print("   • GOOGLE_SERVICE_ACCOUNT_BASE64 - сервисный аккаунт Google")
        print("   • YANDEX_API_KEY - ключ YandexGPT")
        print("   • И другие настройки...")
        print()
        print("🚀 Теперь можно запускать бота!")
        
    except Exception as e:
        print(f"❌ Ошибка создания .env файла: {e}")

if __name__ == "__main__":
    create_env_file()
