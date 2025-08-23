#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для MarketplaceManager
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую папку проекта в PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.marketplace_manager import MarketplaceManager

async def test_marketplace_manager():
    """Тестирует основные функции MarketplaceManager"""
    
    print("🚀 Тестирование MarketplaceManager...")
    print("=" * 50)
    
    # Создаем экземпляр менеджера
    manager = MarketplaceManager()
    
    # Проверяем статус API
    print("\n📊 Статус API:")
    status = manager.get_status()
    for platform, config in status.items():
        print(f"  {platform}: {'✅' if config.get('configured', False) else '❌'}")
        for key, value in config.items():
            if key != 'configured':
                print(f"    {key}: {'✅' if value else '❌'}")
    
    # Тестируем подключения
    print("\n🔗 Тестирование подключений:")
    try:
        connections = await manager.test_connections()
        for platform, result in connections.items():
            if result is True:
                print(f"  {platform}: ✅ Подключение успешно")
            elif isinstance(result, str) and result.startswith("API не настроен"):
                print(f"  {platform}: ⚠️  {result}")
            else:
                print(f"  {platform}: ❌ {result}")
    except Exception as e:
        print(f"  Ошибка тестирования подключений: {e}")
    
    # Тестируем синхронизацию (если API настроены)
    print("\n🔄 Тестирование синхронизации:")
    
    if status['ozon']['configured']:
        print("  Ozon: Тестируем синхронизацию...")
        try:
            result = await manager.sync_ozon_data()
            if result['success']:
                print(f"    ✅ {result['message']}")
            else:
                print(f"    ❌ {result['error']}")
        except Exception as e:
            print(f"    ❌ Ошибка: {e}")
    else:
        print("  Ozon: API не настроен, пропускаем")
    
    if status['wildberries']['configured']:
        print("  Wildberries: Тестируем синхронизацию...")
        try:
            result = await manager.sync_wb_data()
            if result['success']:
                print(f"    ✅ {result['message']}")
            else:
                print(f"    ❌ {result['error']}")
        except Exception as e:
            print(f"    ❌ Ошибка: {e}")
    else:
        print("  Wildberries: API не настроен, пропускаем")
    
    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")

def check_environment():
    """Проверяет наличие необходимых переменных окружения"""
    print("🔍 Проверка переменных окружения:")
    
    required_vars = {
        "OZON_API_KEY": "API ключ Ozon",
        "OZON_CLIENT_ID": "Client ID Ozon", 
        "WB_API_KEY": "API ключ Wildberries"
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  {var}: ✅ {description} (настроен)")
        else:
            print(f"  {var}: ❌ {description} (не настроен)")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Для полного тестирования настройте переменные: {', '.join(missing_vars)}")
        print("   Создайте файл .env или установите переменные окружения")
    
    return len(missing_vars) == 0

if __name__ == "__main__":
    print("🎯 Тестирование модуля управления маркетплейсами")
    print("=" * 60)
    
    # Проверяем переменные окружения
    env_ok = check_environment()
    
    print()
    if env_ok:
        print("🚀 Запуск тестов...")
        asyncio.run(test_marketplace_manager())
    else:
        print("⚠️  Тесты будут запущены с ограниченной функциональностью")
        print("🚀 Запуск тестов...")
        asyncio.run(test_marketplace_manager())
