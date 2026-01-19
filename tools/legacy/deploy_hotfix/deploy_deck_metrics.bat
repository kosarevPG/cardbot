@echo off
chcp 65001 >nul
echo ================================================
echo Деплой метрик популярности колод
echo ================================================
echo.

echo [1/6] Проверка изменений...
git status

echo.
echo [2/6] Добавление файлов...
git add database/db.py
git add modules/card_of_the_day.py
git add main.py
git add tools/test_deck_metrics.py
git add tools/README_deck_metrics.md
git add tools/DECK_METRICS_IMPLEMENTATION.md

echo.
echo [3/6] Статус после добавления...
git status

echo.
echo [4/6] Создание коммита...
git commit -m "feat: добавлены метрики популярности колод карт" -m "- Логирование deck_name при вытягивании карт" -m "- Новый метод get_deck_popularity_metrics() в Database" -m "- Раздел 'Статистика колод' в админке" -m "- Интеграция метрик в главный дашборд" -m "- Поддержка периодов: 1 день, 7 дней, 30 дней" -m "- Обработка старых данных (fallback на 'nature')" -m "- Документация и тесты"

echo.
echo [5/6] Отправка на сервер...
git push origin master

echo.
echo [6/6] Готово!
echo ================================================
echo Деплой завершен успешно!
echo ================================================
pause

