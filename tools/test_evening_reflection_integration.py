#!/usr/bin/env python3
"""
Тестирование интеграции новых AI функций в вечернюю рефлексию
"""
import sys
import os
import asyncio
# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import Database
from modules.card_of_the_day import get_card_info

class TestEveningReflectionIntegration:
    """Тестирование интеграции AI функций в вечернюю рефлексию"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.db = Database('database/dev.db')
        
    def teardown_method(self):
        """Очистка после каждого теста"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def test_imports(self):
        """Тест импортов новых функций"""
        print("Тест импортов новых функций...")
        
        try:
            from modules.ai_service import get_empathetic_response, get_reflection_summary_and_card_synergy
            print("Импорт AI функций успешен")
        except ImportError as e:
            print(f"Ошибка импорта AI функций: {e}")
            return False
        
        try:
            from modules.card_of_the_day import get_card_info
            print("Импорт функций карт дня успешен")
        except ImportError as e:
            print(f"Ошибка импорта функций карт дня: {e}")
            return False
        
        return True
    
    def test_card_integration_functions(self):
        """Тест функций интеграции с картами"""
        print("\nТест функций интеграции с картами...")
        
        # Тест получения информации о карте
        card_info = get_card_info(1)
        assert card_info is not None
        assert "name" in card_info
        assert "meaning" in card_info
        print(f"Информация о карте 1: {card_info['name']} - {card_info['meaning'][:50]}...")
        
        # Тест получения карты дня из БД
        test_user_id = 999999999
        today_card = self.db.get_today_card_of_the_day(test_user_id)
        print(f"Карта дня для пользователя {test_user_id}: {today_card}")
        
        return True
    
    def test_database_new_functions(self):
        """Тест новых функций базы данных"""
        print("\nТест новых функций базы данных...")
        
        # Тест получения рефлексий за период
        test_user_id = 999999999
        reflections = self.db.get_reflections_for_last_n_days(test_user_id, 7)
        assert isinstance(reflections, list)
        print(f"Рефлексии за 7 дней: {len(reflections)} записей")
        
        # Тест получения пользователей с рефлексиями
        users = self.db.get_users_with_recent_reflections(7)
        assert isinstance(users, list)
        print(f"Пользователи с рефлексиями: {len(users)}")
        
        return True
    
    def test_reflection_data_structure(self):
        """Тест структуры данных рефлексии"""
        print("\nТест структуры данных рефлексии...")
        
        # Создаем тестовые данные рефлексии
        test_reflection_data = {
            "gratitude_answer": "Благодарен за поддержку близких",
            "achievement_answer": "Успешно провел презентацию",
            "hard_moments_answer": "Было сложно с подготовкой"
        }
        
        # Проверяем обязательные поля
        required_fields = ['gratitude_answer', 'achievement_answer', 'hard_moments_answer']
        for field in required_fields:
            assert field in test_reflection_data, f"Поле {field} отсутствует"
            assert isinstance(test_reflection_data[field], str), f"Поле {field} не является строкой"
            assert len(test_reflection_data[field]) > 0, f"Поле {field} пустое"
        
        print("Структура данных рефлексии корректна")
        return True
    
    def test_ai_service_availability(self):
        """Тест доступности AI сервиса"""
        print("\nТест доступности AI сервиса...")
        
        try:
            from modules.ai_service import get_empathetic_response, get_weekly_analysis, get_reflection_summary_and_card_synergy
            
            # Проверяем, что функции существуют и являются callable
            assert callable(get_empathetic_response), "get_empathetic_response не является функцией"
            assert callable(get_weekly_analysis), "get_weekly_analysis не является функцией"
            assert callable(get_reflection_summary_and_card_synergy), "get_reflection_summary_and_card_synergy не является функцией"
            
            print("Все AI функции доступны и корректны")
            return True
            
        except Exception as e:
            print(f"Ошибка проверки AI сервиса: {e}")
            return False
    
    def test_evening_reflection_module(self):
        """Тест модуля вечерней рефлексии"""
        print("\nТест модуля вечерней рефлексии...")
        
        try:
            # Проверяем, что модуль импортируется
            from modules.evening_reflection import start_evening_reflection, process_good_moments, process_gratitude, process_hard_moments
            
            # Проверяем, что функции существуют
            assert callable(start_evening_reflection), "start_evening_reflection не найден"
            assert callable(process_good_moments), "process_good_moments не найден"
            assert callable(process_gratitude), "process_gratitude не найден"
            assert callable(process_hard_moments), "process_hard_moments не найден"
            
            print("Модуль вечерней рефлексии доступен")
            return True
            
        except Exception as e:
            print(f"Ошибка проверки модуля вечерней рефлексии: {e}")
            return False
    
    def test_configuration(self):
        """Тест конфигурации"""
        print("\nТест конфигурации...")
        
        try:
            # Проверяем наличие конфигурации
            from config import YANDEX_API_KEY, YANDEX_FOLDER_ID, YANDEX_GPT_URL
            
            assert YANDEX_API_KEY is not None, "YANDEX_API_KEY не настроен"
            assert YANDEX_FOLDER_ID is not None, "YANDEX_FOLDER_ID не настроен"
            assert YANDEX_GPT_URL is not None, "YANDEX_GPT_URL не настроен"
            
            print("Конфигурация YandexGPT доступна")
            return True
            
        except ImportError:
            try:
                from config_local import YANDEX_API_KEY, YANDEX_FOLDER_ID, YANDEX_GPT_URL
                print("Конфигурация YandexGPT доступна (config_local)")
                return True
            except ImportError as e:
                print(f"Конфигурация YandexGPT недоступна: {e}")
                return False
        except Exception as e:
            print(f"Ошибка проверки конфигурации: {e}")
            return False

def run_integration_tests():
    """Запуск всех тестов интеграции"""
    print("Запуск тестирования интеграции AI функций в вечернюю рефлексию...")
    
    test_instance = TestEveningReflectionIntegration()
    
    try:
        test_instance.setup_method()
        
        tests = [
            ("Импорты", test_instance.test_imports),
            ("Интеграция с картами", test_instance.test_card_integration_functions),
            ("Функции БД", test_instance.test_database_new_functions),
            ("Структура данных", test_instance.test_reflection_data_structure),
            ("AI сервис", test_instance.test_ai_service_availability),
            ("Модуль рефлексии", test_instance.test_evening_reflection_module),
            ("Конфигурация", test_instance.test_configuration)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n{'='*50}")
            print(f"Тест: {test_name}")
            print('='*50)
            
            try:
                if test_func():
                    print(f"{test_name}: ПРОЙДЕН")
                    passed += 1
                else:
                    print(f"{test_name}: ПРОВАЛЕН")
            except Exception as e:
                print(f"{test_name}: ОШИБКА - {e}")
        
        print(f"\n{'='*50}")
        print(f"ИТОГИ ТЕСТИРОВАНИЯ: {passed}/{total} тестов пройдено")
        print('='*50)
        
        if passed == total:
            print("\nВсе тесты интеграции успешно пройдены!")
            return True
        else:
            print(f"\n{total - passed} тестов не пройдено")
            return False
        
    except Exception as e:
        print(f"\nКритическая ошибка в тестах интеграции: {e}")
        return False
    finally:
        test_instance.teardown_method()

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
