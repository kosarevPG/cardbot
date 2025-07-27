#!/usr/bin/env python3
"""
Скрипт для анализа реальных шагов воронки "Карта дня"
"""

import sqlite3
import json
from datetime import datetime, timedelta
import os

# Путь к базе данных
DB_PATH = "database/dev.db"

def analyze_funnel_steps(days=7):
    """Анализирует реальные шаги воронки карты дня"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Получаем все уникальные шаги для сценария card_of_day
        cursor = conn.execute("""
            SELECT DISTINCT step, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND timestamp >= datetime('now', '-{} days')
            GROUP BY step
            ORDER BY count DESC
        """.format(days))
        
        steps = cursor.fetchall()
        
        print(f"📊 АНАЛИЗ ВОРОНКИ 'КАРТА ДНЯ' (за {days} дней)")
        print("=" * 60)
        
        # Показываем все шаги с количеством
        print("\n🔍 ВСЕ ШАГИ СЦЕНАРИЯ:")
        for step in steps:
            print(f"  • {step['step']}: {step['count']} пользователей")
        
        # Анализируем последовательность шагов
        print(f"\n📈 ПОСЛЕДОВАТЕЛЬНОСТЬ ШАГОВ:")
        
        # Шаг 1: Начали сессию
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'started'
            AND timestamp >= datetime('now', '-{} days')
        """.format(days))
        started = cursor.fetchone()['count']
        print(f"1️⃣ Начали сессию: {started} пользователей")
        
        # Шаг 2: Выбрали ресурс
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'initial_resource_selected'
            AND timestamp >= datetime('now', '-{} days')
        """.format(days))
        resource_selected = cursor.fetchone()['count']
        print(f"2️⃣ Выбрали ресурс: {resource_selected} пользователей")
        
        # Шаг 3: Выбрали тип запроса
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'request_type_selected'
            AND timestamp >= datetime('now', '-{} days')
        """.format(days))
        request_type_selected = cursor.fetchone()['count']
        print(f"3️⃣ Выбрали тип запроса: {request_type_selected} пользователей")
        
        # Шаг 4: Написали текстовый запрос (если выбрали)
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'text_request_provided'
            AND timestamp >= datetime('now', '-{} days')
        """.format(days))
        text_request_provided = cursor.fetchone()['count']
        print(f"4️⃣ Написали текстовый запрос: {text_request_provided} пользователей")
        
        # Шаг 5: Вытянули карту
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'card_drawn'
            AND timestamp >= datetime('now', '-{} days')
        """.format(days))
        card_drawn = cursor.fetchone()['count']
        print(f"5️⃣ Вытянули карту: {card_drawn} пользователей")
        
        # Шаг 6: Написали первую ассоциацию
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'initial_response_provided'
            AND timestamp >= datetime('now', '-{} days')
        """.format(days))
        initial_response_provided = cursor.fetchone()['count']
        print(f"6️⃣ Написали первую ассоциацию: {initial_response_provided} пользователей")
        
        # Шаг 7: Выбрали углубляющий диалог
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'ai_reflection_choice'
            AND timestamp >= datetime('now', '-{} days')
        """.format(days))
        ai_reflection_choice = cursor.fetchone()['count']
        print(f"7️⃣ Выбрали углубляющий диалог: {ai_reflection_choice} пользователей")
        
        # Шаг 8: Завершили сценарий
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT user_id) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'completed'
            AND timestamp >= datetime('now', '-{} days')
        """.format(days))
        completed = cursor.fetchone()['count']
        print(f"8️⃣ Завершили сценарий: {completed} пользователей")
        
        # Анализ потерь
        print(f"\n🚨 АНАЛИЗ ПОТЕРЬ:")
        if started > 0:
            print(f"  • Шаг 1→2: {started - resource_selected} пользователей ({((started - resource_selected) / started * 100):.1f}%)")
            print(f"  • Шаг 2→3: {resource_selected - request_type_selected} пользователей ({((resource_selected - request_type_selected) / started * 100):.1f}%)")
            print(f"  • Шаг 3→5: {request_type_selected - card_drawn} пользователей ({((request_type_selected - card_drawn) / started * 100):.1f}%)")
            print(f"  • Шаг 5→6: {card_drawn - initial_response_provided} пользователей ({((card_drawn - initial_response_provided) / started * 100):.1f}%)")
            print(f"  • Шаг 6→7: {initial_response_provided - ai_reflection_choice} пользователей ({((initial_response_provided - ai_reflection_choice) / started * 100):.1f}%)")
            print(f"  • Шаг 7→8: {ai_reflection_choice - completed} пользователей ({((ai_reflection_choice - completed) / started * 100):.1f}%)")
        
        # Анализ типов запросов
        print(f"\n📝 АНАЛИЗ ТИПОВ ЗАПРОСОВ:")
        cursor = conn.execute("""
            SELECT metadata, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'request_type_selected'
            AND timestamp >= datetime('now', '-{} days')
            GROUP BY metadata
        """.format(days))
        request_types = cursor.fetchall()
        
        for req_type in request_types:
            try:
                meta = json.loads(req_type['metadata'])
                request_type = meta.get('request_type', 'unknown')
                print(f"  • {request_type}: {req_type['count']} пользователей")
            except:
                print(f"  • Неизвестный тип: {req_type['count']} пользователей")
        
        # Анализ выбора углубляющего диалога
        print(f"\n🤖 АНАЛИЗ ВЫБОРА УГЛУБЛЯЮЩЕГО ДИАЛОГА:")
        cursor = conn.execute("""
            SELECT metadata, COUNT(*) as count
            FROM scenario_logs 
            WHERE scenario = 'card_of_day' 
            AND step = 'ai_reflection_choice'
            AND timestamp >= datetime('now', '-{} days')
            GROUP BY metadata
        """.format(days))
        ai_choices = cursor.fetchall()
        
        for choice in ai_choices:
            try:
                meta = json.loads(choice['metadata'])
                choice_type = meta.get('choice', 'unknown')
                print(f"  • {choice_type}: {choice['count']} пользователей")
            except:
                print(f"  • Неизвестный выбор: {choice['count']} пользователей")
        
        print(f"\n✅ ИТОГОВАЯ КОНВЕРСИЯ: {completed}/{started} = {(completed/started*100):.1f}%" if started > 0 else "\n✅ Нет данных")
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    analyze_funnel_steps(7) 