# modules/texts/gender_utils.py
# Утилиты для персонализации текстов с учетом пола и имени

import re
from typing import Dict, Any, Optional
from database.db import Database

class GenderDeclension:
    """Класс для работы со склонениями по полу"""
    
    # Словарь склонений для разных частей речи
    DECLENSIONS = {
        # Глаголы (готов/готова/готовы)
        'ready': {
            'male': '',
            'female': 'а', 
            'neutral': 'ы'
        },
        # Прилагательные (уверен/уверена/уверены)
        'confident': {
            'male': '',
            'female': 'а',
            'neutral': 'ы'
        },
        # Местоимения (ты/ты/ты - всегда "ты" для доверительности)
        'you': {
            'male': 'ты',
            'female': 'ты', 
            'neutral': 'ты'
        },
        # Притяжательные (твой/твоя/твой)
        'your': {
            'male': 'твой',
            'female': 'твоя',
            'neutral': 'твой'
        }
    }
    
    @classmethod
    def apply_declension(cls, text: str, gender: str = 'neutral') -> str:
        """
        Применяет склонения к тексту
        
        Args:
            text: Исходный текст с плейсхолдерами
            gender: Пол пользователя ('male', 'female', 'neutral')
            
        Returns:
            str: Текст со склонениями
        """
        if gender not in ['male', 'female', 'neutral']:
            gender = 'neutral'
        
        # Применяем склонения по порядку важности
        # 1. Сначала местоимения (ты/вы)
        text = cls._apply_pronoun_declensions(text, gender)
        
        # 2. Потом прилагательные и глаголы
        text = cls._apply_adjective_declensions(text, gender)
        
        return text
    
    @classmethod
    def _apply_pronoun_declensions(cls, text: str, gender: str) -> str:
        """Применяет склонения местоимений"""
        # Заменяем {you} на "ты" (всегда доверительное обращение)
        text = text.replace('{you}', 'ты')
        return text
    
    @classmethod
    def _apply_adjective_declensions(cls, text: str, gender: str) -> str:
        """Применяет склонения прилагательных и глаголов"""
        
        # Специальная обработка для {ready} - заменяем на полное слово
        if '{ready}' in text:
            if gender == 'female':
                text = text.replace('{ready}', 'готова')
            elif gender == 'male':
                text = text.replace('{ready}', 'готов')
            else:  # neutral
                text = text.replace('{ready}', 'готовы')
        
        # Обработка других склонений
        endings_map = {
            'confident': {
                'male': '',      # уверен
                'female': 'а',   # уверена
                'neutral': 'ы'   # уверены
            }
        }
        
        # Заменяем плейсхолдеры на окончания
        for declension_type, variants in endings_map.items():
            placeholder = f"{{{declension_type}}}"
            if placeholder in text:
                ending = variants.get(gender, variants['neutral'])
                text = text.replace(placeholder, ending)
        
        return text

def get_user_info_for_text(user_id: int, db: Database) -> Dict[str, Any]:
    """
    Получает информацию о пользователе для персонализации текстов
    
    Args:
        user_id: ID пользователя
        db: Экземпляр базы данных
        
    Returns:
        Dict с информацией о пользователе
    """
    try:
        user_info = db.get_user_info(user_id)
        if not user_info:
            return {
                'name': None,
                'gender': 'neutral',
                'has_name': False,
                'first_name': None
            }
        
        # Получаем имя из разных источников
        name = user_info.get('first_name') or user_info.get('username')
        has_name = bool(name and name.strip())
        
        # Получаем пол из базы данных (ручное управление)
        # Если не установлен, используем определение по имени как fallback
        gender = user_info.get('gender', 'neutral')
        if gender == 'neutral' or not gender:
            gender = determine_gender_by_name(name)
        
        return {
            'name': name,
            'gender': gender,
            'has_name': has_name,
            'first_name': user_info.get('first_name'),
            'username': user_info.get('username')
        }
        
    except Exception:
        # В случае ошибки возвращаем нейтральные значения
        return {
            'name': None,
            'gender': 'neutral', 
            'has_name': False,
            'first_name': None
        }

def determine_gender_by_name(name: Optional[str]) -> str:
    """
    Определяет пол по имени (простая эвристика)
    
    Args:
        name: Имя пользователя
        
    Returns:
        str: 'male', 'female' или 'neutral'
    """
    if not name:
        return 'neutral'
    
    name = name.lower().strip()
    
    # Мужские имена (окончания)
    male_endings = ['андр', 'ев', 'ов', 'ин', 'енко', 'ский', 'цкий', 'ич', 'ыч']
    # Женские имена (окончания)  
    female_endings = ['а', 'я', 'ова', 'ева', 'ина', 'ская', 'цкая', 'ична', 'ична']
    
    # Проверяем окончания
    for ending in male_endings:
        if name.endswith(ending):
            return 'male'
            
    for ending in female_endings:
        if name.endswith(ending):
            return 'female'
    
    # Список известных имен
    known_male = ['иван', 'александр', 'сергей', 'дмитрий', 'алексей', 'андрей', 'максим', 'егор', 'михаил', 'артём']
    known_female = ['анна', 'елена', 'ольга', 'татьяна', 'наталья', 'ирина', 'светлана', 'мария', 'юлия', 'екатерина']
    
    if name in known_male:
        return 'male'
    elif name in known_female:
        return 'female'
    
    return 'neutral'

def personalize_text(base_text: str, user_info: Dict[str, Any]) -> str:
    """
    Персонализирует текст с учетом имени и пола пользователя
    
    Args:
        base_text: Базовый текст с плейсхолдерами
        user_info: Информация о пользователе
        
    Returns:
        str: Персонализированный текст
    """
    if not base_text:
        return ""
    
    text = base_text
    gender = user_info.get('gender', 'neutral')
    name = user_info.get('name', '')
    has_name = user_info.get('has_name', False)
    
    # 1. Обрабатываем имя
    if has_name and name:
        # Заменяем {name} на имя
        text = text.replace('{name}', name)
        
        # Обработка {name_part} - часть с именем или без
        if '{name_part}' in text:
            name_part = f", {name}" if has_name else ""
            text = text.replace('{name_part}', name_part)
    else:
        # Если имени нет, убираем плейсхолдеры имени
        text = text.replace('{name}', '')
        text = text.replace('{name_part}', '')
        # Убираем только ДВОЙНЫЕ запятые и пробелы (артефакты удаления плейсхолдеров)
        text = re.sub(r',\s*,', ',', text)  # Двойные запятые
        text = re.sub(r'\s+', ' ', text)    # Множественные пробелы
    
    # 2. Применяем склонения по полу (ВАЖНО: до обработки {your})
    text = GenderDeclension.apply_declension(text, gender)
    
    # 3. Обрабатываем {your} отдельно после склонений
    if '{your}' in text:
        if gender == 'female':
            text = text.replace('{your}', 'твоя')
        else:
            text = text.replace('{your}', 'твой')
    
    # 4. Очищаем лишние пробелы, но сохраняем переносы строк
    text = re.sub(r'[ \t]+', ' ', text)  # Только пробелы и табы, не переносы
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Убираем лишние пустые строки
    text = text.strip()
    
    return text

def _get_nested_value(data: Dict, key: str, separator: str = '.') -> Any:
    """
    Получает значение из вложенного словаря по ключу с разделителем
    
    Args:
        data: Словарь
        key: Ключ с разделителем (например, "intro.welcome")
        separator: Разделитель ключей
        
    Returns:
        Any: Значение или None
    """
    keys = key.split(separator)
    current = data
    
    try:
        for k in keys:
            current = current[k]
        return current
    except (KeyError, TypeError):
        return None


def get_personalized_text(text_key: str, texts_dict: Dict, user_id: int, db) -> str:
    """
    Получает персонализированный текст из словаря текстов.
    
    Args:
        text_key: Ключ текста (может быть вложенным, например "intro.welcome")
        texts_dict: Словарь с текстами (LEARNING_TEXTS, CARDS_TEXTS, и т.д.)
        user_id: ID пользователя
        db: Экземпляр базы данных (может быть None для некоторых случаев)
        
    Returns:
        Персонализированный текст
        
    Example:
        >>> text = get_personalized_text('intro.welcome', LEARNING_TEXTS, 12345, db)
        >>> print(text)
        "Привет, Анна! Ты готова начать?"
    """
    # Получаем шаблон текста из словаря
    template = _get_nested_value(texts_dict, text_key)
    
    if template is None:
        # Если текст не найден, возвращаем ключ для отладки
        return f"[TEXT_NOT_FOUND: {text_key}]"
    
    if not isinstance(template, str):
        # Если это не строка (например, словарь), возвращаем как есть
        return str(template)
    
    # Получаем информацию о пользователе
    user_info = get_user_info_for_text(user_id, db) if db else {
        'gender': 'neutral',
        'name': None,
        'has_name': False
    }
    
    # Применяем персонализацию
    return personalize_text(template, user_info)


# Примеры использования:
if __name__ == "__main__":
    # Тестирование
    test_user_info = {
        'name': 'Анна',
        'gender': 'female', 
        'has_name': True
    }
    
    test_text = "Привет{name_part}! Ты{ready} готов{ready} начать обучение?"
    result = personalize_text(test_text, test_user_info)
    print(f"Результат: {result}")
    # Ожидаемый результат: "Привет, Анна! Тыа готоваа начать обучение?"
