# Локальный конфиг для запуска бота
import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Основные настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_ID = os.getenv("CHANNEL_ID", "YOUR_CHANNEL_ID_HERE")
BOT_LINK = os.getenv("BOT_LINK", "YOUR_BOT_LINK_HERE")

# ADMIN_ID может быть как одним числом, так и списком через запятую/пробелы:
# пример: "6682555021,392141189"
def _parse_admin_ids(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []

    raw = raw.replace(";", ",").replace("\n", ",").replace("\t", ",")
    parts = [p.strip() for p in raw.split(",")]

    tokens: list[str] = []
    for part in parts:
        if not part:
            continue
        for sub in part.split():
            sub = sub.strip()
            if sub.isdigit():
                tokens.append(sub)

    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

ADMIN_ID_RAW = os.getenv("ADMIN_ID", "")
ADMIN_IDS = _parse_admin_ids(ADMIN_ID_RAW)
ADMIN_ID = int(ADMIN_IDS[0]) if ADMIN_IDS else 0

if not ADMIN_IDS:
    print("CRITICAL: ADMIN_ID is not set or invalid. Admin features will be disabled until ADMIN_ID is configured.")

# Ozon API ключи
OZON_API_KEY = os.getenv("OZON_API_KEY", "c9e42c45-f46d-4e14-bf5f-a7f124b96b6e")
OZON_CLIENT_ID = os.getenv("OZON_CLIENT_ID", "3033403")

# Google Sheets API
GOOGLE_SERVICE_ACCOUNT_BASE64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64", "ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAiY2FyZC1ib3QtcmVhZGVyIiwKICAicHJpdmF0ZV9rZXlfaWQiOiAiODE5NzQ3ZTM5MTM4Zjc3YjM2OGZlMmI2MTE0ZWY4MjgyNjljZTllNyIsCiAgInByaXZhdGVfa2V5IjogIi0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlJRXZnSUJBREFOQmdrcWhraUc5dzBCQVFFRkFBU0NCS2d3Z2dTa0FnRUFBb0lCQVFETWlnQWVwOGxqTGkzTlxuRFUvbVVvcDdySGhKSWxxdElBYWZGUDcwWDJMWEkzOGJweXpjSkg3Qnp1eXRldzRETFBOU1JibnFCRVpZT3FDU1xuTnZLbnhuVHJvQTlFYnBLZUJpd1BWVDIzM05tYlBJd0dQMzhtUjRqL3oza1NlWXVpMW1jNnA4bmdwSzJGMDBadlxuT2QzU3JPKy9JTXQvOWFTOHJETEgxVzhnZDNUUDYxVUFHdURZVEdFUTRablVQM3EwQXdNMzNNbjBTK3VNUVBNK1xueWxHUmY3R0xLRWtZZUdkMFVzWXBqUkFlbFcyZ1lVWjNFbjJpNmFsTjVjNStwUFBJZnhJc0ZxQWdPS2ZyZW5yd1xuT1JlN3dkeTc1clk2cy9LYU1nZUtaTlkxaXF1ZVRhYW8wVXViSmo4VW1pUlFmSlFpZzJGQk54S3dwaXozTi91QVxuenJDOUU0aGJBZ01CQUFFQ2dnRUFCUnh4c2xKcENEbkZoVGs1bWp6Tkh4Z0pPQjFML01XRWI0SG1lUlFsSG52UlxubDZST1pxWGhlNnNBWTdsanpwVXNvMktyVkZDMUIvYTNGU1diQjF4QWh3bDNPRE9NZXd4cnhNVDhNaXIvbzduRFxuUktpemliRUI3YnFHZ1AxWk9FRjVUNUEzellXYW5ISFNIR3pBRnAxTVdibjlFU2tzbGxaZ2tua2Y1TVRNdmlGTVxuNGNaaDY1MmUzdHFyRkVsUFhNYXNEOW1FUldlMjBYb1RHM3dWeGJoMysyQWE5cUpLMHd4N3dXSEkwU3V6a1R6Zlxudlh2OGhqNUE1dTk5R3ArZnlMZ21IdlAyckgrcm9nZHJmbnhUWElCcGJ5ZEF6UTAxWWxXRVdYWk1paXYzaEFmalxuUXd5M0U2MkpqRUhUR2kvQ1Z1Wkc3ZFNrNzRBbUlSTy8ydFhrNkhQTHFRS0JnUURweHNRWCtoUVd3NHhHbTBPc1xuRHdNY3VtU3prekNlQW5UY21uUElOWTFOL21qdEtxRUdMQ28rbWJQNnlwVTRGSXVmelZlY3hubVZCSTVjWm9tNlxuTzY2T2tQZjJpcHI4OXhGeWRESGlEN0dUeDVDaHlGZzBKSGZRS0h1SjFLL3pOVDZNRm1hdFc1cXRLT2pPOWNBRlxuMkt6akI1bFlKSzZmTHpaRUtlYkdYelBmWHdLQmdRRGYrN1VsTTRuQzJ0S202Ymg4K3QyeERTUVNsbmRYSmV6dFxucy9DZ3U3dTVMM2FEWE1uZFpoSlBoQ1RRdGU2d3J3cXk5TTVxd0dNVS9JY0RURUZvU2NPRExGUHI4cnFSQUNCRFxuT1RRWTc2NXdUNUpmMlhuWWV3RnhpV2s0UzdsZWJDeW5sUlBYUGxyZCtmYThRMm9YekpUUU9WN0VyMVdQWEhvL1xuM3libWdqMEVoUUtCZ1FDblJKMFNPdEVjNkpYNS95WVFlajFUMU5vdzB1UTZhcStMR01nM1BIbjZrRW9yU0JFblxuQlhyRWg5MkxXR0FrWEM3N0RFWGYydk1yZUxNVDBocEJzbXBYZjhxc0VNaU1yNHRBUlh0YnNMYnljaHcrWmNjV1xucC9GQ2MzVFJUZWtITDlXdERtb3hLQllvUjlrc0hCSmxISCszZ2J4cW9QU0EyWnNPY3B5NDIyMldLUUtCZ1FDQlxuZkNOQnFXVEh0L2MxdFVJSlJvSG8rLzdSbkJqTDBjb0J0UmV6NURQbkg5QTBxdXlzU0hqbmJTNVhWZ1h5TUk5UFxuMjRTRlpFa2pkY1dibTNib2tsUXJ2ZkdhSXMzR1M3dGJBWFBqd3BRbXEybWtiYllwOXhwamg1dkRoc3RZRWROU1xuNGpVQkp6UWl4WUhsWGxlMEFIbzdVaDgrTjFxUU1WY2ZHNk9DZU9KTGZRS0JnRGxibis0Sm1UcmxTUFdyV3g0WVxuV0RDRGJQWVM3SjBnS3diR1ljLzlZUCtOZjBTL0kyMUlnY1NNK0xPWnZkVFlVYTVFVElUVmFlV2FSOXV0Mk4zdFxuVjVqZkpYTG43WFIyaG9UeHFJWGdvODkyYWhjdFAxMXJPa3A2TlB1VVFFK1B4WWJCeldLSURkVw0K")

# YandexGPT (если нужен)
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "YOUR_YANDEX_API_KEY_HERE")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "YOUR_YANDEX_FOLDER_ID_HERE")
YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

# Настройки для локального запуска
DATA_DIR = "./data"  # Локальная папка для данных
DB_PATH = "./database/bot.db"  # Локальный путь к БД

# Список советов Вселенной (копируем из основного конфига)
UNIVERSE_ADVICE = [
    "<b>✨ Сегодня вселенная шепчет:</b> Твоя улыбка может изменить чей-то день. Начни со своего.",
    "<b>🌟 Знак свыше:</b> То, что кажется случайностью, — на самом деле идеальное время. Действуй.",
    "<b>🦋 Мудрость момента:</b> Бабочки не помнят, что были гусеницами. Твоя трансформация уже началась.",
    "<b>🎯 Вселенная подсказывает:</b> Ответ, который ты ищешь, придет через неожиданного человека или ситуацию.",
    "<b>🌙 Лунный совет:</b> Даже луна проходит фазы. Твоя 'темная' полоса — это подготовка к новому свету.",
    "<b>🎪 Магия дня:</b> Сегодня обрати внимание на детали. Вселенная говорит с тобой знаками.",
    "<b>🌊 Поток удачи:</b> Препятствие, которое перед тобой, — это не стена, а трамплин для прыжка.",
    "<b>🎨 Секрет творца:</b> Ты — художник своей жизни. Возьми кисть и нарисуй что-то прекрасное прямо сейчас.",
    "<b>🕯️ Свет внутри:</b> Твоя энергия сегодня особенно сильна. Используй её для чего-то важного.",
    "<b>🎭 Театр судьбы:</b> В твоей истории наступает поворотный момент. Будь готов к неожиданному сюжету.",
    "<b>🍀 Удача близко:</b> Три вещи, которые произойдут сегодня, принесут тебе радость. Замечай их.",
    "<b>🗝️ Ключ дня:</b> Доброта к себе откроет дверь, которую ты давно не могла найти.",
    "<b>🌈 После грозы:</b> Твоя награда уже в пути. Она больше, чем ты ожидаешь.",
    "<b>🎁 Подарок от вселенной:</b> Кто-то думает о тебе с благодарностью прямо сейчас. Почувствуй это тепло.",
    "<b>⚡ Молниеносная истина:</b> Ты влияешь на мир больше, чем думаешь. Каждое твое действие важно.",
    "<b>🏔️ Вершина мудрости:</b> Путь наверх всегда кажется сложнее, чем есть. Следующий шаг проще, чем кажется.",
    "<b>🎪 Цирк возможностей:</b> Вселенная готовит для тебя удивительное представление. Занимай лучшие места!",
    "<b>🌸 Весна души:</b> В тебе прорастает что-то новое и прекрасное. Будь терпелива к своему росту.",
    "<b>🎵 Мелодия судьбы:</b> Слушай свое сердце — сегодня оно играет особенно красивую мелодию.",
    "<b>🌅 Рассвет надежды:</b> Каждый новый день — это чистый лист. Напиши на нем что-то удивительное.",
    "<b>🧭 Компас интуиции:</b> Твоя внутренняя навигация работает безупречно. Доверяй первому импульсу.",
    "<b>🎪 Магический цирк жизни:</b> Ты одновременно зритель и артист. Сегодня покажи свой лучший номер.",
    "<b>🌟 Звездная карта:</b> Твоя мечта приближается. Приготовься принять её с распростертыми объятиями.",
    "<b>🎯 Точное попадание:</b> То, что ты делаешь прямо сейчас, попадет точно в цель. Не останавливайся.",
    "<b>🦄 Единорог дня:</b> Сегодня произойдет что-то редкое и прекрасное. Держи глаза открытыми!",
    "<b>🎊 Конфетти вселенной:</b> Повод для празднования уже рядом. Возможно, ты его еще не заметил.",
    "<b>🌺 Аромат успеха:</b> Твои усилия наконец-то дадут плоды. Почувствуй сладкий запах победы.",
    "<b>🎈 Воздушный шар мечты:</b> Отпусти страхи — пусть твоя мечта поднимется высоко в небо.",
    "<b>🎪 Главное представление:</b> Сегодня ты — звезда дня. Сияй так ярко, как только можешь!",
    "<b>💎 Драгоценный момент:</b> Этот день принесет тебе что-то очень ценное. Цени каждую минуту."
]

# Пользователи без ограничений
NO_CARD_LIMIT_USERS = [6682555021, 392141189, 239719200]
NO_LOGS_USERS = [6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985, 999999999]

print("✅ Локальный конфиг загружен!")
print(f"🤖 Бот токен: {'✅ Настроен' if BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else '❌ НЕ настроен'}")
print(f"🛒 Ozon API: {'✅ Настроен' if OZON_API_KEY != 'YOUR_OZON_API_KEY_HERE' else '❌ НЕ настроен'}")
print(f"📊 Google Sheets: {'✅ Настроен' if GOOGLE_SERVICE_ACCOUNT_BASE64 != 'YOUR_GOOGLE_SERVICE_ACCOUNT_BASE64_HERE' else '❌ НЕ настроен'}")
