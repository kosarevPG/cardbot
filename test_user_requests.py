#!/usr/bin/env python3
"""
Тестирование системы сбора запросов пользователей
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import Database

def test_user_requests_system():
    """Тестирует систему сбора запросов пользователей"""
    print("🧪 ТЕСТИРОВАНИЕ СИСТЕМЫ СБОРА ЗАПРОСОВ")
    print("=" * 50)
    
    try:
        db = Database('database/dev.db')
        
        # Тест 1: Сохранение запроса
        print("\n1️⃣ Тест сохранения запроса...")
        test_user_id = 999999999
        test_request = "Помоги мне найти мотивацию для работы над проектом"
        test_session_id = "test_session_123"
        test_card_number = 15
        
        db.save_user_request(test_user_id, test_request, test_session_id, test_card_number)
        print("✅ Запрос сохранен успешно")
        
        # Тест 2: Получение статистики
        print("\n2️⃣ Тест получения статистики...")
        stats = db.get_user_requests_stats(7)
        print(f"📊 Статистика запросов:")
        print(f"  • Всего запросов: {stats.get('total_requests', 0)}")
        print(f"  • Уникальных пользователей: {stats.get('unique_users', 0)}")
        print(f"  • Средняя длина: {stats.get('avg_length', 0)} символов")
        print(f"  • Минимум: {stats.get('min_length', 0)} символов")
        print(f"  • Максимум: {stats.get('max_length', 0)} символов")
        
        # Тест 3: Получение образца запросов
        print("\n3️⃣ Тест получения образца запросов...")
        sample = db.get_user_requests_sample(5, 7)
        print(f"📝 Образец запросов ({len(sample)} записей):")
        for i, req in enumerate(sample, 1):
            user_name = req.get('user_name', 'Аноним')
            request_text = req['request_text'][:30] + "..." if len(req['request_text']) > 30 else req['request_text']
            print(f"  {i}. «{request_text}» - {user_name}")
        
        # Тест 4: Получение запросов конкретного пользователя
        print("\n4️⃣ Тест получения запросов пользователя...")
        user_requests = db.get_user_requests_by_user(test_user_id, 10)
        print(f"👤 Запросы пользователя {test_user_id} ({len(user_requests)} записей):")
        for i, req in enumerate(user_requests, 1):
            request_text = req['request_text'][:40] + "..." if len(req['request_text']) > 40 else req['request_text']
            print(f"  {i}. «{request_text}»")
        
        # Тест 5: Добавление еще нескольких тестовых запросов
        print("\n5️⃣ Добавление тестовых запросов...")
        test_requests = [
            "Как справиться со стрессом на работе?",
            "Нужна помощь в принятии важного решения",
            "Хочу найти баланс между работой и личной жизнью",
            "Как преодолеть страх неудачи?",
            "Ищу вдохновение для творчества"
        ]
        
        for i, request_text in enumerate(test_requests):
            db.save_user_request(test_user_id, request_text, f"test_session_{i+1}", i+1)
            print(f"  ✅ Добавлен запрос {i+1}: «{request_text[:30]}...»")
        
        # Обновленная статистика
        print("\n6️⃣ Обновленная статистика...")
        updated_stats = db.get_user_requests_stats(7)
        print(f"📊 Обновленная статистика:")
        print(f"  • Всего запросов: {updated_stats.get('total_requests', 0)}")
        print(f"  • Уникальных пользователей: {updated_stats.get('unique_users', 0)}")
        print(f"  • Средняя длина: {updated_stats.get('avg_length', 0)} символов")
        
        db.close()
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_user_requests_system() 