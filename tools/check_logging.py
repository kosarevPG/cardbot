#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from database.db import Database
import json
from datetime import datetime, timedelta

def check_scenario_logging():
    """Проверяет корректность логирования сценариев"""
    
    print("=== ПРОВЕРКА ЛОГИРОВАНИЯ СЦЕНАРИЕВ ===\n")
    
    # Инициализируем БД
    db = Database('database/dev.db')
    
    # 1. Проверяем общую статистику сценариев
    print("1. ОБЩАЯ СТАТИСТИКА СЦЕНАРИЕВ:")
    print("-" * 50)
    
    scenarios = ['card_of_day', 'evening_reflection']
    for scenario in scenarios:
        stats = db.get_scenario_stats(scenario, 7)
        print(f"\n{scenario.upper()}:")
        if stats:
            print(f"  Всего запусков за 7 дней: {stats.get('total_starts', 0)}")
            print(f"  Завершено: {stats.get('total_completions', 0)}")
            print(f"  Брошено: {stats.get('total_abandoned', 0)}")
            print(f"  Процент завершения: {stats.get('completion_rate', 0):.1f}%")
            print(f"  Процент брошенных: {stats.get('abandonment_rate', 0):.1f}%")
            print(f"  Среднее количество шагов: {stats.get('avg_steps', 0)}")
        else:
            print("  Нет данных")
    
    # 2. Проверяем детальные логи шагов
    print("\n\n2. ДЕТАЛЬНЫЕ ЛОГИ ШАГОВ:")
    print("-" * 50)
    
    for scenario in scenarios:
        step_stats = db.get_scenario_step_stats(scenario, 7)
        print(f"\n{scenario.upper()} - шаги:")
        
        if step_stats:
            for step_data in step_stats:
                step = step_data.get('step', 'unknown')
                count = step_data.get('count', 0)
                print(f"  {step}: {count}")
        else:
            print("  Нет данных о шагах")
    
    # 3. Проверяем последние сессии карты дня
    print("\n\n3. ПОСЛЕДНИЕ СЕССИИ КАРТЫ ДНЯ:")
    print("-" * 50)
    
    # Получаем все сессии карты дня
    try:
        cursor = db.conn.execute("""
            SELECT * FROM user_scenarios 
            WHERE scenario = 'card_of_day' 
            ORDER BY started_at DESC 
            LIMIT 5
        """)
        
        sessions = cursor.fetchall()
        if sessions:
            print(f"Последние {len(sessions)} сессии:")
            for i, session in enumerate(sessions):
                print(f"\n  Сессия {i+1}:")
                print(f"    ID: {session['session_id']}")
                print(f"    Пользователь: {session['user_id']}")
                print(f"    Статус: {session['status']}")
                print(f"    Шагов: {session['steps_count']}")
                print(f"    Начало: {session['started_at']}")
                print(f"    Завершение: {session['completed_at']}")
        else:
            print("Нет сессий карты дня")
    except Exception as e:
        print(f"Ошибка при получении сессий: {e}")
    
    # 4. Проверяем метаданные для карты дня
    print("\n\n4. МЕТАДАННЫЕ КАРТЫ ДНЯ:")
    print("-" * 50)
    
    # Получаем последние логи с метаданными
    try:
        cursor = db.conn.execute("""
            SELECT user_id, step, metadata, timestamp 
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND metadata IS NOT NULL 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        logs = cursor.fetchall()
        if logs:
            print("Последние 10 логов с метаданными:")
            for log in logs:
                try:
                    metadata = json.loads(log['metadata']) if log['metadata'] else {}
                    print(f"  Пользователь {log['user_id']}: {log['step']} - {metadata}")
                except json.JSONDecodeError:
                    print(f"  Пользователь {log['user_id']}: {log['step']} - [Ошибка парсинга метаданных]")
        else:
            print("Нет логов с метаданными")
    except Exception as e:
        print(f"Ошибка при получении метаданных: {e}")
    
    # 5. Проверяем способы восстановления
    print("\n\n5. СПОСОБЫ ВОССТАНОВЛЕНИЯ:")
    print("-" * 50)
    
    try:
        cursor = db.conn.execute("""
            SELECT user_id, method, timestamp 
            FROM user_recharge_methods 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        
        methods = cursor.fetchall()
        if methods:
            print("Последние 5 способов восстановления:")
            for method in methods:
                print(f"  Пользователь {method['user_id']}: {method['method']} ({method['timestamp']})")
        else:
            print("Нет сохранённых способов восстановления")
    except Exception as e:
        print(f"Ошибка при получении способов восстановления: {e}")
    
    # 6. Сравнение с командой /scenario_stats
    print("\n\n6. СРАВНЕНИЕ С /SCENARIO_STATS:")
    print("-" * 50)
    
    print("Данные, которые должны показываться в /scenario_stats:")
    for scenario in scenarios:
        stats = db.get_scenario_stats(scenario, 7)
        if stats:
            print(f"\n{scenario.upper()}:")
            print(f"  Запусков: {stats.get('total_starts', 0)}")
            print(f"  Завершено: {stats.get('total_completions', 0)} ({stats.get('completion_rate', 0):.1f}%)")
            print(f"  Брошено: {stats.get('total_abandoned', 0)} ({stats.get('abandonment_rate', 0):.1f}%)")
            print(f"  Среднее шагов: {stats.get('avg_steps', 0)}")
    
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 60)

if __name__ == "__main__":
    check_scenario_logging() 