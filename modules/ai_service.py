# код/ai_service.py

import httpx
import json
import random
from config import GROK_API_KEY, GROK_API_URL, TIMEZONE
from datetime import datetime, timedelta
import re
import logging
from database.db import Database # Импортируем Database для аннотации типов
import asyncio # Импортируем asyncio для get_ai_mood

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- <<< НОВАЯ ФУНКЦИЯ: AI Анализ Настроения >>> ---
async def get_ai_mood(text: str) -> str:
    """
    Определяет настроение текста ('positive', 'negative', 'neutral') с помощью AI.
    Возвращает 'unknown' в случае ошибки.
    """
    if not text or not isinstance(text, str) or len(text.strip()) < 3:
        return "unknown" # Не анализируем слишком короткий или некорректный текст

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    system_prompt = "Analyze the sentiment of the following user text. Respond ONLY with one word: 'positive', 'negative', or 'neutral'."
    user_prompt = text[:1000] # Ограничиваем длину текста для API

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-fast", # Используем быструю модель для этой задачи
        "max_tokens": 5,
        "stream": False,
        "temperature": 0.1
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client: # Короткий таймаут
            # logger.debug(f"Sending AI MOOD request for text: '{text[:50]}...'")
            response = await client.post(GROK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # logger.debug(f"Received AI MOOD response: {data}")

        if data.get("choices") and data["choices"][0].get("message"):
            mood_raw = data["choices"][0]["message"].get("content", "").strip().lower()
            # Проверяем, что ответ - одно из ожидаемых слов
            if mood_raw in ["positive", "negative", "neutral"]:
                # logger.debug(f"Determined mood: {mood_raw}")
                return mood_raw
            else:
                logger.warning(f"AI mood analysis returned unexpected word: '{mood_raw}' for text: '{text[:50]}...'")
        else:
            logger.warning(f"Invalid response structure from AI mood analysis for text: '{text[:50]}...'")

    except httpx.TimeoutException:
        logger.warning(f"AI mood analysis request timed out for text: '{text[:50]}...'")
    except httpx.RequestError as e:
        logger.warning(f"AI mood analysis request failed: {e} for text: '{text[:50]}...'")
    except Exception as e:
        logger.error(f"Unexpected error in get_ai_mood: {e}", exc_info=True)

    return "unknown" # Возвращаем unknown при любой ошибке
# --- <<< КОНЕЦ НОВОЙ ФУНКЦИИ >>> ---


# --- Удаляем старую функцию analyze_mood ---
# def analyze_mood(text):
#     ...

# --- Функция extract_themes остается без изменений ---
def extract_themes(text):
    # ... (код функции extract_themes) ...
    """Извлекает основные темы из текста по ключевым словам."""
    themes = {
        "отношения": [
            "отношения", "любовь", "партнёр", "муж", "жена", "парень", "девушка",
            "семья", "близкие", "друзья", "общение", "конфликт", "расставание",
            "свидание", "ссора", "развод", "одиночество", "связь"
        ],
        "работа/карьера": [
            "работа", "карьера", "проект", "коллеги", "начальник", "бизнес",
            "профессия", "успех", "деньги", "финансы", "должность", "задача",
            "увольнение", "зарплата", "занятость", "нагрузка", "офис"
        ],
        "саморазвитие/цели": [
            "развитие", "цель", "мечта", "рост", "обучение", "поиск себя", "смысл",
            "предназначение", "планы", "достижения", "мотивация", "духовность",
            "самооценка", "уверенность", "призвание", "реализация"
        ],
        "здоровье/состояние": [
            "здоровье", "состояние", "энергия", "болезнь", "усталость", "самочувствие",
            "тело", "спорт", "питание", "сон", "отдых", "ресурс", "наполненность",
            "выгорание", "сила", "слабость", "бодрость"
        ],
        "эмоции/чувства": [
            "чувствую", "эмоции", "ощущения", "настроение", "страх", "радость",
            "грусть", "злость", "тревога", "счастье", "переживания", "вина",
            "стыд", "обида", "гнев", "любовь", "интерес", "апатия"
        ],
        "творчество/хобби": [
            "творчество", "хобби", "увлечение", "искусство", "музыка", "рисование",
            "создание", "вдохновение", "креатив", "рукоделие"
        ],
        "быт/рутина": [
            "дом", "быт", "рутина", "повседневность", "дела", "организация",
            "порядок", "уборка", "ремонт", "переезд"
        ]
    }
    found_themes = set()
    text_lower = text.lower()
    words = set(re.findall(r'\b\w{3,}\b', text_lower)) # Находим слова от 3 букв

    for theme, keywords in themes.items():
        # Ищем целые ключевые фразы или отдельные слова из текста в ключах темы
        if any(keyword in text_lower for keyword in keywords) or any(word in keywords for word in words):
             found_themes.add(theme)

    # Если не нашли тем по ключевым словам, но есть текст, добавляем "эмоции/чувства"
    if not found_themes and text_lower.strip():
         found_themes.add("эмоции/чувства")

    return list(found_themes) if found_themes else ["не определено"]


# --- Генерация вопросов Grok (оставляем без изменений) ---
async def get_grok_question(user_id, user_request, user_response, feedback_type, step=1, previous_responses=None, db: Database = None):
    # ... (код функции get_grok_question без изменений) ...
    """
    Генерирует углубляющий вопрос от Grok.
    Учитывает профиль пользователя, включая начальный ресурс.
    """
    if db is None:
        logger.error("Database object 'db' is required for get_grok_question")
        universal_questions = {1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту?", 2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?", 3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"}
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум?')}"
        return fallback_question

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    profile = await build_user_profile(user_id, db)
    profile_themes = profile.get("themes", ["не определено"])
    profile_mood_trend_list = profile.get("mood_trend", [])
    # Фильтруем unknown перед формированием строки тренда
    filtered_trend = [m for m in profile_mood_trend_list if m != "unknown"]
    profile_mood_trend = " -> ".join(filtered_trend) or "нет данных"

    avg_resp_len = profile.get("avg_response_length", 50) # Это поле уберем из расчета профиля, но пока оставим здесь для обратной совместимости промпта
    initial_resource = profile.get("initial_resource", "неизвестно")

    # Используем новый AI анализ для текущего ответа
    current_mood = await get_ai_mood(user_response) # <--- Используем AI

    system_prompt = (
        "Ты — тёплый, мудрый и поддерживающий коуч, работающий с метафорическими ассоциативными картами (МАК). "
        "Твоя главная задача — помочь пользователю глубже понять себя через рефлексию над картой и своими ответами. "
        "Не интерпретируй карту сам, фокусируйся на чувствах, ассоциациях и мыслях пользователя. "
        f"Задай ОДИН открытый, глубокий и приглашающий к размышлению вопрос (15-25 слов). "
        "Вопрос должен побуждать пользователя исследовать причины своих чувств, посмотреть на ситуацию под новым углом или связать увиденное с его жизнью. "
        f"Начальное ресурсное состояние пользователя перед сессией: {initial_resource}. "
        f"Текущее настроение пользователя по его последнему ответу: {current_mood}. "
        f"Основные темы из его прошлых запросов/ответов: {', '.join(profile_themes)}. "
        f"Тренд настроения (по последним ответам): {profile_mood_trend}. "
        "Если настроение пользователя 'negative', начни вопрос с эмпатичной фразы ('Понимаю, это может быть непросто...', 'Спасибо, что делишься...', 'Сочувствую, если это отзывается болью...'), затем задай бережный, поддерживающий вопрос, возможно, сфокусированный на ресурсах или маленьких шагах. "
        f"Если пользователь обычно отвечает кратко (средняя длина ответа ~{avg_resp_len:.0f} симв.), задай более конкретный вопрос ('Что именно вызывает это чувство?', 'Какой аспект карты связан с этим?'). "
        "Если отвечает развернуто - можно задать более открытый ('Как это перекликается с твоим опытом?', 'Что эта ассоциация говорит о твоих потребностях?'). "
        "Постарайся связать вопрос с основными темами пользователя или его начальным ресурсным состоянием, если это уместно и естественно вытекает из его ответа. "
        "НЕ используй нумерацию или префиксы вроде 'Вопрос X:' - это будет добавлено позже. "
        "Избегай прямых советов или решений. "
        "Не задавай вопросы, на которые пользователь уже ответил. "
        "НЕ повторяй вопросы из предыдущих шагов."
        "Все пользователи - женского рода. Не используй к ним обращения в мужском роде."
    )

    session_context = []
    if user_request: session_context.append(f"Начальный запрос: '{user_request}'")
    initial_response = previous_responses.get("initial_response") if previous_responses else None
    if initial_response: session_context.append(f"Первая ассоциация на карту: '{initial_response}'")

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
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "model": "grok-3-latest", "max_tokens": 100, "stream": False, "temperature": 0.5
    }

    universal_questions = {1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту?", 2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?", 3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            logger.info(f"Sending Q{step} request to Grok API for user {user_id}.")
            response = await client.post(GROK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Received Q{step} response from Grok API for user {user_id}.")

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
             raise ValueError("Invalid response structure from Grok API (choices or content missing)")

        question_text = data["choices"][0]["message"]["content"].strip()
        question_text = re.sub(r'^(Хорошо|Вот ваш вопрос|Конечно|Отлично|Понятно)[,.:]?\s*', '', question_text, flags=re.IGNORECASE).strip()
        question_text = re.sub(r'^"|"$', '', question_text).strip()
        question_text = re.sub(r'^Вопрос\s*\d/\d[:.]?\s*', '', question_text).strip()

        if not question_text or len(question_text) < 5:
             raise ValueError("Empty or too short question content after cleaning")

        if previous_responses:
            prev_q_texts = []
            if previous_responses.get('grok_question_1'): prev_q_texts.append(previous_responses['grok_question_1'].split(':')[-1].strip().lower())
            if previous_responses.get('grok_question_2'): prev_q_texts.append(previous_responses['grok_question_2'].split(':')[-1].strip().lower())
            if question_text.lower() in prev_q_texts:
                logger.warning(f"Grok generated a repeated question for step {step}, user {user_id}. Question: '{question_text}'. Using fallback.")
                raise ValueError("Repeated question generated")

        final_question = f"Вопрос ({step}/3): {question_text}"
        return final_question

    except httpx.TimeoutException:
        logger.error(f"Grok API request Q{step} timed out for user {user_id}.")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум, когда ты смотришь на эту карту?')}"
        return fallback_question
    except httpx.RequestError as e:
        logger.error(f"Grok API request Q{step} failed for user {user_id}: {e}")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Какие детали карты привлекают твоё внимание больше всего?')}"
        return fallback_question
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API response Q{step} or invalid data for user {user_id}: {e}")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Как твои ощущения изменились за время размышления над картой?')}"
        return fallback_question
    except Exception as e:
        logger.exception(f"An unexpected error occurred in get_grok_question Q{step} for user {user_id}: {e}")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Попробуй описать свои мысли одним словом. Что это за слово?')}"
        return fallback_question

# --- Генерация саммари карты дня (оставляем без изменений) ---
async def get_grok_summary(user_id, interaction_data, db: Database = None):
    # ... (код функции get_grok_summary без изменений) ...
    """
    Генерирует краткое резюме сессии с картой.
    """
    if db is None:
        logger.error("Database object 'db' is required for get_grok_summary")
        return "Ошибка: Не удалось получить доступ к базе данных для генерации резюме."

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    profile = await build_user_profile(user_id, db)
    profile_themes = profile.get("themes", [])

    system_prompt = (
        "Ты — внимательный и проницательный ИИ-помощник. Твоя задача — проанализировать завершенный диалог пользователя с метафорической картой. "
        "На основе запроса (если был), ответов пользователя на карту и на уточняющие вопросы (если были), сформулируй краткое (2-4 предложения) резюме или основной инсайт сессии. "
        "Резюме должно отражать ключевые чувства, мысли или возможные направления для дальнейших размышлений пользователя, которые проявились в диалоге. "
        "Будь поддерживающим и НЕ давай прямых советов. Фокусируйся на том, что сказал сам пользователь. "
        "Можешь мягко подсветить связь с его основными темами, если она явно прослеживается: " + ", ".join(profile_themes) + ". "
        "Не используй фразы вроде 'Ваше резюме:', 'Итог:'. Начни прямо с сути. "
        "Избегай общих фраз, старайся быть конкретным по содержанию диалога."
    )

    # Собираем текст диалога
    qna_items = []
    if interaction_data.get("initial_response"):
         qna_items.append(f"Первый ответ на карту: {interaction_data['initial_response']}")
    for item in interaction_data.get("qna", []): # qna содержит пары {'question': '...', 'answer': '...'}
        question = item.get('question','').split(':')[-1].strip() # Убираем префикс "Вопрос (X/3):"
        answer = item.get('answer','').strip()
        if question and answer:
             qna_items.append(f"Вопрос ИИ: {question}\nОтвет: {answer}")

    qna_text = "\n\n".join(qna_items)
    user_request_text = interaction_data.get('user_request', 'не указан')

    user_prompt = (
        "Проанализируй следующий диалог:\n"
        f"Запрос пользователя: '{user_request_text}'\n"
        f"Диалог:\n{qna_text if qna_text else 'Только первый ответ на карту.'}\n\n" # Обработка случая без QnA
        "Сформулируй краткое резюме или основной инсайт этой сессии (2-4 предложения)."
    )

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest",
        "max_tokens": 180,
        "stream": False,
        "temperature": 0.4
    }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            logger.info(f"Sending SUMMARY request to Grok API for user {user_id}.")
            response = await client.post(GROK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Received SUMMARY response from Grok API for user {user_id}.")

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
             raise ValueError("Invalid response structure for summary from Grok API")

        summary_text = data["choices"][0]["message"]["content"].strip()
        summary_text = re.sub(r'^(Хорошо|Вот резюме|Конечно|Отлично|Итог|Итак)[,.:]?\s*', '', summary_text, flags=re.IGNORECASE).strip()
        summary_text = re.sub(r'^"|"$', '', summary_text).strip()

        if not summary_text or len(summary_text) < 10:
             raise ValueError("Empty or too short summary content after cleaning")

        return summary_text

    except httpx.TimeoutException:
        logger.error(f"Grok API summary request timed out for user {user_id}.")
        return "К сожалению, не удалось сгенерировать резюме сессии (таймаут). Но твои размышления очень ценны!"
    except httpx.RequestError as e:
        logger.error(f"Grok API summary request failed for user {user_id}: {e}")
        return "К сожалению, не удалось сгенерировать резюме сессии из-за технической проблемы. Но твои размышления очень ценны!"
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API summary response or invalid data for user {user_id}: {e}")
        return "Не получилось сформулировать итог сессии. Главное — те мысли и чувства, которые возникли у тебя."
    except Exception as e:
        logger.exception(f"An unexpected error occurred in get_grok_summary for user {user_id}: {e}")
        return "Произошла неожиданная ошибка при подведении итогов. Пожалуйста, попробуй позже."


# --- Поддержка при низком ресурсе (оставляем без изменений) ---
async def get_grok_supportive_message(user_id, db: Database = None):
    # ... (код функции get_grok_supportive_message без изменений) ...
    """
    Генерирует поддерживающее сообщение и вопрос о способе восстановления
    для пользователя с низким уровнем ресурса после сессии.
    """
    if db is None:
        logger.error("Database object 'db' is required for get_grok_supportive_message")
        fallback_message = ("Пожалуйста, позаботься о себе. Ты важен(на). ✨\n\n"
                            "Что обычно помогает тебе восстановить силы?")
        return fallback_message

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    profile = await build_user_profile(user_id, db)
    user_info = db.get_user(user_id)
    name = user_info.get("name", "Друг") if user_info else "Друг"

    profile_themes = profile.get("themes", [])
    # Получаем последний метод из новой таблицы
    last_recharge_info = db.get_last_recharge_method(user_id)
    recharge_method = last_recharge_info['method'] if last_recharge_info else ""

    system_prompt = (
        f"Ты — очень тёплый, эмпатичный и заботливый друг-помощник. Твоя задача — поддержать пользователя ({name}), который сообщил о низком уровне внутреннего ресурса (😔) после работы с метафорической картой. "
        "Напиши короткое (2-3 предложения), искреннее и ободряющее сообщение. "
        "Признай его чувства ('Слышу тебя...', 'Мне жаль, что сейчас так...', 'Понимаю, это непросто...'), напомни о его ценности и силе. "
        "Избегай банальностей ('все будет хорошо') и ложного позитива. "
        "Не давай советов, кроме мягкого напоминания о заботе о себе. "
        "Тон должен быть мягким, принимающим и обнимающим."
        f" Основные темы, которые волнуют пользователя: {', '.join(profile_themes)}. "
    )
    if recharge_method:
        system_prompt += f" Известно, что ему недавно помогало восстанавливаться: {recharge_method}. Можно мягко упомянуть это или похожие способы заботы о себе, если это уместно."

    user_prompt = f"Пользователь {name} сообщил, что его ресурсное состояние сейчас низкое (😔). Напиши для него короткое поддерживающее сообщение."

    payload = {
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "model": "grok-3-latest", "max_tokens": 120, "stream": False, "temperature": 0.6
    }

    if recharge_method:
        question_about_recharge = (f"\n\nПомнишь, ты недавно упоминала, что тебе помогает '{recharge_method}'? "
                                   "Может, стоит уделить этому время сейчас? Или есть что-то другое, что могло бы поддержать тебя сегодня? Поделись, пожалуйста.")
    else:
        question_about_recharge = "\n\nПоделись, пожалуйста, что обычно помогает тебе восстановить силы и позаботиться о себе в такие моменты?"

    fallback_texts = [
        f"Мне очень жаль, что ты сейчас так себя чувствуешь... Пожалуйста, будь к себе особенно бережен(на). ✨{question_about_recharge}",
        f"Очень сочувствую твоему состоянию... Помни, что любые чувства важны и имеют право быть. Позаботься о себе. 🙏{question_about_recharge}",
        f"Слышу тебя... Иногда бывает тяжело. Помни, ты не один(на) в своих переживаниях. ❤️{question_about_recharge}",
        f"Мне жаль, что тебе сейчас нелегко... Пожалуйста, найди минутку для себя, сделай что-то приятное. ☕️{question_about_recharge}"
    ]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            logger.info(f"Sending SUPPORTIVE request to Grok API for user {user_id}.")
            response = await client.post(GROK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Received SUPPORTIVE response from Grok API for user {user_id}.")

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
             raise ValueError("Invalid response structure for supportive message from Grok API")

        support_text = data["choices"][0]["message"]["content"].strip()
        support_text = re.sub(r'^(Хорошо|Вот сообщение|Конечно|Понятно)[,.:]?\s*', '', support_text, flags=re.IGNORECASE).strip()
        support_text = re.sub(r'^"|"$', '', support_text).strip()

        if not support_text or len(support_text) < 10:
             raise ValueError("Empty or too short support message content after cleaning")

        return support_text + question_about_recharge

    except httpx.TimeoutException:
        logger.error(f"Grok API supportive message request timed out for user {user_id}.")
        return random.choice(fallback_texts)
    except httpx.RequestError as e:
        logger.error(f"Grok API supportive message request failed for user {user_id}: {e}")
        return random.choice(fallback_texts)
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API supportive message response for user {user_id}: {e}")
        return random.choice(fallback_texts)
    except Exception as e:
        logger.exception(f"An unexpected error occurred in get_grok_supportive_message for user {user_id}: {e}")
        return random.choice(fallback_texts)


# --- <<< Функция построения профиля пользователя (ПЕРЕРАБОТАНА) >>> ---
async def build_user_profile(user_id, db: Database):
    """
    Строит или обновляет профиль пользователя.
    Использует AI для анализа настроения, учитывает данные рефлексий,
    хранит историю методов восстановления, упрощает статистику.
    """
    profile_data = db.get_user_profile(user_id) # Получаем кэшированный профиль
    now = datetime.now(TIMEZONE)
    cache_is_valid = False

    # Проверка валидности кэша (раз в 30 минут)
    cache_ttl = 1800
    if profile_data and isinstance(profile_data.get("last_updated"), datetime):
        last_updated_dt = profile_data["last_updated"]
        # Убедимся, что last_updated_dt aware
        if last_updated_dt.tzinfo is None:
            try:
                last_updated_dt = TIMEZONE.localize(last_updated_dt)
            except Exception as tz_err:
                 logger.error(f"Could not localize naive last_updated timestamp from cache for user {user_id}: {tz_err}")
                 last_updated_dt = None # Считаем кэш невалидным

        if last_updated_dt and (now - last_updated_dt).total_seconds() < cache_ttl:
            cache_is_valid = True
            # Гарантируем наличие всех НОВЫХ ключей при возврате кэша
            profile_data.setdefault("mood", "unknown")
            profile_data.setdefault("mood_trend", [])
            profile_data.setdefault("themes", ["не определено"])
            profile_data.setdefault("response_count", 0) # Переименовать бы
            # profile_data.setdefault("request_count", 0) # Убрали
            # profile_data.setdefault("avg_response_length", 0) # Убрали
            profile_data.setdefault("days_active", 0)
            # profile_data.setdefault("interactions_per_day", 0) # Убрали
            profile_data.setdefault("initial_resource", None)
            profile_data.setdefault("final_resource", None)
            profile_data.setdefault("recharge_method", None) # Последний метод
            profile_data.setdefault("last_reflection_date", None) # Новое
            profile_data.setdefault("reflection_count", 0) # Новое
            profile_data.setdefault("total_cards_drawn", 0) # Новое
            logger.info(f"Using cached profile for user {user_id}, updated at {last_updated_dt}")
            return profile_data

    logger.info(f"Rebuilding profile for user {user_id} (Cache expired or profile missing/invalid)")

    # --- Получаем данные из БД ---
    actions = db.get_actions(user_id) # Все действия пользователя
    reflection_texts_data = db.get_all_reflection_texts(user_id, limit=20) # Последние 20 рефлексий для анализа тем
    last_recharge_info = db.get_last_recharge_method(user_id)
    last_reflection_date = db.get_last_reflection_date(user_id)
    reflection_count = db.count_reflections(user_id)

    # --- Инициализация переменных ---
    card_responses = []
    timestamps = []
    mood_trend_list = []
    last_mood = "unknown"
    last_initial_resource = None
    last_final_resource = None
    total_cards_drawn = 0
    all_texts_for_themes = [] # Собираем все тексты для тем

    # --- Обработка действий (actions) ---
    for action in actions:
        details = action.get("details", {})
        action_type = action.get("action", "")
        timestamp_str = action.get("timestamp")

        # Временные метки для расчета дней активности
        try:
            if timestamp_str:
                 ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).astimezone(TIMEZONE)
                 timestamps.append(ts)
        except Exception as e:
             logger.warning(f"Could not parse action timestamp {timestamp_str} for user {user_id}, action {action_type}: {e}")

        # Считаем карты
        if action_type == "card_drawn":
            total_cards_drawn += 1

        # Ответы на вопросы карты дня
        is_card_response = False
        response_text = None
        if action_type in ["initial_response_provided", "grok_response_provided"] and "response" in details:
             response_text = details["response"]
             if isinstance(response_text, str):
                 card_responses.append(response_text)
                 all_texts_for_themes.append(response_text) # Добавляем текст для анализа тем
                 is_card_response = True

        # Настроение (берем из лога, если сохранено там)
        if is_card_response and details.get("mood"):
             mood = details["mood"]
             if mood in ["positive", "negative", "neutral"]: # Проверяем валидность
                 mood_trend_list.append(mood)
                 last_mood = mood # Обновляем последнее известное настроение

        # Ресурсы (из логов карты дня)
        if action_type == "initial_resource_selected" and "resource" in details:
            last_initial_resource = details["resource"]
        if action_type == "final_resource_selected" and "resource" in details:
            last_final_resource = details["resource"]

    # --- Обработка текстов рефлексий для тем ---
    for reflection in reflection_texts_data:
        if reflection.get("good_moments"): all_texts_for_themes.append(reflection["good_moments"])
        if reflection.get("gratitude"): all_texts_for_themes.append(reflection["gratitude"])
        if reflection.get("hard_moments"): all_texts_for_themes.append(reflection["hard_moments"])

    # --- Расчет финальных метрик ---

    # Темы (по всем собранным текстам)
    full_text_for_themes = " ".join(all_texts_for_themes)
    themes = extract_themes(full_text_for_themes)

    # Количество ответов (только карта дня)
    response_count = len(card_responses)

    # Дни активности
    days_active = 0
    if timestamps:
        unique_dates = {ts.date() for ts in timestamps}
        if unique_dates:
            first_interaction_date = min(unique_dates)
            # last_interaction_date = max(unique_dates) # Не используется?
            days_active = len(unique_dates) # Считаем уникальные дни

    # Тренд настроения (последние 5)
    mood_trend = mood_trend_list[-5:]

    # Последний метод восстановления
    recharge_method_to_display = last_recharge_info['method'] if last_recharge_info else None

    # --- Собираем и сохраняем обновленный профиль ---
    updated_profile = {
        "user_id": user_id,
        "mood": last_mood, # Последнее определенное настроение
        "mood_trend": mood_trend, # Список последних 5 настроений
        "themes": themes,
        "response_count": response_count,
        "days_active": days_active,
        "initial_resource": last_initial_resource,
        "final_resource": last_final_resource,
        "recharge_method": recharge_method_to_display, # Последний известный
        "last_reflection_date": last_reflection_date, # Дата последней рефлексии
        "reflection_count": reflection_count, # Кол-во рефлексий
        "total_cards_drawn": total_cards_drawn, # Кол-во карт
        "last_updated": now # Новое время обновления
    }

    # Обновляем кэш в user_profiles
    db.update_user_profile(user_id, updated_profile)
    logger.info(f"Profile rebuilt and updated for user {user_id}.")
    # logger.debug(f"Rebuilt profile data for {user_id}: {updated_profile}")

    return updated_profile
# --- <<< КОНЕЦ ПЕРЕРАБОТАННОЙ ФУНКЦИИ >>> ---


# --- <<< Резюме для Вечерней Рефлексии (ИЗМЕНЕННЫЙ ПРОМПТ) >>> ---
async def get_reflection_summary(user_id: int, reflection_data: dict, db: Database) -> str | None:
    """
    Генерирует AI-резюме для вечерней рефлексии (более развернутое).
    """
    logger.info(f"Starting evening reflection summary generation for user {user_id}")
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    good_moments = reflection_data.get("good_moments", "не указано")
    gratitude = reflection_data.get("gratitude", "не указано")
    hard_moments = reflection_data.get("hard_moments", "не указано")

    profile = await build_user_profile(user_id, db)
    user_info = db.get_user(user_id)
    name = user_info.get("name", "Друг") if user_info else "Друг"
    profile_themes_str = ", ".join(profile.get("themes", ["не определено"]))

    # --- ОБНОВЛЕННЫЙ СИСТЕМНЫЙ ПРОМПТ ---
    system_prompt = (
        f"Ты — очень тёплый, мудрый и эмпатичный ИИ-помощник. Твоя задача — проанализировать ответы пользователя ({name}) на вопросы вечерней рефлексии. "
        "Напиши ТЁПЛОЕ, ПОДДЕРЖИВАЮЩЕЕ и РАЗВЕРНУТОЕ (3-5 предложений) резюме его дня. "
        "Мягко объедини его хорошие моменты, благодарности и признанные трудности, подчеркивая ценность всего прожитого опыта. "
        "Обязательно вырази поддержку и принятие в отношении упомянутых трудностей ('Это нормально чувствовать...', 'Понимаю, что это было непросто...'). "
        "Поблагодари пользователя за уделённое время рефлексии и честность. "
        "Не давай советов, не делай глубоких интерпретаций, не приуменьшай и не преувеличивай чувства. "
        "Тон — мягкий, УСПОКАИВАЮЩИЙ, принимающий, завершающий день. "
        f"Основные темы пользователя (для твоего сведения): {profile_themes_str}. "
        "Всегда обращайся на 'ты'. Не используй префиксы типа 'Резюме:', 'Итог:'. Начни прямо с сути."
    )

    user_prompt = (
        "Пожалуйста, напиши тёплое и поддерживающее резюме дня (3-5 предложений) на основе этих ответов:\n\n"
        f"1. Что было хорошего? Ответ: \"{good_moments}\"\n\n"
        f"2. За что благодарность? Ответ: \"{gratitude}\"\n\n"
        f"3. Какие были трудности? Ответ: \"{hard_moments}\""
    )

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest",
        "max_tokens": 250, # Увеличили лимит для более развернутого ответа
        "stream": False,
        "temperature": 0.6 # Чуть повысили для большей теплоты/вариативности
    }

    fallback_summary = "Спасибо, что поделилась своими мыслями и чувствами. Важно замечать разное в своем дне. Позаботься о себе."

    try:
        async with httpx.AsyncClient(timeout=30.0) as client: # Увеличили таймаут
            logger.info(f"Sending REFLECTION SUMMARY request to Grok API for user {user_id}.")
            response = await client.post(GROK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Received REFLECTION SUMMARY response from Grok API for user {user_id}.")

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
             raise ValueError("Invalid response structure for reflection summary from Grok API")

        summary_text = data["choices"][0]["message"]["content"].strip()
        summary_text = re.sub(r'^(Хорошо|Вот резюме|Конечно|Отлично|Итог|Итак)[,.:]?\s*', '', summary_text, flags=re.IGNORECASE).strip()
        summary_text = re.sub(r'^"|"$', '', summary_text).strip()

        if not summary_text or len(summary_text) < 10:
             raise ValueError("Empty or too short reflection summary content after cleaning")

        return summary_text

    except httpx.TimeoutException:
        logger.error(f"Grok API reflection summary request timed out for user {user_id}.")
        return fallback_summary
    except httpx.RequestError as e:
        logger.error(f"Grok API reflection summary request failed for user {user_id}: {e}")
        return fallback_summary
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API reflection summary response for user {user_id}: {e}")
        return fallback_summary
    except Exception as e:
        logger.exception(f"An unexpected error occurred in get_reflection_summary for user {user_id}: {e}")
        return None
# --- <<< КОНЕЦ ИЗМЕНЕННОЙ ФУНКЦИИ >>> ---


# Импорт pytz (без изменений)
try:
    import pytz
except ImportError:
    pytz = None
    logger.warning("pytz library not found. Timezone conversions might be affected.")
