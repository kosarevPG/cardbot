#!/usr/bin/env python3
"""
Скрипт для принудительной пересборки на Amvera
Добавляет временную метку в main.py и пушит изменения
"""

import os
import subprocess
from datetime import datetime

def force_rebuild():
    """Принудительно инициирует пересборку на Amvera"""
    print("🚀 Принудительная пересборка на Amvera...")
    
    try:
        # Создаем небольшое изменение для принудительной пересборки
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Добавляем комментарий с временной меткой
        if "# Last Amvera rebuild:" not in content:
            content = f"# Last Amvera rebuild: {timestamp}\n{content}"
            
            with open("main.py", "w", encoding="utf-8") as f:
                f.write(content)
            
            print("✅ Добавлена временная метка для пересборки")
            
            # Коммитим и пушим
            commands = [
                "git add main.py",
                f'git commit -m "force: Принудительная пересборка на Amvera - {timestamp}"',
                "git push origin master"
            ]
            
            for cmd in commands:
                print(f"🔄 Выполняем: {cmd}")
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
                print(f"✅ Успешно: {cmd}")
            
            print("🎉 Принудительная пересборка инициирована!")
            print("⏳ Подождите 5-10 минут и проверьте работу новых функций")
            return True
        else:
            print("ℹ️ Временная метка уже добавлена")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка принудительной пересборки: {e}")
        return False

if __name__ == "__main__":
    print("🔍 АНАЛИЗ СИТУАЦИИ:")
    print("=" * 40)
    print("✅ Новые AI функции интегрированы в код")
    print("✅ Планировщик еженедельного анализа добавлен")
    print("✅ Git push выполнен успешно")
    print("❌ Но новые функции не работают в продакшне")
    print("\n💡 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
    print("1. Amvera еще не завершил пересборку")
    print("2. Есть ошибки в логах Amvera")
    print("3. Требуется принудительная пересборка")
    print("\n🚀 РЕШЕНИЕ:")
    print("Принудительная пересборка на Amvera")
    
    response = input("\n❓ Выполнить принудительную пересборку? (y/n): ")
    if response.lower() in ['y', 'yes', 'да', 'д']:
        force_rebuild()
    else:
        print("ℹ️ Пересборка пропущена")
        print("💡 Проверьте логи Amvera вручную")
