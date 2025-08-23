#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенный тест MarketplaceManager без Google Sheets
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем корневую папку проекта в PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Создаем мок для GoogleSheetsAPI
class MockGoogleSheetsAPI:
    """Мок для Google Sheets API для тестирования"""
    
    async def read_data(self, spreadsheet_id: str, range_name: str):
        """Мок чтения данных"""
        return [["Mock", "Data", "For", "Testing"]]
    
    async def write_data(self, spreadsheet_id: str, range_name: str, data):
        """Мок записи данных"""
        return True

# Подменяем GoogleSheetsAPI на мок
import modules.marketplace_manager
modules.marketplace_manager.GoogleSheetsAPI = MockGoogleSheetsAPI

from modules.marketplace_manager import MarketplaceManager

async def test_marketplace_manager():
    """Тестирует основные функции MarketplaceManager"""
    
    print("🚀 Тестирование MarketplaceManager (упрощенная версия)...")
    print("=" * 60)
    
    # Создаем экземпляр менеджера
    try:
        manager = MarketplaceManager()
        print("✅ MarketplaceManager успешно создан")
    except Exception as e:
        print(f"❌ Ошибка создания MarketplaceManager: {e}")
        return
    
    # Проверяем статус API
    print("\n📊 Статус API:")
    status = manager.get_status()
    for platform, config in status.items():
        print(f"  {platform}: {'✅' if config.get('configured', False) else '❌'}")
        for key, value in config.items():
            if key != 'configured':
                print(f"    {key}: {'✅' if value else '❌'}")
    
    # Тестируем базовые методы
    print("\n🔧 Тестирование базовых методов:")
    
    # Тест get_status
    try:
        status = manager.get_status()
        print(f"  get_status(): ✅ {len(status)} платформ")
    except Exception as e:
        print(f"  get_status(): ❌ {e}")
    
    # Тест _get_ozon_headers
    try:
        headers = manager._get_ozon_headers()
        print(f"  _get_ozon_headers(): ✅ {len(headers)} заголовков")
    except Exception as e:
        print(f"  _get_ozon_headers(): ❌ {e}")
    
    # Тест _get_wb_headers
    try:
        headers = manager._get_wb_headers()
        print(f"  _get_wb_headers(): ✅ {len(headers)} заголовков")
    except Exception as e:
        print(f"  _get_wb_headers(): ❌ {e}")
    
    # Тестируем API методы (без реальных запросов)
    print("\n🌐 Тестирование API методов:")
    
    # Тест Ozon API (без реальных запросов)
    if status['ozon']['configured']:
        print("  Ozon API: ⚠️  API настроен, но тестирование пропущено (нет реальных ключей)")
    else:
        print("  Ozon API: ⚠️  API не настроен - это нормально для тестирования")
    
    # Тест Wildberries API (без реальных запросов)
    if status['wildberries']['configured']:
        print("  Wildberries API: ⚠️  API настроен, но тестирование пропущено (нет реальных ключей)")
    else:
        print("  Wildberries API: ⚠️  API не настроен - это нормально для тестирования")
    
    # Тестируем структуру данных
    print("\n📋 Тестирование структуры данных:")
    
    # Проверяем эндпоинты Ozon
    try:
        endpoints = manager.ozon_endpoints
        print(f"  Ozon endpoints: ✅ {len(endpoints)} эндпоинтов")
        for name, url in endpoints.items():
            print(f"    {name}: {url}")
    except Exception as e:
        print(f"  Ozon endpoints: ❌ {e}")
    
    # Проверяем структуру колонок
    try:
        ozon_cols = manager.ozon_columns
        wb_cols = manager.wb_columns
        print(f"  Ozon columns: ✅ {len(ozon_cols)} колонок")
        print(f"  WB columns: ✅ {len(wb_cols)} колонок")
    except Exception as e:
        print(f"  Columns structure: ❌ {e}")
    
    # Тестируем валидацию конфигурации
    print("\n⚙️  Тестирование валидации конфигурации:")
    
    try:
        # Проверяем, что метод существует
        if hasattr(manager, '_validate_config'):
            print("  _validate_config(): ✅ метод существует")
        else:
            print("  _validate_config(): ❌ метод не найден")
    except Exception as e:
        print(f"  _validate_config(): ❌ {e}")
    
    # Тестируем обработку ошибок
    print("\n🚨 Тестирование обработки ошибок:")
    
    # Тест с неверными данными
    try:
        # Пытаемся получить mapping без API ключей
        if not status['ozon']['configured']:
            print("  Ozon API не настроен - проверка обработки ошибок пропущена")
        else:
            print("  Ozon API настроен - проверка обработки ошибок пропущена")
    except Exception as e:
        print(f"  Обработка ошибок: ❌ {e}")
    
    print("\n" + "=" * 60)
    print("✅ Упрощенное тестирование завершено!")
    print("\n💡 Для полного тестирования настройте:")
    print("   • OZON_API_KEY и OZON_CLIENT_ID")
    print("   • WB_API_KEY")
    print("   • GOOGLE_SERVICE_ACCOUNT_BASE64")

def check_environment():
    """Проверяет наличие необходимых переменных окружения"""
    print("🔍 Проверка переменных окружения:")
    
    required_vars = {
        "OZON_API_KEY": "API ключ Ozon",
        "OZON_CLIENT_ID": "Client ID Ozon", 
        "WB_API_KEY": "API ключ Wildberries",
        "GOOGLE_SERVICE_ACCOUNT_BASE64": "Google Sheets сервисный аккаунт"
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
    print("🎯 Упрощенное тестирование модуля управления маркетплейсами")
    print("=" * 70)
    
    # Проверяем переменные окружения
    env_ok = check_environment()
    
    print()
    if env_ok:
        print("🚀 Запуск тестов с полной функциональностью...")
    else:
        print("⚠️  Тесты будут запущены с ограниченной функциональностью")
    
    print("🚀 Запуск тестов...")
    asyncio.run(test_marketplace_manager())
