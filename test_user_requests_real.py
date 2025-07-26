#!/usr/bin/env python3
"""
Тестирование системы сбора запросов с реальным пользователем
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import Database

def test_with_real_user():
    """Тестирует с реальным пользователем"""
    print("🧪 ТЕСТИРОВАНИЕ С РЕАЛЬНЫМ ПОЛЬЗОВАТЕЛЕМ")
    print("=" * 50)
    
    try:
        db = Database('database/dev.db')
        
        # Получаем реального пользователя (не из NO_LOGS_USERS)
        all_users = db.get_all_users()
        print(f"👥 Всего пользователей в БД: {len(all_users)}")
        
        # Ищем пользователя не из NO_LOGS_USERS
        try:
            from config_local import NO_LOGS_USERS
        except ImportError:
            from config import NO_LOGS_USERS
        
        excluded_users = set(NO_LOGS_USERS) if NO_LOGS_USERS else set()
        real_users = [uid for uid in all_users if uid not in excluded_users]
        
        if real_users:
            test_user_id = real_users[0]
            print(f"✅ Используем реального пользователя: {test_user_id}")
        else:
            # Создаем тестового пользователя
            test_user_id = 123456789
            print(f"⚠️ Создаем тестового пользователя: {test_user_id}")
            db.update_user(test_user_id, {"name": "Тестовый пользователь"})
        
        # Добавляем тестовые запросы
        test_requests = [
            "Как найти баланс между работой и отдыхом?",
            "Нужна помощь в принятии важного решения о карьере",
            "Хочу преодолеть страх публичных выступлений",
            "Ищу мотивацию для регулярных тренировок",
            "Как справиться с тревожностью перед важными событиями?"
        ]
        
        print(f"\n📝 Добавляем {len(test_requests)} тестовых запросов...")
        for i, request_text in enumerate(test_requests):
            db.save_user_request(test_user_id, request_text, f"real_session_{i+1}", i+1)
            print(f"  ✅ Запрос {i+1}: «{request_text[:40]}...»")
        
        # Проверяем статистику
        print(f"\n📊 Статистика запросов:")
        stats = db.get_user_requests_stats(7)
        print(f"  • Всего запросов: {stats.get('total_requests', 0)}")
        print(f"  • Уникальных пользователей: {stats.get('unique_users', 0)}")
        print(f"  • Средняя длина: {stats.get('avg_length', 0)} символов")
        print(f"  • Минимум: {stats.get('min_length', 0)} символов")
        print(f"  • Максимум: {stats.get('max_length', 0)} символов")
        
        # Проверяем образец
        print(f"\n📋 Образец запросов:")
        sample = db.get_user_requests_sample(3, 7)
        for i, req in enumerate(sample, 1):
            user_name = req.get('user_name', 'Аноним')
            request_text = req['request_text'][:50] + "..." if len(req['request_text']) > 50 else req['request_text']
            print(f"  {i}. «{request_text}» - {user_name}")
        
        db.close()
        print(f"\n🎉 ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_real_user() 