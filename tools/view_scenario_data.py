#!/usr/bin/env python3
"""
Скрипт для просмотра данных логирования сценариев
"""

import os
import sys
import json
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config_local import TIMEZONE, DB_PATH
except ImportError:
    from config import TIMEZONE
    DB_PATH = None

from database.db import Database

def view_scenario_data():
    """Просматривает данные логирования сценариев"""
    print("🔍 Просмотр данных логирования сценариев...")
    
    # Определяем путь к БД
    if DB_PATH and os.path.exists(DB_PATH):
        db_path = DB_PATH
        print(f"📁 Используем dev БД: {db_path}")
    else:
        db_path = "database/dev.db"
        if not os.path.exists(db_path):
            db_path = "database/bot.db"
        print(f"📁 Используем БД: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ БД не найдена: {db_path}")
        return
    
    # Инициализируем БД
    db = Database(db_path)
    
    print("\n" + "="*60)
    print("📊 ОБЩАЯ СТАТИСТИКА СЦЕНАРИЕВ")
    print("="*60)
    
    # Получаем статистику за последние 7 дней
    card_stats = db.get_scenario_stats('card_of_day', 7)
    reflection_stats = db.get_scenario_stats('evening_reflection', 7)
    
    if card_stats:
        print(f"\n🎴 СЦЕНАРИЙ 'КАРТА ДНЯ' (за 7 дней):")
        print(f"  • Запусков: {card_stats['total_starts']}")
        print(f"  • Завершений: {card_stats['total_completions']}")
        print(f"  • Брошено: {card_stats['total_abandoned']}")
        print(f"  • Процент завершения: {card_stats['completion_rate']:.1f}%")
        print(f"  • Среднее шагов: {card_stats['avg_steps']}")
    else:
        print("\n🎴 СЦЕНАРИЙ 'КАРТА ДНЯ': Нет данных")
    
    if reflection_stats:
        print(f"\n🌙 СЦЕНАРИЙ 'ВЕЧЕРНЯЯ РЕФЛЕКСИЯ' (за 7 дней):")
        print(f"  • Запусков: {reflection_stats['total_starts']}")
        print(f"  • Завершений: {reflection_stats['total_completions']}")
        print(f"  • Брошено: {reflection_stats['total_abandoned']}")
        print(f"  • Процент завершения: {reflection_stats['completion_rate']:.1f}%")
        print(f"  • Среднее шагов: {reflection_stats['avg_steps']}")
    else:
        print("\n🌙 СЦЕНАРИЙ 'ВЕЧЕРНЯЯ РЕФЛЕКСИЯ': Нет данных")
    
    print("\n" + "="*60)
    print("📋 ДЕТАЛЬНЫЕ ДАННЫЕ ПО ШАГАМ")
    print("="*60)
    
    # Получаем статистику по шагам
    card_steps = db.get_scenario_step_stats('card_of_day', 7)
    reflection_steps = db.get_scenario_step_stats('evening_reflection', 7)
    
    # Анализируем детальные метрики для "Карта дня"
    print(f"\n🎴 ДЕТАЛЬНЫЕ МЕТРИКИ 'КАРТА ДНЯ':")
    
    # 1. Тип запроса (текстовый vs мысленный)
    try:
        cursor = db.conn.execute("""
            SELECT step, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step IN ('text_request_provided', 'request_type_selected')
            AND timestamp >= datetime('now', '-7 days')
            GROUP BY step
        """)
        request_stats = cursor.fetchall()
        
        text_requests = 0
        mental_requests = 0
        for stat in request_stats:
            if stat['step'] == 'text_request_provided':
                text_requests = stat['count']
            elif stat['step'] == 'request_type_selected':
                mental_requests = stat['count']
        
        total_requests = text_requests + mental_requests
        if total_requests > 0:
            print(f"  📝 Запросы к карте:")
            print(f"    • Текстовые: {text_requests} ({text_requests/total_requests*100:.1f}%)")
            print(f"    • Мысленные: {mental_requests} ({mental_requests/total_requests*100:.1f}%)")
    except Exception as e:
        print(f"  ❌ Ошибка при анализе запросов: {e}")
    
    # 2. Выбор рефлексии с ИИ
    try:
        cursor = db.conn.execute("""
            SELECT metadata, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'ai_reflection_choice'
            AND timestamp >= datetime('now', '-7 days')
            GROUP BY metadata
        """)
        ai_choice_stats = cursor.fetchall()
        
        ai_yes = 0
        ai_no = 0
        for stat in ai_choice_stats:
            try:
                meta = json.loads(stat['metadata'])
                if meta.get('choice') == 'yes':
                    ai_yes = stat['count']
                elif meta.get('choice') == 'no':
                    ai_no = stat['count']
            except:
                pass
        
        total_ai_choices = ai_yes + ai_no
        if total_ai_choices > 0:
            print(f"  🤖 Рефлексия с ИИ:")
            print(f"    • Выбрали: {ai_yes} ({ai_yes/total_ai_choices*100:.1f}%)")
            print(f"    • Отказались: {ai_no} ({ai_no/total_ai_choices*100:.1f}%)")
    except Exception as e:
        print(f"  ❌ Ошибка при анализе выбора ИИ: {e}")
    
    # 3. Количество ответов на ИИ-вопросы
    try:
        cursor = db.conn.execute("""
            SELECT step, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step IN ('ai_response_1_provided', 'ai_response_2_provided', 'ai_response_3_provided')
            AND timestamp >= datetime('now', '-7 days')
            GROUP BY step
        """)
        ai_responses = cursor.fetchall()
        
        responses_1 = 0
        responses_2 = 0
        responses_3 = 0
        for stat in ai_responses:
            if stat['step'] == 'ai_response_1_provided':
                responses_1 = stat['count']
            elif stat['step'] == 'ai_response_2_provided':
                responses_2 = stat['count']
            elif stat['step'] == 'ai_response_3_provided':
                responses_3 = stat['count']
        
        print(f"  💬 Ответы на ИИ-вопросы:")
        print(f"    • 1-й вопрос: {responses_1}")
        print(f"    • 2-й вопрос: {responses_2} ({responses_2/responses_1*100:.1f}% от 1-го)" if responses_1 > 0 else "    • 2-й вопрос: 0")
        print(f"    • 3-й вопрос: {responses_3} ({responses_3/responses_1*100:.1f}% от 1-го)" if responses_1 > 0 else "    • 3-й вопрос: 0")
    except Exception as e:
        print(f"  ❌ Ошибка при анализе ответов ИИ: {e}")
    
    # 4. Изменение самочувствия
    try:
        cursor = db.conn.execute("""
            SELECT metadata, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'mood_change_recorded'
            AND timestamp >= datetime('now', '-7 days')
            GROUP BY metadata
        """)
        mood_stats = cursor.fetchall()
        
        mood_better = 0
        mood_worse = 0
        mood_same = 0
        mood_unknown = 0
        
        for stat in mood_stats:
            try:
                meta = json.loads(stat['metadata'])
                change = meta.get('change_direction', 'unknown')
                if change == 'better':
                    mood_better = stat['count']
                elif change == 'worse':
                    mood_worse = stat['count']
                elif change == 'same':
                    mood_same = stat['count']
                else:
                    mood_unknown = stat['count']
            except:
                mood_unknown += stat['count']
        
        total_mood_changes = mood_better + mood_worse + mood_same + mood_unknown
        if total_mood_changes > 0:
            print(f"  😊 Изменение самочувствия:")
            print(f"    • Улучшилось: {mood_better} ({mood_better/total_mood_changes*100:.1f}%)")
            print(f"    • Ухудшилось: {mood_worse} ({mood_worse/total_mood_changes*100:.1f}%)")
            print(f"    • Осталось тем же: {mood_same} ({mood_same/total_mood_changes*100:.1f}%)")
            if mood_unknown > 0:
                print(f"    • Неопределено: {mood_unknown} ({mood_unknown/total_mood_changes*100:.1f}%)")
    except Exception as e:
        print(f"  ❌ Ошибка при анализе самочувствия: {e}")
    
    # 5. Оценка полезности
    try:
        cursor = db.conn.execute("""
            SELECT metadata, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'usefulness_rating'
            AND timestamp >= datetime('now', '-7 days')
            GROUP BY metadata
        """)
        rating_stats = cursor.fetchall()
        
        rating_helped = 0
        rating_interesting = 0
        rating_notdeep = 0
        
        for stat in rating_stats:
            try:
                meta = json.loads(stat['metadata'])
                rating = meta.get('rating', 'unknown')
                if rating == 'helped':
                    rating_helped = stat['count']
                elif rating == 'interesting':
                    rating_interesting = stat['count']
                elif rating == 'notdeep':
                    rating_notdeep = stat['count']
            except:
                pass
        
        total_ratings = rating_helped + rating_interesting + rating_notdeep
        if total_ratings > 0:
            print(f"  ⭐ Оценка полезности:")
            print(f"    • Помогло: {rating_helped} ({rating_helped/total_ratings*100:.1f}%)")
            print(f"    • Было интересно: {rating_interesting} ({rating_interesting/total_ratings*100:.1f}%)")
            print(f"    • Недостаточно глубоко: {rating_notdeep} ({rating_notdeep/total_ratings*100:.1f}%)")
    except Exception as e:
        print(f"  ❌ Ошибка при анализе оценок: {e}")
    
    if card_steps:
        print(f"\n🎴 ШАГИ СЦЕНАРИЯ 'КАРТА ДНЯ':")
        for step in card_steps:
            print(f"  • {step['step']}: {step['count']} раз")
    else:
        print("\n🎴 ШАГИ 'КАРТА ДНЯ': Нет данных")
    
    if reflection_steps:
        print(f"\n🌙 ШАГИ СЦЕНАРИЯ 'ВЕЧЕРНЯЯ РЕФЛЕКСИЯ':")
        for step in reflection_steps:
            print(f"  • {step['step']}: {step['count']} раз")
    else:
        print("\n🌙 ШАГИ 'ВЕЧЕРНЯЯ РЕФЛЕКСИЯ': Нет данных")
    
    print("\n" + "="*60)
    print("👤 ПОСЛЕДНИЕ СЕССИИ ПОЛЬЗОВАТЕЛЕЙ")
    print("="*60)
    
    # Получаем последние сессии
    try:
        cursor = db.conn.execute("""
            SELECT user_id, scenario, status, started_at, completed_at, steps_count, session_id
            FROM user_scenarios 
            ORDER BY started_at DESC 
            LIMIT 10
        """)
        
        sessions = cursor.fetchall()
        if sessions:
            for session in sessions:
                user_id = session['user_id']
                scenario = session['scenario']
                status = session['status']
                started_at = session['started_at']
                completed_at = session['completed_at']
                steps_count = session['steps_count']
                session_id = session['session_id']
                
                print(f"\n👤 Пользователь {user_id}:")
                print(f"  • Сценарий: {scenario}")
                print(f"  • Статус: {status}")
                print(f"  • Начало: {started_at}")
                if completed_at:
                    print(f"  • Завершение: {completed_at}")
                print(f"  • Шагов: {steps_count}")
                print(f"  • Session ID: {session_id[:20]}...")
        else:
            print("Нет данных о сессиях")
    except Exception as e:
        print(f"Ошибка при получении сессий: {e}")
    
    print("\n" + "="*60)
    print("🔍 ДЕТАЛЬНЫЕ ЛОГИ ПОСЛЕДНИХ ШАГОВ")
    print("="*60)
    
    # Получаем последние логи
    try:
        cursor = db.conn.execute("""
            SELECT user_id, scenario, step, metadata, timestamp
            FROM scenario_logs 
            ORDER BY timestamp DESC 
            LIMIT 15
        """)
        
        logs = cursor.fetchall()
        if logs:
            for log in logs:
                user_id = log['user_id']
                scenario = log['scenario']
                step = log['step']
                metadata = log['metadata']
                timestamp = log['timestamp']
                
                print(f"\n📝 {timestamp}:")
                print(f"  • Пользователь: {user_id}")
                print(f"  • Сценарий: {scenario}")
                print(f"  • Шаг: {step}")
                if metadata:
                    try:
                        meta_dict = json.loads(metadata)
                        meta_str = ", ".join([f"{k}={v}" for k, v in meta_dict.items() if len(str(v)) < 50])
                        if meta_str:
                            print(f"  • Метаданные: {meta_str}")
                    except:
                        print(f"  • Метаданные: {metadata[:100]}...")
        else:
            print("Нет данных о логах")
    except Exception as e:
        print(f"Ошибка при получении логов: {e}")
    
    # Закрываем соединение
    db.close()
    
    print("\n" + "="*60)
    print("✅ Просмотр завершен!")
    print("💡 Для получения статистики в боте используйте: /scenario_stats")

if __name__ == "__main__":
    view_scenario_data() 