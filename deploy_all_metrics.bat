@echo off
chcp 65001 >nul
echo ================================================
echo Деплой метрик колод и вечерней рефлексии
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
git add tools/README_reflection_metrics.md

echo.
echo [3/6] Статус после добавления...
git status

echo.
echo [4/6] Создание коммита...
git commit -m "feat: добавлены метрики колод и вечерней рефлексии в админку" -m "" -m "Метрики популярности колод:" -m "- Логирование deck_name при вытягивании карт" -m "- Новый метод get_deck_popularity_metrics() в Database" -m "- Раздел 'Статистика колод' в админке" -m "- Интеграция метрик в главный дашборд" -m "- Поддержка периодов: 1 день, 7 дней, 30 дней" -m "" -m "Метрики вечерней рефлексии:" -m "- Новый метод get_evening_reflection_metrics() в Database" -m "- Раздел 'Вечерняя рефлексия' в админке" -m "- Статистика: количество рефлексий, AI-резюме, длина ответов" -m "- Топ активных пользователей" -m "" -m "Документация и тесты включены"

echo.
echo [5/6] Отправка на сервер...
git push origin master

echo.
echo [6/6] Готово!
echo ================================================
echo Деплой завершен успешно!
echo ================================================
echo.
echo Новые возможности:
echo   - /admin -^> Статистика колод
echo   - /admin -^> Вечерняя рефлексия
echo.
pause

