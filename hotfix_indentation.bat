@echo off
chcp 65001 > nul
echo ============================================================
echo 🔥 HOTFIX: IndentationError в main.py строка 853
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленного файла...
git add main.py
echo ✅ Файл добавлен
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправлен IndentationError в make_help_handler - Убран лишний отступ в строке 853 - Функция /help теперь работает корректно"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX ПРИМЕНЕН!
echo ============================================================
echo.
echo 🔧 ИСПРАВЛЕНИЕ:
echo - main.py строка 853: убран лишний отступ
echo - Функция make_help_handler теперь корректна
echo.
echo Amvera задеплоит исправление в течение 1-2 минут.
echo Команда /help должна заработать!
echo.
pause


