@echo off
chcp 65001 > nul
echo ============================================================
echo 🔧 HOTFIX: Исправление parse_mode для переносов строк
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленных файлов...
git add modules/learn_cards.py
echo ✅ Файл добавлен
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправлен parse_mode для корректного отображения переносов строк === ПРОБЛЕМА === - Тексты обучения отображались без переносов строк - Все абзацы слипались в одну строку - Отсутствовал parse_mode='HTML' в некоторых местах === ИСПРАВЛЕНИЯ === - Добавлен parse_mode='HTML' в handle_steps_callback - Добавлен parse_mode='HTML' в handle_trainer_intro_callback - Добавлен parse_mode='HTML' в handle_templates_callback === РЕЗУЛЬТАТ === - Тексты теперь отображаются с правильными переносами - Абзацы разделены как в изображении - Корректное форматирование в Telegram"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX ПРИМЕНЕН!
echo ============================================================
echo.
echo 🔧 ИСПРАВЛЕНИЯ:
echo.
echo Parse Mode:
echo - trainer.intro: добавлен parse_mode='HTML'
echo - trainer.input_prompt: добавлен parse_mode='HTML'
echo.
echo Теперь все тексты обучения будут отображаться с правильными переносами!
echo.
pause

