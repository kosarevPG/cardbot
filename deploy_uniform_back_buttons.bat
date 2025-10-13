@echo off
chcp 65001 > nul
echo ============================================================
echo 🔧 ДЕПЛОЙ: ЕДИНООБРАЗНЫЕ КНОПКИ "НАЗАД"
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 Добавление всех обновленных файлов...
git add modules/texts/common.py
git add modules/card_of_the_day.py
git add modules/settings_menu.py
git add modules/admin/users.py
git add modules/admin/training_logs.py
git add modules/admin/dashboard.py
git add modules/admin/core.py
git add modules/admin/marketplaces.py
git add modules/admin/posts.py
git add modules/texts/marketplace.py
echo ✅ Файлы добавлены
echo.

echo 💬 Коммит изменений...
git commit -m "feat(UI): Единообразные кнопки 'Назад' по всему боту === ИЗМЕНЕНИЯ === - Все кнопки '← Назад' → '⬅️ Назад' - Обновлены константы в modules/texts/common.py - Приведены к единому стилю все модули === ФАЙЛЫ === - modules/texts/common.py: добавлены константы навигации - modules/card_of_the_day.py: кнопки выбора колоды и ресурса - modules/settings_menu.py: уже был правильный стиль - modules/admin/users.py: все кнопки 'Назад' - modules/admin/training_logs.py: кнопки логов обучения - modules/admin/dashboard.py: все админские кнопки - modules/admin/core.py: главное меню админки - modules/admin/marketplaces.py: кнопки маркетплейсов - modules/admin/posts.py: кнопки управления постами - modules/texts/marketplace.py: тексты маркетплейсов === РЕЗУЛЬТАТ === - 100%% единообразие кнопок 'Назад' - Все эмодзи ⬅️ вместо ← - Интерфейс стал консистентным - Улучшен UX навигации"
echo.

echo 🚀 Пуш на GitHub...
git push origin master
echo.

echo ============================================================
echo ✅ КНОПКИ "НАЗАД" СТАЛИ ЕДИНООБРАЗНЫМИ!
echo ============================================================
echo.
echo 🔧 ОБНОВЛЕННЫЕ ФАЙЛЫ:
echo.
echo 📝 Тексты:
echo - modules/texts/common.py: константы навигации
echo - modules/texts/marketplace.py: тексты маркетплейсов
echo.
echo 🎮 Интерфейс:
echo - modules/card_of_the_day.py: выбор колоды и ресурса
echo - modules/settings_menu.py: меню настроек (уже был правильный)
echo.
echo 🛠️ Админ-панель:
echo - modules/admin/users.py: управление пользователями
echo - modules/admin/training_logs.py: логи обучения
echo - modules/admin/dashboard.py: главная панель
echo - modules/admin/core.py: основное меню
echo - modules/admin/marketplaces.py: маркетплейсы
echo - modules/admin/posts.py: управление постами
echo.
echo 🎯 РЕЗУЛЬТАТ:
echo - Все кнопки теперь: ⬅️ Назад
echo - Единообразный стиль по всему боту
echo - Улучшен UX навигации
echo.
echo Amvera задеплоит изменения в течение 1-2 минут.
echo Интерфейс станет более консистентным!
echo.
pause


