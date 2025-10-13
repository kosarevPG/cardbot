@echo off
chcp 65001 > nul
echo ============================================================
echo 🔥 HOTFIX: NameError 'db' is not defined в learn_cards.py
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленного файла...
git add modules/learn_cards.py
echo ✅ Файл добавлен
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправлен NameError в handle_choice_with_poll - Добавлен параметр db: Database в сигнатуру функции - Обновлена регистрация обработчика с partial(handle_choice_with_poll, db=db) - Функция теперь корректно получает доступ к базе данных"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX ПРИМЕНЕН!
echo ============================================================
echo.
echo 🔧 ИСПРАВЛЕНИЕ:
echo - modules/learn_cards.py: добавлен параметр db в handle_choice_with_poll
echo - Регистрация обработчика обновлена с partial()
echo - Функция теперь получает доступ к базе данных
echo.
echo Amvera задеплоит исправление в течение 1-2 минут.
echo Кнопка 'С входным опросом' должна заработать!
echo.
pause


