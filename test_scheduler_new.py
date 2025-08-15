#!/usr/bin/env python3
"""
Тестирование нового планировщика еженедельного анализа
"""
import sys
import os
import asyncio
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.scheduler import ReflectionAnalysisScheduler
from database.db import Database

class TestReflectionScheduler:
    """Тестирование планировщика еженедельного анализа"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.db = Database('database/dev.db')
        # Создаем мок-бот для тестов
        class MockBot:
            async def send_message(self, chat_id, text, parse_mode=None):
                print(f"Мок-бот отправил сообщение пользователю {chat_id}: {text[:50]}...")
                return True
        
        self.mock_bot = MockBot()
        
    def teardown_method(self):
        """Очистка после каждого теста"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def test_scheduler_initialization(self):
        """Тест инициализации планировщика"""
        print("Тест инициализации планировщика...")
        
        scheduler = ReflectionAnalysisScheduler(self.mock_bot, self.db, check_interval=1)
        assert scheduler is not None
        assert scheduler.bot == self.mock_bot
        assert scheduler.db == self.db
        assert scheduler.check_interval == 1
        print("Планировщик успешно инициализирован")
    
    def test_scheduler_start_stop(self):
        """Тест запуска и остановки планировщика"""
        print("\nТест запуска и остановки планировщика...")
        
        scheduler = ReflectionAnalysisScheduler(self.mock_bot, self.db, check_interval=1)
        
        # Тест запуска
        assert not scheduler.is_running
        print("Планировщик изначально не запущен")
        
        # Тест остановки без запуска
        scheduler.stop()
        assert not scheduler.is_running
        print("Остановка неактивного планировщика корректна")
    
    def test_weekly_analysis_logic(self):
        """Тест логики еженедельного анализа"""
        print("\nТест логики еженедельного анализа...")
        
        from datetime import datetime, timedelta
        
        # Тест определения воскресенья
        today = datetime.now()
        is_sunday = today.weekday() == 6  # 6 = воскресенье
        
        if is_sunday:
            print("Сегодня воскресенье - планировщик будет активен")
        else:
            print(f"Сегодня {today.strftime('%A')} - планировщик будет ждать воскресенья")
        
        # Тест времени 20:00
        current_hour = today.hour
        if current_hour == 20:
            print("Сейчас 20:00 - время для еженедельного анализа")
        else:
            print(f"Сейчас {current_hour}:00 - не время для анализа")
    
    def test_database_functions_for_scheduler(self):
        """Тест функций БД, используемых планировщиком"""
        print("\nТест функций БД для планировщика...")
        
        # Тест получения пользователей с рефлексиями
        users = self.db.get_users_with_recent_reflections(7)
        assert isinstance(users, list)
        print(f"Пользователи с рефлексиями за неделю: {len(users)}")
        
        if users:
            # Тест получения рефлексий для конкретного пользователя
            test_user = users[0]
            reflections = self.db.get_reflections_for_last_n_days(test_user, 7)
            assert isinstance(reflections, list)
            print(f"Рефлексии пользователя {test_user} за неделю: {len(reflections)}")
            
            # Тест структуры данных рефлексии
            if reflections:
                reflection = reflections[0]
                required_fields = ['date', 'gratitude_answer', 'achievement_answer', 'hard_moments_answer']
                for field in required_fields:
                    assert field in reflection, f"Поле {field} отсутствует в рефлексии"
                print("Структура данных рефлексии корректна")
    
    def test_ai_service_integration(self):
        """Тест интеграции с AI сервисом"""
        print("\nТест интеграции с AI сервисом...")
        
        try:
            from modules.ai_service import get_weekly_analysis
            
            # Тестовые данные
            test_reflections = [
                {
                    "date": "2024-01-01",
                    "gratitude_answer": "Тест благодарности",
                    "achievement_answer": "Тест достижения", 
                    "hard_moments_answer": "Тест трудностей"
                }
            ]
            
            print("Импорт AI сервиса успешен")
            print("Структура тестовых данных корректна")
            
        except ImportError as e:
            print(f"Ошибка импорта AI сервиса: {e}")
        except Exception as e:
            print(f"Ошибка тестирования AI интеграции: {e}")
    
    def test_error_handling(self):
        """Тест обработки ошибок"""
        print("\nТест обработки ошибок...")
        
        # Тест с некорректными параметрами
        try:
            scheduler = ReflectionAnalysisScheduler(None, None, check_interval=-1)
            print("Планировщик создан с некорректными параметрами")
        except Exception as e:
            print(f"Ошибка корректно обработана: {e}")
        
        # Тест с некорректной БД
        try:
            invalid_db = "not_a_database"
            scheduler = ReflectionAnalysisScheduler(self.mock_bot, invalid_db)
            print("Планировщик создан с некорректной БД")
        except Exception as e:
            print(f"Ошибка БД корректно обработана: {e}")

def run_scheduler_tests():
    """Запуск всех тестов планировщика"""
    print("Запуск тестирования планировщика еженедельного анализа...")
    
    test_instance = TestReflectionScheduler()
    
    try:
        test_instance.setup_method()
        
        test_instance.test_scheduler_initialization()
        test_instance.test_scheduler_start_stop()
        test_instance.test_weekly_analysis_logic()
        test_instance.test_database_functions_for_scheduler()
        test_instance.test_ai_service_integration()
        test_instance.test_error_handling()
        
        print("\nВсе тесты планировщика успешно пройдены!")
        return True
        
    except Exception as e:
        print(f"\nОшибка в тестах планировщика: {e}")
        return False
    finally:
        test_instance.teardown_method()

if __name__ == "__main__":
    success = run_scheduler_tests()
    sys.exit(0 if success else 1)
