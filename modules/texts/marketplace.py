# modules/texts/marketplace.py
# Тексты модуля маркетплейсов

MARKETPLACE_TEXTS = {
    "admin_menu": {
        "title": "🛍️ **Управление маркетплейсами**",
        "description": "Здесь ты можешь управлять интеграциями с Ozon и Wildberries, синхронизировать данные и обновлять Google Sheets.",
        "buttons": {
            "ozon_status": "📦 Статус Ozon",
            "wb_status": "🛒 Статус Wildberries", 
            "sheets_status": "📊 Статус Google Sheets",
            "sync_ozon": "🔄 Синхронизировать Ozon",
            "sync_wb": "🔄 Синхронизировать WB",
            "update_prices": "💰 Обновить цены",
            "help": "❓ Помощь",
            "back": "← Назад в меню"
        }
    },
    
    "status": {
        "ozon_connected": "✅ **Ozon API**\nСтатус: Подключен\nТоваров: {product_count}\nПоследняя синхронизация: {last_sync}",
        "ozon_error": "❌ **Ozon API**\nСтатус: Ошибка подключения\nОшибка: {error}",
        "wb_connected": "✅ **Wildberries API**\nСтатус: Подключен\nТоваров: {product_count}\nПоследняя синхронизация: {last_sync}",
        "wb_error": "❌ **Wildberries API**\nСтатус: Ошибка подключения\nОшибка: {error}",
        "sheets_connected": "✅ **Google Sheets**\nСтатус: Подключен\nТаблица: {sheet_name}\nПоследнее обновление: {last_update}",
        "sheets_error": "❌ **Google Sheets**\nСтатус: Ошибка подключения\nОшибка: {error}"
    },
    
    "sync": {
        "ozon_starting": "🔄 Начинаю синхронизацию данных Ozon...",
        "ozon_success": "✅ **Синхронизация Ozon завершена!**\n\n📊 Обновлено:\n• Товаров: {products_count}\n• Остатков: {stock_count}\n• Продаж: {sales_count}\n• Выручки: {revenue_count}",
        "ozon_error": "❌ **Ошибка синхронизации Ozon**\n\n{error}",
        "wb_starting": "🔄 Начинаю синхронизацию данных Wildberries...",
        "wb_success": "✅ **Синхронизация Wildberries завершена!**\n\n📊 Обновлено:\n• Товаров: {products_count}\n• Остатков: {stock_count}\n• Продаж: {sales_count}\n• Выручки: {revenue_count}",
        "wb_error": "❌ **Ошибка синхронизации Wildberries**\n\n{error}",
        "processing": "⏳ Обрабатываю данные... Это может занять несколько минут."
    },
    
    "prices": {
        "updating": "💰 Получаю актуальные цены товаров...",
        "success": "✅ **Цены обновлены успешно!**\n\n🛒 Цены Ozon: {ozon_count}\n🛍️ Цены WB: {wb_count}",
        "error": "❌ **Ошибка получения цен**\n\n{error}",
        "ozon_unavailable": "⚠️ Цены Ozon недоступны через текущий API",
        "wb_unavailable": "⚠️ Цены Wildberries недоступны через текущий API"
    },
    
    "help": {
        "title": "📚 **Помощь по маркетплейсам**",
        "description": "Здесь ты можешь управлять интеграциями с маркетплейсами и синхронизировать данные.",
        "commands": {
            "ozon": "**📦 Ozon:**\n• `/ozon_status` - Проверить статус API\n• `/ozon_sync` - Синхронизировать данные\n• `/ozon_products` - Список товаров",
            "wb": "**🛒 Wildberries:**\n• `/wb_status` - Проверить статус API\n• `/wb_sync` - Синхронизировать данные\n• `/wb_products` - Список товаров",
            "sheets": "**📊 Google Sheets:**\n• `/sheets_status` - Статус подключения\n• `/sheets_sync` - Обновить данные в таблице",
            "prices": "**💰 Цены товаров:**\n• `/get_prices` - Получить актуальные цены всех товаров"
        },
        "note": "*💡 Все команды доступны только администраторам*"
    },
    
    "errors": {
        "api_key_missing": "❌ API ключ не настроен. Обратись к администратору.",
        "connection_failed": "❌ Не удалось подключиться к API. Проверь интернет-соединение.",
        "rate_limit": "⚠️ Превышен лимит запросов к API. Попробуй позже.",
        "invalid_response": "❌ Получен некорректный ответ от API.",
        "sheets_access_denied": "❌ Нет доступа к Google Sheets. Проверь настройки.",
        "sheets_not_found": "❌ Таблица Google Sheets не найдена.",
        "data_processing_error": "❌ Ошибка обработки данных. Попробуй еще раз.",
        "unknown_error": "❌ Произошла неизвестная ошибка: {error}"
    },
    
    "notifications": {
        "sync_completed": "🔔 Синхронизация завершена успешно!",
        "sync_failed": "⚠️ Синхронизация завершилась с ошибками.",
        "prices_updated": "💰 Цены обновлены в Google Sheets.",
        "new_products": "🆕 Обнаружены новые товары на маркетплейсах."
    }
}
