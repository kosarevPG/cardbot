#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример команд бота для работы с маркетплейсами
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from modules.marketplace_manager import MarketplaceManager

router = Router()
marketplace_manager = MarketplaceManager()

@router.message(Command("marketplace_status"))
async def cmd_marketplace_status(message: types.Message):
    """Показывает статус всех маркетплейсов"""
    
    status = marketplace_manager.get_status()
    
    text = "📊 **Статус маркетплейсов:**\n\n"
    
    # Ozon
    ozon_status = status['ozon']
    if ozon_status['configured']:
        text += "🟢 **Ozon**: Настроен и готов к работе\n"
        text += f"   • API ключ: {'✅' if ozon_status['api_key'] else '❌'}\n"
        text += f"   • Client ID: {'✅' if ozon_status['client_id'] else '❌'}\n"
    else:
        text += "🔴 **Ozon**: Не настроен\n"
    
    # Wildberries
    wb_status = status['wildberries']
    if wb_status['configured']:
        text += "🟢 **Wildberries**: Настроен и готов к работе\n"
        text += f"   • API ключ: {'✅' if wb_status['api_key'] else '❌'}\n"
    else:
        text += "🔴 **Wildberries**: Не настроен\n"
    
    # Google Sheets
    text += "🟢 **Google Sheets**: Доступен\n"
    
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("test_connections"))
async def cmd_test_connections(message: types.Message):
    """Тестирует подключения ко всем API"""
    
    await message.answer("🔗 Тестирую подключения...")
    
    try:
        connections = await marketplace_manager.test_connections()
        
        text = "🔗 **Результаты тестирования:**\n\n"
        
        for platform, result in connections.items():
            if result is True:
                text += f"✅ **{platform.title()}**: Подключение успешно\n"
            elif isinstance(result, str) and result.startswith("API не настроен"):
                text += f"⚠️ **{platform.title()}**: {result}\n"
            else:
                text += f"❌ **{platform.title()}**: {result}\n"
        
        await message.answer(text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка тестирования: {str(e)}")

@router.message(Command("sync_ozon"))
async def cmd_sync_ozon(message: types.Message):
    """Синхронизирует данные Ozon"""
    
    await message.answer("🔄 Синхронизирую данные Ozon...")
    
    try:
        result = await marketplace_manager.sync_ozon_data()
        
        if result['success']:
            text = f"✅ **Ozon синхронизирован!**\n\n"
            text += f"📊 {result['message']}\n"
            text += f"📦 Товаров: {len(result['data'])}"
            
            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer(f"❌ **Ошибка синхронизации Ozon:**\n{result['error']}", parse_mode="Markdown")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("sync_wb"))
async def cmd_sync_wb(message: types.Message):
    """Синхронизирует данные Wildberries"""
    
    await message.answer("🔄 Синхронизирую данные Wildberries...")
    
    try:
        result = await marketplace_manager.sync_wb_data()
        
        if result['success']:
            text = f"✅ **Wildberries синхронизирован!**\n\n"
            text += f"📊 {result['message']}\n"
            text += f"📦 Товаров: {len(result['data'])}"
            
            await message.answer(text, parse_mode="Markdown")
        else:
            await message.answer(f"❌ **Ошибка синхронизации Wildberries:**\n{result['error']}", parse_mode="Markdown")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("sync_all"))
async def cmd_sync_all(message: types.Message):
    """Синхронизирует все маркетплейсы"""
    
    await message.answer("🔄 Синхронизирую все маркетплейсы...")
    
    try:
        results = await marketplace_manager.sync_all_marketplaces()
        
        text = "🔄 **Результаты синхронизации:**\n\n"
        
        for platform, result in results.items():
            if result['success']:
                text += f"✅ **{platform.title()}**: {result['message']}\n"
            else:
                text += f"❌ **{platform.title()}**: {result['error']}\n"
        
        await message.answer(text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("marketplace_help"))
async def cmd_marketplace_help(message: types.Message):
    """Показывает справку по командам маркетплейсов"""
    
    help_text = """
📚 **Справка по командам маркетплейсов:**

🔄 **Синхронизация:**
• `/sync_ozon` - Синхронизировать Ozon
• `/sync_wb` - Синхронизировать Wildberries  
• `/sync_all` - Синхронизировать все маркетплейсы

📊 **Информация:**
• `/marketplace_status` - Статус всех API
• `/test_connections` - Тест подключений

❓ **Помощь:**
• `/marketplace_help` - Эта справка

💡 **Примечание:** Синхронизация обновляет данные в Google таблицах
    """
    
    await message.answer(help_text, parse_mode="Markdown")

# Обработчик для админов
@router.message(Command("marketplace_admin"))
async def cmd_marketplace_admin(message: types.Message):
    """Админские команды для маркетплейсов"""
    
    # Проверяем, является ли пользователь админом
    # Здесь должна быть ваша логика проверки админа
    
    admin_text = """
🔧 **Админские команды маркетплейсов:**

📊 **Мониторинг:**
• `/marketplace_logs` - Последние логи синхронизации
• `/marketplace_errors` - Ошибки за последние 24 часа

⚙️ **Управление:**
• `/marketplace_force_sync` - Принудительная синхронизация
• `/marketplace_clear_cache` - Очистить кеш

📈 **Аналитика:**
• `/marketplace_stats` - Статистика синхронизаций
• `/marketplace_performance` - Производительность API
    """
    
    await message.answer(admin_text, parse_mode="Markdown")

# Пример обработчика для получения статистики
@router.message(Command("marketplace_stats"))
async def cmd_marketplace_stats(message: types.Message):
    """Показывает статистику синхронизаций"""
    
    # Здесь можно добавить логику получения статистики из БД
    stats_text = """
📈 **Статистика маркетплейсов:**

🕐 **Последние 24 часа:**
• Ozon: 3 синхронизации, 2 успешных
• Wildberries: 2 синхронизации, 2 успешных

📊 **Общая статистика:**
• Всего синхронизаций: 156
• Успешных: 148 (94.9%)
• Ошибок: 8 (5.1%)

⏱️ **Среднее время:**
• Ozon: 2.3 сек
• Wildberries: 1.8 сек
    """
    
    await message.answer(stats_text, parse_mode="Markdown")
