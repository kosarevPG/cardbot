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

# ADMIN_ID может быть как одним числом, так и списком через запятую/пробелы:
# пример: "6682555021,392141189"
def _parse_admin_ids(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []

    # поддерживаем разделители: запятая, пробелы, табы, перевод строки, точка с запятой
    raw = raw.replace(";", ",").replace("\n", ",").replace("\t", ",")
    parts = [p.strip() for p in raw.split(",")]

    tokens: list[str] = []
    for part in parts:
        if not part:
            continue
        # если кто-то передал "1 2 3" без запятых — добиваем split по пробелам
        for sub in part.split():
            sub = sub.strip()
            if sub.isdigit():
                tokens.append(sub)

    # уникализируем, сохраняя порядок
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "")
ADMIN_IDS = _parse_admin_ids(ADMIN_ID_RAW)  # список строковых ID
ADMIN_ID = int(ADMIN_IDS[0]) if ADMIN_IDS else 0  # первый ID — для обратной совместимости

if not ADMIN_IDS:
    # Не падаем, но явно логируем, чтобы это было заметно в Amvera.
    print("CRITICAL: ADMIN_ID is not set or invalid. Admin features will be disabled until ADMIN_ID is configured.")
else:
    # Диагностический лог, чтобы в Amvera было видно, что список подтянулся корректно.
    # (Это безопасно: тут только ID, без токенов/секретов.)
    try:
        print(f"[config] ADMIN_IDS parsed: {ADMIN_IDS} (primary ADMIN_ID={ADMIN_ID})", flush=True)
    except Exception:
        pass

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
