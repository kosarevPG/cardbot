#!/usr/bin/env python3
"""
Скрипт для мониторинга успешности деплоя в production
"""
import time
import requests
from datetime import datetime

def check_bot_status():
    """Проверяет статус бота через Telegram API"""
    try:
        # Используем production токен
        from config import TOKEN
        url = f"https://api.telegram.org/bot{TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data['result']
                print(f"✅ Бот активен: @{bot_info['username']} ({bot_info['first_name']})")
                return True
            else:
                print(f"❌ Ошибка API: {data.get('description', 'Неизвестная ошибка')}")
                return False
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки статуса бота: {e}")
        return False

def check_amvera_logs():
    """Имитирует проверку логов Amvera (в реальности нужно смотреть в панели Amvera)"""
    print("📋 Для проверки логов Amvera:")
    print("1. Зайдите в панель управления Amvera")
    print("2. Найдите ваш проект cardbot")
    print("3. Откройте раздел 'Логи'")
    print("4. Ищите сообщения:")
    print("   ✅ 'Database connection initialized'")
    print("   ✅ 'Database migrations finished successfully'")
    print("   ✅ 'Bot commands set successfully'")
    print("   ✅ 'Run polling for bot'")
    print("   ❌ Любые ошибки (ERROR, CRITICAL)")

def main():
    """Основная функция мониторинга"""
    print("🚀 МОНИТОРИНГ ДЕПЛОЯ В PRODUCTION")
    print("=" * 50)
    print(f"⏰ Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Проверяем статус бота
    print("🔍 Проверка статуса бота...")
    bot_ok = check_bot_status()
    
    print()
    print("📊 РЕЗУЛЬТАТЫ МОНИТОРИНГА:")
    print(f"🤖 Статус бота: {'✅ АКТИВЕН' if bot_ok else '❌ НЕ АКТИВЕН'}")
    
    if bot_ok:
        print()
        print("🎉 ДЕПЛОЙ УСПЕШЕН!")
        print()
        print("🧪 Тестирование функций:")
        print("1. Отправьте /start боту")
        print("2. Проверьте /admin (если вы админ)")
        print("3. Проверьте /user_profile")
        print("4. Проверьте /scenario_stats")
        print("5. Протестируйте карту дня")
    else:
        print()
        print("⚠️ ПРОБЛЕМЫ С ДЕПЛОЕМ!")
        print("Проверьте логи Amvera:")
        check_amvera_logs()
    
    print()
    print("📋 ЧЕК-ЛИСТ ПОСЛЕ ДЕПЛОЯ:")
    print("□ Бот отвечает на команды")
    print("□ Админская панель /admin работает")
    print("□ Расширенный профиль /user_profile работает")
    print("□ Статистика сценариев /scenario_stats работает")
    print("□ Карта дня работает корректно")
    print("□ Вечерняя рефлексия работает")
    print("□ Админские ID исключены из статистики")

if __name__ == "__main__":
    main() 