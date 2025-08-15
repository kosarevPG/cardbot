Write-Host "🚀 Деплой на Amvera..." -ForegroundColor Green
Write-Host ""

Write-Host "🔄 Добавляем изменения в git..." -ForegroundColor Yellow
git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка при git add" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host "🔄 Коммитим изменения..." -ForegroundColor Yellow
git commit -m "feat: AI функции для вечерней рефлексии - эмпатичный ответ, еженедельный анализ, синергия с картами"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка при git commit" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host "🔄 Отправляем на сервер..." -ForegroundColor Yellow
git push origin master
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка при git push" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""
Write-Host "🎉 Деплой завершен успешно!" -ForegroundColor Green
Write-Host "⏳ Amvera начнет пересборку через 1-2 минуты" -ForegroundColor Cyan
Write-Host "🔍 Проверьте работу через 5-10 минут" -ForegroundColor Cyan
Write-Host ""
Read-Host "Нажмите Enter для выхода"
