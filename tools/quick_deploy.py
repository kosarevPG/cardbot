#!/usr/bin/env python3
"""
Быстрый деплой на Amvera - простой git push
"""
import subprocess
import sys

def quick_deploy():
    """Быстрый деплой через git push"""
    print("🚀 Быстрый деплой на Amvera...")
    
    commands = [
        "git add .",
        "git commit -m 'feat: AI функции для вечерней рефлексии - эмпатичный ответ, еженедельный анализ, синергия с картами'",
        "git push origin master"
    ]
    
    for cmd in commands:
        print(f"🔄 {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            print(f"✅ Успешно")
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    print("\n🎉 Деплой завершен!")
    print("⏳ Amvera начнет пересборку через 1-2 минуты")
    print("🔍 Проверьте работу через 5-10 минут")
    return True

if __name__ == "__main__":
    success = quick_deploy()
    sys.exit(0 if success else 1)
