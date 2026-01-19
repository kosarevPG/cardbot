@echo off
chcp 65001 > nul
echo ============================================================
echo 🔥 HOTFIX: Исправление ImportError для get_personalized_text
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленных файлов...
git add modules/texts/__init__.py
git add modules/texts/gender_utils.py
echo ✅ Файлы добавлены
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Добавлена функция get_personalized_text - Исправлен ImportError в card_of_the_day.py - Функция экспортирована из modules/texts/__init__.py"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX ПРИМЕНЕН!
echo ============================================================
echo.
echo Amvera задеплоит изменения в течение 1-2 минут.
echo Проверь логи деплоя на Amvera!
echo.
pause


