"""
Тестирование системы персонализации текстов
"""
import sys
import os

# Добавляем текущую директорию в path
sys.path.insert(0, os.path.dirname(__file__))

from database.db import Database
from modules.texts import get_personalized_text, LEARNING_TEXTS, CARDS_TEXTS, ERROR_TEXTS

def test_database_connection():
    """Тест 1: Подключение к БД"""
    print("🔧 Тест 1: Подключение к базе данных...")
    try:
        db = Database("data/bot.db")
        print("✅ База данных подключена успешно")
        return db
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return None

def test_user_genders(db):
    """Тест 2: Проверка гендеров пользователей"""
    print("\n🔧 Тест 2: Проверка гендеров пользователей...")
    try:
        cursor = db.conn.execute("SELECT user_id, name, username, gender FROM users LIMIT 10")
        users = cursor.fetchall()
        
        if not users:
            print("⚠️ Нет пользователей в базе")
            return []
        
        print(f"✅ Найдено {len(users)} пользователей:")
        for user in users:
            user_id = user[0]
            name = user[1] or "Нет имени"
            username = user[2] or "Нет username"
            gender = user[3] or "neutral"
            print(f"  - ID: {user_id} | @{username} | {name} | Пол: {gender}")
        
        return users
    except Exception as e:
        print(f"❌ Ошибка получения пользователей: {e}")
        return []

def test_personalization_learning(db, user_id, gender, name):
    """Тест 3: Персонализация текстов обучения"""
    print(f"\n🔧 Тест 3: Персонализация обучения для пользователя {user_id} ({gender}, {name})...")
    
    tests = [
        ("intro.welcome", LEARNING_TEXTS),
        ("theory_1", LEARNING_TEXTS),
        ("entry_poll.q1.question", LEARNING_TEXTS),
    ]
    
    for key, texts_dict in tests:
        try:
            text = get_personalized_text(key, texts_dict, user_id, db)
            print(f"✅ {key}:")
            print(f"   {text[:100]}...")
        except Exception as e:
            print(f"❌ Ошибка для {key}: {e}")

def test_personalization_cards(db, user_id, gender, name):
    """Тест 4: Персонализация текстов карт"""
    print(f"\n🔧 Тест 4: Персонализация карт для пользователя {user_id} ({gender}, {name})...")
    
    tests = [
        ("card_of_day.deck_selection", CARDS_TEXTS),
        ("card_of_day.resource_confirmation", CARDS_TEXTS),
        ("card_of_day.drawing_card", CARDS_TEXTS),
    ]
    
    for key, texts_dict in tests:
        try:
            text = get_personalized_text(key, texts_dict, user_id, db)
            if "{resource}" in text:
                text = text.format(resource="Высокий")
            print(f"✅ {key}:")
            print(f"   {text}")
        except Exception as e:
            print(f"❌ Ошибка для {key}: {e}")

def test_personalization_errors(db, user_id, gender, name):
    """Тест 5: Персонализация ошибок"""
    print(f"\n🔧 Тест 5: Персонализация ошибок для пользователя {user_id} ({gender}, {name})...")
    
    tests = [
        ("admin.training_logs_load_error", ERROR_TEXTS),
        ("permissions.access_denied", ERROR_TEXTS),
    ]
    
    for key, texts_dict in tests:
        try:
            text = get_personalized_text(key, texts_dict, user_id, db)
            print(f"✅ {key}:")
            print(f"   {text}")
        except Exception as e:
            print(f"❌ Ошибка для {key}: {e}")

def main():
    print("="*60)
    print("🚀 ТЕСТИРОВАНИЕ СИСТЕМЫ ПЕРСОНАЛИЗАЦИИ ТЕКСТОВ")
    print("="*60)
    
    # Тест 1: Подключение к БД
    db = test_database_connection()
    if not db:
        return
    
    # Тест 2: Получение пользователей
    users = test_user_genders(db)
    if not users:
        print("\n⚠️ Невозможно продолжить тестирование без пользователей")
        return
    
    # Берем первого пользователя с гендером
    test_user = None
    for user in users:
        if user[3] and user[3] != "neutral":  # Ищем пользователя с заданным гендером
            test_user = user
            break
    
    if not test_user:
        test_user = users[0]  # Берем первого, если нет с гендером
    
    user_id = test_user[0]
    name = test_user[1] or "Пользователь"
    username = test_user[2] or "unknown"
    gender = test_user[3] or "neutral"
    
    print(f"\n📝 Тестируем с пользователем: ID={user_id}, @{username}, {name}, gender={gender}")
    
    # Тест 3-5: Персонализация
    test_personalization_learning(db, user_id, gender, name)
    test_personalization_cards(db, user_id, gender, name)
    test_personalization_errors(db, user_id, gender, name)
    
    print("\n" + "="*60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    print("="*60)

if __name__ == "__main__":
    main()


