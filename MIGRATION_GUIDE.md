# 🚀 Руководство по миграции на MarketplaceManager

## 📋 Обзор изменений

Мы объединили два модуля (`ozon_api.py` и `ozon_sync.py`) в один универсальный `marketplace_manager.py` для лучшей управляемости кода и избежания дублирования.

## 🔄 Что изменилось

### ✅ Преимущества нового подхода:
- **Единая точка входа** для всех маркетплейсов
- **Устранение дублирования** кода
- **Лучшая структура** и читаемость
- **Единообразное API** для всех платформ
- **Централизованная обработка ошибок**

### 📁 Новые файлы:
- `modules/marketplace_manager.py` - основной модуль
- `test_marketplace_manager.py` - тестовый скрипт

### 🗑️ Файлы для удаления (после миграции):
- `modules/ozon_api.py`
- `modules/ozon_sync.py`

## 🔧 Шаги миграции

### 1. Обновление импортов

Замените все импорты в вашем коде:

```python
# ❌ Старый способ
from modules.ozon_api import OzonAPI
from modules.ozon_sync import OzonDataSync

# ✅ Новый способ
from modules.marketplace_manager import MarketplaceManager
```

### 2. Обновление инициализации

```python
# ❌ Старый способ
ozon_api = OzonAPI()
ozon_sync = OzonDataSync()

# ✅ Новый способ
marketplace_manager = MarketplaceManager()
```

### 3. Обновление вызовов методов

#### Получение mapping товаров:
```python
# ❌ Старый способ
mapping = await ozon_api.get_product_mapping()

# ✅ Новый способ
result = await marketplace_manager.get_ozon_product_mapping()
if result['success']:
    mapping = result['mapping']
```

#### Синхронизация данных:
```python
# ❌ Старый способ
await ozon_sync.sync_ozon_data()

# ✅ Новый способ
result = await marketplace_manager.sync_ozon_data()
if result['success']:
    print(result['message'])
```

#### Синхронизация всех маркетплейсов:
```python
# ❌ Старый способ - нужно было делать отдельно
await ozon_sync.sync_ozon_data()
# await wb_sync.sync_wb_data() - если был

# ✅ Новый способ - одной командой
results = await marketplace_manager.sync_all_marketplaces()
for platform, result in results.items():
    if result['success']:
        print(f"{platform}: {result['message']}")
```

## 📊 Новые возможности

### 1. Единый статус всех API
```python
status = marketplace_manager.get_status()
print(f"Ozon: {'✅' if status['ozon']['configured'] else '❌'}")
print(f"Wildberries: {'✅' if status['wildberries']['configured'] else '❌'}")
```

### 2. Тестирование подключений
```python
connections = await marketplace_manager.test_connections()
for platform, result in connections.items():
    if result is True:
        print(f"{platform}: Подключение успешно")
    else:
        print(f"{platform}: {result}")
```

### 3. Автоматическая обработка ошибок
```python
# Все методы возвращают единообразный формат ответа
result = await marketplace_manager.sync_ozon_data()
if result['success']:
    print(f"Успешно: {result['message']}")
    print(f"Данные: {result['data']}")
else:
    print(f"Ошибка: {result['error']}")
```

## 🧪 Тестирование

Запустите тестовый скрипт для проверки:

```bash
python test_marketplace_manager.py
```

## 🔒 Переменные окружения

Убедитесь, что у вас настроены все необходимые переменные:

```bash
# Ozon API
OZON_API_KEY=your_ozon_api_key
OZON_CLIENT_ID=your_ozon_client_id

# Wildberries API
WB_API_KEY=your_wb_api_key

# Google Sheets (если используется)
GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
```

## 📝 Примеры использования

### Базовое использование:
```python
from modules.marketplace_manager import MarketplaceManager

async def main():
    manager = MarketplaceManager()
    
    # Проверяем статус
    status = manager.get_status()
    
    # Синхронизируем все маркетплейсы
    results = await manager.sync_all_marketplaces()
    
    # Обрабатываем результаты
    for platform, result in results.items():
        if result['success']:
            print(f"✅ {platform}: {result['message']}")
        else:
            print(f"❌ {platform}: {result['error']}")

# Запуск
asyncio.run(main())
```

### Работа с конкретным маркетплейсом:
```python
async def sync_ozon_only():
    manager = MarketplaceManager()
    
    # Получаем mapping товаров
    mapping_result = await manager.get_ozon_product_mapping()
    if not mapping_result['success']:
        print(f"Ошибка получения mapping: {mapping_result['error']}")
        return
    
    # Получаем остатки
    product_ids = list(mapping_result['mapping'].values())
    stocks_result = await manager.get_ozon_stocks(product_ids)
    
    if stocks_result['success']:
        print(f"Получено остатков: {len(stocks_result['stocks'])}")
    else:
        print(f"Ошибка получения остатков: {stocks_result['error']}")
```

## ⚠️ Важные замечания

1. **Все методы асинхронные** - используйте `await`
2. **Все методы возвращают словарь** с ключом `success`
3. **Обрабатывайте ошибки** через проверку `result['success']`
4. **Логирование** происходит автоматически через стандартный logger

## 🆘 Поддержка

Если возникнут проблемы при миграции:

1. Проверьте логи на наличие ошибок
2. Убедитесь, что все переменные окружения настроены
3. Запустите тестовый скрипт для диагностики
4. Проверьте, что Google Sheets API настроен корректно

## 🎯 Следующие шаги

После успешной миграции:

1. Удалите старые файлы `ozon_api.py` и `ozon_sync.py`
2. Обновите документацию проекта
3. Добавьте новые команды в бота для управления маркетплейсами
4. Настройте автоматическую синхронизацию через планировщик
