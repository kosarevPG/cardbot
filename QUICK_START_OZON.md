# 🚀 Быстрый старт с Ozon API

## 1. Настройка переменных окружения

```bash
# PowerShell
$env:OZON_API_KEY="ваш_api_ключ"
$env:OZON_CLIENT_ID="ваш_client_id"

# Bash
export OZON_API_KEY="ваш_api_ключ"
export OZON_CLIENT_ID="ваш_client_id"
```

## 2. Тестирование подключения

```bash
python test_ozon_api.py
```

## 3. Примеры использования

```bash
python examples/ozon_api_usage.py
```

## 4. Основные функции

### Получение соответствия offer_id → product_id
```python
from modules.ozon_api import OzonAPI

ozon_api = OzonAPI()
mapping = await ozon_api.get_product_mapping()
```

### Получение аналитики
```python
product_ids = [1982647068, 2343897403]
analytics = await ozon_api.get_analytics(product_ids, days=7)
```

### Получение остатков
```python
stocks = await ozon_api.get_stocks(product_id)
```

### Полный цикл
```python
offer_ids = ["RV-01", "KU-1-PVK"]
complete_data = await ozon_api.get_complete_product_data(offer_ids)
```

## 5. Что реализовано

✅ **POST /v2/product/list** - получение product_id по offer_id  
✅ **POST /v1/analytics/data** - аналитика продаж и выручки  
✅ **POST /v3/product/info/stocks** - остатки на складе  
✅ Batch операции для множественных товаров  
✅ Обработка ошибок и логирование  
✅ Полный цикл получения данных  

## 6. Структура файлов

- `modules/ozon_api.py` - основной модуль API
- `test_ozon_api.py` - тестирование
- `examples/ozon_api_usage.py` - примеры использования
- `OZON_API_README.md` - полная документация

## 7. Следующие шаги

1. Настройте переменные окружения
2. Запустите тесты
3. Изучите примеры
4. Интегрируйте в ваш проект

---

**Готово к использованию! 🎉**
