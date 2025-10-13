#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка исключения админов из метрик
"""

import sqlite3

def test_admin_exclusion():
    """Проверка исключения админов из метрик."""
    db_path = "bot (10).db"
    
    print(f"📁 База данных: {db_path}")
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Проверяем, есть ли VIEW
        print("1️⃣  ПРОВЕРКА VIEW:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'v_%'")
        views = cursor.fetchall()
        
        if views:
            print(f"✅ Найдено VIEW: {len(views)}")
            for view in views:
                print(f"  ✅ {view['name']}")
        else:
            print("❌ VIEW НЕ НАЙДЕНЫ!")
            return
        
        # Проверяем ignored_users
        print("\n2️⃣  ПРОВЕРКА IGNORED_USERS:")
        cursor.execute("SELECT user_id FROM ignored_users")
        ignored_users = cursor.fetchall()
        
        if ignored_users:
            print(f"✅ Исключенных пользователей: {len(ignored_users)}")
            for user in ignored_users:
                print(f"  • {user['user_id']}")
        else:
            print("❌ Нет исключенных пользователей.")
            return
        
        # Проверяем исключение в v_events
        print("\n3️⃣  ПРОВЕРКА ИСКЛЮЧЕНИЯ АДМИНОВ В v_events:")
        cursor.execute("SELECT COUNT(*) as total FROM scenario_logs")
        total_logs = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM v_events")
        total_events = cursor.fetchone()['total']
        
        excluded = total_logs - total_events
        print(f"📊 Всего событий в scenario_logs: {total_logs}")
        print(f"📊 Событий в v_events (после исключения админов): {total_events}")
        print(f"📊 Исключено событий: {excluded}")
        
        if excluded > 0:
            print("✅ Админы исключаются из v_events!")
        else:
            print("❌ Админы НЕ исключаются из v_events!")
        
        # Проверяем конкретных админов
        print("\n4️⃣  ПРОВЕРКА КОНКРЕТНЫХ АДМИНОВ:")
        for user in ignored_users:
            admin_id = user['user_id']
            print(f"👤 Админ {admin_id}:")
            
            cursor.execute("SELECT COUNT(*) as count FROM scenario_logs WHERE user_id = ?", (admin_id,))
            logs_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM v_events WHERE user_id = ?", (admin_id,))
            events_count = cursor.fetchone()['count']
            
            print(f"   В scenario_logs: {logs_count} событий")
            print(f"   В v_events: {events_count} событий")
            
            if logs_count > 0 and events_count == 0:
                print("   ✅ Исключен корректно!")
            else:
                print("   ❌ НЕ исключен корректно!")
        
        # Проверяем метрики
        print("\n5️⃣  ПРОВЕРКА МЕТРИК:")
        
        # DAU сегодня
        cursor.execute("SELECT dau FROM v_dau_daily WHERE d_local = DATE('now', '+3 hours')")
        dau_row = cursor.fetchone()
        if dau_row:
            print(f"📊 DAU сегодня (v_dau_daily): {dau_row['dau']}")
        else:
            print("📊 DAU сегодня: нет данных")
        
        # Уникальные пользователи сегодня
        cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM v_events WHERE d_local = DATE('now', '+3 hours')")
        unique_view = cursor.fetchone()['count']
        print(f"📊 Уникальных пользователей сегодня (v_events): {unique_view}")
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM scenario_logs WHERE DATE(timestamp, '+3 hours') = DATE('now', '+3 hours')")
        unique_logs = cursor.fetchone()['count']
        print(f"📊 Уникальных пользователей сегодня (scenario_logs): {unique_logs}")
        
        excluded_users = unique_logs - unique_view
        print(f"📊 Исключено пользователей: {excluded_users}")
        
        if unique_view < unique_logs:
            print("✅ Пользователи исключаются из метрик!")
        else:
            print("❌ Пользователи НЕ исключаются из метрик!")
        
        print("\n============================================================")
        print("🎯 ИТОГОВЫЙ ВЫВОД:")
        print("============================================================")
        
        if excluded > 0 and excluded_users > 0:
            print("✅ ВСЕ РАБОТАЕТ КОРРЕКТНО!")
            print("   • Админы исключаются из v_events")
            print("   • Метрики показывают только обычных пользователей")
            print("   • VIEW работают правильно")
        else:
            print("❌ ЕСТЬ ПРОБЛЕМЫ!")
            print("   • Проверьте логи выше")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_admin_exclusion()