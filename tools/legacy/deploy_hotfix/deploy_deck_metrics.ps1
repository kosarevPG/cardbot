# Скрипт деплоя метрик популярности колод
$ErrorActionPreference = "Stop"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Деплой метрик популярности колод" -ForegroundColor Cyan
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

Write-Host ""
Write-Host "[3/6] Статус после добавления..." -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "[4/6] Создание коммита..." -ForegroundColor Yellow
$commitMessage = @"
feat: добавлены метрики популярности колод карт

- Логирование deck_name при вытягивании карт
- Новый метод get_deck_popularity_metrics() в Database
- Раздел 'Статистика колод' в админке
- Интеграция метрик в главный дашборд
- Поддержка периодов: 1 день, 7 дней, 30 дней
- Обработка старых данных (fallback на 'nature')
- Документация и тесты
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
Write-Host "Новые возможности:" -ForegroundColor Cyan
Write-Host "  • /admin → 🃏 Статистика колод" -ForegroundColor White
Write-Host "  • Метрики в главном дашборде" -ForegroundColor White
Write-Host ""

Read-Host "Нажмите Enter для завершения"

