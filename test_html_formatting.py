#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест для проверки HTML-форматирования
"""

# Импортируем тексты обучения
from modules.texts.learning import LEARNING_TEXTS

def test_html_formatting():
    """Тестирует HTML-форматирование в текстах обучения"""
    
    print("🧪 Тестирование HTML-форматирования в текстах обучения...")
    
    # Проверяем тексты с HTML-тегами
    test_texts = [
        ("theory_1", LEARNING_TEXTS["theory_1"]),
        ("theory_2", LEARNING_TEXTS["theory_2"]),
        ("theory_3", LEARNING_TEXTS["theory_3"]),
        ("theory_4", LEARNING_TEXTS["theory_4"]),
        ("trainer.examples", LEARNING_TEXTS["trainer"]["examples"]),
        ("feedback.request_prefix", LEARNING_TEXTS["feedback"]["request_prefix"]),
        ("feedback.resourceful", LEARNING_TEXTS["feedback"]["resourceful"]),
        ("feedback.neutral", LEARNING_TEXTS["feedback"]["neutral"]),
        ("feedback.external", LEARNING_TEXTS["feedback"]["external"]),
    ]
    
    print("\n📋 Проверка текстов с HTML-тегами:")
    
    for key, text in test_texts:
        print(f"\n🔍 {key}:")
        print(f"   Текст: {text[:100]}...")
        
        # Проверяем наличие HTML-тегов
        has_html_tags = any(tag in text for tag in ['<b>', '<i>', '<code>', '<u>', '<s>'])
        
        if has_html_tags:
            print("   ✅ Содержит HTML-теги")
            # Проверяем, что теги правильно закрыты
            open_tags = text.count('<b>') + text.count('<i>') + text.count('<code>') + text.count('<u>') + text.count('<s>')
            close_tags = text.count('</b>') + text.count('</i>') + text.count('</code>') + text.count('</u>') + text.count('</s>')
            
            if open_tags == close_tags:
                print("   ✅ HTML-теги правильно сбалансированы")
            else:
                print(f"   ❌ Несбалансированные теги: открывающих {open_tags}, закрывающих {close_tags}")
        else:
            print("   ℹ️  Не содержит HTML-тегов")
    
    print("\n✨ Тест завершен!")

def test_parse_mode_usage():
    """Проверяет использование parse_mode в коде"""
    
    print("\n🔍 Проверка использования parse_mode в коде...")
    
    # Читаем файл learn_cards.py
    try:
        with open('modules/learn_cards.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Подсчитываем использование parse_mode
        parse_mode_count = content.count('parse_mode="HTML"')
        message_answer_count = content.count('.answer(')
        
        print(f"   📊 Найдено {parse_mode_count} использований parse_mode='HTML'")
        print(f"   📊 Найдено {message_answer_count} отправок сообщений")
        
        if parse_mode_count > 0:
            print("   ✅ parse_mode='HTML' используется в коде")
        else:
            print("   ❌ parse_mode='HTML' не найден в коде")
            
    except FileNotFoundError:
        print("   ❌ Файл modules/learn_cards.py не найден")

if __name__ == "__main__":
    print("🚀 Запуск тестов форматирования...")
    
    # Запускаем тесты
    test_html_formatting()
    test_parse_mode_usage()
    
    print("\n🎯 Рекомендации:")
    print("1. Убедитесь, что все сообщения с HTML-тегами отправляются с parse_mode='HTML'")
    print("2. Проверьте баланс открывающих и закрывающих тегов")
    print("3. Используйте только поддерживаемые Telegram HTML-теги: <b>, <i>, <code>, <u>, <s>")
    print("4. Не используйте <br> - используйте \\n для переносов строк")
