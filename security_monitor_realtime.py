#!/usr/bin/env python3
"""
Скрипт для мониторинга безопасности в реальном времени
Отслеживает попытки несанкционированного доступа к админ-панели
"""

import sqlite3
import time
import logging
from datetime import datetime, timedelta
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ID администраторов
ADMIN_IDS = ['6682555021', '392141189', '239719200', '7494824111', '171507422', '138192985']

class SecurityMonitor:
    def __init__(self, db_path='database/bot.db'):
        self.db_path = db_path
        self.last_check_time = datetime.now()
        self.alert_threshold = 3  # Количество попыток для срабатывания тревоги
        
    def check_recent_admin_actions(self):
        """Проверяет недавние админские действия на предмет подозрительной активности."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем действия за последние 5 минут
            check_time = datetime.now() - timedelta(minutes=5)
            
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
                    AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (check_time.strftime('%Y-%m-%d %H:%M:%S'),))
            
            recent_actions = cursor.fetchall()
            unauthorized_actions = []
            
            for action in recent_actions:
                user_id, username, name, action_type, timestamp, access_type = action
                if access_type == 'UNAUTHORIZED_ACCESS':
                    unauthorized_actions.append({
                        'user_id': user_id,
                        'username': username,
                        'name': name,
                        'action': action_type,
                        'timestamp': timestamp
                    })
            
            conn.close()
            return unauthorized_actions
            
        except Exception as e:
            logger.error(f"Ошибка при проверке админских действий: {e}")
            return []
    
    def check_suspicious_patterns(self):
        """Проверяет подозрительные паттерны активности."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем пользователей, которые выполняли много действий за короткое время
            check_time = datetime.now() - timedelta(minutes=10)
            
            cursor.execute("""
                SELECT 
                    user_id,
                    username,
                    name,
                    COUNT(*) as action_count,
                    GROUP_CONCAT(DISTINCT action) as actions
                FROM actions 
                WHERE timestamp >= ?
                    AND user_id NOT IN (6682555021, 392141189, 239719200, 7494824111, 171507422, 138192985)
                GROUP BY user_id, username, name
                HAVING action_count >= 5
                ORDER BY action_count DESC
            """, (check_time.strftime('%Y-%m-%d %H:%M:%S'),))
            
            suspicious_users = cursor.fetchall()
            conn.close()
            
            return suspicious_users
            
        except Exception as e:
            logger.error(f"Ошибка при проверке подозрительных паттернов: {e}")
            return []
    
    def log_security_alert(self, alert_type, details):
        """Логирует тревогу безопасности."""
        alert_message = f"🚨 СИГНАЛ БЕЗОПАСНОСТИ: {alert_type}\n{details}"
        logger.warning(alert_message)
        
        # Сохраняем в файл тревог
        with open('security_alerts.log', 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {alert_message}\n")
    
    def run_monitoring_cycle(self):
        """Выполняет один цикл мониторинга."""
        logger.info("🔍 Выполняется проверка безопасности...")
        
        # 1. Проверка несанкционированных админских действий
        unauthorized_actions = self.check_recent_admin_actions()
        
        if unauthorized_actions:
            details = "\n".join([
                f"User {action['user_id']} ({action['username']}): {action['action']} at {action['timestamp']}"
                for action in unauthorized_actions
            ])
            self.log_security_alert("НЕСАНКЦИОНИРОВАННЫЙ ДОСТУП К АДМИН-ПАНЕЛИ", details)
        
        # 2. Проверка подозрительных паттернов
        suspicious_users = self.check_suspicious_patterns()
        
        if suspicious_users:
            details = "\n".join([
                f"User {user[0]} ({user[1]}): {user[3]} действий - {user[4]}"
                for user in suspicious_users
            ])
            self.log_security_alert("ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ", details)
        
        # 3. Обновляем время последней проверки
        self.last_check_time = datetime.now()
        
        if not unauthorized_actions and not suspicious_users:
            logger.info("✅ Безопасность в норме")
    
    def start_monitoring(self, interval_seconds=60):
        """Запускает непрерывный мониторинг."""
        logger.info(f"🚀 Запуск мониторинга безопасности (интервал: {interval_seconds} сек)")
        
        try:
            while True:
                self.run_monitoring_cycle()
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("🛑 Мониторинг безопасности остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка в мониторинге: {e}")

def main():
    """Главная функция."""
    print("🔒 МОНИТОРИНГ БЕЗОПАСНОСТИ АДМИН-ПАНЕЛИ")
    print("=" * 50)
    
    # Проверяем существование базы данных
    if not os.path.exists('database/bot.db'):
        print("❌ База данных не найдена: database/bot.db")
        return
    
    # Создаем монитор
    monitor = SecurityMonitor()
    
    # Запускаем мониторинг
    monitor.start_monitoring(interval_seconds=30)  # Проверка каждые 30 секунд

if __name__ == "__main__":
    main() 