#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка формата timestamp в scenario_logs
"""

import sqlite3

db_path = "bot (7).db"

print(f"📁 База данных: {db_path}")
print()

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Проверяем формат timestamp
    print("🔍 Формат timestamp в scenario_logs:")
    cursor.execute("""
        SELECT timestamp, step, scenario
        FROM scenario_logs
        ORDER BY rowid DESC
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        print(f"  • timestamp: {row['timestamp']} | step: {row['step']}")
    
    print()
    
    # Проверяем, что возвращает datetime() с unixepoch
    print("🔍 Тест datetime(timestamp, 'unixepoch'):")
    cursor.execute("""
        SELECT 
            timestamp,
            datetime(timestamp, 'unixepoch') as dt_unix,
            datetime(timestamp) as dt_direct,
            date(timestamp) as date_direct
        FROM scenario_logs
        ORDER BY rowid DESC
        LIMIT 3
    """)
    
    for row in cursor.fetchall():
        print(f"  • timestamp: {row['timestamp']}")
        print(f"    datetime(unixepoch): {row['dt_unix']}")
        print(f"    datetime(direct): {row['dt_direct']}")
        print(f"    date(direct): {row['date_direct']}")
        print()
    
    print()
    print("🎯 ВЫВОД:")
    
    first_ts = cursor.execute("SELECT timestamp FROM scenario_logs LIMIT 1").fetchone()
    if first_ts:
        ts_value = first_ts['timestamp']
        
        if isinstance(ts_value, (int, float)):
            print("  ✅ timestamp хранится как число (unix timestamp)")
            print("     VIEW правильно используют datetime(timestamp, 'unixepoch')")
        elif isinstance(ts_value, str):
            if 'T' in str(ts_value) or '-' in str(ts_value):
                print("  ⚠️  timestamp хранится как ISO строка!")
                print("     VIEW НЕПРАВИЛЬНО используют 'unixepoch'")
                print()
                print("  🔧 РЕШЕНИЕ:")
                print("     Нужно изменить VIEW, чтобы использовать timestamp напрямую:")
                print("     datetime(l.timestamp) вместо datetime(l.timestamp, 'unixepoch')")
            else:
                print(f"  ❓ timestamp в неизвестном формате: {ts_value}")
        else:
            print(f"  ❓ timestamp имеет неожиданный тип: {type(ts_value)}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

