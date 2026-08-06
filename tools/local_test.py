import os
import asyncio
import sys
import json

# Добавляем корневую папку проекта в sys.path для корректного импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Добавляем путь к каталогу modules для импорта подмодулей
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'modules')))

from aiogram import types # Добавлен импорт types
from modules.purchase_menu import handle_purchase_menu, handle_purchase_callbacks, get_purchase_menu # Добавлены импорты из modules.purchase_menu
from modules.card_of_the_day import get_main_menu # Для получения главного меню
from modules.logging_service import LoggingService # Добавлен импорт LoggingService
from database.db import Database # Добавлен импорт Database

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

# WB_API_KEY берём из окружения. Раньше сюда был вписан реальный JWT-ключ продавца
# (истёк 02.03.2026) — не вписывайте секреты в файлы репозитория, они остаются в истории git.
# Перед запуском:  set WB_API_KEY=...  (cmd)  или  $env:WB_API_KEY="..."  (PowerShell)
os.environ['WB_API_KEY'] = os.getenv('WB_API_KEY', '')
if not os.environ['WB_API_KEY']:
    print("ВНИМАНИЕ: WB_API_KEY не задан в окружении — тесты Wildberries работать не будут.")


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
    
    # Инициализация для тестов бота
    logging_service = LoggingService()
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bot.db')
    db = Database(db_path)

    print("\n--- Тест кнопки \"Приобрести МАК\" ---")
    # Имитация объектов Message и CallbackQuery
    class MockMessage:
        def __init__(self):
            self.text = "🛍 Приобрести МАК"
            self.from_user = types.User(id=12345, is_bot=False, first_name="Test", last_name="User")
            self.answer_text = None
            self.reply_markup = None

        async def answer(self, text, reply_markup=None):
            print(f"Бот ответил: {text}")
            self.answer_text = text
            self.reply_markup = reply_markup
            return self

        async def edit_text(self, text, reply_markup=None):
            print(f"Бот изменил сообщение: {text}")
            self.answer_text = text
            self.reply_markup = reply_markup
            return self

    class MockCallbackQuery:
        def __init__(self, data):
            self.data = data
            self.from_user = types.User(id=12345, is_bot=False, first_name="Test", last_name="User")
            self.message = MockMessage() # Связываем с MockMessage для edit_text
            self.answer_called = False

        async def answer(self):
            print(f"CallbackQuery.answer() вызван для: {self.data}")
            self.answer_called = True

    # Для `handle_purchase_menu`
    mock_message = MockMessage()
    # Передаем db и logging_service
    await handle_purchase_menu(mock_message, db, logging_service)

    # Проверка ответа после нажатия "Приобрести МАК"
    assert mock_message.answer_text == "Выберите, где приобрести МАК:", f"Expected 'Выберите, где приобрести МАК:', got {mock_message.answer_text}"
    assert mock_message.reply_markup is not None, "Reply markup should not be None"
    
    # Проверка наличия кнопок
    markup_buttons = [button.text for row in mock_message.reply_markup.inline_keyboard for button in row]
    print(f"Кнопки в меню: {markup_buttons}")
    assert "Приобрести на Ozon" in markup_buttons, "Ozon button missing"
    assert "Приобрести на WB" in markup_buttons, "WB button missing"
    assert "⬅️ Назад" in markup_buttons, "Back button missing"

    # Для `handle_purchase_callbacks` (кнопка "Назад")
    print("\n--- Тест кнопки \"⬅️ Назад\" ---")
    mock_callback_back = MockCallbackQuery(data="back_to_main_menu")
    # Передаем db
    await handle_purchase_callbacks(mock_callback_back, db)

    # Проверка, что сообщение изменено на главное меню
    expected_main_menu_markup = await get_main_menu(mock_callback_back.from_user.id, db) # Получаем ожидаемую разметку главного меню
    assert mock_callback_back.message.answer_text == "Главное меню:", f"Expected 'Главное меню:', got {mock_callback_back.message.answer_text}"
    assert mock_callback_back.message.reply_markup == expected_main_menu_markup, "Reply markup for main menu is incorrect"
    assert mock_callback_back.answer_called, "Callback answer not called for back button"
    
    db.close()

if __name__ == "__main__":
    # Для Windows может потребоваться следующая строка, если возникают проблемы с циклом событий
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
