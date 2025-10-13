@echo off
chcp 65001 > nul
echo ============================================================
echo 🔥 HOTFIX: NameError 'user_id' в функциях опросника
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленного файла...
git add modules/learn_cards.py
echo ✅ Файл добавлен
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправлены NameError 'user_id' во всех функциях опросника === ИСПРАВЛЕНИЯ === - handle_entry_poll_q1: добавлен user_id = callback.from_user.id - handle_entry_poll_q2: добавлен user_id = callback.from_user.id - handle_entry_poll_q3: добавлен user_id = callback.from_user.id - handle_exit_poll_q1: добавлен user_id = callback.from_user.id - handle_exit_poll_q2: добавлен user_id = callback.from_user.id === ПРОБЛЕМА === - Функции опросника пытались использовать user_id в get_learning_text() - Но переменная user_id не была определена в этих функциях - Это вызывало NameError при прохождении опросника === РЕШЕНИЕ === - Добавлено user_id = callback.from_user.id в начало каждой функции - Теперь персонализация текстов работает корректно - Опросники должны работать без ошибок"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX ПРИМЕНЕН!
echo ============================================================
echo.
echo 🔧 ИСПРАВЛЕННЫЕ ФУНКЦИИ:
echo.
echo Входной опросник:
echo - handle_entry_poll_q1: добавлен user_id
echo - handle_entry_poll_q2: добавлен user_id  
echo - handle_entry_poll_q3: добавлен user_id
echo.
echo Выходной опросник:
echo - handle_exit_poll_q1: добавлен user_id
echo - handle_exit_poll_q2: добавлен user_id
echo.
echo Amvera задеплоит исправление в течение 1-2 минут.
echo Опросники должны заработать без NameError!
echo.
pause


