@echo off
echo 🚀 Исправляем конфигурацию Amvera и деплоим

echo.
echo 🔄 Проверка статуса Git...
git status

echo.
echo 🔄 Добавление amvera.yml...
git add amvera.yml

echo.
echo 🔄 Создание коммита...
git commit -m "Fix amvera.yml - Remove problematic run section"

echo.
echo 🔄 Отправка изменений...
git push origin master

echo.
echo 🎉 Деплой завершен!
echo 📊 Веб-интерфейс должен быть доступен по адресу: https://cardbot-kosarevpg.amvera.io
echo 🔐 Логин: admin
echo 🔑 Пароль: root
echo.
echo ⏳ Подождите несколько минут, пока изменения применятся на сервере

pause 