import requests
import json
from config import GROK_API_KEY, GROK_API_URL, TIMEZONE
from datetime import datetime, timedelta
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_mood(text):
    text = text.lower()
    positive_keywords = ["хорошо", "рад", "счастлив", "здорово", "круто", "отлично", "прекрасно", "вдохновлен", "доволен", "спокоен", "уверен"]
    negative_keywords = ["плохо", "грустно", "тревож", "страх", "боюсь", "злюсь", "устал", "раздражен", "обижен", "разочарован", "одиноко", "негатив"]
    neutral_keywords = ["нормально", "обычно", "никак", "спокойно", "ровно", "задумался", "размышляю"]
    if any(keyword in text for keyword in negative_keywords):
        return "negative"
    elif any(keyword in text for keyword in positive_keywords):
        return "positive"
    elif any(keyword in text for keyword in neutral_keywords):
        return "neutral"
    return "unknown"

def extract_themes(text):
    themes = {
        "отношения": ["отношения", "любовь", "партнёр", "муж", "жена", "парень", "девушка", "семья", "близкие", "друзья", "общение", "конфликт", "расставание", "свидание"],
        "работа/карьера": ["работа", "карьера", "проект", "коллеги", "начальник", "бизнес", "профессия", "успех", "деньги", "финансы", "должность", "задача", "увольнение"],
        "саморазвитие/цели": ["развитие", "цель", "мечта", "рост", "обучение", "поиск себя", "смысл", "предназначение", "планы", "достижения", "мотивация", "духовность"],
        "здоровье/состояние": ["здоровье", "состояние", "энергия", "болезнь", "усталость", "самочувствие", "тело", "спорт", "питание", "сон", "отдых"],
        "эмоции/чувства": ["чувствую", "эмоции", "ощущения", "настроение", "страх", "радость", "грусть", "злость", "тревога", "счастье", "переживания"],
        "творчество/хобби": ["творчество", "хобби", "увлечение", "искусство", "музыка", "рисование", "создание"],
        "быт/рутина": ["дом", "быт", "рутина", "повседневность", "дела", "организация"]
    }
    found_themes = set()
    text = text.lower()
    for theme, keywords in themes.items():
        if any(keyword in text for keyword in keywords):
            found_themes.add(theme)
    return list(found_themes) if found_themes else ["не определено"]

async def get_grok_question(user_id, user_request, user_response, feedback_type, step=1, previous_responses=None, db=None):
    if db is None:
        logger.error("Database object 'db' is required for get_grok_question")
        raise ValueError("Parameter 'db' is required for get_grok_question")

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    profile = await build_user_profile(user_id, db)
    profile_themes = profile.get("themes", ["не определено"])
    profile_mood_trend = " -> ".join(profile.get("mood_trend", [])) or "нет данных"
    current_mood = analyze_mood(user_response)

    system_prompt = (
        "Ты — тёплый, мудрый и поддерживающий коуч, работающий с метафорическими ассоциативными картами (МАК). "
        "Твоя главная задача — помочь пользователю глубже понять себя через рефлексию над картой и своими ответами. "
        "Не интерпретируй карту сам, фокусируйся на чувствах, ассоциациях и мыслях пользователя. "
        "Задай ОДИН открытый, глубокий и приглашающий к размышлению вопрос (до 15-20 слов). "
        "Вопрос должен побуждать пользователя исследовать причины своих чувств, посмотреть на ситуацию под новым углом или связать увиденное с его жизнью. "
        f"Текущее настроение пользователя: {current_mood}. "
        f"Основные темы из его прошлых запросов: {', '.join(profile_themes)}. "
        f"Тренд настроения: {profile_mood_trend}. "
        "Если настроение негативное ('negative'), начни с эмпатичной фразы ('Понимаю, это может быть непросто...', 'Спасибо, что делишься этим...'), затем задай бережный, поддерживающий вопрос. "
        "Если пользователь обычно отвечает кратко (подсказка: используй это для стиля, а не содержания), задай более конкретный вопрос. Если отвечает развернуто - можно задать более открытый."
        "Постарайся связать вопрос с основными темами пользователя, если это уместно и не выглядит натянуто. "
        "НЕ используй нумерацию или префиксы вроде 'Вопрос (X/3):' - это будет добавлено позже."
        "Избегай прямых советов или решений."
    )

    actions = db.get_actions(user_id)
    history_summary = []
    relevant_actions = [a for a in actions if a['details'].get('card_number') or a['details'].get('request')][-5:]
    for action in relevant_actions:
        if "request" in action["details"]: history_summary.append(f"Запрос: {action['details']['request'][:50]}...")
        if "initial_response" in action["details"]: history_summary.append(f"Ответ на карту: {action['details']['response'][:50]}...")
        if "grok_question" in action["details"]: history_summary.append(f"Вопрос ИИ: {action['details']['grok_question'][:50]}...")
        if "first_grok_response" in action["details"]: history_summary.append(f"Ответ на 1й вопрос: {action['details']['response'][:50]}...")
    history_text = " | ".join(history_summary) if history_summary else "Нет релевантной истории."

    context_lines = [
        f"Краткая история: {history_text}",
        f"Запрос пользователя (если был): '{user_request or 'не указан, фокус на карте дня'}'",
        f"Текущий ответ пользователя: '{user_response}'",
    ]
    if step == 2 and previous_responses:
        context_lines.append(f"Первый вопрос ИИ: '{previous_responses.get('first_question', 'N/A')}'")
        context_lines.append(f"Ответ на него: '{previous_responses.get('first_response', 'N/A')}'")
    elif step == 3 and previous_responses:
        context_lines.append(f"Первый вопрос ИИ: '{previous_responses.get('first_question', 'N/A')}'")
        context_lines.append(f"Ответ на него: '{previous_responses.get('first_response', 'N/A')}'")
        context_lines.append(f"Второй вопрос ИИ: '{previous_responses.get('second_question', 'N/A')}'")
        context_lines.append(f"Ответ на него: '{previous_responses.get('second_response', 'N/A')}'")

    user_prompt = "\n".join(context_lines)

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest",
        "max_tokens": 80,
        "stream": False,
        "temperature": 0.4
    }

    universal_questions = {
        1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту interviewed_request?",
        2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?",
        3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"
    }

    try:
        logger.info(f"Sending request to Grok API for user {user_id}, step {step}. Payload: {json.dumps(payload, ensure_ascii=False)}")
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Received response from Grok API: {json.dumps(data, ensure_ascii=False)}")

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
            raise ValueError("Invalid response structure from Grok API")

        question_text = data["choices"][0]["message"]["content"].strip()
        question_text = re.sub(r'^(Хорошо|Вот ваш вопрос|Конечно)[,:]?\s*', '', question_text, flags=re.IGNORECASE).strip()

        if not question_text:
            raise ValueError("Empty question content after cleaning")

        final_question = f"Вопрос ({step}/3): {question_text}"
        return final_question

    except requests.exceptions.RequestException as e:
        logger.error(f"Grok API request failed for user {user_id}, step {step}: {e}")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум, когда ты смотришь на эту карту?')}"
        return fallback_question
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API response or invalid data for user {user_id}, step {step}: {e}")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Какие детали карты привлекают твоё внимание больше всего?')}"
        return fallback_question
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_grok_question for user {user_id}, step {step}: {e}")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Как твои ощущения изменились за время размышления над картой?')}"
        return fallback_question

async def get_grok_summary(user_id, interaction_data, db=None):
    if db is None:
        logger.error("Database object 'db' is required for get_grok_summary")
        return "Ошибка: Не удалось получить доступ к базе данных для генерации резюме."

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    profile = await build_user_profile(user_id, db)
    profile_themes = profile.get("themes", [])

    system_prompt = (
        "Ты — внимательный и проницательный ИИ-помощник. Твоя задача — проанализировать завершенный диалог пользователя с метафорической картой. "
        "На основе запроса, ответов пользователя на карту и на уточняющие вопросы, сформулируй краткое (2-3 предложения) резюме или инсайт. "
        "Резюме должно отражать ключевые чувства, мысли или возможные направления для дальнейших размышлений пользователя, которые проявились в диалоге. "
        "Будь поддерживающим и НЕ давай прямых советов. Фокусируйся на том, что сказал сам пользователь. "
        "Можешь мягко подсветить связь с его основными темами, если она явно прослеживается: " + ", ".join(profile_themes) + "."
        "Не используй фразы вроде 'Ваше резюме:'."
    )

    qna_text = "\n".join([f"Вопрос ИИ: {item['question']}\nОтвет: {item['answer']}" for item in interaction_data.get("qna", [])])
    user_prompt = (
        "Проанализируй следующий диалог:\n"
        f"Запрос пользователя: '{interaction_data.get('user_request', 'не указан')}'\n"
        f"Номер карты: {interaction_data.get('card_number', 'N/A')}\n"
        f"Первый ответ на карту: '{interaction_data.get('initial_response', 'N/A')}'\n"
        f"Диалог (вопросы и ответы):\n{qna_text}\n\n"
        "Сформулируй краткое резюме или инсайт на основе этого диалога."
    )

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest",
        "max_tokens": 150,
        "stream": False,
        "temperature": 0.3
    }

    try:
        logger.info(f"Sending SUMMARY request to Grok API for user {user_id}. Payload: {json.dumps(payload, ensure_ascii=False)}")
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Received SUMMARY response from Grok API: {json.dumps(data, ensure_ascii=False)}")

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
            raise ValueError("Invalid response structure for summary from Grok API")

        summary_text = data["choices"][0]["message"]["content"].strip()
        summary_text = re.sub(r'^(Хорошо|Вот резюме|Конечно)[,:]?\s*', '', summary_text, flags=re.IGNORECASE).strip()

        if not summary_text:
            raise ValueError("Empty summary content after cleaning")

        return summary_text

    except requests.exceptions.RequestException as e:
        logger.error(f"Grok API summary request failed for user {user_id}: {e}")
        return "К сожалению, не удалось сгенерировать резюме сессии из-за технической проблемы. Но твои размышления очень ценны!"
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API summary response or invalid data for user {user_id}: {e}")
        return "Не получилось сформулировать итог сессии. Главное — те мысли и чувства, которые возникли у тебя."
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_grok_summary for user {user_id}: {e}")
        return "Произошла неожиданная ошибка при подведении итогов. Пожалуйста, попробуй позже."

async def get_supportive_message(user_id, db=None):
    if db is None:
        logger.error("Database object 'db' is required for get_supportive_message")
        return "Понимаю, сейчас может быть непросто. Попробуй сделать что-то приятное для себя."

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    profile = await build_user_profile(user_id, db)
    profile_themes = profile.get("themes", ["не определено"])
    profile_mood_trend = " -> ".join(profile.get("mood_trend", [])) or "нет данных"

    system_prompt = (
        "Ты — тёплый и поддерживающий ИИ-помощник. Пользователь чувствует себя с низким внутренним ресурсом (усталость, грусть или подобное). "
        "Сформулируй короткое (1-2 предложения) сообщение, чтобы поддержать его. "
        "Будь искренним, эмпатичным, избегай клише и прямых советов, если они не уместны. "
        f"Основные темы пользователя: {', '.join(profile_themes)}. "
        f"Тренд настроения: {profile_mood_trend}. "
        "Можешь мягко намекнуть на заботу о себе, связав с темами пользователя, если это естественно."
    )

    user_prompt = "Пользователь указал, что его внутренний ресурс низкий. Напиши короткое поддерживающее сообщение."

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest",
        "max_tokens": 50,
        "stream": False,
        "temperature": 0.3
    }

    try:
        logger.info(f"Sending supportive message request to Grok API for user {user_id}")
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
            raise ValueError("Invalid response structure for supportive message")

        message_text = data["choices"][0]["message"]["content"].strip()
        message_text = re.sub(r'^(Хорошо|Вот сообщение|Конечно)[,:]?\s*', '', message_text, flags=re.IGNORECASE).strip()

        if not message_text:
            raise ValueError("Empty message content after cleaning")

        return message_text

    except requests.exceptions.RequestException as e:
        logger.error(f"Grok API supportive message request failed for user {user_id}: {e}")
        return "Понимаю, сейчас может быть непросто. Ты делаешь лучшее, что можешь, и это уже много."
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API supportive message response for user {user_id}: {e}")
        return "Спасибо, что поделилась. Позволь себе немного отдыха — ты заслуживаешь заботы."
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_supportive_message for user {user_id}: {e}")
        return "Сейчас может быть тяжело, но ты не одна. Побудь с собой бережно."

async def build_user_profile(user_id, db):
    profile_data = db.get_user_profile(user_id)
    now = datetime.now(TIMEZONE)

    if profile_data and "last_updated" in profile_data:
        last_updated_dt = profile_data["last_updated"]
        if isinstance(last_updated_dt, str):
            try:
                last_updated_dt = datetime.fromisoformat(last_updated_dt).astimezone(TIMEZONE)
            except ValueError:
                last_updated_dt = now - timedelta(hours=2)
        if (now - last_updated_dt).total_seconds() < 3600:
            logger.info(f"Using cached profile for user {user_id}, updated at {last_updated_dt}")
            profile_data.setdefault("mood", "unknown")
            profile_data.setdefault("mood_trend", [])
            profile_data.setdefault("themes", ["не определено"])
            profile_data.setdefault("response_count", 0)
            profile_data.setdefault("request_count", 0)
            profile_data.setdefault("avg_response_length", 0)
            profile_data.setdefault("days_active", 0)
            profile_data.setdefault("interactions_per_day", 0)
            profile_data["last_updated"] = last_updated_dt
            return profile_data

    logger.info(f"Rebuilding profile for user {user_id}")
    actions = db.get_actions(user_id)
    if not actions:
        logger.info(f"No actions found for user {user_id}, returning empty profile.")
        empty_profile = {
            "user_id": user_id, "mood": "unknown", "mood_trend": [], "themes": ["не определено"],
            "response_count": 0, "request_count": 0, "avg_response_length": 0,
            "days_active": 0, "interactions_per_day": 0, "last_updated": now
        }
        db.update_user_profile(user_id, empty_profile)
        return empty_profile

    requests_texts = [a["details"].get("request", "") for a in actions if a["action"] == "card_drawn_with_request" and "request" in a["details"]]
    responses = []
    mood_trend_responses = []
    for action in actions:
        details = action["details"]
        if action["action"] in ["initial_response", "first_grok_response", "second_grok_response", "third_grok_response"] and "response" in details:
            responses.append(details["response"])
        if action["action"] in ["initial_response", "first_grok_response", "second_grok_response", "third_grok_response"] and "response" in details:
            mood_trend_responses.append(details["response"])

    all_responses_text = " ".join(responses)
    all_requests_text = " ".join(requests_texts)
    full_text = all_requests_text + " " + all_responses_text

    mood = analyze_mood(all_responses_text[-500:])
    themes = extract_themes(full_text)

    response_count = len(responses)
    request_count = len(requests_texts)
    avg_response_length = sum(len(r) for r in responses) / response_count if response_count > 0 else 0

    timestamps = []
    for a in actions:
        try:
            ts = datetime.fromisoformat(a["timestamp"]).astimezone(TIMEZONE)
            timestamps.append(ts)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp {a.get('timestamp')} for user {user_id}")
            continue

    days_active = 0
    interactions_per_day = 0
    if timestamps:
        first_interaction = min(timestamps)
        last_interaction = max(timestamps)
        days_active = (last_interaction.date() - first_interaction.date()).days + 1
        interactions_per_day = len(actions) / days_active if days_active > 0 else len(actions)

    mood_trend = [analyze_mood(resp) for resp in mood_trend_responses[-5:]]

    profile = {
        "user_id": user_id,
        "mood": mood,
        "mood_trend": mood_trend,
        "themes": themes,
        "response_count": response_count,
        "request_count": request_count,
        "avg_response_length": round(avg_response_length, 2),
        "days_active": days_active,
        "interactions_per_day": round(interactions_per_day, 2),
        "last_updated": now
    }

    db.update_user_profile(user_id, profile)
    logger.info(f"Profile updated for user {user_id}: {profile}")
    return profile
