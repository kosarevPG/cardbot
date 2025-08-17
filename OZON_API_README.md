# Ozon API - Интеграция

Этот модуль предоставляет полную интеграцию с API Ozon Seller для получения данных о товарах, аналитике и остатках.

## 🚀 Основные возможности

### 1. Получение product_id по offer_id
- **Метод:** `POST /v2/product/list`
- **Функция:** `get_product_mapping()`
- **Описание:** Строит словарь соответствия между `offer_id` и `product_id`

### 2. Получение аналитики (продажи, выручка)
- **Метод:** `POST /v1/analytics/data`
- **Функция:** `get_analytics()`
- **Описание:** Получает статистику продаж и выручки по товарам

### 3. Остатки на складе
- **Метод:** `POST /v3/product/info/stocks`
- **Функция:** `get_stocks()`
- **Описание:** Получает текущие остатки товаров на складах

## 📋 Требования

### Переменные окружения
```bash
export OZON_API_KEY="ваш_api_ключ"
export OZON_CLIENT_ID="ваш_client_id"
```

### Зависимости
```bash
pip install httpx
```

## 🔧 Использование

### Базовое использование

```python
from modules.ozon_api import OzonAPI

# Создание экземпляра
ozon_api = OzonAPI()

# Получение соответствия offer_id → product_id
mapping_result = await ozon_api.get_product_mapping()
if mapping_result["success"]:
    mapping = mapping_result["mapping"]
    print(f"Найдено {len(mapping)} товаров")
```

### Полный цикл получения данных

```python
# Получение всех данных для конкретных offer_id
offer_ids = ["RV-01", "KU-1-PVK", "ZL-01"]
complete_result = await ozon_api.get_complete_product_data(offer_ids)

if complete_result["success"]:
    # Аналитика
    analytics = complete_result["analytics"]
    
    # Остатки
    stocks = complete_result["stocks"]
    
    # Соответствия
    mapping = complete_result["mapping"]
```

## 📊 Структура ответов

### Product Mapping
```python
{
    "success": True,
    "mapping": {
        "RV-01": 1982647068,
        "KU-1-PVK": 2343897403,
        "ZL-01": 2220053403
    },
    "total_count": 3,
    "page": 1,
    "page_size": 1000
}
```

### Analytics
```python
{
    "success": True,
    "data": {
        "result": {
            "data": [
                {
                    "dimensions": {"product_id": 1982647068},
                    "metrics": {
                        "ordered_units": 5,
                        "revenue": 15000
                    }
                }
            ]
        }
    },
    "period": "2024-01-01 - 2024-01-08",
    "product_count": 1
}
```

### Stocks
```python
{
    "success": True,
    "product_id": 1982647068,
    "total_stock": 25,
    "warehouse_stocks": [
        {
            "warehouse_id": 123,
            "present": 15,
            "reserved": 2
        }
    ],
    "raw_data": {...}
}
```

## 🧪 Тестирование

### Запуск тестов
```bash
python test_ozon_api.py
```

### Примеры использования
```bash
python examples/ozon_api_usage.py
```

## 🔍 Логирование

Модуль использует стандартное логирование Python. Для включения отладочных сообщений:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## ⚠️ Ограничения API

- **Rate Limiting:** API Ozon имеет ограничения на количество запросов
- **Таймауты:** Рекомендуется использовать таймауты 15-20 секунд
- **Пагинация:** Для больших объемов данных используйте пагинацию

## 🚨 Обработка ошибок

Все методы возвращают словарь с ключом `success`:
- `True` - операция выполнена успешно
- `False` - произошла ошибка (детали в ключе `error`)

```python
result = await ozon_api.get_stocks(product_id)
if not result["success"]:
    print(f"Ошибка: {result['error']}")
    return

# Используем данные
stock_data = result["total_stock"]
```

## 📈 Оптимизация

### Batch операции
Для получения данных по нескольким товарам используйте batch методы:
- `get_stocks_batch()` - остатки для нескольких товаров
- `get_complete_product_data()` - полный цикл для нескольких offer_id

### Кэширование
Рекомендуется кэшировать `product_mapping`, так как он редко изменяется.

## 🔐 Безопасность

- API ключи хранятся в переменных окружения
- Не коммитьте ключи в репозиторий
- Используйте `.env` файлы для локальной разработки

## 📞 Поддержка

При возникновении проблем:
1. Проверьте переменные окружения
2. Убедитесь в корректности API ключей
3. Проверьте логи на наличие ошибок
4. Убедитесь в доступности API Ozon

## 🔄 Обновления

Модуль автоматически адаптируется к изменениям API Ozon и использует актуальные эндпоинты согласно официальной документации.
