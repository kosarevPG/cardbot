@echo off
chcp 65001 > nul
echo ============================================================
echo 🔥 HOTFIX: TypeError в settings_purchase
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленного файла...
git add modules/settings_menu.py
echo ✅ Файл добавлен
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправлен TypeError в settings_purchase - Убран параметр from_callback из handle_purchase_menu - Функция вызывается с правильными параметрами"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX ПРИМЕНЕН!
echo ============================================================
echo.
pause


