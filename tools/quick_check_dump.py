#!/usr/bin/env python3
import sqlite3

try:
    conn = sqlite3.connect('database/dump_production.db')
    cursor = conn.execute('SELECT COUNT(*) FROM user_requests')
    count = cursor.fetchone()[0]
    print(f'Запросов в dump_production.db: {count}')
    
    if count > 0:
        cursor = conn.execute('SELECT * FROM user_requests LIMIT 3')
        rows = cursor.fetchall()
        print('Примеры запросов:')
        for row in rows:
            print(f'  {row}')
    
    conn.close()
except Exception as e:
    print(f'Ошибка: {e}') 