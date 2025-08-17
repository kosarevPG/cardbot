#!/usr/bin/env python3
"""
Тест исправлений Ozon API
Проверяет синтаксис и базовую функциональность
"""

import asyncio
import sys
import os

# Добавляем текущую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_ozon_api_import():
    """Тестирует импорт Ozon API модуля"""
    try:
        from modules.ozon_api import OzonAPI, test_ozon_connection
        print("✅ Импорт OzonAPI успешен")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта OzonAPI: {e}")
        return False

async def test_ozon_sync_import():
    """Тестирует импорт Ozon Sync модуля"""
    try:
        from modules.ozon_sync import OzonDataSync
        print("✅ Импорт OzonDataSync успешен")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта OzonDataSync: {e}")
        return False

async def test_marketplace_commands_import():
    """Тестирует импорт marketplace_commands"""
    try:
        from modules.marketplace_commands import register_marketplace_handlers
        print("✅ Импорт marketplace_commands успешен")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта marketplace_commands: {e}")
        return False

async def test_ozon_api_class():
    """Тестирует создание экземпляра OzonAPI"""
    try:
        from modules.ozon_api import OzonAPI
        
        # Проверяем, что класс можно создать (без API ключей)
        try:
            api = OzonAPI()
            print("✅ Экземпляр OzonAPI создан")
        except ValueError as e:
            if "API ключ Ozon не настроен" in str(e):
                print("✅ OzonAPI корректно проверяет API ключи")
            else:
                print(f"❌ Неожиданная ошибка при создании OzonAPI: {e}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Ошибка тестирования OzonAPI класса: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование исправлений Ozon API...\n")
    
    tests = [
        ("Импорт OzonAPI", test_ozon_api_import),
        ("Импорт OzonDataSync", test_ozon_sync_import),
        ("Импорт marketplace_commands", test_marketplace_commands_import),
        ("Создание OzonAPI", test_ozon_api_class),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"🔍 Тест: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            print()
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте {test_name}: {e}")
            results.append((test_name, False))
            print()
    
    # Итоговый отчет
    print("📊 ИТОГОВЫЙ ОТЧЕТ:")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{test_name}: {status}")
    
    print("=" * 50)
    print(f"Результат: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Исправления работают корректно.")
        return True
    else:
        print("⚠️ Некоторые тесты провалены. Требуется дополнительная отладка.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка тестирования: {e}")
        sys.exit(1)
