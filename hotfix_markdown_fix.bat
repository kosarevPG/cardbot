@echo off
chcp 65001 > nul
echo ============================================================
echo 🔧 HOTFIX: Исправление ошибки с HTML тегами <br>
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление исправленных файлов...
git add modules/texts/learning.py modules/learn_cards.py
echo ✅ Файлы добавлены
echo.

echo 💬 Коммит изменений...
git commit -m "hotfix: Исправление ошибки с неподдерживаемыми HTML тегами <br> === ПРОБЛЕМА === - Telegram не поддерживает HTML тег <br> - Ошибка: Unsupported start tag 'br' at byte offset 47 - Бот падал при отправке сообщений с <br> === ИСПРАВЛЕНИЯ === - Убраны все HTML теги <br><br> и <br> - Возвращен Markdown форматирование: **text** и *text* - Изменен parse_mode с 'HTML' на 'Markdown' во всех местах - Восстановлены обычные переносы \\n\\n === ДЕТАЛИ === modules/texts/learning.py: - theory_1: убраны <br>, возвращен Markdown - theory_2: убраны <br>, возвращен Markdown - theory_3: убраны <br>, возвращен Markdown - steps: убраны <br>, возвращен Markdown modules/learn_cards.py: - Все parse_mode='HTML' → parse_mode='Markdown' === РЕЗУЛЬТАТ === - Бот больше не падает с ошибками HTML - Markdown форматирование работает корректно - Переносы \\n\\n должны работать с Markdown"
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
echo Проблема:
echo - Telegram не поддерживает <br> теги
echo - Ошибка: Unsupported start tag 'br'
echo.
echo Решение:
echo - Убраны все <br> теги
echo - Возвращен Markdown: **text** и *text*
echo - parse_mode: HTML → Markdown
echo.
echo Теперь бот не должен падать с ошибками!
echo.
pause

