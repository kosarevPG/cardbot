# modules/ai_service.py

import httpx
import json
import random
import asyncio
import os
from datetime import datetime, date
import re
import logging
from database.db import Database
try:
    import pytz
except ImportError:
    pytz = None

# Корректировка импорта для доступа к config.py в корне
import sys
sys.path.append('..')  # Добавляем корень проекта в путь поиска
from config import GROK_API_URL, TIMEZONE

# Настройка базового логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- ПЕРЕМЕЩЕНО ВВЕРХ: Анализ текста ---
def analyze_mood(text):
    """Анализирует настроение в тексте по ключевым словам."""
    if not isinstance(text, str):
        logger.warning(f"analyze_mood received non-string input: {type(text)}. Returning 'unknown'.")
        return "unknown"
    text = text.lower()
    positive_keywords = [
        "хорошо", "рад", "счастлив", "здорово", "круто", "отлично", "польза", "полезно",
        "прекрасно", "вдохновлен", "доволен", "спокоен", "уверен", "лучше", "интересно",
        "полегче", "спокойнее", "ресурсно", "наполнено", "заряжен", "позитив", "благодар",
        "ценно", "важно", "тепло", "вдохновение", "радость", "помогло"
    ]
    negative_keywords = [
        "плохо", "грустно", "тревож", "страх", "боюсь", "злюсь", "устал", "напряжение",
        "раздражен", "обижен", "разочарован", "одиноко", "негатив", "тяжело", "сложно",
        "низко", "не очень", "хуже", "обессилен", "вымотан", "пусто", "не хватило",
        "нет сил", "упадок", "негатив", "сомнения", "непонятно"
    ]
    neutral_keywords = [
        "нормально", "обычно", "никак", "спокойно", "ровно", "задумался", "интересно",
        "размышляю", "средне", "так себе", "не изменилось", "нейтрально", "понятно",
        "запрос", "тема", "мысли", "воспоминания", "чувства", "образы"
    ]

    if any(keyword in text for keyword in negative_keywords): return "negative"
    if any(keyword in text for keyword in positive_keywords): return "positive"
    if any(keyword in text for keyword in neutral_keywords): return "neutral"
    return "unknown"

def extract_themes(text):
    """Извлекает основные темы из текста по ключевым словам."""
    if not isinstance(text, str):
        logger.warning(f"extract_themes received non-string input: {type(text)}. Returning ['не определено'].")
        return ["не определено"]

    themes = {
        "отношения": ["отношения", "любовь", "партнёр", "муж", "жена", "парень", "девушка",
                      "семья", "близкие", "друзья", "общение", "конфликт", "расставание",
                      "свидание", "ссора", "развод", "одиночество", "связь", "поддержка", "понимание"],
        "работа/карьера": ["работа", "карьера", "проект", "коллеги", "начальник", "бизнес", "задачи",
                           "профессия", "успех", "деньги", "финансы", "должность", "задача", "нагрузка",
                           "увольнение", "зарплата", "занятость", "нагрузка", "офис", "признание", "коллектив"],
        "саморазвитие/цели": ["развитие", "цель", "мечта", "рост", "обучение", "поиск себя", "смысл", "книга",
                              "предназначение", "планы", "достижения", "мотивация", "духовность", "желания",
                              "самооценка", "уверенность", "призвание", "реализация", "ценности", "потенциал"],
        "здоровье/состояние": ["здоровье", "состояние", "энергия", "болезнь", "усталость", "самочувствие", "сон",
                               "тело", "спорт", "питание", "сон", "отдых", "ресурс", "наполненность", "упадок",
                               "выгорание", "сила", "слабость", "бодрость", "расслабление", "баланс", "телесное"],
        "эмоции/чувства": ["чувствую", "эмоции", "ощущения", "настроение", "страх", "радость", "тепло",
                           "грусть", "злость", "тревога", "счастье", "переживания", "вина", "весна",
                           "стыд", "обида", "гнев", "любовь", "интерес", "апатия", "спокойствие", "вдохновение"],
        "творчество/хобби": ["творчество", "хобби", "увлечение", "искусство", "музыка", "рисование", "цветы",
                             "создание", "вдохновение", "креатив", "рукоделие", "природа", "солнце", "красота"],
        "быт/рутина": ["дом", "быт", "рутина", "повседневность", "дела", "организация", "время",
                       "порядок", "уборка", "ремонт", "переезд", "планирование"]
    }
    found_themes = set()
    text_lower = text.lower()
    words = set(re.findall(r'\b[а-яё]{3,}\b', text_lower))

    for theme, keywords in themes.items():
        if any(keyword in text_lower for keyword in keywords) or any(word in keywords for word in words):
            found_themes.add(theme)

    if not found_themes:
        mood = analyze_mood(text_lower)
        if mood in ["positive", "negative", "neutral"]:
            found_themes.add("эмоции/чувства")

    return list(found_themes) if found_themes else ["не определено"]

# --- Генерация вопросов Grok ---
async def get_grok_question(user_id, user_request, user_response, feedback_type, step=1, previous_responses=None, db: Database = None):
    if db is None:
        logger.error("Database object 'db' is required for get_grok_question")
        universal_questions = {
            1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту?",
            2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?",
            3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"
        }
        return f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум?')}"

    headers = {"Authorization": f"Bearer {os.getenv('XAI_API_KEY', 'xai-TINf07SPF3JTZEF9YkpTa8DMTVM6GYNKYE6YgYHOy5U9DxnEcnwKuU3IG2GBZEwcXFsYM42tbQo3Dfir')}", "Content-Type": "application/json"}
    logger.info(f"Using API key: {headers['Authorization'][:20]}... for user {user_id}")

    profile = await build_user_profile(user_id, db)
    profile_themes = profile.get("themes", []) if profile.get("themes") is not None else ["не определено"]
    profile_mood_trend_list = profile.get("mood_trend", []) if profile.get("mood_trend") is not None else []
    profile_mood_trend = " -> ".join(profile_mood_trend_list) if profile_mood_trend_list else "нет данных"
    avg_resp_len = profile.get("avg_response_length", 50.0) if profile.get("avg_response_length") is not None else 50.0
    initial_resource = profile.get("initial_resource", "неизвестно") if profile.get("initial_resource") is not None else "неизвестно"
    current_mood = analyze_mood(user_response)

    system_prompt = (
        "Ты — тёплый, мудрый и поддерживающий коуч, работающий с метафорическими ассоциативными картами (МАК). "
        "Твоя главная задача — помочь пользователю глубже понять себя через рефлексию над картой и своими ответами. "
        "Не интерпретируй карту сам, фокусируйся на чувствах, ассоциациях и мыслях пользователя. "
        f"Задай ОДИН открытый, глубокий и приглашающий к размышлению вопрос (15-25 слов). "
        f"Начальное ресурсное состояние пользователя перед сессией: {initial_resource}. "
        f"Текущее настроение пользователя по его последнему ответу: {current_mood}. "
        f"Основные темы из его прошлых запросов/ответов: {', '.join(profile_themes)}. "
        f"Тренд настроения (по последним ответам): {profile_mood_trend}. "
        "Если настроение 'negative', начни с эмпатичной фразы ('Понимаю, это может быть непросто...', 'Спасибо, что делишься...'), затем задай бережный вопрос. "
        f"Если ответы короткие (~{avg_resp_len:.0f} симв.), задай конкретный вопрос ('Что именно вызывает это чувство?'). "
        "Если развернутые — задай открытый ('Как это перекликается с твоим опытом?'). "
        "Связывай с темами или ресурсом, если уместно. НЕ используй нумерацию или префиксы, избегай советов, не повторяй вопросы."
        "Все пользователи — женского рода."
    )

    session_context = []
    if user_request: session_context.append(f"Начальный запрос: '{user_request}'")
    initial_response_from_ctx = previous_responses.get("initial_response") if previous_responses else None
    if initial_response_from_ctx: session_context.append(f"Первая ассоциация на карту: '{initial_response_from_ctx}'")
    if step > 1 and previous_responses:
        q1 = previous_responses.get('grok_question_1')
        r1 = previous_responses.get('first_grok_response')
        if q1: session_context.append(f"Вопрос ИИ (1/3): '{q1.split(':')[-1].strip()}'")
        if r1: session_context.append(f"Ответ пользователя 1: '{r1}'")
    if step > 2 and previous_responses:
        q2 = previous_responses.get('grok_question_2')
        r2 = previous_responses.get('second_grok_response')
        if q2: session_context.append(f"Вопрос ИИ (2/3): '{q2.split(':')[-1].strip()}'")
        if r2: session_context.append(f"Ответ пользователя 2: '{r2}'")
    session_context.append(f"ПОСЛЕДНИЙ ответ пользователя (на него нужен вопрос {step}/3): '{user_response}'")
    user_prompt = "Контекст текущей сессии:\n" + "\n".join(session_context)

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-fast"
    }
    logger.info(f"Sending payload to {GROK_API_URL}: {json.dumps(payload, indent=2)}")

    universal_questions = {
        1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту?",
        2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?",
        3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"
    }

    max_retries = 3
    base_delay = 1.0
    final_question = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                logger.info(f"Sending Q{step} request to Grok API for user {user_id} (Attempt {attempt + 1})")
                response = await client.post(GROK_API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Received Q{step} response from Grok API for user {user_id}: {json.dumps(data, indent=2)}")

            if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
                raise ValueError("Invalid response structure from Grok API (choices or content missing)")

            question_text = data["choices"][0]["message"]["content"].strip()
            question_text = re.sub(r'^(Хорошо|Вот ваш вопрос|Конечно|Отлично|Понятно)[,.:]?\s*', '', question_text, flags=re.IGNORECASE).strip()
            question_text = re.sub(r'^"|"$', '', question_text).strip()
            question_text = re.sub(r'^Вопрос\s*\d/\d[:.]?\s*', '', question_text).strip()

            if not question_text or len(question_text) < 5:
                raise ValueError("Empty or too short question content after cleaning")

            if previous_responses:
                prev_q_texts = [previous_responses.get(f'grok_question_{i}').split(':')[-1].strip().lower() for i in range(1, step) if previous_responses.get(f'grok_question_{i}')]
                if question_text.lower() in prev_q_texts:
                    logger.warning(f"Grok generated a repeated question for step {step}, user {user_id}. Question: '{question_text}'. Using fallback.")
                    raise ValueError("Repeated question generated")

            final_question = f"Вопрос ({step}/3): {question_text}"
            break

        except httpx.TimeoutException:
            logger.warning(f"Grok API request Q{step} timed out for user {user_id} (Attempt {attempt + 1})")
            if attempt == max_retries - 1:
                final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум, когда ты смотришь на эту карту?')}"
        except httpx.HTTPStatusError as e:
            logger.error(f"Grok API request Q{step} failed with status {e.response.status_code} for user {user_id}: {e.response.text}")
            if e.response.status_code in [403, 429] or e.response.status_code >= 500:
                logger.warning(f"Retrying due to {e.response.status_code}...")
                if attempt == max_retries - 1:
                    final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Какие детали карты привлекают твоё внимание больше всего?')}"
            else:
                final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Как твои ощущения изменились за время размышления над картой?')}"
                break
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse Grok API response Q{step} or invalid data/repeat for user {user_id}: {e}")
            final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Как твои ощущения изменились за время размышления над картой?')}"
            break
        except Exception as e:
            logger.exception(f"An unexpected error occurred in get_grok_question Q{step} for user {user_id} during attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Попробуй описать свои мысли одним словом. Что это за слово?')}"

        if attempt < max_retries - 1 and final_question is None:
            delay = base_delay * (2 ** attempt)
            logger.info(f"Waiting {delay:.1f}s before retrying Grok request Q{step}...")
            await asyncio.sleep(delay)
        elif final_question is None:
            logger.error(f"Grok API request Q{step} failed after {max_retries} attempts for user {user_id}.")
            final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Как бы ты описала свои чувства сейчас?')}"

    if final_question is None:
        logger.error(f"Critical logic error: final_question is None after retry loop for Q{step}, user {user_id}. Returning default fallback.")
        final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что еще важно для тебя в этой ситуации?')}"

    return final_question

# --- Генерация саммари карты дня ---
async def get_grok_summary(user_id, interaction_data, db: Database = None):
    if db is None:
        logger.error("Database object 'db' is required for get_grok_summary")
        return "Ошибка: Не удалось получить доступ к базе данных для генерации резюме."

    headers = {"Authorization": f"Bearer {os.getenv('XAI_API_KEY', 'xai-TINf07SPF3JTZEF9YkpTa8DMTVM6GYNKYE6YgYHOy5U9DxnEcnwKuU3IG2GBZEwcXFsYM42tbQo3Dfir')}", "Content-Type": "application/json"}
    logger.info(f"Using API key: {headers['Authorization'][:20]}... for user {user_id}")

    profile = await build_user_profile(user_id, db)
    profile_themes = profile.get("themes", [])

    system_prompt = (
        "Ты — внимательный и проницательный ИИ-помощник. Твоя задача — проанализировать завершенный диалог пользователя с метафорической картой. "
        "Сформулируй краткое (2-4 предложения) резюме или основной инсайт сессии на основе запроса (если был), ответов на карту и уточняющих вопросов (если были). "
        "Резюме должно отражать ключевые чувства, мысли или направления для размышлений, проявившиеся в диалоге. "
        "Будь поддерживающим, НЕ давай советов, фокусируйся на словах пользователя. "
        f"Можешь подсветить связь с темами: {', '.join(profile_themes)}, если она очевидна. "
        "Избегай общих фраз, начни с сути, без префиксов вроде 'Резюме:'."
    )

    qna_items = []
    if interaction_data.get("initial_response"):
        qna_items.append(f"Первый ответ на карту: {interaction_data['initial_response']}")
    for item in interaction_data.get("qna", []):
        question = item.get('question', '').split(':')[-1].strip()
        answer = item.get('answer', '').strip()
        if question and answer:
            qna_items.append(f"Вопрос ИИ: {question}\nОтвет: {answer}")

    qna_text = "\n\n".join(qna_items)
    user_request_text = interaction_data.get('user_request', 'не указан')

    user_prompt = (
        f"Проанализируй диалог:\nЗапрос пользователя: '{user_request_text}'\n"
        f"Диалог:\n{qna_text if qna_text else 'Только первый ответ на карту.'}\n"
        "Сформулируй краткое резюме или инсайт сессии (2-4 предложения)."
    )

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-fast"
    }
    logger.info(f"Sending payload to {GROK_API_URL}: {json.dumps(payload, indent=2)}")

    max_retries = 3
    base_delay = 1.0
    summary_text = None
    fallback_summary = "Не получилось сформулировать итог сессии. Главное — те мысли и чувства, которые возникли у тебя."

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                logger.info(f"Sending SUMMARY request to Grok API for user {user_id} (Attempt {attempt + 1})")
                response = await client.post(GROK_API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Received SUMMARY response from Grok API for user {user_id}: {json.dumps(data, indent=2)}")

            if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
                raise ValueError("Invalid response structure for summary from Grok API")

            summary_text_raw = data["choices"][0]["message"]["content"].strip()
            summary_text_raw = re.sub(r'^(Хорошо|Вот резюме|Конечно|Отлично|Итог|Итак)[,.:]?\s*', '', summary_text_raw, flags=re.IGNORECASE).strip()
            summary_text_raw = re.sub(r'^"|"$', '', summary_text_raw).strip()

            if not summary_text_raw or len(summary_text_raw) < 10:
                raise ValueError("Empty or too short summary content after cleaning")

            summary_text = summary_text_raw
            break

        except httpx.TimeoutException:
            logger.warning(f"Grok API summary request timed out for user {user_id} (Attempt {attempt + 1})")
            if attempt == max_retries - 1:
                summary_text = "К сожалению, не удалось сгенерировать резюме сессии (таймаут). Но твои размышления очень ценны!"
        except httpx.HTTPStatusError as e:
            logger.error(f"Grok API request SUMMARY failed with status {e.response.status_code} for user {user_id}: {e.response.text}")
            if e.response.status_code in [403, 429] or e.response.status_code >= 500:
                logger.warning(f"Retrying due to {e.response.status_code}...")
                if attempt == max_retries - 1:
                    summary_text = "К сожалению, не удалось сгенерировать резюме сессии из-за временной ошибки сервера. Но твои размышления очень ценны!"
            else:
                summary_text = fallback_summary
                break
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse Grok API summary response for user {user_id}: {e}")
            summary_text = fallback_summary
            break
        except Exception as e:
            logger.exception(f"An unexpected error occurred in get_grok_summary for user {user_id} during attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                summary_text = "Произошла неожиданная ошибка при подведении итогов. Пожалуйста, попробуй позже."

        if attempt < max_retries - 1 and summary_text is None:
            delay = base_delay * (2 ** attempt)
            logger.info(f"Waiting {delay:.1f}s before retrying Grok SUMMARY request...")
            await asyncio.sleep(delay)
        elif summary_text is None:
            logger.error(f"Grok API summary request failed after {max_retries} attempts for user {user_id}.")
            summary_text = fallback_summary

    return summary_text if summary_text is not None else fallback_summary

# --- Поддержка при низком ресурсе ---
async def get_grok_supportive_message(user_id, db: Database = None):
    if db is None:
        logger.error("Database object 'db' is required for get_grok_supportive_message")
        return ("Пожалуйста, позаботься о себе. Ты важен(на). ✨\n\n"
                "Что обычно помогает тебе восстановить силы?")

    headers = {"Authorization": f"Bearer {os.getenv('XAI_API_KEY', 'xai-TINf07SPF3JTZEF9YkpTa8DMTVM6GYNKYE6YgYHOy5U9DxnEcnwKuU3IG2GBZEwcXFsYM42tbQo3Dfir')}", "Content-Type": "application/json"}
    logger.info(f"Using API key: {headers['Authorization'][:20]}... for user {user_id}")

    profile = await build_user_profile(user_id, db)
    user_info = db.get_user(user_id)
    name = user_info.get("name", "Друг") if user_info else "Друг"
    profile_themes = profile.get("themes", [])

    system_prompt = (
        f"Ты — тёплый, эмпатичный и заботливый друг-помощник. Поддержи пользователя ({name}) с низким ресурсом (😔) после работы с картой. "
        "Напиши короткое (2-3 предложения) искреннее сообщение, признай её чувства ('Слышу тебя...', 'Мне жаль...'), напомни о ценности. "
        "Избегай банальностей и советов, кроме мягкого напоминания о заботе. Тон — мягкий и обнимающий. "
        f"Темы пользователя: {', '.join(profile_themes)}."
    )

    user_prompt = f"Пользователь {name} сообщил, что её ресурсное состояние сейчас низкое (😔). Напиши поддерживающее сообщение."

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-fast"
    }
    logger.info(f"Sending payload to {GROK_API_URL}: {json.dumps(payload, indent=2)}")

    question_about_recharge = "\n\nПоделись, пожалуйста, что обычно помогает тебе восстановить силы и позаботиться о себе в такие моменты?"
    fallback_texts = [
        f"Мне очень жаль, что ты сейчас так себя чувствуешь... Пожалуйста, будь к себе особенно бережен(на). ✨{question_about_recharge}",
        f"Очень сочувствую твоему состоянию... Помни, что любые чувства важны и имеют право быть. Позаботься о себе. 🙏{question_about_recharge}",
        f"Слышу тебя... Иногда бывает тяжело. Помни, ты не один(на) в своих переживаниях. ❤️{question_about_recharge}",
        f"Мне жаль, что тебе сейчас нелегко... Пожалуйста, найди минутку для себя, сделай что-то приятное. ☕️{question_about_recharge}"
    ]

    max_retries = 3
    base_delay = 1.0
    final_message = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                logger.info(f"Sending SUPPORTIVE request to Grok API for user {user_id} (Attempt {attempt + 1})")
                response = await client.post(GROK_API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Received SUPPORTIVE response from Grok API for user {user_id}: {json.dumps(data, indent=2)}")

            if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
                raise ValueError("Invalid response structure for supportive message from Grok API")

            support_text = data["choices"][0]["message"]["content"].strip()
            support_text = re.sub(r'^(Хорошо|Вот сообщение|Конечно|Понятно)[,.:]?\s*', '', support_text, flags=re.IGNORECASE).strip()
            support_text = re.sub(r'^"|"$', '', support_text).strip()

            if not support_text or len(support_text) < 10:
                raise ValueError("Empty or too short support message content after cleaning")

            final_message = support_text + question_about_recharge
            break

        except httpx.TimeoutException:
            logger.warning(f"Grok API supportive message request timed out for user {user_id} (Attempt {attempt + 1})")
            if attempt == max_retries - 1:
                final_message = random.choice(fallback_texts)
        except httpx.HTTPStatusError as e:
            logger.error(f"Grok API request SUPPORTIVE failed with status {e.response.status_code} for user {user_id}: {e.response.text}")
            if e.response.status_code in [403, 429] or e.response.status_code >= 500:
                logger.warning(f"Retrying due to {e.response.status_code}...")
                if attempt == max_retries - 1:
                    final_message = random.choice(fallback_texts)
            else:
                final_message = random.choice(fallback_texts)
                break
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse Grok API supportive message response for user {user_id}: {e}")
            final_message = random.choice(fallback_texts)
            break
        except Exception as e:
            logger.exception(f"An unexpected error occurred in get_grok_supportive_message for user {user_id} during attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                final_message = random.choice(fallback_texts)

        if attempt < max_retries - 1 and final_message is None:
            delay = base_delay * (2 ** attempt)
            logger.info(f"Waiting {delay:.1f}s before retrying Grok SUPPORTIVE request...")
            await asyncio.sleep(delay)
        elif final_message is None:
            logger.error(f"Grok API supportive message request failed after {max_retries} attempts for user {user_id}.")
            final_message = random.choice(fallback_texts)

    return final_message if final_message is not None else random.choice(fallback_texts)

# --- Построение профиля пользователя (ОБНОВЛЕНО) ---
async def build_user_profile(user_id, db: Database):
    profile_data = db.get_user_profile(user_id)
    now = datetime.now(TIMEZONE)

    cache_ttl = 1800
    if profile_data and isinstance(profile_data.get("last_updated"), datetime):
        last_updated_dt = profile_data["last_updated"]
        is_aware = last_updated_dt.tzinfo is not None and last_updated_dt.tzinfo.utcoffset(last_updated_dt) is not None
        if not is_aware and pytz:
            try:
                last_updated_dt = TIMEZONE.localize(last_updated_dt)
                is_aware = True
            except Exception as tz_err:
                logger.error(f"Could not localize naive last_updated timestamp for user {user_id}: {tz_err}. Using naive comparison.")
        elif is_aware:
            last_updated_dt = last_updated_dt.astimezone(TIMEZONE)

        if is_aware and (now - last_updated_dt).total_seconds() < cache_ttl:
            logger.info(f"Using cached profile for user {user_id}, updated at {last_updated_dt}")
            profile_data.setdefault("mood", "unknown")
            profile_data.setdefault("mood_trend", [])
            profile_data.setdefault("themes", ["не определено"])
            profile_data.setdefault("response_count", 0)
            profile_data.setdefault("days_active", 0)
            profile_data.setdefault("initial_resource", None)
            profile_data.setdefault("final_resource", None)
            profile_data.setdefault("recharge_method", None)
            profile_data.setdefault("total_cards_drawn", 0)
            profile_data.setdefault("last_reflection_date", None)
            profile_data.setdefault("reflection_count", 0)
            profile_data.setdefault("request_count", None)
            profile_data.setdefault("avg_response_length", None)
            profile_data.setdefault("interactions_per_day", None)
            return profile_data

    logger.info(f"Rebuilding profile for user {user_id} (Cache expired or profile missing/invalid)")
    base_profile_data = profile_data if profile_data else {"user_id": user_id}

    actions = db.get_actions(user_id)
    reflection_texts_list = db.get_all_reflection_texts(user_id)
    last_recharge_method = db.get_last_recharge_method(user_id)
    last_reflection_date_obj = db.get_last_reflection_date(user_id)
    reflection_count = db.count_reflections(user_id)
    total_cards_drawn = db.count_user_cards(user_id)

    responses = []
    mood_trend_responses = []
    timestamps = []
    last_initial_resource = base_profile_data.get("initial_resource")
    last_final_resource = base_profile_data.get("final_resource")

    for action in actions:
        details = action.get("details", {})
        action_type = action.get("action", "")

        if action_type in ["initial_response_provided", "grok_response_provided", "initial_response", "first_grok_response",
                           "second_grok_response", "third_grok_response"] and "response" in details:
            response_text = details["response"]
            if isinstance(response_text, str):
                responses.append(response_text)
                mood_trend_responses.append(response_text)

        if action_type == "initial_resource_selected" and "resource" in details:
            last_initial_resource = details["resource"]
        if action_type == "final_resource_selected" and "resource" in details:
            last_final_resource = details["resource"]

        raw_timestamp = action.get("timestamp")
        if isinstance(raw_timestamp, str):
            try:
                if raw_timestamp.endswith('Z'):
                    dt_naive = datetime.fromisoformat(raw_timestamp[:-1])
                    dt_aware = pytz.utc.localize(dt_naive) if pytz else dt_naive.replace(tzinfo=datetime.timezone.utc)
                elif '+' in raw_timestamp:
                    dt_aware = datetime.fromisoformat(raw_timestamp)
                else:
                    dt_naive = datetime.fromisoformat(raw_timestamp)
                    dt_aware = pytz.utc.localize(dt_naive) if pytz else dt_naive.replace(tzinfo=datetime.timezone.utc)
                ts = dt_aware.astimezone(TIMEZONE) if pytz else dt_aware
                timestamps.append(ts)
            except (ValueError, Exception) as e:
                logger.warning(f"Could not parse timestamp '{raw_timestamp}' for user {user_id}, action '{action_type}': {e}")
        elif isinstance(raw_timestamp, datetime):
            try:
                ts = raw_timestamp.astimezone(TIMEZONE) if raw_timestamp.tzinfo and pytz else (TIMEZONE.localize(raw_timestamp) if pytz and not raw_timestamp.tzinfo else raw_timestamp)
                timestamps.append(ts)
            except Exception as e:
                logger.warning(f"Error converting datetime timestamp '{raw_timestamp}' for user {user_id}, action '{action_type}': {e}")
        else:
            logger.warning(f"Skipping action due to invalid timestamp type: {type(raw_timestamp)} in action: {action_type}")

    if not actions and not reflection_count and not total_cards_drawn and not base_profile_data.get("last_updated"):
        logger.info(f"No actions or other data for user {user_id}. Creating empty profile.")
        empty_profile = {
            "user_id": user_id, "mood": "unknown", "mood_trend": [], "themes": ["не определено"],
            "response_count": 0, "days_active": 0, "initial_resource": None, "final_resource": None,
            "recharge_method": None, "total_cards_drawn": 0, "last_reflection_date": None, "reflection_count": 0,
            "last_updated": now
        }
        db.update_user_profile(user_id, empty_profile)
        return empty_profile

    all_responses_text = " ".join(responses)
    reflection_full_text = " ".join(filter(None, [item.get(key) for item in reflection_texts_list for key in ['good_moments', 'gratitude', 'hard_moments']]))
    full_text = all_responses_text + " " + reflection_full_text

    mood_source_texts = mood_trend_responses[-5:]
    mood = "unknown"
    if mood_source_texts:
        mood = analyze_mood(mood_source_texts[-1])
    elif base_profile_data:
        mood = base_profile_data.get("mood", "unknown")

    themes = extract_themes(full_text) if full_text.strip() else base_profile_data.get("themes", ["не определено"])
    response_count = len(responses)
    days_active = 0
    if timestamps:
        unique_dates = {ts.date() for ts in timestamps}
        if unique_dates:
            days_active = (now.date() - min(unique_dates)).days + 1
    elif base_profile_data:
        days_active = base_profile_data.get("days_active", 0)

    mood_trend = [analyze_mood(resp) for resp in mood_source_texts]
    last_reflection_date_str = None
    if isinstance(last_reflection_date_obj, date):
        try:
            last_reflection_date_str = last_reflection_date_obj.strftime('%Y-%m-%d')
        except ValueError:
            logger.warning(f"Could not format last_reflection_date_obj {last_reflection_date_obj} for user {user_id}")
            last_reflection_date_str = str(last_reflection_date_obj)
    elif last_reflection_date_obj:
        logger.warning(f"last_reflection_date_obj is not a date object: {type(last_reflection_date_obj)} for user {user_id}")
        last_reflection_date_str = str(last_reflection_date_obj)

    updated_profile = {
        "user_id": user_id, "mood": mood, "mood_trend": mood_trend, "themes": themes,
        "response_count": response_count, "days_active": days_active, "initial_resource": last_initial_resource,
        "final_resource": last_final_resource, "recharge_method": last_recharge_method, "total_cards_drawn": total_cards_drawn,
        "last_reflection_date": last_reflection_date_str, "reflection_count": reflection_count, "last_updated": now
    }

    db.update_user_profile(user_id, updated_profile)
    logger.info(f"Profile rebuilt and updated for user {user_id}.")
    return updated_profile

# --- Резюме для Вечерней Рефлексии ---
async def get_reflection_summary(user_id: int, reflection_data: dict, db: Database) -> str | None:
    logger.info(f"Starting evening reflection summary generation for user {user_id}")
    headers = {"Authorization": f"Bearer {os.getenv('XAI_API_KEY', 'xai-TINf07SPF3JTZEF9YkpTa8DMTVM6GYNKYE6YgYHOy5U9DxnEcnwKuU3IG2GBZEwcXFsYM42tbQo3Dfir')}", "Content-Type": "application/json"}
    logger.info(f"Using API key: {headers['Authorization'][:20]}... for user {user_id}")

    good_moments = reflection_data.get("good_moments", "не указано")
    gratitude = reflection_data.get("gratitude", "не указано")
    hard_moments = reflection_data.get("hard_moments", "не указано")

    profile = await build_user_profile(user_id, db)
    user_info = db.get_user(user_id)
    name = user_info.get("name", "Друг") if user_info else "Друг"
    profile_themes_str = ", ".join(profile.get("themes", ["не определено"]))

    system_prompt = (
        f"Ты — тёплый, мудрый и эмпатичный ИИ-помощник. Проанализируй ответы пользователя ({name}) на вопросы вечерней рефлексии. "
        "Напиши краткое (2-4 предложения) обобщающее и поддерживающее резюме дня, упомяни хорошие моменты, благодарности и трудности. "
        "Признай важность всего опыта и подчеркни ценность рефлексии. Тон — спокойный, принимающий, без советов или акцента на негатив/позитив. "
        f"Темы пользователя (для сведения): {profile_themes_str}. Обращайся на 'ты', начни с сути."
    )

    user_prompt = (
        f"Напиши резюме дня на основе ответов:\n\n1. Что было хорошего? Ответ: \"{good_moments}\"\n\n"
        f"2. За что благодарность? Ответ: \"{gratitude}\"\n\n3. Какие были трудности? Ответ: \"{hard_moments}\""
    )

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-fast"
    }
    logger.info(f"Sending payload to {GROK_API_URL}: {json.dumps(payload, indent=2)}")

    fallback_summary = "Спасибо, что поделилась своими мыслями и чувствами. Важно замечать разное в своем дне."

    max_retries = 3
    base_delay = 1.0
    summary_text = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                logger.info(f"Sending REFLECTION SUMMARY request to Grok API for user {user_id} (Attempt {attempt + 1})")
                response = await client.post(GROK_API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Received REFLECTION SUMMARY response from Grok API for user {user_id}: {json.dumps(data, indent=2)}")

            if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
                raise ValueError("Invalid response structure for reflection summary from Grok API")

            summary_text_raw = data["choices"][0]["message"]["content"].strip()
            summary_text_raw = re.sub(r'^(Хорошо|Вот резюме|Конечно|Отлично|Итог|Итак)[,.:]?\s*', '', summary_text_raw, flags=re.IGNORECASE).strip()
            summary_text_raw = re.sub(r'^"|"$', '', summary_text_raw).strip()

            if not summary_text_raw or len(summary_text_raw) < 10:
                raise ValueError("Empty or too short reflection summary content after cleaning")

            summary_text = summary_text_raw
            break

        except httpx.TimeoutException:
            logger.warning(f"Grok API reflection summary request timed out for user {user_id} (Attempt {attempt + 1})")
            if attempt == max_retries - 1:
                summary_text = "К сожалению, не удалось сгенерировать резюме дня (таймаут)."
        except httpx.HTTPStatusError as e:
            logger.error(f"Grok API request REFLECTION SUMMARY failed with status {e.response.status_code} for user {user_id}: {e.response.text}")
            if e.response.status_code in [403, 429] or e.response.status_code >= 500:
                logger.warning(f"Retrying due to {e.response.status_code}...")
                if attempt == max_retries - 1:
                    summary_text = "К сожалению, не удалось сгенерировать резюме дня из-за временной ошибки сервера."
            else:
                summary_text = fallback_summary
                break
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse Grok API reflection summary response for user {user_id}: {e}")
            summary_text = fallback_summary
            break
        except Exception as e:
            logger.exception(f"An unexpected error occurred in get_reflection_summary for user {user_id} during attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                summary_text = "Произошла неожиданная ошибка при генерации резюме дня."

        if attempt < max_retries - 1 and summary_text is None:
            delay = base_delay * (2 ** attempt)
            logger.info(f"Waiting {delay:.1f}s before retrying Grok REFLECTION SUMMARY request...")
            await asyncio.sleep(delay)
        elif summary_text is None:
            logger.error(f"Grok API reflection summary request failed after {max_retries} attempts for user {user_id}.")
            summary_text = fallback_summary

    return summary_text if summary_text is not None else fallback_summary

# --- КОНЕЦ ФАЙЛА ---
