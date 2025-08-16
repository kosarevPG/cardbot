#!/usr/bin/env python3
"""
Тестирование отложенных постов
"""
import sys
import os
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_local import ADMIN_ID
from database.db import Database
from modules.logging_service import LoggingService
from modules.post_management import PostManager

def test_scheduled_post_creation():
    """Тест создания отложенного поста"""
    print("⏰ Тест создания отложенного поста...")
    
    # Создаем временную БД
    test_db_path = tempfile.mktemp(suffix='.db')
    shutil.copy('database/dev.db', test_db_path)
    
    try:
        db = Database(test_db_path)
        logger_service = LoggingService(db)
        mock_bot = Mock()
        mock_bot.send_message = AsyncMock()
        
        post_manager = PostManager(db, mock_bot, logger_service)
        
        # Создаем пост
        post_id = post_manager.create_post("Тестовый отложенный пост", "Содержание поста", int(ADMIN_ID))
        
        # Создаем отложенную рассылку (через 1 час)
        future_time = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        
        mailing_id = post_manager.create_mailing(
            post_id=post_id,
            title="Отложенная рассылка",
            send_to_all=True,
            created_by=int(ADMIN_ID),
            scheduled_at=future_time
        )
        
        print(f"✅ Отложенная рассылка создана с ID: {mailing_id}")
        
        # Проверяем рассылку
        mailing = post_manager.get_mailing(mailing_id)
        assert mailing is not None, "Рассылка не найдена"
        assert mailing['scheduled_at'] is not None, "Время отправки не установлено"
        assert mailing['status'] == 'pending', "Статус должен быть pending"
        
        print("✅ Отложенная рассылка корректно сохранена")
        
        # Тестируем валидацию времени
        validation = post_manager.validate_mailing_data(True, None, future_time)
        assert validation['valid'] == True, "Валидное время должно пройти проверку"
        
        # Тестируем невалидное время (в прошлом)
        past_time = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        invalid_validation = post_manager.validate_mailing_data(True, None, past_time)
        assert invalid_validation['valid'] == False, "Время в прошлом должно быть отклонено"
        
        print("✅ Валидация времени работает корректно")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования отложенных постов: {e}")
        return False
    finally:
        if 'db' in locals():
            db.close()
        if test_db_path and os.path.exists(test_db_path):
            os.remove(test_db_path)

def test_scheduled_post_formatting():
    """Тест форматирования отложенных постов"""
    print("\n🎨 Тест форматирования отложенных постов...")
    
    test_db_path = tempfile.mktemp(suffix='.db')
    shutil.copy('database/dev.db', test_db_path)
    
    try:
        db = Database(test_db_path)
        logger_service = LoggingService(db)
        mock_bot = Mock()
        
        post_manager = PostManager(db, mock_bot, logger_service)
        
        # Создаем отложенную рассылку
        post_id = post_manager.create_post("Тест форматирования", "Содержание", int(ADMIN_ID))
        future_time = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        
        mailing_id = post_manager.create_mailing(
            post_id=post_id,
            title="Тестовая отложенная рассылка",
            send_to_all=True,
            created_by=int(ADMIN_ID),
            scheduled_at=future_time
        )
        
        mailing = post_manager.get_mailing(mailing_id)
        preview = post_manager.format_mailing_preview(mailing)
        
        # Проверяем форматирование
        assert "⏳" in preview, "Должен быть эмодзи ожидания"
        assert "📅" in preview, "Должна быть информация о времени"
        assert future_time.split()[0] in preview, "Должна быть дата"
        
        print("✅ Форматирование отложенных постов работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка форматирования: {e}")
        return False
    finally:
        if 'db' in locals():
            db.close()
        if test_db_path and os.path.exists(test_db_path):
            os.remove(test_db_path)

def test_command_parsing():
    """Тест парсинга команд с отложенными постами"""
    print("\n🔍 Тест парсинга команд...")
    
    # Симулируем команды
    commands = [
        "/send_post 1 all",
        "/send_post 1 all 2024-12-31 15:30",
        "/send_post 1 123456,789012",
        "/send_post 1 123456,789012 2024-12-31 15:30"
    ]
    
    for command in commands:
        try:
            # Парсим команду
            text = command[len("/send_post"):].strip()
            parts = text.split()
            
            assert len(parts) >= 2, f"Недостаточно частей в команде: {command}"
            
            post_id = int(parts[0])
            target = parts[1]
            
            # Проверяем время
            scheduled_at = None
            if len(parts) >= 3:
                time_parts = parts[2:]
                scheduled_at = " ".join(time_parts)
            
            print(f"✅ Команда '{command}' распарсена:")
            print(f"   Post ID: {post_id}")
            print(f"   Target: {target}")
            print(f"   Scheduled: {scheduled_at}")
            
        except Exception as e:
            print(f"❌ Ошибка парсинга команды '{command}': {e}")
            return False
    
    print("✅ Все команды распарсены корректно")
    return True

def main():
    """Главная функция"""
    print("🚀 Тестирование отложенных постов...")
    
    tests = [
        ("Создание отложенных постов", test_scheduled_post_creation),
        ("Форматирование отложенных постов", test_scheduled_post_formatting),
        ("Парсинг команд", test_command_parsing),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: ПРОЙДЕН")
            else:
                print(f"❌ {test_name}: ПРОВАЛЕН")
        except Exception as e:
            print(f"❌ {test_name}: ОШИБКА - {e}")
    
    print(f"\n📊 Результаты тестирования отложенных постов: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ОТЛОЖЕННЫХ ПОСТОВ ПРОЙДЕНЫ!")
    else:
        print("⚠️ Некоторые тесты не прошли")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 