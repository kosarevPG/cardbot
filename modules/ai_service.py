import requests
import json
from config import GROK_API_KEY, GROK_API_URL

async def get_grok_question(user_id, user_request, user_response, feedback_type, step=1, previous_responses=None):
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = (
        "Ты работаешь с метафорическими ассоциативными картами (МАК). "
        "На основе запроса пользователя, его ответа после реакции на карту и истории взаимодействий, "
        "задай один открытый вопрос для рефлексии. Не интерпретируй карту, "
        "только помоги пользователю глубже исследовать свои ассоциации. "
        "Вопрос должен быть кратким и связанным с контекстом."
    )
    
    if step == 1:
        user_prompt = f"Запрос: '{user_request}'. Ответ: '{user_response}'. Реакция: '{feedback_type}'."
    elif step == 2:
        user_prompt = (
            f"Запрос: '{user_request}'. Ответ: '{user_response}'. Реакция: '{feedback_type}'. "
            f"Первый вопрос: '{previous_responses['first_question']}'. Ответ: '{previous_responses['first_response']}'."
        )
    elif step == 3:
        user_prompt = (
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
        "max_tokens": 50,
        "stream": False,
        "temperature": 0
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
        return f"Вопрос ({step}/3): {question_text}"
    except Exception:
        return f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё ты можешь сказать о своих ассоциациях?')}"

async def build_user_profile(user_id, db):
    actions = db.get_actions(user_id)
    responses = [a["details"].get("response", "") for a in actions if "response" in a["details"]]
    text = " ".join(responses).lower()
    mood = "positive" if "хорошо" in text or "рад" in text else "neutral"
    return {"mood": mood, "response_count": len(responses)}
