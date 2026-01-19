#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправления форматирования - проверяем, что переносы строк сохраняются
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.texts.gender_utils import personalize_text

def test_formatting_preservation():
    """Тестирует, что переносы строк сохраняются после персонализации"""
    
    print("🧪 Тестирование сохранения переносов строк...")
    
    # Тестовый текст с переносами строк и HTML-тегами
    test_text = "🎯 <b>Что такое МАК-карты</b>\n\nКарты помогают увидеть внутренний смысл через образы, ассоциации и чувства.\n\nПравильного ответа нет — важно, что ты <b>видишь</b> и <b>чувствуешь</b>.\n\nМАК — это трамплин для проявления фантазии."
    
    # Информация о пользователе без имени (случай, когда применяется проблемная регулярка)
    user_info = {
        'gender': 'female',
        'name': '',
        'has_name': False
    }
    
    print(f"\n📝 Исходный текст:")
    print(f"'{test_text}'")
    print(f"\n📊 Анализ исходного текста:")
    print(f"• Символов: {len(test_text)}")
    print(f"• Переносов \\n: {test_text.count(chr(10))}")
    print(f"• Двойных переносов \\n\\n: {test_text.count(chr(10) + chr(10))}")
    print(f"• HTML-тегов <b>: {test_text.count('<b>')}")
    
    # Применяем персонализацию
    result = personalize_text(test_text, user_info)
    
    print(f"\n✅ Результат после персонализации:")
    print(f"'{result}'")
    print(f"\n📊 Анализ результата:")
    print(f"• Символов: {len(result)}")
    print(f"• Переносов \\n: {result.count(chr(10))}")
    print(f"• Двойных переносов \\n\\n: {result.count(chr(10) + chr(10))}")
    print(f"• HTML-тегов <b>: {result.count('<b>')}")
    
    # Проверяем, сохранились ли переносы
    original_newlines = test_text.count(chr(10))
    result_newlines = result.count(chr(10))
    
    print(f"\n🔍 Проверка:")
    if original_newlines == result_newlines:
        print(f"✅ ПЕРЕНОСЫ СТРОК СОХРАНЕНЫ! ({original_newlines} = {result_newlines})")
    else:
        print(f"❌ ПЕРЕНОСЫ СТРОК ПОТЕРЯНЫ! ({original_newlines} ≠ {result_newlines})")
    
    # Проверяем HTML-теги
    original_b_tags = test_text.count('<b>')
    result_b_tags = result.count('<b>')
    
    if original_b_tags == result_b_tags:
        print(f"✅ HTML-ТЕГИ СОХРАНЕНЫ! ({original_b_tags} = {result_b_tags})")
    else:
        print(f"❌ HTML-ТЕГИ ПОТЕРЯНЫ! ({original_b_tags} ≠ {result_b_tags})")
    
    # Проверяем двойные переносы (абзацы)
    original_double_newlines = test_text.count(chr(10) + chr(10))
    result_double_newlines = result.count(chr(10) + chr(10))
    
    if original_double_newlines == result_double_newlines:
        print(f"✅ АБЗАЦЫ СОХРАНЕНЫ! ({original_double_newlines} = {result_double_newlines})")
    else:
        print(f"❌ АБЗАЦЫ ПОТЕРЯНЫ! ({original_double_newlines} ≠ {result_double_newlines})")
    
    print(f"\n🎯 Итог:")
    if (original_newlines == result_newlines and 
        original_b_tags == result_b_tags and 
        original_double_newlines == result_double_newlines):
        print("🎉 ВСЕ ИСПРАВЛЕНИЯ РАБОТАЮТ! Форматирование должно отображаться правильно.")
    else:
        print("⚠️  Есть проблемы с форматированием.")

if __name__ == "__main__":
    test_formatting_preservation()

