@echo off
chcp 65001 > nul
echo ============================================================
echo 🚀 ДЕПЛОЙ СИСТЕМЫ ПЕРСОНАЛИЗАЦИИ ТЕКСТОВ
echo ============================================================
echo.

cd /d "%~dp0"

echo 📋 Шаг 1: Проверка статуса Git...
git status
echo.

echo 📝 Шаг 2: Добавление измененных файлов...
git add modules/learn_cards.py
git add modules/card_of_the_day.py
git add modules/marketplace_commands.py
git add modules/admin/training_logs.py
git add modules/texts/
git add modules/texts/gender_utils.py
git add modules/texts/learning.py
git add modules/texts/cards.py
git add modules/texts/common.py
git add modules/texts/errors.py
git add modules/texts/marketplace.py
git add modules/texts/__init__.py
echo ✅ Файлы добавлены
echo.

echo 💬 Шаг 3: Коммит изменений...
git commit -m "feat: Интегрирована система персонализации текстов - Заменены все хардкодные TEXTS на get_personalized_text() - Добавлены склонения по полу (male/female/neutral) - Поддержка обращения по имени - Обновлены модули: learn_cards, card_of_the_day, marketplace_commands, admin/training_logs"
echo.

echo 🚀 Шаг 4: Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ ДЕПЛОЙ ЗАВЕРШЕН!
echo ============================================================
echo.
echo Amvera автоматически задеплоит изменения в течение 1-2 минут.
echo Проверь бота командой /learn_cards для теста персонализации!
echo.
pause


