@echo off
chcp 65001 > nul
echo ============================================================
echo 🔥 HOTFIX 2: Исправление NameError для _get_nested_value
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленного файла...
git add modules/texts/gender_utils.py
echo ✅ Файл добавлен
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправлен NameError '_get_nested_value' - Переименована get_nested_value в _get_nested_value - Удалена дублирующая старая версия get_personalized_text - Оставлена только новая версия функции"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX 2 ПРИМЕНЕН!
echo ============================================================
echo.
echo Amvera задеплоит изменения в течение 1-2 минут.
echo Теперь персонализация должна работать полностью!
echo.
pause

