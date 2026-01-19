@echo off
chcp 65001 >nul
echo ========================================
echo ДЕПЛОЙ ИЗМЕНЕНИЙ CARDBOT
echo ========================================
echo.

REM Удаляем неправильный git из корня
if exist "D:\.git" (
    echo Удаляю неправильный git из D:\...
    rmdir /s /q "D:\.git"
)

REM Переходим в папку проекта
cd /d "%~dp0"

REM Инициализируем git если нужно
if not exist ".git" (
    echo Инициализирую git репозиторий...
    git init
    echo.
)

REM Проверяем remote
echo Проверяю remote...
git remote -v
if errorlevel 1 (
    echo.
    echo WARNING: Remote не настроен!
    echo Добавьте remote вручную: git remote add origin [URL]
    echo.
)

REM Добавляем изменения
echo.
echo Добавляю изменённые файлы...
git add .

REM Показываем статус
echo.
echo Статус изменений:
git status --short

REM Делаем коммит
echo.
echo Создаю коммит...
git commit -m "Complete text inventory & improvements: Fix bugs, unify emojis, centralize texts (Phase 1+2+main.py)"

REM Показываем инструкцию для пуша
echo.
echo ========================================
echo ГОТОВО К ДЕПЛОЮ!
echo ========================================
echo.
echo Для деплоя на Amvera выполните:
echo   git push origin master
echo.
echo Если remote не настроен, добавьте его:
echo   git remote add origin [URL вашего Amvera репозитория]
echo.
pause

