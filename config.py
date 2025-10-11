# Импорт pytz с обработкой ошибок
try:
    import pytz
    TIMEZONE = pytz.timezone("Europe/Moscow")
except ImportError:
    pytz = None
    TIMEZONE = None
    print("Warning: pytz library not found. TIMEZONE will be None.")

import os

# Токены и настройки из переменных окружения (секреты Amvera)
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_ID = os.getenv("CHANNEL_ID", "YOUR_CHANNEL_ID_HERE")
BOT_LINK = os.getenv("BOT_LINK", "YOUR_BOT_LINK_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "YOUR_ADMIN_ID_HERE"))
ADMIN_IDS = [str(ADMIN_ID)]  # Список ID администраторов для админ-панели

# Настройки для YandexGPT из секретов
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "YOUR_YANDEX_API_KEY_HERE")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "YOUR_YANDEX_FOLDER_ID_HERE")
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

# Старые ключи Grok закомментированы
# GROK_API_KEY = os.getenv("GROK_API_KEY", "YOUR_GROK_API_KEY_HERE")
# GROK_API_URL = "https://api.x.ai/v1/chat/completions"

NO_CARD_LIMIT_USERS = [6682555021, 392141189, 239719200]
NO_LOGS_USERS = [6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985, 999999999]
DATA_DIR = "/data"
# DB_PATH не указываем для production - будет использоваться DATA_DIR + "bot.db"

# Примечание: UNIVERSE_ADVICE, CARD_MEANINGS и другие константы перенесены в modules/constants.py
