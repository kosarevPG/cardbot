import os
import asyncio
import sys
import json

# --- ВАЖНО ---
# Перед запуском теста убедитесь, что вы создали файл 'tools/google_creds.json'
# и поместили в него содержимое вашего JSON-ключа для доступа к Google Sheets.
# Также убедитесь, что переменные окружения ниже установлены,
# либо задайте их прямо здесь для локального теста.

# Пример установки переменных для теста:
os.environ['OZON_API_KEY'] = os.getenv('OZON_API_KEY', 'your_ozon_api_key')
os.environ['OZON_CLIENT_ID'] = os.getenv('OZON_CLIENT_ID', 'your_ozon_client_id')
os.environ['BOT_TOKEN'] = os.getenv('BOT_TOKEN', 'your_bot_token')
os.environ['ADMIN_ID'] = os.getenv('ADMIN_ID', 'your_admin_id')
os.environ['WB_API_TOKEN'] = os.getenv('WB_API_TOKEN', 'your_wb_api_token')


# Добавляем корневую папку проекта в sys.path для корректного импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.marketplace_manager import MarketplaceManager

# Загружаем учетные данные напрямую из JSON-файла
google_creds_info = None
try:
    # Путь к файлу относительно корня проекта, так как скрипт запускается оттуда
    with open('tools/google_creds.json', 'r', encoding='utf-8') as f:
        google_creds_info = json.load(f)
except FileNotFoundError:
    print("Ошибка: Файл 'tools/google_creds.json' не найден.")
    print("Пожалуйста, создайте этот файл и поместите в него содержимое вашего JSON-ключа.")
except json.JSONDecodeError:
    print("Ошибка: Не удалось прочитать JSON из файла 'tools/google_creds.json'.")
    print("Пожалуйста, убедитесь, что файл содержит корректный JSON.")
except Exception as e:
    print(f"Произошла непредвиденная ошибка при чтении файла с ключами: {e}")

async def main():
    if not google_creds_info:
        print("Не удалось загрузить учетные данные Google. Тест прерван.")
        return

    print("Инициализация MarketplaceManager...")
    manager = MarketplaceManager(google_creds=google_creds_info)
    
    print("Запуск синхронизации данных Ozon...")
    result = await manager.sync_ozon_data()
    
    print("\n--- Результат синхронизации ---")
    print(result)
    print("---------------------------------")

if __name__ == "__main__":
    # Для Windows может потребоваться следующая строка, если возникают проблемы с циклом событий
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
