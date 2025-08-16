#!/usr/bin/env python3
"""
Комплексное тестирование функционала постов
"""
import sys
import os
import asyncio
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_local import ADMIN_ID
from database.db import Database
from modules.logging_service import LoggingService
from modules.post_management import PostManager
from modules.user_management import UserManager

class TestPostFunctionality:
    """Класс для тестирования функционала постов"""
    
    def __init__(self):
        self.test_db_path = None
        self.db = None
        self.logger_service = None
        self.user_manager = None
        self.post_manager = None
        self.mock_bot = None
        
    def setup(self):
        """Настройка тестового окружения"""
        print("🔧 Настройка тестового окружения...")
        
        # Создаем временную БД для тестов
        self.test_db_path = tempfile.mktemp(suffix='.db')
        shutil.copy('database/dev.db', self.test_db_path)
        
        # Инициализируем компоненты
        self.db = Database(self.test_db_path)
        self.logger_service = LoggingService(self.db)
        self.user_manager = UserManager(self.db)
        
        # Создаем мок бота
        self.mock_bot = Mock()
        self.mock_bot.send_message = AsyncMock()
        self.mock_bot.send_photo = AsyncMock()
        
        self.post_manager = PostManager(self.db, self.mock_bot, self.logger_service)
        
        print("✅ Тестовое окружение настроено")
    
    def teardown(self):
        """Очистка тестового окружения"""
        if self.db:
            self.db.close()
        if self.test_db_path and os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        print("🧹 Тестовое окружение очищено")
    
    def test_post_creation(self):
        """Тест создания поста"""
        print("\n📝 Тест создания поста...")
        try:
            # Создаем тестовый пост
            title = "Тестовый заголовок"
            content = "Тестовое содержание поста"
            created_by = int(ADMIN_ID)
            
            post_id = self.post_manager.create_post(title, content, created_by)
            print(f"✅ Пост создан с ID: {post_id}")
            
            # Проверяем, что пост создался
            post = self.post_manager.get_post(post_id)
            assert post is not None, "Пост не найден в БД"
            assert post['title'] == title, "Неправильный заголовок"
            assert post['content'] == content, "Неправильное содержание"
            assert post['created_by'] == created_by, "Неправильный создатель"
            
            print("✅ Пост корректно сохранен в БД")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания поста: {e}")
            return False
    
    def test_post_validation(self):
        """Тест валидации постов"""
        print("\n✅ Тест валидации постов...")
        try:
            # Тест валидных данных
            valid_result = self.post_manager.validate_post_data("Заголовок", "Содержание")
            assert valid_result['valid'] == True, "Валидные данные должны пройти проверку"
            print("✅ Валидные данные прошли проверку")
            
            # Тест пустого заголовка
            invalid_title = self.post_manager.validate_post_data("", "Содержание")
            assert invalid_title['valid'] == False, "Пустой заголовок должен быть отклонен"
            assert "заголовок" in str(invalid_title['errors']).lower(), "Должна быть ошибка о заголовке"
            print("✅ Пустой заголовок корректно отклонен")
            
            # Тест слишком длинного заголовка
            long_title = "Очень длинный заголовок " * 10
            invalid_long_title = self.post_manager.validate_post_data(long_title, "Содержание")
            assert invalid_long_title['valid'] == False, "Слишком длинный заголовок должен быть отклонен"
            print("✅ Слишком длинный заголовок корректно отклонен")
            
            # Тест пустого содержания
            invalid_content = self.post_manager.validate_post_data("Заголовок", "")
            assert invalid_content['valid'] == False, "Пустое содержание должно быть отклонено"
            print("✅ Пустое содержание корректно отклонено")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка валидации постов: {e}")
            return False
    
    def test_post_formatting(self):
        """Тест форматирования постов"""
        print("\n🎨 Тест форматирования постов...")
        try:
            # Создаем пост с жирным заголовком
            title = "Тестовый заголовок"
            content = "Обычное содержание"
            created_by = int(ADMIN_ID)
            
            # Форматируем контент с жирным заголовком
            formatted_content = f"<b>{title}</b>\n\n{content}"
            
            post_id = self.post_manager.create_post(title, formatted_content, created_by)
            post = self.post_manager.get_post(post_id)
            
            # Проверяем форматирование
            assert "<b>" in post['content'], "Заголовок должен быть обернут в <b>"
            assert "</b>" in post['content'], "Заголовок должен быть закрыт </b>"
            assert "\n\n" in post['content'], "Должен быть двойной перенос строки"
            
            print("✅ Форматирование с жирным заголовком корректно")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка форматирования постов: {e}")
            return False
    
    def test_mailing_creation(self):
        """Тест создания рассылки"""
        print("\n📧 Тест создания рассылки...")
        try:
            # Создаем пост для рассылки
            post_id = self.post_manager.create_post("Заголовок рассылки", "Содержание рассылки", int(ADMIN_ID))
            
            # Создаем рассылку всем пользователям
            mailing_id = self.post_manager.create_mailing(
                post_id=post_id,
                title="Тестовая рассылка",
                send_to_all=True,
                created_by=int(ADMIN_ID)
            )
            
            print(f"✅ Рассылка создана с ID: {mailing_id}")
            
            # Проверяем рассылку
            mailing = self.post_manager.get_mailing(mailing_id)
            assert mailing is not None, "Рассылка не найдена в БД"
            assert mailing['post_id'] == post_id, "Неправильный ID поста"
            assert mailing['send_to_all'] == True, "Должна быть рассылка всем"
            assert mailing['status'] == 'pending', "Статус должен быть pending"
            
            print("✅ Рассылка корректно сохранена в БД")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания рассылки: {e}")
            return False
    
    def test_mailing_validation(self):
        """Тест валидации рассылок"""
        print("\n✅ Тест валидации рассылок...")
        try:
            # Тест валидной рассылки всем
            valid_all = self.post_manager.validate_mailing_data(send_to_all=True)
            assert valid_all['valid'] == True, "Рассылка всем должна быть валидна"
            print("✅ Рассылка всем прошла валидацию")
            
            # Тест валидной рассылки конкретным пользователям
            valid_specific = self.post_manager.validate_mailing_data(
                send_to_all=False, 
                target_user_ids=[123456, 789012]
            )
            assert valid_specific['valid'] == True, "Рассылка конкретным пользователям должна быть валидна"
            print("✅ Рассылка конкретным пользователям прошла валидацию")
            
            # Тест невалидной рассылки (не всем и без списка пользователей)
            invalid = self.post_manager.validate_mailing_data(send_to_all=False)
            assert invalid['valid'] == False, "Рассылка без списка пользователей должна быть отклонена"
            print("✅ Рассылка без списка пользователей корректно отклонена")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка валидации рассылок: {e}")
            return False
    
    async def test_post_sending(self):
        """Тест отправки постов"""
        print("\n📤 Тест отправки постов...")
        try:
            # Создаем тестового пользователя (get_user автоматически создает запись)
            test_user_id = 999999999
            user_data = self.db.get_user(test_user_id)
            # Обновляем имя пользователя
            self.db.update_user(test_user_id, {"name": "Тестовый пользователь"})
            
            # Создаем пост
            post_id = self.post_manager.create_post("Тест отправки", "Тестовое содержание", int(ADMIN_ID))
            post = self.post_manager.get_post(post_id)
            
            # Отправляем пост
            success = await self.post_manager.send_post_to_user(test_user_id, post)
            assert success == True, "Пост должен быть отправлен успешно"
            
            # Проверяем, что бот был вызван
            self.mock_bot.send_message.assert_called_once()
            call_args = self.mock_bot.send_message.call_args
            assert call_args[1]['chat_id'] == test_user_id, "Неправильный получатель"
            assert call_args[1]['parse_mode'] == 'HTML', "Должен быть HTML режим"
            
            print("✅ Пост успешно отправлен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка отправки постов: {e}")
            return False
    
    async def test_mailing_processing(self):
        """Тест обработки рассылок"""
        print("\n📨 Тест обработки рассылок...")
        try:
            # Создаем тестовых пользователей (get_user автоматически создает записи)
            test_users = [111111111, 222222222, 333333333]
            for user_id in test_users:
                user_data = self.db.get_user(user_id)
                # Обновляем имя пользователя
                self.db.update_user(user_id, {"name": f"Тестовый пользователь {user_id}"})
            
            # Создаем пост и рассылку
            post_id = self.post_manager.create_post("Тест рассылки", "Тестовое содержание", int(ADMIN_ID))
            mailing_id = self.post_manager.create_mailing(
                post_id=post_id,
                title="Тестовая рассылка",
                send_to_all=True,
                created_by=int(ADMIN_ID)
            )
            
            # Обрабатываем рассылку
            result = await self.post_manager.process_mailing({
                'id': mailing_id,
                'post_content': f"<b>Тест рассылки</b>\n\nТестовое содержание",
                'send_to_all': True
            })
            
            # Проверяем результаты
            assert result['total'] > 0, "Должны быть получатели"
            assert result['sent'] > 0, "Должны быть отправленные сообщения"
            print(f"✅ Рассылка обработана: {result['sent']}/{result['total']} отправлено")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обработки рассылок: {e}")
            return False
    
    def test_post_preview(self):
        """Тест предварительного просмотра постов"""
        print("\n👁️ Тест предварительного просмотра постов...")
        try:
            # Создаем пост с длинным содержанием
            long_content = "Очень длинное содержание " * 20
            post_id = self.post_manager.create_post("Заголовок", long_content, int(ADMIN_ID))
            post = self.post_manager.get_post(post_id)
            
            # Тестируем предварительный просмотр
            preview = self.post_manager.format_post_preview(post, max_length=100)
            # Проверяем, что предварительный просмотр содержит заголовок и обрезанное содержание
            assert "📝" in preview, "Должен быть эмодзи поста"
            assert "..." in preview, "Должно быть многоточие для обрезанного текста"
            assert len(preview) > 0, "Предварительный просмотр не должен быть пустым"
            
            print("✅ Предварительный просмотр работает корректно")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка предварительного просмотра: {e}")
            return False
    
    def test_post_management_operations(self):
        """Тест операций управления постами"""
        print("\n🔧 Тест операций управления постами...")
        try:
            # Создаем пост
            post_id = self.post_manager.create_post("Исходный заголовок", "Исходное содержание", int(ADMIN_ID))
            
            # Обновляем пост
            success = self.post_manager.update_post(
                post_id=post_id,
                title="Обновленный заголовок",
                content="Обновленное содержание"
            )
            assert success == True, "Обновление должно быть успешным"
            
            # Проверяем обновление
            updated_post = self.post_manager.get_post(post_id)
            assert updated_post['title'] == "Обновленный заголовок", "Заголовок должен быть обновлен"
            assert updated_post['content'] == "Обновленное содержание", "Содержание должно быть обновлено"
            
            # Получаем все посты
            all_posts = self.post_manager.get_all_posts(limit=10)
            assert len(all_posts) > 0, "Должны быть посты в списке"
            
            # Удаляем пост
            delete_success = self.post_manager.delete_post(post_id)
            assert delete_success == True, "Удаление должно быть успешным"
            
            # Проверяем удаление
            deleted_post = self.post_manager.get_post(post_id)
            assert deleted_post is None, "Пост должен быть удален"
            
            print("✅ Операции управления постами работают корректно")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка операций управления постами: {e}")
            return False
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        print("🚀 Запуск тестов функционала постов...")
        
        self.setup()
        
        tests = [
            ("Создание постов", self.test_post_creation),
            ("Валидация постов", self.test_post_validation),
            ("Форматирование постов", self.test_post_formatting),
            ("Создание рассылок", self.test_mailing_creation),
            ("Валидация рассылок", self.test_mailing_validation),
            ("Отправка постов", self.test_post_sending),
            ("Обработка рассылок", self.test_mailing_processing),
            ("Предварительный просмотр", self.test_post_preview),
            ("Операции управления", self.test_post_management_operations),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                
                if result:
                    passed += 1
                    print(f"✅ {test_name}: ПРОЙДЕН")
                else:
                    print(f"❌ {test_name}: ПРОВАЛЕН")
                    
            except Exception as e:
                print(f"❌ {test_name}: ОШИБКА - {e}")
        
        print(f"\n📊 Результаты тестирования: {passed}/{total} тестов пройдено")
        
        if passed == total:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        else:
            print("⚠️ Некоторые тесты не прошли")
        
        self.teardown()
        return passed == total

async def main():
    """Главная функция"""
    tester = TestPostFunctionality()
    success = await tester.run_all_tests()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 