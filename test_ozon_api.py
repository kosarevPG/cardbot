#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы обновленного Ozon API
"""

import asyncio
import os
from modules.ozon_api import OzonAPI, test_ozon_connection

async def test_ozon_api():
    """Тестирует основные функции Ozon API"""
    
    print("🧪 Тестирование Ozon API...")
    print("=" * 50)
    
    # Проверяем переменные окружения
    api_key = os.getenv("OZON_API_KEY")
    client_id = os.getenv("OZON_CLIENT_ID")
    
    if not api_key:
        print("❌ OZON_API_KEY не найден в переменных окружения")
        print("Установите переменную: export OZON_API_KEY='ваш_ключ'")
        return
    
    if not client_id:
        print("❌ OZON_CLIENT_ID не найден в переменных окружения")
        print("Установите переменную: export OZON_CLIENT_ID='ваш_client_id'")
        return
    
    print(f"✅ API Key: {api_key[:8]}...")
    print(f"✅ Client ID: {client_id[:8]}...")
    print()
    
    try:
        # Создаем экземпляр API
        ozon_api = OzonAPI()
        print("✅ OzonAPI инициализирован успешно")
        
        # Тест подключения
        print("\n🔗 Тестирование подключения...")
        connection_result = await ozon_api.test_connection()
        if connection_result["success"]:
            print(f"✅ {connection_result['message']}")
        else:
            print(f"❌ {connection_result['message']}")
            return
        
        # Тест получения product_mapping
        print("\n📋 Тестирование получения product_mapping...")
        mapping_result = await ozon_api.get_product_mapping(page_size=10, page=1)
        if mapping_result["success"]:
            mapping = mapping_result["mapping"]
            print(f"✅ Получено {len(mapping)} соответствий offer_id → product_id")
            if mapping:
                print("Примеры соответствий:")
                for i, (offer_id, product_id) in enumerate(list(mapping.items())[:5]):
                    print(f"  {offer_id} → {product_id}")
                
                # Тест получения аналитики для первых 2 товаров
                if len(mapping) >= 2:
                    product_ids = list(mapping.values())[:2]
                    print(f"\n📊 Тестирование аналитики для {len(product_ids)} товаров...")
                    analytics_result = await ozon_api.get_analytics(product_ids, days=7)
                    if analytics_result["success"]:
                        print("✅ Аналитика получена успешно")
                        print(f"   Период: {analytics_result['period']}")
                        print(f"   Товаров: {analytics_result['product_count']}")
                    else:
                        print(f"❌ Ошибка получения аналитики: {analytics_result['error']}")
                
                # Тест получения остатков для первого товара
                if mapping:
                    first_product_id = list(mapping.values())[0]
                    print(f"\n📦 Тестирование получения остатков для product_id {first_product_id}...")
                    stocks_result = await ozon_api.get_stocks(first_product_id)
                    if stocks_result["success"]:
                        print("✅ Остатки получены успешно")
                        print(f"   Общий остаток: {stocks_result['total_stock']}")
                        print(f"   Складов: {len(stocks_result['warehouse_stocks'])}")
                    else:
                        print(f"❌ Ошибка получения остатков: {stocks_result['error']}")
                
                # Тест полного цикла получения данных
                if len(mapping) >= 2:
                    test_offer_ids = list(mapping.keys())[:2]
                    print(f"\n🔄 Тестирование полного цикла для {len(test_offer_ids)} товаров...")
                    complete_result = await ozon_api.get_complete_product_data(test_offer_ids)
                    if complete_result["success"]:
                        print("✅ Полный цикл выполнен успешно")
                        summary = complete_result["summary"]
                        print(f"   Обработано offer_id: {summary['total_offers']}")
                        print(f"   Найдено product_id: {summary['found_products']}")
                        print(f"   Аналитика: {'✅' if summary['analytics_success'] else '❌'}")
                        print(f"   Остатки: {'✅' if summary['stocks_success'] else '❌'}")
                    else:
                        print(f"❌ Ошибка полного цикла: {complete_result['error']}")
            else:
                print("⚠️  Соответствия не найдены (возможно, нет товаров в аккаунте)")
        else:
            print(f"❌ Ошибка получения product_mapping: {mapping_result['error']}")
        
        print("\n" + "=" * 50)
        print("🎉 Тестирование завершено!")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Запускаем тест
    asyncio.run(test_ozon_api())
