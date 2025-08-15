@echo off
echo 🚀 Деплой на Amvera...
echo.

echo 🔄 Добавляем изменения в git...
git add .
if %errorlevel% neq 0 (
    echo ❌ Ошибка при git add
    pause
    exit /b 1
)

echo 🔄 Коммитим изменения...
git commit -m "feat: AI функции для вечерней рефлексии - эмпатичный ответ, еженедельный анализ, синергия с картами"
if %errorlevel% neq 0 (
    echo ❌ Ошибка при git commit
    pause
    exit /b 1
)

echo 🔄 Отправляем на сервер...
git push origin master
if %errorlevel% neq 0 (
    echo ❌ Ошибка при git push
    pause
    exit /b 1
)

echo.
echo 🎉 Деплой завершен успешно!
echo ⏳ Amvera начнет пересборку через 1-2 минуты
echo 🔍 Проверьте работу через 5-10 минут
echo.
pause
