#!/usr/bin/env python3
"""
Пример использования обновленного Ozon API
Демонстрирует все три основных метода:
1. Получение product_id по offer_id
2. Получение аналитики (продажи, выручка)
3. Остатки на складе
"""

import asyncio
import os
from datetime import datetime, timedelta
from modules.ozon_api import OzonAPI

async def example_usage():
    """Пример использования Ozon API"""
    
    print("🚀 Пример использования Ozon API")
    print("=" * 50)
    
    # Проверяем переменные окружения
    if not os.getenv("OZON_API_KEY") or not os.getenv("OZON_CLIENT_ID"):
        print("❌ Установите переменные окружения:")
        print("   export OZON_API_KEY='ваш_api_ключ'")
        print("   export OZON_CLIENT_ID='ваш_client_id'")
        return
    
    try:
        # Создаем экземпляр API
        ozon_api = OzonAPI()
        print("✅ OzonAPI инициализирован")
        
        # 1. Получение product_id по offer_id
        print("\n📋 1. Получение product_id по offer_id...")
        mapping_result = await ozon_api.get_product_mapping(page_size=100, page=1)
        
        if not mapping_result["success"]:
            print(f"❌ Ошибка: {mapping_result['error']}")
            return
        
        mapping = mapping_result["mapping"]
        print(f"✅ Получено {len(mapping)} соответствий offer_id → product_id")
        
        if not mapping:
            print("⚠️  Нет товаров для работы")
            return
        
        # Показываем первые 5 соответствий
        print("Примеры соответствий:")
        for i, (offer_id, product_id) in enumerate(list(mapping.items())[:5]):
            print(f"  {offer_id} → {product_id}")
        
        # 2. Получение аналитики для первых 3 товаров
        print(f"\n📊 2. Получение аналитики для {min(3, len(mapping))} товаров...")
        product_ids = list(mapping.values())[:3]
        
        # Аналитика за последние 7 дней
        analytics_result = await ozon_api.get_analytics(product_ids, days=7)
        
        if analytics_result["success"]:
            print("✅ Аналитика получена успешно")
            print(f"   Период: {analytics_result['period']}")
            print(f"   Товаров: {analytics_result['product_count']}")
            
            # Показываем данные аналитики
            data = analytics_result["data"]
            if "result" in data and "data" in data["result"]:
                analytics_data = data["result"]["data"]
                print(f"   Записей аналитики: {len(analytics_data)}")
                
                # Показываем первые записи
                for i, record in enumerate(analytics_data[:3]):
                    print(f"   Запись {i+1}: {record}")
        else:
            print(f"❌ Ошибка получения аналитики: {analytics_result['error']}")
        
        # 3. Получение остатков для первых 3 товаров
        print(f"\n📦 3. Получение остатков для {min(3, len(mapping))} товаров...")
        stocks_result = await ozon_api.get_stocks_batch(product_ids)
        
        if stocks_result["success"]:
            print("✅ Остатки получены успешно")
            print(f"   Обработано: {stocks_result['total_processed']}")
            print(f"   Успешно: {stocks_result['successful']}")
            print(f"   Ошибок: {stocks_result['failed']}")
            
            # Показываем остатки по каждому товару
            for product_id, stock_data in stocks_result["stocks"].items():
                offer_id = [k for k, v in mapping.items() if v == product_id][0]
                total_stock = stock_data["total_stock"]
                warehouses = len(stock_data["warehouse_stocks"])
                print(f"   {offer_id} (ID: {product_id}): {total_stock} шт. на {warehouses} складах")
        else:
            print(f"❌ Ошибка получения остатков: {stocks_result['error']}")
        
        # 4. Полный цикл получения данных
        print(f"\n🔄 4. Полный цикл получения данных для {min(2, len(mapping))} товаров...")
        test_offer_ids = list(mapping.keys())[:2]
        complete_result = await ozon_api.get_complete_product_data(test_offer_ids)
        
        if complete_result["success"]:
            print("✅ Полный цикл выполнен успешно")
            summary = complete_result["summary"]
            print(f"   Обработано offer_id: {summary['total_offers']}")
            print(f"   Найдено product_id: {summary['found_products']}")
            print(f"   Аналитика: {'✅' if summary['analytics_success'] else '❌'}")
            print(f"   Остатки: {'✅' if summary['stocks_success'] else '❌'}")
            
            # Показываем детали по каждому товару
            for offer_id, product_id in complete_result["mapping"].items():
                print(f"\n   Товар: {offer_id} (ID: {product_id})")
                
                # Аналитика
                if complete_result["analytics"]["success"]:
                    analytics_data = complete_result["analytics"]["data"]
                    if "result" in analytics_data and "data" in analytics_data["result"]:
                        for record in analytics_data["result"]["data"]:
                            if record.get("dimensions", {}).get("product_id") == product_id:
                                ordered_units = record.get("metrics", {}).get("ordered_units", 0)
                                revenue = record.get("metrics", {}).get("revenue", 0)
                                print(f"     📊 Продажи: {ordered_units} шт., Выручка: {revenue} ₽")
                
                # Остатки
                if complete_result["stocks"]["success"] and product_id in complete_result["stocks"]["stocks"]:
                    stock_data = complete_result["stocks"]["stocks"][product_id]
                    total_stock = stock_data["total_stock"]
                    warehouses = len(stock_data["warehouse_stocks"])
                    print(f"     📦 Остаток: {total_stock} шт. на {warehouses} складах")
        else:
            print(f"❌ Ошибка полного цикла: {complete_result['error']}")
        
        print("\n" + "=" * 50)
        print("🎉 Пример использования завершен!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

async def example_specific_offers():
    """Пример работы с конкретными offer_id"""
    
    print("\n🎯 Пример работы с конкретными offer_id")
    print("=" * 50)
    
    try:
        ozon_api = OzonAPI()
        
        # Пример offer_id (замените на реальные)
        example_offer_ids = ["RV-01", "KU-1-PVK", "ZL-01"]
        print(f"Тестируем offer_id: {example_offer_ids}")
        
        # Получаем полные данные
        complete_result = await ozon_api.get_complete_product_data(example_offer_ids)
        
        if complete_result["success"]:
            print("✅ Данные получены успешно")
            
            for offer_id, product_id in complete_result["mapping"].items():
                print(f"\n📦 {offer_id} → {product_id}")
                
                # Аналитика
                if complete_result["analytics"]["success"]:
                    analytics_data = complete_result["analytics"]["data"]
                    if "result" in analytics_data and "data" in analytics_data["result"]:
                        for record in analytics_data["result"]["data"]:
                            if record.get("dimensions", {}).get("product_id") == product_id:
                                ordered_units = record.get("metrics", {}).get("ordered_units", 0)
                                revenue = record.get("metrics", {}).get("revenue", 0)
                                print(f"   📊 Продажи: {ordered_units} шт., Выручка: {revenue} ₽")
                
                # Остатки
                if complete_result["stocks"]["success"] and product_id in complete_result["stocks"]["stocks"]:
                    stock_data = complete_result["stocks"]["stocks"][product_id]
                    total_stock = stock_data["total_stock"]
                    print(f"   📦 Остаток: {total_stock} шт.")
        else:
            print(f"❌ Ошибка: {complete_result['error']}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    # Запускаем примеры
    asyncio.run(example_usage())
    asyncio.run(example_specific_offers())
