# Скрипт деплоя метрик колод и вечерней рефлексии
$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Деплой новых метрик в админку" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Определяем путь к проекту
$projectPath = $PSScriptRoot
Write-Host "[INFO] Рабочая директория: $projectPath" -ForegroundColor Green
Set-Location $projectPath

Write-Host ""
Write-Host "[1/6] Проверка изменений..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "[2/6] Добавление файлов..." -ForegroundColor Yellow
git add database/db.py
git add modules/card_of_the_day.py
git add main.py
git add tools/test_deck_metrics.py
git add tools/README_deck_metrics.md
git add tools/DECK_METRICS_IMPLEMENTATION.md
git add tools/README_reflection_metrics.md
git add deploy_deck_metrics.bat
git add deploy_deck_metrics.ps1
git add deploy_all_metrics.ps1

Write-Host ""
Write-Host "[3/6] Статус после добавления..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "[4/6] Создание коммита..." -ForegroundColor Yellow
$commitMessage = @"
feat: добавлены метрики колод и вечерней рефлексии в админку

🃏 Метрики популярности колод:
- Логирование deck_name при вытягивании карт
- Новый метод get_deck_popularity_metrics() в Database
- Раздел 'Статистика колод' в админке
- Интеграция метрик в главный дашборд
- Поддержка периодов: 1 день, 7 дней, 30 дней
- Обработка старых данных (fallback на 'nature')

🌙 Метрики вечерней рефлексии:
- Новый метод get_evening_reflection_metrics() в Database
- Раздел 'Вечерняя рефлексия' в админке
- Статистика: количество рефлексий, AI-резюме, длина ответов
- Топ активных пользователей
- Просмотр последних рефлексий

📚 Документация:
- tools/README_deck_metrics.md
- tools/DECK_METRICS_IMPLEMENTATION.md
- tools/README_reflection_metrics.md
- Тестовый скрипт для метрик колод
"@

git commit -m $commitMessage

Write-Host ""
Write-Host "[5/6] Отправка на сервер..." -ForegroundColor Yellow
git push origin master

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "✅ Деплой завершен успешно!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Новые возможности в админке:" -ForegroundColor Cyan
Write-Host "  🃏 Статистика колод" -ForegroundColor White
Write-Host "     • Популярность каждой колоды" -ForegroundColor Gray
Write-Host "     • Уникальные пользователи" -ForegroundColor Gray
Write-Host "     • Процентное соотношение" -ForegroundColor Gray
Write-Host ""
Write-Host "  🌙 Вечерняя рефлексия" -ForegroundColor White
Write-Host "     • Общая статистика рефлексий" -ForegroundColor Gray
Write-Host "     • Средняя длина ответов" -ForegroundColor Gray
Write-Host "     • Топ активных пользователей" -ForegroundColor Gray
Write-Host "     • AI-резюме статистика" -ForegroundColor Gray
Write-Host ""
Write-Host "Доступ: /admin → выберите нужный раздел" -ForegroundColor Yellow
Write-Host ""

Read-Host "Нажмите Enter для завершения"

