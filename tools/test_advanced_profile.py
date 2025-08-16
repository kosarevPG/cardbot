#!/usr/bin/env python3
from database.db import Database
from datetime import datetime, timedelta
import pytz

def test_advanced_profile():
    """Тестирует расширенную статистику профиля"""
    
    print("=== ТЕСТИРОВАНИЕ РАСШИРЕННОГО ПРОФИЛЯ ===\n")
    
    # Инициализируем БД
    db = Database('database/dev.db')
    
    # Тестируем на реальном пользователе (ваш ID)
    test_user_id = 6682555021
    
    print(f"Тестируем профиль для пользователя {test_user_id}...\n")
    
    # Получаем расширенную статистику
    advanced_stats = db.get_user_advanced_stats(test_user_id)
    
    print("📊 РАСШИРЕННАЯ СТАТИСТИКА:")
    print("-" * 50)
    
    for key, value in advanced_stats.items():
        if key == 'achievements':
            print(f"🏆 {key}: {', '.join(value) if value else 'нет'}")
        else:
            print(f"• {key}: {value}")
    
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ОТДЕЛЬНЫХ МЕТРИК:")
    print("=" * 60)
    
    # Проверяем серии дней
    print(f"\n🔥 Серия дней:")
    print(f"  • Текущая: {advanced_stats.get('current_streak', 0)}")
    print(f"  • Максимальная: {advanced_stats.get('max_consecutive_days', 0)}")
    
    # Проверяем паттерны
    print(f"\n⏰ Паттерны:")
    print(f"  • Любимое время: {advanced_stats.get('favorite_time', 'нет данных')}")
    print(f"  • Любимый день: {advanced_stats.get('favorite_day', 'нет данных')}")
    
    # Проверяем статистику
    print(f"\n📈 Статистика:")
    print(f"  • Завершенность: {advanced_stats.get('completion_rate', 0)}%")
    print(f"  • Глубина сессий: {advanced_stats.get('avg_session_depth', 0)} шагов")
    print(f"  • Сессий в день: {advanced_stats.get('avg_sessions_per_day', 0)}")
    
    # Проверяем достижения
    achievements = advanced_stats.get('achievements', [])
    if achievements:
        print(f"\n🏆 Достижения:")
        for achievement in achievements:
            print(f"  • {achievement}")
    else:
        print(f"\n🏆 Достижения: пока нет")
    
    # Проверяем историю
    first_day = advanced_stats.get('first_day')
    last_day = advanced_stats.get('last_day')
    if first_day and last_day:
        print(f"\n📅 История:")
        print(f"  • Первый день: {first_day}")
        print(f"  • Последний день: {last_day}")
        print(f"  • Всего дней: {advanced_stats.get('total_unique_days', 0)}")
    
    db.close()
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    test_advanced_profile() 