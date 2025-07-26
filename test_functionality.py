#!/usr/bin/env python3
"""
Комплексное тестирование функциональности бота
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_local import NO_LOGS_USERS, ADMIN_ID
from database.db import Database
from modules.logging_service import LoggingService
from modules.user_management import UserManager

def test_database_connection():
    """Тест подключения к БД"""
    print("🔍 Тест подключения к БД...")
    try:
        db = Database('database/dev.db')
        print("✅ Подключение к БД успешно")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False

def test_user_management():
    """Тест управления пользователями"""
    print("\n👥 Тест управления пользователями...")
    try:
        db = Database('database/dev.db')
        user_manager = UserManager(db)
        
        # Тест получения всех пользователей
        all_users = db.get_all_users()
        print(f"✅ Всего пользователей в БД: {len(all_users)}")
        
        # Тест исключения админских ID
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        filtered_users = [uid for uid in all_users if uid not in excluded_users]
        print(f"✅ После исключения админских ID: {len(filtered_users)}")
        
        # Тест получения данных пользователя
        if all_users:
            test_user_id = all_users[0]
            user_data = db.get_user(test_user_id)
            print(f"✅ Данные пользователя {test_user_id}: {user_data['name']}")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка управления пользователями: {e}")
        return False

def test_logging_service():
    """Тест сервиса логирования"""
    print("\n📝 Тест сервиса логирования...")
    try:
        db = Database('database/dev.db')
        logger_service = LoggingService(db)
        
        # Тест логирования действия (пропускаем асинхронный тест)
        print("✅ Логирование действия (асинхронный метод, пропускаем в тестах)")
        
        # Тест логирования сценария (используем метод БД напрямую)
        test_user_id = 999999999  # Тестовый пользователь
        db.log_scenario_step(test_user_id, "test_scenario", "test_step", {"test": "data"})
        print("✅ Логирование шага сценария успешно")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка сервиса логирования: {e}")
        return False

def test_admin_metrics():
    """Тест админских метрик"""
    print("\n📊 Тест админских метрик...")
    try:
        db = Database('database/dev.db')
        
        # Тест метрик удержания
        retention = db.get_retention_metrics(7)
        print(f"✅ Метрики удержания (D1): {retention['d1_retention']}%")
        print(f"✅ Метрики удержания (D7): {retention['d7_retention']}%")
        
        # Тест DAU
        dau = db.get_dau_metrics(7)
        print(f"✅ DAU за 7 дней: {len(dau)} записей")
        
        # Тест воронки карты дня
        funnel = db.get_card_funnel_metrics(7)
        print(f"✅ Воронка карты дня: {funnel['completion_rate']}%")
        
        # Тест метрик ценности
        value = db.get_value_metrics(7)
        print(f"✅ Resource Lift: {value['resource_lift']['positive_pct']}%")
        print(f"✅ Feedback Score: {value['feedback_score']}%")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка админских метрик: {e}")
        return False

def test_advanced_user_stats():
    """Тест расширенной статистики пользователей"""
    print("\n🎯 Тест расширенной статистики пользователей...")
    try:
        db = Database('database/dev.db')
        
        # Получаем тестового пользователя
        all_users = db.get_all_users()
        if all_users:
            test_user_id = all_users[0]
            advanced_stats = db.get_user_advanced_stats(test_user_id)
            
            print(f"✅ Статистика для пользователя {test_user_id}:")
            print(f"  • Максимальная серия дней: {advanced_stats.get('max_consecutive_days', 0)}")
            print(f"  • Текущая серия: {advanced_stats.get('current_streak', 0)}")
            print(f"  • Любимое время: {advanced_stats.get('favorite_time', 'не определено')}")
            print(f"  • Процент завершения: {advanced_stats.get('completion_rate', 0):.1f}%")
            print(f"  • Достижения: {len(advanced_stats.get('achievements', []))}")
        else:
            print("⚠️ Нет пользователей для тестирования")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка расширенной статистики: {e}")
        return False

def test_scenario_logging():
    """Тест логирования сценариев"""
    print("\n🔄 Тест логирования сценариев...")
    try:
        db = Database('database/dev.db')
        
        # Тест статистики сценариев
        scenario_stats = db.get_scenario_stats(7)
        print(f"✅ Статистика сценариев: {scenario_stats} сессий")
        
        # Тест статистики шагов
        step_stats = db.get_scenario_step_stats('card_of_day', 7)
        print(f"✅ Статистика шагов карты дня: {len(step_stats)} записей")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка логирования сценариев: {e}")
        return False

def test_configuration():
    """Тест конфигурации"""
    print("\n⚙️ Тест конфигурации...")
    try:
        print(f"✅ ADMIN_ID: {ADMIN_ID}")
        print(f"✅ NO_LOGS_USERS: {NO_LOGS_USERS}")
        print(f"✅ Количество исключаемых пользователей: {len(NO_LOGS_USERS)}")
        
        # Проверяем, что ADMIN_ID в списке исключений
        if ADMIN_ID in NO_LOGS_USERS:
            print("✅ ADMIN_ID корректно исключен из статистики")
        else:
            print("⚠️ ADMIN_ID НЕ исключен из статистики")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ\n")
    
    tests = [
        test_configuration,
        test_database_connection,
        test_user_management,
        test_logging_service,
        test_admin_metrics,
        test_advanced_user_stats,
        test_scenario_logging
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте {test.__name__}: {e}")
    
    print(f"\n📈 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"✅ Пройдено: {passed}/{total}")
    print(f"❌ Провалено: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("⚠️ ЕСТЬ ПРОБЛЕМЫ, ТРЕБУЕТСЯ ДОРАБОТКА")

if __name__ == "__main__":
    main() 