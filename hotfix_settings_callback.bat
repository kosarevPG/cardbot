@echo off
chcp 65001 > nul
echo ============================================================
echo 🔥 HOTFIX: TypeError в handle_settings_callback
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленного файла...
git add modules/settings_menu.py
echo ✅ Файл добавлен
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправлен TypeError в handle_settings_callback - user_id теперь извлекается из callback.from_user.id - Убран лишний параметр user_id из сигнатуры функции"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX ПРИМЕНЕН!
echo ============================================================
echo.
echo Меню 'Еще...' теперь работает корректно!
echo.
pause


