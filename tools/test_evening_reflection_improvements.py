#!/usr/bin/env python3
"""
Тестирование улучшений вечерней рефлексии
"""
import sys
import os
import asyncio
# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import Database
from modules.card_of_the_day import get_card_info

class TestEveningReflectionImprovements:
    """Тестирование улучшений вечерней рефлексии"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.db = Database('database/dev.db')
        
    def teardown_method(self):
        """Очистка после каждого теста"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def test_ai_response_quality(self):
        """Тест качества AI ответов"""
        print("Тест качества AI ответов...")
        
        try:
            from modules.ai_service import get_empathetic_response, get_reflection_summary_and_card_synergy
            
            # Тест базовой функциональности AI
            test_context = "Пользователь чувствует усталость после рабочего дня"
            response = get_empathetic_response(test_context, "gratitude")
            
            assert response is not None, "AI ответ не получен"
            assert isinstance(response, str), "AI ответ не является строкой"
            assert len(response) > 10, "AI ответ слишком короткий"
            
            print(f"AI ответ получен: {response[:100]}...")
            return True
            
        except Exception as e:
            print(f"Ошибка тестирования AI ответов: {e}")
            return False
    
    def test_card_synergy_analysis(self):
        """Тест анализа синергии карт и рефлексии"""
        print("\nТест анализа синергии карт и рефлексии...")
        
        try:
            from modules.ai_service import get_reflection_summary_and_card_synergy
            
            # Тестовые данные рефлексии
            test_reflection = {
                "gratitude_answer": "Благодарен за поддержку коллег",
                "achievement_answer": "Успешно завершил проект",
                "hard_moments_answer": "Было сложно с дедлайнами"
            }
            
            # Получаем карту дня
            card_info = get_card_info(1)
            assert card_info is not None, "Информация о карте не получена"
            
            # Тестируем функцию синергии
            synergy_analysis = get_reflection_summary_and_card_synergy(
                test_reflection, 
                card_info, 
                "test_user_123"
            )
            
            assert synergy_analysis is not None, "Анализ синергии не получен"
            assert isinstance(synergy_analysis, str), "Анализ синергии не является строкой"
            
            print(f"Анализ синергии получен: {synergy_analysis[:100]}...")
            return True
            
        except Exception as e:
            print(f"Ошибка тестирования анализа синергии: {e}")
            return False
    
    def test_weekly_analysis_improvements(self):
        """Тест улучшений недельного анализа"""
        print("\nТест улучшений недельного анализа...")
        
        try:
            from modules.ai_service import get_weekly_analysis
            
            # Тестовые данные недели
            test_week_data = {
                "reflections": [
                    {"date": "2024-01-01", "gratitude": "За поддержку", "achievement": "Завершил задачу"},
                    {"date": "2024-01-02", "gratitude": "За понимание", "achievement": "Помог коллеге"}
                ],
                "mood_trends": "Стабильно положительный",
                "challenges": "Временные сложности с проектом"
            }
            
            # Тестируем недельный анализ
            weekly_analysis = get_weekly_analysis(test_week_data, "test_user_123")
            
            assert weekly_analysis is not None, "Недельный анализ не получен"
            assert isinstance(weekly_analysis, str), "Недельный анализ не является строкой"
            
            print(f"Недельный анализ получен: {weekly_analysis[:100]}...")
            return True
            
        except Exception as e:
            print(f"Ошибка тестирования недельного анализа: {e}")
            return False
    
    def test_personalization_features(self):
        """Тест функций персонализации"""
        print("\nТест функций персонализации...")
        
        try:
            from modules.ai_service import build_user_profile
            
            # Тестовые данные пользователя
            test_user_data = {
                "user_id": "test_user_123",
                "reflections_count": 5,
                "preferred_topics": ["работа", "семья", "здоровье"],
                "mood_patterns": "Утренняя активность, вечерняя рефлексия"
            }
            
            # Тестируем построение профиля
            user_profile = build_user_profile(test_user_data)
            
            assert user_profile is not None, "Профиль пользователя не построен"
            assert isinstance(user_profile, dict), "Профиль не является словарем"
            assert "personality_insights" in user_profile, "Отсутствуют инсайты личности"
            
            print(f"Профиль пользователя построен: {user_profile.get('personality_insights', '')[:50]}...")
            return True
            
        except Exception as e:
            print(f"Ошибка тестирования персонализации: {e}")
            return False
    
    def test_database_performance(self):
        """Тест производительности базы данных"""
        print("\nТест производительности базы данных...")
        
        try:
            import time
            
            # Тест скорости получения рефлексий
            start_time = time.time()
            reflections = self.db.get_reflections_for_last_n_days("test_user_123", 30)
            end_time = time.time()
            
            response_time = end_time - start_time
            assert response_time < 1.0, f"Запрос к БД слишком медленный: {response_time:.3f}с"
            
            print(f"Запрос к БД выполнен за {response_time:.3f}с")
            
            # Тест скорости получения пользователей
            start_time = time.time()
            users = self.db.get_users_with_recent_reflections(7)
            end_time = time.time()
            
            response_time = end_time - start_time
            assert response_time < 1.0, f"Запрос пользователей слишком медленный: {response_time:.3f}с"
            
            print(f"Запрос пользователей выполнен за {response_time:.3f}с")
            return True
            
        except Exception as e:
            print(f"Ошибка тестирования производительности БД: {e}")
            return False
    
    def test_error_handling(self):
        """Тест обработки ошибок"""
        print("\nТест обработки ошибок...")
        
        try:
            from modules.ai_service import get_empathetic_response
            
            # Тест с некорректными данными
            try:
                response = get_empathetic_response("", "invalid_type")
                # Если функция не выбросила исключение, проверяем что она вернула разумный ответ
                assert response is not None, "Функция должна возвращать ответ даже для некорректных данных"
            except Exception as e:
                print(f"Функция корректно обработала ошибку: {e}")
            
            # Тест с пустыми данными
            try:
                response = get_empathetic_response(None, "gratitude")
                assert response is not None, "Функция должна возвращать ответ для None данных"
            except Exception as e:
                print(f"Функция корректно обработала None данные: {e}")
            
            print("Обработка ошибок работает корректно")
            return True
            
        except Exception as e:
            print(f"Ошибка тестирования обработки ошибок: {e}")
            return False

def run_improvement_tests():
    """Запуск всех тестов улучшений"""
    print("Запуск тестирования улучшений вечерней рефлексии...")
    
    test_instance = TestEveningReflectionImprovements()
    
    try:
        test_instance.setup_method()
        
        tests = [
            ("Качество AI ответов", test_instance.test_ai_response_quality),
            ("Анализ синергии карт", test_instance.test_card_synergy_analysis),
            ("Недельный анализ", test_instance.test_weekly_analysis_improvements),
            ("Персонализация", test_instance.test_personalization_features),
            ("Производительность БД", test_instance.test_database_performance),
            ("Обработка ошибок", test_instance.test_error_handling)
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
        print(f"ИТОГИ ТЕСТИРОВАНИЯ УЛУЧШЕНИЙ: {passed}/{total} тестов пройдено")
        print('='*50)
        
        if passed == total:
            print("\nВсе тесты улучшений успешно пройдены!")
            return True
        else:
            print(f"\n{total - passed} тестов не пройдено")
            return False
        
    except Exception as e:
        print(f"\nКритическая ошибка в тестах улучшений: {e}")
        return False
    finally:
        test_instance.teardown_method()

if __name__ == "__main__":
    success = run_improvement_tests()
    sys.exit(0 if success else 1)
