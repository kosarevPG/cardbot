import requests
from config import GROK_API_KEY, GROK_API_URL

async def get_grok_question(user_id, user_request, user_response, feedback_type, step=1, previous_responses=None):
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    system_prompt = "Ты работаешь с метафорическими картами. Задай один открытый вопрос для рефлексии."
    user_prompt = f"Запрос: '{user_request}'. Ответ: '{user_response}'. Шаг: {step}."
    payload = {
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "model": "grok-2-latest",
        "max_tokens": 50,
        "temperature": 0
    }
    try:
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Вопрос ({step}/3): Что ещё ты можешь сказать о своих ассоциациях?"

# Будущая функция для персонализации
async def build_user_profile(user_id, db):
    actions = db.get_user_actions(user_id)
    responses = [a["details"]["response"] for a in actions if "response" in a["details"]]
    # Логика анализа ответов для построения портрета
    return {"mood": "positive" if "хорошо" in " ".join(responses) else "neutral"}
