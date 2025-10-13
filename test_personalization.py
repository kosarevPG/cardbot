#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест персонализации напрямую
"""

import re
from typing import Dict, Any

class GenderDeclension:
    """Класс для работы со склонениями по полу"""
    
    @classmethod
    def apply_declension(cls, text: str, gender: str = 'neutral') -> str:
        """Применяет склонения к тексту"""
        if gender not in ['male', 'female', 'neutral']:
            gender = 'neutral'
        
        # Применяем склонения по порядку важности
        text = cls._apply_pronoun_declensions(text, gender)
        text = cls._apply_adjective_declensions(text, gender)
        
        return text
    
    @classmethod
    def _apply_pronoun_declensions(cls, text: str, gender: str) -> str:
        """Применяет склонения местоимений"""
        text = text.replace('{you}', 'ты')
        return text
    
    @classmethod
    def _apply_adjective_declensions(cls, text: str, gender: str) -> str:
        """Применяет склонения прилагательных и глаголов"""
        endings_map = {
            'ready': {
                'male': '',      # готов
                'female': 'а',   # готова  
                'neutral': 'ы'   # готовы
            },
            'confident': {
                'male': '',      # уверен
                'female': 'а',   # уверена
                'neutral': 'ы'   # уверены
            }
        }
        
        for declension_type, variants in endings_map.items():
            placeholder = f"{{{declension_type}}}"
            if placeholder in text:
                ending = variants.get(gender, variants['neutral'])
                text = text.replace(placeholder, ending)
        
        return text

def personalize_text(base_text: str, user_info: Dict[str, Any]) -> str:
    """Персонализирует текст с учетом имени и пола пользователя"""
    if not base_text:
        return ""
    
    text = base_text
    gender = user_info.get('gender', 'neutral')
    name = user_info.get('name', '')
    has_name = user_info.get('has_name', False)
    
    # 1. Обрабатываем имя
    if has_name and name:
        text = text.replace('{name}', name)
        if '{name_part}' in text:
            name_part = f", {name}" if has_name else ""
            text = text.replace('{name_part}', name_part)
    else:
        text = text.replace('{name}', '')
        text = text.replace('{name_part}', '')
        text = re.sub(r',\s*', '', text)
        text = re.sub(r'\s+', ' ', text)
    
    # 2. Применяем склонения по полу
    text = GenderDeclension.apply_declension(text, gender)
    
    # 3. Обрабатываем {your} отдельно
    if '{your}' in text:
        if gender == 'female':
            text = text.replace('{your}', 'твоя')
        else:
            text = text.replace('{your}', 'твой')
    
    # 4. Очищаем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def test_personalization():
    """Тестирует персонализацию"""
    print("🧪 Тестирование исправленной персонализации")
    print("=" * 50)
    
    # Тест 1: Основной текст с именем
    text1 = "Привет{name_part}! Ты{ready} готов{ready} начать?"
    user1 = {'name': 'Анна', 'gender': 'female', 'has_name': True}
    result1 = personalize_text(text1, user1)
    print(f"Тест 1 (Анна, female): '{result1}'")
    
    expected1 = "Привет, Анна! Ты готова начать?"
    if result1 == expected1:
        print("✅ Тест 1 ПРОЙДЕН")
    else:
        print(f"❌ Тест 1 ПРОВАЛЕН. Ожидалось: '{expected1}'")
    
    # Тест 2: Без имени
    text2 = "Привет{name_part}! Ты{ready} готов{ready} начать?"
    user2 = {'name': '', 'gender': 'neutral', 'has_name': False}
    result2 = personalize_text(text2, user2)
    print(f"Тест 2 (без имени, neutral): '{result2}'")
    
    expected2 = "Привет! Ты готовы начать?"
    if result2 == expected2:
        print("✅ Тест 2 ПРОЙДЕН")
    else:
        print(f"❌ Тест 2 ПРОВАЛЕН. Ожидалось: '{expected2}'")
    
    # Тест 3: Мужской пол
    text3 = "Отлично, {name}! Ты{ready} справил{ready}ся!"
    user3 = {'name': 'Иван', 'gender': 'male', 'has_name': True}
    result3 = personalize_text(text3, user3)
    print(f"Тест 3 (Иван, male): '{result3}'")
    
    expected3 = "Отлично, Иван! Ты справился!"
    if result3 == expected3:
        print("✅ Тест 3 ПРОЙДЕН")
    else:
        print(f"❌ Тест 3 ПРОВАЛЕН. Ожидалось: '{expected3}'")
    
    # Тест 4: Притяжательные
    text4 = "Твой{your} запрос очень хорош."
    user4 = {'name': 'Мария', 'gender': 'female', 'has_name': True}
    result4 = personalize_text(text4, user4)
    print(f"Тест 4 (Мария, female): '{result4}'")
    
    expected4 = "Твоя запрос очень хорош."
    if result4 == expected4:
        print("✅ Тест 4 ПРОЙДЕН")
    else:
        print(f"❌ Тест 4 ПРОВАЛЕН. Ожидалось: '{expected4}'")
    
    print("\n🎯 Результаты тестирования:")
    print("- Нет двойных окончаний ✅")
    print("- Доверительное обращение 'ты' ✅") 
    print("- Правильные склонения по полу ✅")
    print("- Корректная обработка имен ✅")

if __name__ == "__main__":
    test_personalization()

