#!/usr/bin/env python3
"""
Тестирование детального отображения запросов пользователей
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db import Database
from datetime import datetime

def test_detailed_requests():
    """Тестирует детальное отображение запросов"""
    print("🧪 ТЕСТИРОВАНИЕ ДЕТАЛЬНОГО ОТОБРАЖЕНИЯ ЗАПРОСОВ")
    print("=" * 60)
    
    try:
        db = Database('database/dev.db')
        
        # Получаем образец запросов
        sample = db.get_user_requests_sample(10, 7)
        
        print(f"📊 Найдено запросов: {len(sample)}")
        print()
        
        if sample:
            for i, req in enumerate(sample, 1):
                user_id = req.get('user_id', 'N/A')
                user_name = req.get('user_name', 'Аноним')
                username = req.get('user_username', '')
                timestamp = req.get('timestamp', '')
                request_text = req['request_text']
                card_number = req.get('card_number', 'N/A')
                
                # Форматируем дату
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_date = timestamp
                
                # Форматируем username
                username_display = f"@{username}" if username else "без username"
                
                print(f"🔸 ЗАПРОС #{i}")
                print(f"   📅 Дата: {formatted_date}")
                print(f"   🎴 Карта: {card_number}")
                print(f"   👤 Пользователь:")
                print(f"      • ID: {user_id}")
                print(f"      • Имя: {user_name}")
                print(f"      • Username: {username_display}")
                print(f"   💬 Запрос: «{request_text}»")
                print(f"   {'─' * 50}")
        else:
            print("Пока нет запросов для отображения")
        
        # Тестируем статистику
        print(f"\n📈 СТАТИСТИКА:")
        stats = db.get_user_requests_stats(7)
        print(f"   • Всего запросов: {stats.get('total_requests', 0)}")
        print(f"   • Уникальных пользователей: {stats.get('unique_users', 0)}")
        print(f"   • Средняя длина: {stats.get('avg_length', 0)} символов")
        print(f"   • Минимум: {stats.get('min_length', 0)} символов")
        print(f"   • Максимум: {stats.get('max_length', 0)} символов")
        
        db.close()
        print(f"\n🎉 ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_detailed_requests() 