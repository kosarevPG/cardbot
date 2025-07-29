#!/usr/bin/env python3
"""
Скрипт для проверки безопасности в продакшн БД
"""

import sqlite3
import os
from datetime import datetime

def check_production_security():
    """Проверяет безопасность в продакшн БД"""
    print("🔒 ПРОВЕРКА БЕЗОПАСНОСТИ В PRODUCTION БД")
    print("=" * 50)
    
    # ID администраторов
    ADMIN_IDS = ['6682555021', '392141189', '239719200', '7494824111', '171507422', '138192985']
    
    try:
        # Подключаемся к продакшн БД
        db_path = '/data/bot.db'
        if not os.path.exists(db_path):
            print(f"❌ Продакшн БД не найдена: {db_path}")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем админские действия
        print("1️⃣ Проверка админских действий:")
        cursor.execute("""
            SELECT 
                user_id,
                username,
                name,
                action,
                timestamp,
                CASE 
                    WHEN user_id IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985) 
                    THEN 'LEGITIMATE_ADMIN' 
                    ELSE 'UNAUTHORIZED_ACCESS' 
                END as access_type
            FROM actions 
            WHERE action LIKE 'admin_%'
            ORDER BY timestamp DESC
        """)
        
        admin_actions = cursor.fetchall()
        unauthorized_count = 0
        
        for action in admin_actions:
            user_id, username, name, action_type, timestamp, access_type = action
            if access_type == 'UNAUTHORIZED_ACCESS':
                unauthorized_count += 1
                print(f"   🚨 НЕСАНКЦИОНИРОВАННЫЙ ДОСТУП: User {user_id} ({username}) - {action_type} at {timestamp}")
            else:
                print(f"   ✅ Легитимный доступ: User {user_id} ({username}) - {action_type}")
        
        if unauthorized_count == 0:
            print("   ✅ Нет попыток несанкционированного доступа")
        else:
            print(f"   🚨 ОБНАРУЖЕНО {unauthorized_count} попыток несанкционированного доступа!")
        
        # Проверяем пользователя 865377684
        print(f"\n2️⃣ Проверка пользователя 865377684:")
        cursor.execute("""
            SELECT 
                user_id,
                username,
                name,
                action,
                timestamp
            FROM actions 
            WHERE user_id = 865377684
            ORDER BY timestamp DESC
        """)
        
        user_actions = cursor.fetchall()
        
        if user_actions:
            print(f"   📊 Найдено {len(user_actions)} действий пользователя 865377684:")
            for action in user_actions:
                user_id, username, name, action_type, timestamp = action
                print(f"      - {action_type} at {timestamp}")
                
                if action_type.startswith('admin_'):
                    print(f"      🚨 КРИТИЧЕСКО: Пользователь {name} ({user_id}) получил доступ к админ-функции!")
        else:
            print("   ℹ️ Действий пользователя 865377684 не найдено")
        
        # Проверяем общую статистику
        print(f"\n3️⃣ Общая статистика безопасности:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_admin_actions,
                COUNT(CASE WHEN user_id IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985) THEN 1 END) as legitimate_actions,
                COUNT(CASE WHEN user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985) THEN 1 END) as unauthorized_actions
            FROM actions 
            WHERE action LIKE 'admin_%'
        """)
        
        security_stats = cursor.fetchone()
        if security_stats:
            total, legitimate, unauthorized = security_stats
            print(f"   📊 Всего админских действий: {total}")
            print(f"   ✅ Легитимных действий: {legitimate}")
            print(f"   🚨 Несанкционированных действий: {unauthorized}")
            
            if unauthorized > 0:
                print("   ⚠️ ВНИМАНИЕ: Обнаружены несанкционированные действия!")
                print("   🚨 ТРЕБУЕТСЯ НЕМЕДЛЕННОЕ ВМЕШАТЕЛЬСТВО!")
            else:
                print("   🛡️ БЕЗОПАСНОСТЬ: Все действия легитимны")
        
        conn.close()
        
        if unauthorized_count > 0:
            print(f"\n🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА БЕЗОПАСНОСТИ!")
            print("Рядовые пользователи получают доступ к админ-функциям!")
            print("НЕМЕДЛЕННО проверьте деплой обновлений безопасности!")
            return False
        else:
            print(f"\n✅ Безопасность в норме")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при проверке безопасности: {e}")
        return False

if __name__ == "__main__":
    check_production_security() 