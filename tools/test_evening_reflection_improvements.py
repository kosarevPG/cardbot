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
from modules.ai_service import get_integrated_reflection_summary

class TestEveningReflectionImprovements:
    """Тестирование улучшений вечерней рефлексии"""
    
    def __init__(self):
        """Инициализация тестового класса"""
        self.db = None
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.db = Database('database/dev.db')
        
    def teardown_method(self):
        """Очистка после каждого теста"""
        if hasattr(self, 'db') and self.db:
            self.db.close()
    
    def test_integrated_reflection_summary(self):
        """Тест интегрированной вечерней рефлексии"""
        print("🧪 Тестирование интегрированной вечерней рефлексии...")
        
        # Убеждаемся, что setup_method был вызван
        if not self.db:
            self.setup_method()
        
        # Тестовые данные
        test_user_id = 12345
        reflection_data = {
            "good_moments": "Встретился с другом, выпил вкусный кофе",
            "gratitude": "За поддержку близких и хорошую погоду",
            "hard_moments": "Было много работы, устал"
        }
        
        # Запускаем тест
        async def run_test():
            try:
                result = await get_integrated_reflection_summary(
                    test_user_id, 
                    reflection_data, 
                    self.db
                )
                
                if result:
                    print(f"✅ Интегрированная рефлексия сгенерирована успешно")
                    print(f"📝 Результат: {result[:100]}...")
                    return True
                else:
                    print(f"❌ Не удалось сгенерировать интегрированную рефлексию")
                    return False
                    
            except Exception as e:
                print(f"❌ Ошибка при тестировании: {e}")
                return False
        
        # Запускаем асинхронный тест
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(run_test())
            assert success, "Тест интегрированной рефлексии не прошел"
        finally:
            loop.close()
        
        print("✅ Тест интегрированной вечерней рефлексии прошел успешно!")

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов улучшений вечерней рефлексии...")
    
    test_suite = TestEveningReflectionImprovements()
    
    # Запускаем тесты
    test_suite.test_integrated_reflection_summary()
    
    print("🎉 Все тесты улучшений вечерней рефлексии прошли успешно!")

if __name__ == "__main__":
    main()
