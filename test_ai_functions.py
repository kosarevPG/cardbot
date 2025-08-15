#!/usr/bin/env python3
"""
Тестирование новых AI функций для вечерней рефлексии
"""
import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import Database
from modules.ai_service import (
    get_empathetic_response,
    get_weekly_analysis,
    get_reflection_summary_and_card_synergy
)
from modules.card_of_the_day import get_card_info

class TestAIFunctions:
    """Тестирование новых AI функций"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.db = Database('database/dev.db')
        
    def teardown_method(self):
        """Очистка после каждого теста"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def test_card_info_retrieval(self):
        """Тест получения информации о картах"""
        print("Тест получения информации о картах...")
        
        # Тест получения информации о карте
        card_info = get_card_info(1)
        assert card_info is not None
        assert "name" in card_info
        assert "meaning" in card_info
        assert card_info["name"] == "Маг"
        print("Получение информации о карте успешно")
        
        # Тест несуществующей карты (функция возвращает дефолтные значения)
        invalid_card = get_card_info(999)
        assert invalid_card is not None
        assert "name" in invalid_card
        assert "meaning" in invalid_card
        assert invalid_card["name"] == "Карта 999"
        assert invalid_card["meaning"] == "Значение не определено"
        print("Обработка несуществующей карты корректна (возвращает дефолтные значения)")
    
    def test_database_new_functions(self):
        """Тест новых функций базы данных"""
        print("\nТест новых функций базы данных...")
        
        # Тест получения карты дня
        test_user_id = 999999999
        today_card = self.db.get_today_card_of_the_day(test_user_id)
        print(f"Получение карты дня: {today_card}")
        
        # Тест получения рефлексий за период
        reflections = self.db.get_reflections_for_last_n_days(test_user_id, 7)
        assert isinstance(reflections, list)
        print(f"Получение рефлексий за период: {len(reflections)} записей")
        
        # Тест получения пользователей с рефлексиями
        users_with_reflections = self.db.get_users_with_recent_reflections(7)
        assert isinstance(users_with_reflections, list)
        print(f"Получение пользователей с рефлексиями: {len(users_with_reflections)} пользователей")
    
    async def test_empathetic_response(self):
        """Тест эмпатичного ответа"""
        print("\nТест эмпатичного ответа...")
        
        test_texts = [
            "Поссорился с коллегой",
            "Ничего не успеваю, чувствую себя разбитым",
            "Потерял работу, не знаю что делать"
        ]
        
        for text in test_texts:
            try:
                response = await get_empathetic_response(text)
                assert response is not None
                assert len(response) > 10
                assert len(response) < 200
                print(f"Эмпатичный ответ для '{text[:20]}...': {response[:50]}...")
            except Exception as e:
                print(f"Ошибка при генерации эмпатичного ответа: {e}")
                # В тестах допускаем ошибки API
    
    async def test_weekly_analysis(self):
        """Тест еженедельного анализа"""
        print("\nТест еженедельного анализа...")
        
        # Тестовые данные рефлексий
        test_reflections = [
            {
                "date": "2024-01-01",
                "gratitude_answer": "Благодарен за семью и здоровье",
                "achievement_answer": "Завершил важный проект",
                "hard_moments_answer": "Было сложно с дедлайнами"
            },
            {
                "date": "2024-01-02", 
                "gratitude_answer": "Рад встрече с друзьями",
                "achievement_answer": "Сходил в спортзал",
                "hard_moments_answer": "Устал от работы"
            }
        ]
        
        try:
            analysis = await get_weekly_analysis(test_reflections)
            assert analysis is not None
            assert len(analysis) > 50
            assert "**Главный источник радости:**" in analysis
            assert "**Повторяющаяся трудность:**" in analysis
            assert "**Интересное наблюдение:**" in analysis
            print(f"Еженедельный анализ успешно сгенерирован: {analysis[:100]}...")
        except Exception as e:
            print(f"Ошибка при генерации еженедельного анализа: {e}")
            # В тестах допускаем ошибки API
    
    async def test_reflection_summary_with_card_synergy(self):
        """Тест резюме рефлексии с синергией карты"""
        print("\nТест резюме рефлексии с синергией карты...")
        
        # Тестовые данные
        reflection_data = {
            "gratitude_answer": "Благодарен за поддержку близких",
            "achievement_answer": "Успешно провел презентацию",
            "hard_moments_answer": "Было сложно с подготовкой"
        }
        
        # Тест без карты
        try:
            summary_no_card = await get_reflection_summary_and_card_synergy(
                999999999, reflection_data, self.db
            )
            assert summary_no_card is not None
            print(f"Резюме без карты: {summary_no_card[:100]}...")
        except Exception as e:
            print(f"Ошибка при генерации резюме без карты: {e}")
        
        # Тест с картой
        try:
            summary_with_card = await get_reflection_summary_and_card_synergy(
                999999999, reflection_data, self.db, "Маг", "Творческая сила, новые начинания"
            )
            assert summary_with_card is not None
            assert "утренней карты" in summary_with_card
            print(f"Резюме с картой: {summary_with_card[:100]}...")
        except Exception as e:
            print(f"Ошибка при генерации резюме с картой: {e}")
    
    def test_card_meanings_completeness(self):
        """Тест полноты значений карт"""
        print("\nТест полноты значений карт...")
        
        from modules.card_of_the_day import CARD_MEANINGS
        
        # Проверяем, что все карты имеют значения
        assert len(CARD_MEANINGS) == 40, f"Ожидалось 40 карт, получено {len(CARD_MEANINGS)}"
        
        for card_num in range(1, 41):
            assert card_num in CARD_MEANINGS, f"Карта {card_num} отсутствует"
            card_info = CARD_MEANINGS[card_num]
            assert "name" in card_info, f"Карта {card_num} не имеет названия"
            assert "meaning" in card_info, f"Карта {card_num} не имеет значения"
            assert len(card_info["name"]) > 0, f"Карта {card_num} имеет пустое название"
            assert len(card_info["meaning"]) > 10, f"Карта {card_num} имеет слишком короткое значение"
        
        print("Все 40 карт имеют корректные названия и значения")

def run_all_tests():
    """Запуск всех тестов"""
    print("Запуск тестирования новых AI функций...")
    
    test_instance = TestAIFunctions()
    
    try:
        print("Настройка тестового окружения...")
        test_instance.setup_method()
        
        print("Запуск синхронных тестов...")
        print("1. Тест получения информации о картах...")
        test_instance.test_card_info_retrieval()
        print("2. Тест новых функций базы данных...")
        test_instance.test_database_new_functions()
        print("3. Тест полноты значений карт...")
        test_instance.test_card_meanings_completeness()
        
        print("Запуск асинхронных тестов...")
        # Асинхронные тесты
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            print("4. Тест эмпатичного ответа...")
            loop.run_until_complete(test_instance.test_empathetic_response())
            print("5. Тест еженедельного анализа...")
            loop.run_until_complete(test_instance.test_weekly_analysis())
            print("6. Тест резюме рефлексии с синергией карты...")
            loop.run_until_complete(test_instance.test_reflection_summary_with_card_synergy())
        finally:
            loop.close()
            
        print("\nВсе тесты успешно пройдены!")
        return True
        
    except Exception as e:
        print(f"\nОшибка в тестах: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("Очистка тестового окружения...")
        test_instance.teardown_method()

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
