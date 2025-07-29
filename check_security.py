#!/usr/bin/env python3
"""
Скрипт для проверки безопасности админ-панели
Проверяет попытки несанкционированного доступа
"""

import sqlite3
import logging
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ID администраторов
ADMIN_IDS = ['6682555021', '392141189', '239719200', '7494824111', '171507422', '138192985']

def check_security():
    """Проверяет безопасность админ-панели."""
    try:
        conn = sqlite3.connect('database/bot.db')
        cursor = conn.cursor()
        
        print("🔒 ПРОВЕРКА БЕЗОПАСНОСТИ АДМИН-ПАНЕЛИ")
        print("=" * 50)
        
        # 1. Проверка попыток несанкционированного доступа
        print("\n1️⃣ Проверка попыток доступа к админ-функциям:")
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
                AND timestamp >= datetime('now', '-7 days')
            ORDER BY timestamp DESC
        """)
        
        admin_attempts = cursor.fetchall()
        unauthorized_count = 0
        
        for attempt in admin_attempts:
            user_id, username, name, action, timestamp, access_type = attempt
            if access_type == 'UNAUTHORIZED_ACCESS':
                unauthorized_count += 1
                print(f"   🚨 НЕСАНКЦИОНИРОВАННЫЙ ДОСТУП: User {user_id} ({username}) - {action} at {timestamp}")
            else:
                print(f"   ✅ Легитимный доступ: User {user_id} ({username}) - {action}")
        
        if unauthorized_count == 0:
            print("   ✅ Нет попыток несанкционированного доступа")
        else:
            print(f"   🚨 ОБНАРУЖЕНО {unauthorized_count} попыток несанкционированного доступа!")
        
        # 2. Поиск пользователей с подозрительной активностью
        print("\n2️⃣ Пользователи с подозрительной активностью:")
        cursor.execute("""
            SELECT 
                user_id,
                username,
                name,
                COUNT(*) as action_count,
                GROUP_CONCAT(DISTINCT action) as actions_performed,
                MIN(timestamp) as first_attempt,
                MAX(timestamp) as last_attempt
            FROM actions 
            WHERE action LIKE 'admin_%'
                AND user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985)
                AND timestamp >= datetime('now', '-7 days')
            GROUP BY user_id, username, name
            ORDER BY action_count DESC
        """)
        
        suspicious_users = cursor.fetchall()
        
        if suspicious_users:
            print("   🚨 ОБНАРУЖЕНЫ ПОДОЗРИТЕЛЬНЫЕ ПОЛЬЗОВАТЕЛИ:")
            for user in suspicious_users:
                user_id, username, name, action_count, actions, first_attempt, last_attempt = user
                print(f"      User {user_id} ({username}): {action_count} админских действий")
                print(f"         Действия: {actions}")
                print(f"         Период: {first_attempt} - {last_attempt}")
        else:
            print("   ✅ Подозрительных пользователей не обнаружено")
        
        # 3. Проверка доступа к конфиденциальным данным
        print("\n3️⃣ Проверка доступа к конфиденциальным данным:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_requests,
                COUNT(DISTINCT user_id) as unique_users,
                MIN(timestamp) as earliest_access,
                MAX(timestamp) as latest_access
            FROM user_requests 
            WHERE timestamp >= datetime('now', '-7 days')
                AND user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985, 999999999)
        """)
        
        data_access = cursor.fetchone()
        if data_access:
            total_requests, unique_users, earliest, latest = data_access
            print(f"   📊 Всего запросов: {total_requests}")
            print(f"   👥 Уникальных пользователей: {unique_users}")
            print(f"   📅 Период: {earliest} - {latest}")
        
        # 4. Общие рекомендации
        print("\n4️⃣ Рекомендации по безопасности:")
        
        if unauthorized_count > 0:
            print("   🚨 КРИТИЧЕСКИЕ МЕРЫ:")
            print("      - Немедленно заблокировать подозрительных пользователей")
            print("      - Проверить логи на предмет утечки данных")
            print("      - Усилить проверки прав доступа")
            print("      - Рассмотреть возможность смены токенов")
        else:
            print("   ✅ Система безопасности работает корректно")
            print("   💡 Рекомендации:")
            print("      - Регулярно проверять логи доступа")
            print("      - Мониторить подозрительную активность")
            print("      - Обновлять список администраторов")
        
        # 5. Статистика безопасности
        print("\n5️⃣ Статистика безопасности (за 7 дней):")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_admin_actions,
                COUNT(DISTINCT user_id) as unique_admin_users,
                COUNT(CASE WHEN user_id IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985) THEN 1 END) as legitimate_actions,
                COUNT(CASE WHEN user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985) THEN 1 END) as unauthorized_actions
            FROM actions 
            WHERE action LIKE 'admin_%'
                AND timestamp >= datetime('now', '-7 days')
        """)
        
        security_stats = cursor.fetchone()
        if security_stats:
            total_admin, unique_users, legitimate, unauthorized = security_stats
            print(f"   📊 Всего админских действий: {total_admin}")
            print(f"   👥 Уникальных пользователей: {unique_users}")
            print(f"   ✅ Легитимных действий: {legitimate}")
            print(f"   🚨 Несанкционированных действий: {unauthorized}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Ошибка при проверке безопасности: {e}")
        print(f"❌ Ошибка при проверке безопасности: {e}")

if __name__ == "__main__":
    check_security() 