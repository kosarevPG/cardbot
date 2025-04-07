import requests
import json
from config import GROK_API_KEY, GROK_API_URL, TIMEZONE
from datetime import datetime
import re

async def get_grok_question(user_id, user_request, user_response, feedback_type, step=1, previous_responses=None, db=None):
    if db is None:
        raise ValueError("Parameter 'db' is required for get_grok_question")

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    
    # Получаем историю взаимодействий пользователя из базы данных
    actions = db.get_actions(user_id)
    history = []
    for action in actions:
        if "request" in action["details"]:
            history.append(f"Запрос: {action['details']['request']}")
        if "response" in action["details"]:
            history.append(f"Ответ: {action['details']['response']}")
        if "grok_question" in action["details"]:
            history.append(f"Вопрос Grok: {action['details']['grok_question']}")

    # Анализируем настроение пользователя на основе текущего ответа
    mood = analyze_mood(user_response.lower())
    
    # Формируем системный промпт с учётом настроения и истории
    system_prompt = (
        "Ты — тёплый и поддерживающий помощник, работающий с метафорическими ассоциативными картами (МАК). "
        "Твоя задача — помочь пользователю глубже исследовать свои эмоции и ассоциации, связанные с картой. "
        "На основе запроса пользователя, его ответа на карту, истории взаимодействий и текущего настроения, "
        "задай один открытый вопрос для рефлексии, который побуждает пользователя к глубокому осмыслению своих чувств и мыслей. "
        "Вопрос должен быть кратким (до 15 слов), связанным с контекстом и учитывать настроение пользователя. "
        "Фокусируйся на эмоциях и ассоциациях пользователя, а не на самой карте, и не интерпретируй её. "
        f"Настроение пользователя: {mood}. "
        "Если настроение грустное или тревожное, начни с поддерживающей фразы (например, 'Понимаю, это может быть непросто.' или 'Спасибо, что поделилась, это важно.'). "
        "Если в истории взаимодействий есть повторяющиеся темы (например, работа, отношения), попробуй связать вопрос с этой темой. "
        "Не добавляй префикс вроде 'Вопрос (X/3):', я добавлю его сам."
    )
    
    # Формируем пользовательский промпт
    if not user_request:
        last_request = next((h.split(": ")[1] for h in reversed(history) if h.startswith("Запрос: ")), "пользователь хочет узнать про карту дня")
        user_request = last_request

    if step == 1:
        user_prompt = (
            f"История взаимодействий: {' | '.join(history[-5:])}. "
            f"Запрос: '{user_request}'. Ответ: '{user_response}'. Реакция: '{feedback_type}'."
        )
    elif step == 2:
        user_prompt = (
            f"История взаимодействий: {' | '.join(history[-5:])}. "
            f"Запрос: '{user_request}'. Ответ: '{user_response}'. Реакция: '{feedback_type}'. "
            f"Первый вопрос: '{previous_responses['first_question']}'. Ответ: '{previous_responses['first_response']}'."
        )
    elif step == 3:
        user_prompt = (
            f"История взаимодействий: {' | '.join(history[-5:])}. "
            f"Запрос: '{user_request}'. Ответ: '{user_response}'. Реакция: '{feedback_type}'. "
            f"Первый вопрос: '{previous_responses['first_question']}'. Ответ: '{previous_responses['first_response']}'. "
            f"Второй вопрос: '{previous_responses['second_question']}'. Ответ: '{previous_responses['second_response']}'."
        )
    
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-2-latest",
        "max_tokens": 70,
        "stream": False,
        "temperature": 0.2
    }
    
    universal_questions = {
        1: "Какие чувства или эмоции вызывает у тебя этот образ?",
        2: "Как этот образ связан с тем, что происходит в твоей жизни сейчас?",
        3: "Что бы ты хотела изменить или добавить к этому образу?"
    }
    
    try:
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        question_text = data["choices"][0]["message"]["content"].strip()
        if question_text.startswith(f"Вопрос ({step}/3):"):
            question_text = question_text[len(f"Вопрос ({step}/3):"):].strip()
        return f"Вопрос ({step}/3): {question_text}"
    except Exception:
        return f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё ты можешь сказать о своих ассоциациях?')}"

def analyze_mood(text):
    positive_keywords = ["хорошо", "рад", "счастлив", "здорово", "круто", "отлично"]
    negative_keywords = ["плохо", "грустно", "тревож", "страх", "злюсь", "устал"]
    neutral_keywords = ["нормально", "обычно", "ничего"]

    if any(keyword in text for keyword in positive_keywords):
        return "positive"
    elif any(keyword in text for keyword in negative_keywords):
        return "negative"
    elif any(keyword in text for keyword in neutral_keywords):
        return "neutral"
    return "unknown"

def extract_themes(text):
    themes = {
        "любовь": ["любовь", "отношения", "партнёр", "семья"],
        "работа": ["работа", "карьера", "проект", "коллеги"],
        "саморазвитие": ["развитие", "цель", "мечта", "рост"],
        "здоровье": ["здоровье", "энергия", "болезнь", "спорт"],
        "эмоции": ["чувствую", "эмоции", "страх", "радость"]
    }
    found_themes = []
    text = text.lower()
    for theme, keywords in themes.items():
        if any(keyword in text for keyword in keywords):
            found_themes.append(theme)
    return found_themes or ["не определено"]

async def build_user_profile(user_id, db):
    # Проверяем, есть ли профиль в БД и не устарел ли он
    profile_data = db.get_user_profile(user_id)
    if profile_data and (datetime.now(TIMEZONE) - profile_data["last_updated"]).total_seconds() < 3600:  # Обновляем раз в час
        return profile_data

    # Если профиля нет или он устарел, пересчитываем
    actions = db.get_actions(user_id)
    
    requests = [a["details"].get("request", "") for a in actions if "request" in a["details"]]
    responses = [a["details"].get("response", "") for a in actions if "response" in a["details"]]
    grok_questions = [a["details"].get("grok_question", "") for a in actions if "grok_question" in a["details"]]
    
    all_text = " ".join(requests + responses + grok_questions).lower()
    
    mood = analyze_mood(all_text)
    themes = extract_themes(all_text)
    
    response_count = len(responses)
    request_count = len(requests)
    avg_response_length = sum(len(r) for r in responses) / response_count if response_count > 0 else 0
    
    timestamps = [datetime.fromisoformat(a["timestamp"]) for a in actions]
    if timestamps:
        first_interaction = min(timestamps)
        last_interaction = max(timestamps)
        days_active = (last_interaction - first_interaction).days + 1
        interactions_per_day = len(actions) / days_active if days_active > 0 else 0
    else:
        days_active = 0
        interactions_per_day = 0
    
    mood_trend = []
    recent_responses = responses[-5:]
    for response in recent_responses:
        mood_trend.append(analyze_mood(response.lower()))
    
    profile = {
        "user_id": user_id,
        "mood": mood,
        "mood_trend": mood_trend,
        "themes": themes,
        "response_count": response_count,
        "request_count": request_count,
        "avg_response_length": avg_response_length,
        "days_active": days_active,
        "interactions_per_day": interactions_per_day,
        "last_updated": datetime.now(TIMEZONE)
    }
    
    # Сохраняем профиль в БД
    db.update_user_profile(user_id, profile)
    
    return profile
