@echo off
chcp 65001 > nul
echo ============================================================
echo 🔧 HOTFIX: Исправление parse_mode во всех модулях
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленных файлов...
git add modules/learn_cards.py modules/settings_menu.py modules/evening_reflection.py modules/card_of_the_day.py
echo ✅ Файлы добавлены
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправлен parse_mode во всех модулях для корректных переносов строк === ПРОБЛЕМА === - Тексты отображались без переносов строк в Telegram - Отсутствовал parse_mode='HTML' в нескольких модулях - Все абзацы слипались в одну строку === ИСПРАВЛЕНИЯ === modules/learn_cards.py: - Добавлен parse_mode='HTML' в trainer.intro - Добавлен parse_mode='HTML' в trainer.input_prompt modules/settings_menu.py: - Добавлен parse_mode='HTML' в settings_back callback modules/evening_reflection.py: - Добавлен parse_mode='HTML' в fallback_message modules/card_of_the_day.py: - Добавлен parse_mode='HTML' в deck_selection - Добавлен parse_mode='HTML' во всех text2 сообщениях === РЕЗУЛЬТАТ === - Все тексты теперь отображаются с правильными переносами - Корректное форматирование во всех модулях - Единообразное использование parse_mode='HTML'"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ HOTFIX ПРИМЕНЕН!
echo ============================================================
echo.
echo 🔧 ИСПРАВЛЕННЫЕ МОДУЛИ:
echo.
echo 📚 Обучение (learn_cards.py):
echo - trainer.intro: добавлен parse_mode
echo - trainer.input_prompt: добавлен parse_mode
echo.
echo ⚙️ Настройки (settings_menu.py):
echo - settings_back: добавлен parse_mode
echo.
echo 🌙 Вечерняя рефлексия (evening_reflection.py):
echo - fallback_message: добавлен parse_mode
echo.
echo 🃏 Карта дня (card_of_the_day.py):
echo - deck_selection: добавлен parse_mode
echo - Все text2 сообщения: добавлен parse_mode
echo.
echo Теперь ВСЕ тексты будут отображаться с правильными переносами!
echo.
pause

