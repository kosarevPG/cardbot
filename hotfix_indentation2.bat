@echo off
chcp 65001 > nul
echo ============================================================
echo 🔥 HOTFIX #2: IndentationError в main.py строка 1409
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленного файла...
git add main.py
echo ✅ Файл добавлен
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправлен второй IndentationError в make_process_name_handler - Убран лишний отступ в строке 1409 - Функция обработки имени теперь работает корректно"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX #2 ПРИМЕНЕН!
echo ============================================================
echo.
echo 🔧 ИСПРАВЛЕНИЕ:
echo - main.py строка 1409: убран лишний отступ
echo - Функция make_process_name_handler теперь корректна
echo.
echo Amvera задеплоит исправление в течение 1-2 минут.
echo Обработка имени должна заработать!
echo.
pause


