# 🏪 MarketplaceManager - Управление маркетплейсами

## 📋 Описание

`MarketplaceManager` - это единый модуль для работы с маркетплейсами Ozon и Wildberries. Он объединяет функциональность API клиентов, синхронизацию данных и интеграцию с Google Sheets.

## 🚀 Основные возможности

### ✅ Поддерживаемые платформы:
- **Ozon** - полная интеграция с API продавца
- **Wildberries** - интеграция с API поставщика
- **Google Sheets** - автоматическая синхронизация данных

### 🔧 Функции:
- Получение остатков товаров
- Синхронизация с Google таблицами
- Аналитика продаж и выручки
- Тестирование подключений
- Единообразное API для всех платформ

## 📦 Установка и настройка

### 1. Переменные окружения

Создайте файл `.env` или установите переменные окружения:

```bash
# Ozon API
OZON_API_KEY=your_ozon_api_key
OZON_CLIENT_ID=your_ozon_client_id

# Wildberries API
WB_API_KEY=your_wb_api_key

# Google Sheets (если используется)
GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
```

### 2. Импорт модуля

```python
from modules.marketplace_manager import MarketplaceManager

# Создание экземпляра
manager = MarketplaceManager()
```

## 📚 API Reference

### Основные методы

#### `get_status() -> Dict[str, Any]`
Возвращает статус всех API маркетплейсов.

```python
status = manager.get_status()
print(f"Ozon: {'✅' if status['ozon']['configured'] else '❌'}")
```

#### `test_connections() -> Dict[str, Union[bool, str]]`
Тестирует подключения ко всем API.

```python
connections = await manager.test_connections()
for platform, result in connections.items():
    if result is True:
        print(f"{platform}: Подключение успешно")
```

### Ozon API методы

#### `get_ozon_product_mapping(page_size: int = 1000) -> Dict`
Получает соответствие offer_id → product_id.

```python
result = await manager.get_ozon_product_mapping()
if result['success']:
    mapping = result['mapping']
    print(f"Получено {len(mapping)} товаров")
```

#### `get_ozon_stocks(product_ids: List[int]) -> Dict`
Получает остатки товаров по product_id.

```python
result = await manager.get_ozon_stocks([12345, 67890])
if result['success']:
    stocks = result['stocks']
    print(f"Остатки: {stocks}")
```

#### `get_ozon_analytics(date_from: str, date_to: str) -> Dict`
Получает аналитику продаж и выручки.

```python
result = await manager.get_ozon_analytics("2024-01-01", "2024-01-31")
if result['success']:
    analytics = result['analytics']
    print(f"Аналитика: {analytics}")
```

### Wildberries API методы

#### `get_wb_stocks() -> Dict`
Получает остатки товаров Wildberries.

```python
result = await manager.get_wb_stocks()
if result['success']:
    stocks = result['stocks']
    print(f"Остатки WB: {len(stocks)} товаров")
```

#### `get_wb_analytics(date_from: str, date_to: str) -> Dict`
Получает аналитику Wildberries.

```python
result = await manager.get_wb_analytics("2024-01-01", "2024-01-31")
if result['success']:
    analytics = result['analytics']
    print(f"Аналитика WB: {analytics}")
```

### Синхронизация

#### `sync_ozon_data() -> Dict`
Синхронизирует данные Ozon с Google таблицами.

```python
result = await manager.sync_ozon_data()
if result['success']:
    print(f"✅ {result['message']}")
    print(f"Синхронизировано: {len(result['data'])} товаров")
else:
    print(f"❌ {result['error']}")
```

#### `sync_wb_data() -> Dict`
Синхронизирует данные Wildberries с Google таблицами.

```python
result = await manager.sync_wb_data()
if result['success']:
    print(f"✅ {result['message']}")
    print(f"Синхронизировано: {len(result['data'])} товаров")
else:
    print(f"❌ {result['error']}")
```

#### `sync_all_marketplaces() -> Dict`
Синхронизирует все маркетплейсы одновременно.

```python
results = await manager.sync_all_marketplaces()
for platform, result in results.items():
    if result['success']:
        print(f"✅ {platform}: {result['message']}")
    else:
        print(f"❌ {platform}: {result['error']}")
```

## 📊 Структура Google таблиц

### Ozon данные (колонки D-J):
- **D** - offer_id (артикул)
- **E** - (пустая)
- **F** - остаток
- **G** - (пустая)
- **H** - продажи
- **I** - (пустая)
- **J** - выручка

### Wildberries данные (колонки B-I):
- **B** - nm_id (артикул)
- **C** - (пустая)
- **D** - (пустая)
- **E** - остаток
- **F** - (пустая)
- **G** - продажи
- **H** - (пустая)
- **I** - выручка

## 🔍 Обработка ошибок

Все методы возвращают единообразный формат ответа:

```python
{
    "success": bool,           # True/False
    "message": str,           # Сообщение об успехе
    "error": str,             # Описание ошибки (если success=False)
    "data": Any,              # Данные (если success=True)
    # ... другие поля
}
```

### Пример обработки:

```python
result = await manager.sync_ozon_data()

if result['success']:
    # Успешное выполнение
    print(f"✅ {result['message']}")
    data = result['data']
    # Обрабатываем данные
else:
    # Ошибка
    print(f"❌ {result['error']}")
    # Логируем ошибку или уведомляем пользователя
```

## 🧪 Тестирование

Запустите тестовый скрипт:

```bash
python test_marketplace_manager.py
```

Скрипт проверит:
- Настройку переменных окружения
- Подключения к API
- Синхронизацию данных
- Работу с Google Sheets

## 📝 Примеры использования

### Базовый пример:

```python
import asyncio
from modules.marketplace_manager import MarketplaceManager

async def main():
    manager = MarketplaceManager()
    
    # Проверяем статус
    status = manager.get_status()
    print(f"Ozon настроен: {status['ozon']['configured']}")
    
    # Синхронизируем все маркетплейсы
    results = await manager.sync_all_marketplaces()
    
    for platform, result in results.items():
        if result['success']:
            print(f"✅ {platform}: {result['message']}")
        else:
            print(f"❌ {platform}: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Работа с конкретным маркетплейсом:

```python
async def sync_ozon_only():
    manager = MarketplaceManager()
    
    # Получаем mapping товаров
    mapping_result = await manager.get_ozon_product_mapping()
    if not mapping_result['success']:
        print(f"Ошибка: {mapping_result['error']}")
        return
    
    # Получаем остатки
    product_ids = list(mapping_result['mapping'].values())
    stocks_result = await manager.get_ozon_stocks(product_ids)
    
    if stocks_result['success']:
        print(f"Остатки получены: {len(stocks_result['stocks'])} товаров")
    else:
        print(f"Ошибка получения остатков: {stocks_result['error']}")
```

## 🔧 Интеграция с ботом

См. файл `examples/marketplace_bot_commands.py` для примеров команд Telegram бота.

## 🚨 Лимиты и ограничения

### Ozon API:
- Лимит запросов: зависит от тарифа
- Размер страницы: до 1000 товаров
- Таймаут: 20 секунд для больших запросов

### Wildberries API:
- Лимит запросов: зависит от тарифа
- Таймаут: 15 секунд

### Google Sheets:
- Лимит запросов: 100 запросов в минуту
- Размер данных: до 10MB на запрос

## 🆘 Устранение неполадок

### Частые проблемы:

1. **"API не настроен"** - проверьте переменные окружения
2. **"Ошибка подключения"** - проверьте интернет и доступность API
3. **"Ошибка Google Sheets"** - проверьте права доступа и credentials

### Логирование:

Все операции логируются через стандартный Python logger. Уровень логирования можно настроить в основном приложении.

## 🔮 Планы развития

- [ ] Кеширование данных для уменьшения нагрузки на API
- [ ] Автоматическая синхронизация по расписанию
- [ ] Уведомления об ошибках синхронизации
- [ ] Поддержка других маркетплейсов (Яндекс.Маркет, AliExpress)
- [ ] Дашборд для мониторинга синхронизаций
- [ ] Экспорт данных в другие форматы (CSV, Excel)

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи
2. Запустите тестовый скрипт
3. Убедитесь в корректности настроек
4. Проверьте документацию API маркетплейсов
