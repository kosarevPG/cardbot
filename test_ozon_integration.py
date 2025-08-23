#!/usr/bin/env python3
"""
Тестирование интеграции с Ozon API
Запуск: python test_ozon_integration.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули
try:
    from modules.ozon_api import OzonAPI
    from modules.ozon_sync import OzonDataSync
    print("✅ Модули ozon_api и ozon_sync импортированы успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта модулей: {e}")
    sys.exit(1)

# Проверяем переменные окружения
def check_environment():
    """Проверяет наличие необходимых переменных окружения"""
    print("\n🔍 Проверка переменных окружения...")
    
    required_vars = ["OZON_API_KEY", "OZON_CLIENT_ID"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value and value not in ["", "YOUR_OZON_API_KEY_HERE", "YOUR_OZON_CLIENT_ID_HERE"]:
            print(f"   ✅ {var}: {'*' * (len(value) - 4) + value[-4:] if len(value) > 4 else '*' * len(value)}")
        else:
            print(f"   ❌ {var}: НЕ НАСТРОЕН")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Отсутствуют переменные: {', '.join(missing_vars)}")
        print("   Установите их через переменные окружения или в local_config.py")
        return False
    
    print("   ✅ Все необходимые переменные настроены")
    return True

async def test_ozon_api_connection():
    """Тестирует подключение к Ozon API"""
    print("\n�� Тест подключения к Ozon API...")
    
    try:
        ozon_api = OzonAPI()
        print("   ✅ Объект OzonAPI создан успешно")
        
        # Тест подключения
        result = await ozon_api.test_connection()
        if result["success"]:
            print(f"   ✅ Подключение успешно: {result['message']}")
            return True
        else:
            print(f"   ❌ Ошибка подключения: {result['message']}")
            return False
            
    except Exception as e:
        print(f"   ❌ Критическая ошибка: {e}")
        return False

async def test_product_mapping():
    """Тестирует получение mapping товаров"""
    print("\n📋 Тест получения mapping товаров...")
    
    try:
        ozon_api = OzonAPI()
        
        # Получаем mapping с ограничением для теста
        result = await ozon_api.get_product_mapping(page_size=10, page=1)
        
        if result["success"]:
            mapping = result["mapping"]
            total_count = result["total_count"]
            
            print(f"   ✅ Получено {total_count} товаров")
            
            if mapping:
                print("   📦 Примеры товаров:")
                for i, (offer_id, product_id) in enumerate(list(mapping.items())[:3], 1):
                    print(f"      {i}. {offer_id} → {product_id}")
                
                if total_count > 3:
                    print(f"      ... и еще {total_count - 3} товаров")
                
                return True, mapping
            else:
                print("   ⚠️  Товары не найдены")
                return True, {}
        else:
            print(f"   ❌ Ошибка получения mapping: {result.get('error')}")
            return False, {}
            
    except Exception as e:
        print(f"   ❌ Критическая ошибка: {e}")
        return False, {}

async def test_analytics(mapping):
    """Тестирует получение аналитики"""
    print("\n📊 Тест получения аналитики...")
    
    if not mapping:
        print("   ⚠️  Нет товаров для тестирования аналитики")
        return False
    
    try:
        ozon_api = OzonAPI()
        
        # Берем первые 3 product_id для теста
        test_product_ids = list(mapping.values())[:3]
        print(f"   🔍 Тестируем аналитику для {len(test_product_ids)} товаров...")
        
        # Получаем аналитику за последние 7 дней
        date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        
        result = await ozon_api.get_analytics(test_product_ids, date_from, date_to)
        
        if result["success"]:
            print(f"   ✅ Аналитика получена успешно")
            print(f"   📅 Период: {result['period']}")
            print(f"   �� Товаров: {result['product_count']}")
            
            # Парсим данные аналитики
            data = result["data"]
            if "result" in data and "data" in data["result"]:
                analytics_data = data["result"]["data"]
                print(f"   �� Строк данных: {len(analytics_data)}")
                
                if analytics_data:
                    print("   📊 Пример данных:")
                    for i, row in enumerate(analytics_data[:2], 1):
                        product_id = row.get("dimensions", {}).get("product_id", "N/A")
                        ordered_units = row.get("metrics", {}).get("ordered_units", 0)
                        revenue = row.get("metrics", {}).get("revenue", 0.0)
                        print(f"      {i}. Product ID: {product_id}, Продажи: {ordered_units}, Выручка: {revenue} ₽")
            
            return True
        else:
            print(f"   ❌ Ошибка получения аналитики: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Критическая ошибка: {e}")
        return False

async def test_stocks(mapping):
    """Тестирует получение остатков"""
    print("\n📦 Тест получения остатков...")
    
    if not mapping:
        print("   ⚠️  Нет товаров для тестирования остатков")
        return False
    
    try:
        ozon_api = OzonAPI()
        
        # Берем первые 3 product_id для теста
        test_product_ids = list(mapping.values())[:3]
        print(f"   🔍 Тестируем остатки для {len(test_product_ids)} товаров...")
        
        # Получаем остатки batch запросом
        result = await ozon_api.get_stocks_batch(test_product_ids)
        
        if result["success"]:
            stocks = result["stocks"]
            successful = result["successful"]
            failed = result["failed"]
            
            print(f"   ✅ Остатки получены: {successful} успешно, {failed} ошибок")
            
            if stocks:
                print("   �� Данные по остаткам:")
                for product_id, stock_info in list(stocks.items())[:3]:
                    total_stock = stock_info.get("total_stock", 0)
                    warehouse_count = len(stock_info.get("warehouse_stocks", []))
                    print(f"      Product ID {product_id}: {total_stock} шт. (складов: {warehouse_count})")
            
            return True
        else:
            print(f"   ❌ Ошибка получения остатков: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Критическая ошибка: {e}")
        return False

async def test_complete_data(mapping):
    """Тестирует получение полных данных"""
    print("\n�� Тест получения полных данных...")
    
    if not mapping:
        print("   ⚠️  Нет товаров для тестирования полных данных")
        return False
    
    try:
        ozon_api = OzonAPI()
        
        # Берем первые 2 offer_id для теста
        test_offer_ids = list(mapping.keys())[:2]
        print(f"   🔍 Тестируем полные данные для {len(test_offer_ids)} товаров...")
        
        result = await ozon_api.get_complete_product_data(test_offer_ids)
        
        if result["success"]:
            summary = result["summary"]
            print(f"   ✅ Полные данные получены успешно")
            print(f"   📦 Всего offer_id: {summary['total_offers']}")
            print(f"   �� Найдено товаров: {summary['found_products']}")
            print(f"   �� Аналитика: {'✅' if summary['analytics_success'] else '❌'}")
            print(f"   📦 Остатки: {'✅' if summary['stocks_success'] else '❌'}")
            
            return True
        else:
            print(f"   ❌ Ошибка получения полных данных: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Критическая ошибка: {e}")
        return False

async def test_ozon_sync():
    """Тестирует функциональность синхронизации"""
    print("\n🔄 Тест функциональности синхронизации...")
    
    try:
        sync = OzonDataSync()
        print("   ✅ Объект OzonDataSync создан успешно")
        
        # Тестируем чтение offer_id из таблицы
        print("   📖 Тест чтения offer_id из Google таблицы...")
        offer_ids = await sync.read_offer_ids_from_sheet()
        
        if offer_ids:
            print(f"   ✅ Прочитано {len(offer_ids)} offer_id из таблицы")
            print(f"   📋 Примеры: {', '.join(offer_ids[:3])}")
            
            if len(offer_ids) > 3:
                print(f"      ... и еще {len(offer_ids) - 3}")
            
            return True
        else:
            print("   ⚠️  Offer ID не найдены в таблице")
            return False
            
    except Exception as e:
        print(f"   ❌ Критическая ошибка: {e}")
        return False

async def test_google_sheets_connection():
    """Тестирует подключение к Google Sheets"""
    print("\n�� Тест подключения к Google Sheets...")
    
    try:
        from modules.google_sheets import GoogleSheetsAPI
        
        sheets_api = GoogleSheetsAPI()
        print("   ✅ Объект GoogleSheetsAPI создан успешно")
        
        # Тестируем подключение к таблице
        spreadsheet_id = "1RoWWv9BgiwlSu9H-KJNsFItQxlUVhG1WMbyB0eFxzYM"
        sheet_name = "marketplaces"
        
        print(f"   �� Тест подключения к таблице {spreadsheet_id}...")
        
        # Пытаемся прочитать небольшой диапазон
        result = await sheets_api.get_sheet_data(spreadsheet_id, sheet_name, "A1:A5")
        
        if result["success"]:
            print("   ✅ Подключение к Google Sheets успешно")
            data = result["data"]
            print(f"   📊 Прочитано {len(data)} строк")
            return True
        else:
            print(f"   ❌ Ошибка подключения: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Критическая ошибка: {e}")
        return False

async def run_performance_test(mapping):
    """Запускает тест производительности"""
    print("\n⚡ Тест производительности...")
    
    if not mapping:
        print("   ⚠️  Нет товаров для тестирования производительности")
        return
    
    try:
        ozon_api = OzonAPI()
        
        # Тестируем время выполнения для разных размеров batch
        test_sizes = [1, 5, 10]
        
        for size in test_sizes:
            if len(mapping) >= size:
                test_product_ids = list(mapping.values())[:size]
                
                print(f"   🔍 Тест для {size} товаров...")
                
                start_time = datetime.now()
                
                # Тест получения остатков
                stocks_result = await ozon_api.get_stocks_batch(test_product_ids)
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                if stocks_result["success"]:
                    print(f"      ✅ Остатки ({size} товаров): {duration:.2f} сек")
                else:
                    print(f"      ❌ Ошибка получения остатков: {stocks_result.get('error')}")
                
                # Небольшая пауза между тестами
                await asyncio.sleep(1)
        
        print("   ✅ Тест производительности завершен")
        
    except Exception as e:
        print(f"   ❌ Ошибка теста производительности: {e}")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования интеграции с Ozon API")
    print("=" * 60)
    
    # Проверяем окружение
    if not check_environment():
        print("\n❌ Тестирование прервано из-за отсутствия настроек")
        return
    
    # Запускаем тесты
    tests = [
        ("Подключение к Ozon API", test_ozon_api_connection),
        ("Google Sheets подключение", test_google_sheets_connection),
        ("Mapping товаров", test_product_mapping),
        ("Аналитика", test_analytics),
        ("Остатки", test_stocks),
        ("Полные данные", test_complete_data),
        ("Синхронизация", test_ozon_sync),
    ]
    
    results = {}
    mapping = {}
    
    for test_name, test_func in tests:
        try:
            if test_name == "Mapping товаров":
                success, mapping_data = await test_func()
                results[test_name] = success
                if success:
                    mapping = mapping_data
            elif test_name == "Аналитика":
                results[test_name] = await test_func(mapping)
            elif test_name == "Остатки":
                results[test_name] = await test_func(mapping)
            elif test_name == "Полные данные":
                results[test_name] = await test_func(mapping)
            else:
                results[test_name] = await test_func()
                
        except Exception as e:
            print(f"   ❌ Неожиданная ошибка в тесте '{test_name}': {e}")
            results[test_name] = False
    
    # Тест производительности (если есть товары)
    if mapping:
        await run_performance_test(mapping)
    
    # Выводим итоговые результаты
    print("\n" + "=" * 60)
    print("�� ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print(f"{test_name:<25} {status}")
        if success:
            passed += 1
    
    print("-" * 60)
    print(f"Всего тестов: {total}")
    print(f"Пройдено: {passed}")
    print(f"Провалено: {total - passed}")
    
    if passed == total:
        print("\n�� ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("   Интеграция с Ozon API работает корректно")
    else:
        print(f"\n⚠️  ПРОВАЛЕНО {total - passed} ТЕСТОВ")
        print("   Проверьте настройки и логи для диагностики")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    # Запускаем тестирование
    asyncio.run(main())
