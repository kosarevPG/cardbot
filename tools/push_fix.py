#!/usr/bin/env python3
import subprocess

print("🚀 Отправляем исправления на сервер...")

# Добавляем изменения
result = subprocess.run(['git', 'add', 'Procfile'], capture_output=True, text=True)
print("git add:", result.returncode)

# Делаем коммит
result = subprocess.run(['git', 'commit', '-m', 'Fix Procfile - Remove duplicate sqlite_web process'], capture_output=True, text=True)
print("git commit:", result.returncode)

# Пушим
result = subprocess.run(['git', 'push', 'origin', 'master'], capture_output=True, text=True)
print("git push:", result.returncode)

print("✅ Исправления отправлены!")
print("📊 Веб-интерфейс должен быть доступен по адресу: https://cardbot-kosarevpg.amvera.io")
print("🔐 Логин: admin")
print("🔑 Пароль: root") 