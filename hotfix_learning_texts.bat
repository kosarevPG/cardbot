@echo off
chcp 65001 > nul
echo ============================================================
echo 🔥 HOTFIX: [TEXT_NOT_FOUND] в обучении
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленного файла...
git add modules/texts/learning.py
echo ✅ Файл добавлен
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправлены [TEXT_NOT_FOUND] в модуле обучения === ПРОБЛЕМЫ === - [TEXT_NOT_FOUND: theory_1] - [TEXT_NOT_FOUND: theory_2] - [TEXT_NOT_FOUND: theory_3] - [TEXT_NOT_FOUND: exit_feedback_invite] === ИСПРАВЛЕНИЯ === - Изменена структура theory: part1/part2/part3 → theory_1/theory_2/theory_3 - Добавлен недостающий ключ exit_feedback_invite - Все тексты теперь находятся по правильным ключам === ДЕТАЛИ === - theory_1: 'Что такое МАК-карты' - theory_2: 'Зачем нужен запрос' - theory_3: 'Типичные ошибки' - exit_feedback_invite: приглашение к обратной связи === РЕЗУЛЬТАТ === - Все тексты обучения теперь отображаются корректно - Убраны заглушки [TEXT_NOT_FOUND] - Обучение работает полностью"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX ПРИМЕНЕН!
echo ============================================================
echo.
echo 🔧 ИСПРАВЛЕННЫЕ ТЕКСТЫ:
echo.
echo Теория:
echo - theory_1: 'Что такое МАК-карты'
echo - theory_2: 'Зачем нужен запрос'  
echo - theory_3: 'Типичные ошибки'
echo.
echo Финальные тексты:
echo - exit_feedback_invite: приглашение к обратной связи
echo.
echo Amvera задеплоит исправление в течение 1-2 минут.
echo Обучение должно работать без [TEXT_NOT_FOUND]!
echo.
pause


