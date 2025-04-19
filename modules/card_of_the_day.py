# код/ai_service.py

import httpx
import json
import random
from config import GROK_API_KEY, GROK_API_URL, TIMEZONE
from datetime import datetime, timedelta
import re
import logging
# Импортируем Database для аннотации типов и доступа к методам
# и pytz для обработки ошибок таймзон, если он используется
from database.db import Database
try:
    import pytz
except ImportError:
    pytz = None

# Настройка базового логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Анализ текста (оставляем без изменений) ---
def analyze_mood(text):
    # ... (код функции analyze_mood) ...
    """Анализирует настроение в тексте по ключевым словам."""
    text = text.lower()
    # Расширенные списки ключевых слов для лучшего распознавания
    positive_keywords = [
        "хорошо", "рад", "счастлив", "здорово", "круто", "отлично",
        "прекрасно", "вдохновлен", "доволен", "спокоен", "уверен", "лучше",
        "полегче", "спокойнее", "ресурсно", "наполнено", "заряжен", "позитив"
    ]
    negative_keywords = [
        "плохо", "грустно", "тревож", "страх", "боюсь", "злюсь", "устал",
        "раздражен", "обижен", "разочарован", "одиноко", "негатив", "тяжело",
        "сложно", "низко", "не очень", "хуже", "обессилен", "вымотан", "пусто",
        "нет сил", "упадок"
    ]
    neutral_keywords = [
        "нормально", "обычно", "никак", "спокойно", "ровно", "задумался",
        "размышляю", "средне", "так себе", "не изменилось", "нейтрально"
    ]

    # Приоритет негативных, затем позитивных, затем нейтральных
    if any(keyword in text for keyword in negative_keywords): return "negative"
    if any(keyword in text for keyword in positive_keywords): return "positive"
    if any(keyword in text for keyword in neutral_keywords): return "neutral"
    return "unknown"

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

    # Дополнительная проверка по настроению, если темы не найдены
    if not found_themes:
        mood = analyze_mood(text_lower)
        if mood in ["positive", "negative", "neutral"]:
            found_themes.add("эмоции/чувства") # Если есть явное настроение, это тоже тема

    return list(found_themes) if found_themes else ["не определено"]


# --- Генерация вопросов Grok (оставляем без изменений) ---
async def get_grok_question(user_id, user_request, user_response, feedback_type, step=1, previous_responses=None, db: Database = None):
    # ... (код функции get_grok_question) ...
    """
    Генерирует углубляющий вопрос от Grok.
    Учитывает профиль пользователя, включая начальный ресурс.
    """
    if db is None:
        logger.error("Database object 'db' is required for get_grok_question")
        # Запасные вопросы
        universal_questions = {
            1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту?",
            2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?",
            3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"
        }
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум?')}"
        return fallback_question

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    # Получаем профиль и начальный ресурс
    profile = await build_user_profile(user_id, db) # Должен вернуть словарь
    profile_themes = profile.get("themes", ["не определено"])
    profile_mood_trend = " -> ".join(profile.get("mood_trend", [])) or "нет данных"
    avg_resp_len = profile.get("avg_response_length", 50)
    initial_resource = profile.get("initial_resource", "неизвестно") # << НОВОЕ: Учет начального ресурса

    current_mood = analyze_mood(user_response)

    system_prompt = (
        "Ты — тёплый, мудрый и поддерживающий коуч, работающий с метафорическими ассоциативными картами (МАК). "
        "Твоя главная задача — помочь пользователю глубже понять себя через рефлексию над картой и своими ответами. "
        "Не интерпретируй карту сам, фокусируйся на чувствах, ассоциациях и мыслях пользователя. "
        f"Задай ОДИН открытый, глубокий и приглашающий к размышлению вопрос (15-25 слов). "
        "Вопрос должен побуждать пользователя исследовать причины своих чувств, посмотреть на ситуацию под новым углом или связать увиденное с его жизнью. "
        f"Начальное ресурсное состояние пользователя перед сессией: {initial_resource}. " # << НОВОЕ: Добавляем в промпт
        f"Текущее настроение пользователя по его последнему ответу: {current_mood}. "
        f"Основные темы из его прошлых запросов/ответов: {', '.join(profile_themes)}. "
        f"Тренд настроения (по последним ответам): {profile_mood_trend}. "
        # Улучшенные инструкции по адаптации:
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

    # Формируем пользовательский промпт с контекстом сессии
    session_context = []
    if user_request: session_context.append(f"Начальный запрос: '{user_request}'")
    # Используем previous_responses для контекста (структура из card_of_the_day.py)
    initial_response = previous_responses.get("initial_response") if previous_responses else None
    if initial_response: session_context.append(f"Первая ассоциация на карту: '{initial_response}'")

    # Добавляем предыдущие Q&A Grok, если они есть
    if step > 1 and previous_responses:
        q1 = previous_responses.get('grok_question_1')
        r1 = previous_responses.get('first_grok_response')
        if q1: session_context.append(f"Вопрос ИИ (1/3): '{q1.split(':')[-1].strip()}'") # Убираем префикс
        if r1: session_context.append(f"Ответ пользователя 1: '{r1}'")
    if step > 2 and previous_responses:
        q2 = previous_responses.get('grok_question_2')
        r2 = previous_responses.get('second_grok_response')
        if q2: session_context.append(f"Вопрос ИИ (2/3): '{q2.split(':')[-1].strip()}'") # Убираем префикс
        if r2: session_context.append(f"Ответ пользователя 2: '{r2}'")

    # Текущий ответ пользователя, на который нужен вопрос
    session_context.append(f"ПОСЛЕДНИЙ ответ пользователя (на него нужен вопрос {step}/3): '{user_response}'")
    user_prompt = "Контекст текущей сессии:\n" + "\n".join(session_context)

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest", # Или актуальная модель
        "max_tokens": 100,
        "stream": False,
        "temperature": 0.5
    }

    # Запасные вопросы
    universal_questions = {
        1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту?",
        2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?",
        3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"
    }

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
    # ... (код функции get_grok_summary) ...
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

    qna_items = []
    if interaction_data.get("initial_response"):
         qna_items.append(f"Первый ответ на карту: {interaction_data['initial_response']}")
    for item in interaction_data.get("qna", []):
        question = item.get('question','').split(':')[-1].strip()
        answer = item.get('answer','').strip()
        if question and answer:
             qna_items.append(f"Вопрос ИИ: {question}\nОтвет: {answer}")

    qna_text = "\n\n".join(qna_items)
    user_request_text = interaction_data.get('user_request', 'не указан')

    user_prompt = (
        "Проанализируй следующий диалог:\n"
        f"Запрос пользователя: '{user_request_text}'\n"
        f"Диалог:\n{qna_text if qna_text else 'Только первый ответ на карту.'}\n\n"
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
    # ... (код функции get_grok_supportive_message) ...
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
    recharge_method = profile.get("recharge_method", "") # Получаем последний метод из профиля

    system_prompt = (
        f"Ты — очень тёплый, эмпатичный и заботливый друг-помощник. Твоя задача — поддержать пользователя ({name}), который сообщил о низком уровне внутреннего ресурса (😔) после работы с метафорической картой. "
        "Напиши короткое (2-3 предложения), искреннее и ободряющее сообщение. "
        "Признай его чувства ('Слышу тебя...', 'Мне жаль, что сейчас так...', 'Понимаю, это непросто...'), напомни о его ценности и силе. "
        "Избегай банальностей ('все будет хорошо') и ложного позитива. "
        "Не давай советов, кроме мягкого напоминания о заботе о себе. "
        "Тон должен быть мягким, принимающим и обнимающим."
        f" Основные темы, которые волнуют пользователя: {', '.join(profile_themes)}. "
    )
    # Убрали упоминание конкретного recharge_method из системного промпта, т.к. он может быть неактуальным
    # if recharge_method:
    #     system_prompt += f" Известно, что ему обычно помогает восстанавливаться: {recharge_method}. Можно мягко упомянуть это или похожие способы заботы о себе, если это уместно."

    user_prompt = f"Пользователь {name} сообщил, что его ресурсное состояние сейчас низкое (😔). Напиши для него короткое поддерживающее сообщение."

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest",
        "max_tokens": 120,
        "stream": False,
        "temperature": 0.6
    }

    # Убрали упоминание последнего метода из вопроса, чтобы не сбивать пользователя
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


# --- Построение профиля пользователя (ОБНОВЛЕНО) ---
async def build_user_profile(user_id, db: Database):
    """
    Строит или обновляет профиль пользователя.
    Включает данные рефлексии, статистику карт, хранит все методы восстановления (но получает последний).
    Убраны avg_response_length и interactions_per_day.
    """
    profile_data = db.get_user_profile(user_id) # Получаем профиль из БД (может быть None)
    now = datetime.now(TIMEZONE)

    # Проверка кэша (обновление раз в 30 минут)
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
        elif is_aware: # Если aware, просто приводим к нужной таймзоне
            last_updated_dt = last_updated_dt.astimezone(TIMEZONE)

        if is_aware and (now - last_updated_dt).total_seconds() < cache_ttl:
            logger.info(f"Using cached profile for user {user_id}, updated at {last_updated_dt}")
            # Гарантируем наличие всех ключей при возврате кэша
            profile_data.setdefault("mood", "unknown")
            profile_data.setdefault("mood_trend", [])
            profile_data.setdefault("themes", ["не определено"])
            profile_data.setdefault("response_count", 0)
            # profile_data.setdefault("request_count", 0) # Убрали request_count
            # profile_data.setdefault("avg_response_length", 0) # Убрали
            profile_data.setdefault("days_active", 0)
            # profile_data.setdefault("interactions_per_day", 0) # Убрали
            profile_data.setdefault("initial_resource", None)
            profile_data.setdefault("final_resource", None)
            profile_data.setdefault("recharge_method", None) # Последний метод
            profile_data.setdefault("total_cards_drawn", 0) # Новая метрика
            profile_data.setdefault("last_reflection_date", None) # Новая метрика
            profile_data.setdefault("reflection_count", 0) # Новая метрика
            return profile_data

    logger.info(f"Rebuilding profile for user {user_id} (Cache expired or profile missing/invalid)")
    base_profile_data = profile_data if profile_data else {"user_id": user_id}

    # --- Получаем данные из БД ---
    actions = db.get_actions(user_id)
    # Новые вызовы для рефлексии и метода восстановления
    reflection_texts = db.get_all_reflection_texts(user_id) # Получаем тексты рефлексий
    last_recharge_method = db.get_last_recharge_method(user_id) # Получаем последний метод
    last_reflection_date_obj = db.get_last_reflection_date(user_id) # Получаем дату последней рефлексии
    reflection_count = db.count_reflections(user_id) # Получаем кол-во рефлексий
    total_cards_drawn = db.count_user_cards(user_id) # Получаем кол-во карт

    # --- Извлечение данных из логов действий (для того, что не берем напрямую из БД) ---
    # requests_texts = [] # Убрали, т.к. request_count не нужен
    responses = []
    mood_trend_responses = []
    timestamps = []
    last_initial_resource = base_profile_data.get("initial_resource")
    last_final_resource = base_profile_data.get("final_resource")
    # last_recharge_method уже получен из БД

    for action in actions:
        details = action.get("details", {})
        action_type = action.get("action", "")

        # # Запросы (больше не нужны)
        # if action_type == "request_text_provided" and "request" in details:
        #      requests_texts.append(details["request"])
        # elif action_type == "card_drawn_with_request" and "request" in details:
        #      requests_texts.append(details["request"])

        # Ответы (для анализа настроения и тем)
        relevant_response_actions = [
            "initial_response_provided", "grok_response_provided",
            "initial_response", "first_grok_response",
            "second_grok_response", "third_grok_response"
        ]
        if action_type in relevant_response_actions and "response" in details:
            response_text = details["response"]
            if isinstance(response_text, str):
                responses.append(response_text)
                mood_trend_responses.append(response_text)

        # Ресурсы (из логов, т.к. они связаны с конкретной сессией карты)
        if action_type == "initial_resource_selected" and "resource" in details:
             last_initial_resource = details["resource"]
        if action_type == "final_resource_selected" and "resource" in details:
             last_final_resource = details["resource"]
        # Метод восстановления берется из БД

        # Временные метки (для расчета дней активности)
        # --- НАЧАЛО ИСПРАВЛЕННОГО БЛОКА ---
        raw_timestamp = action.get("timestamp")
        if isinstance(raw_timestamp, str):
            try:
                # Парсим ISO строку и делаем aware
                dt_aware = datetime.fromisoformat(raw_timestamp.replace('Z', '+00:00'))
                # Конвертируем в нужную таймзону
                ts = dt_aware.astimezone(TIMEZONE)
                timestamps.append(ts)
            except ValueError as e:
                logger.warning(f"Could not parse ISO timestamp string '{raw_timestamp}' for user {user_id}, action '{action.get('action')}': {e}")
            except Exception as e: # Ловим другие возможные ошибки (напр., pytz)
                 logger.warning(f"Error converting timestamp '{raw_timestamp}' for user {user_id}, action '{action.get('action')}': {e}")
        elif isinstance(raw_timestamp, datetime): # На случай если get_actions вернул datetime
             try:
                 # Делаем aware и конвертируем
                 ts = raw_timestamp.astimezone(TIMEZONE) if raw_timestamp.tzinfo else TIMEZONE.localize(raw_timestamp)
                 timestamps.append(ts)
             except Exception as e:
                 logger.warning(f"Error converting datetime timestamp '{raw_timestamp}' for user {user_id}, action '{action.get('action')}': {e}")
        else:
             logger.warning(f"Skipping action due to invalid timestamp type: {type(raw_timestamp)} in action: {action.get('action')}")
        # --- КОНЕЦ ИСПРАВЛЕННОГО БЛОКА ---


    # --- Расчет метрик ---
    if not actions and not reflection_count and not total_cards_drawn and not base_profile_data.get("last_updated"):
        logger.info(f"No actions or other data for user {user_id}. Creating empty profile.")
        empty_profile = {
            "user_id": user_id, "mood": "unknown", "mood_trend": [], "themes": ["не определено"],
            "response_count": 0, "days_active": 0,
            "initial_resource": None, "final_resource": None, "recharge_method": None,
            "total_cards_drawn": 0, "last_reflection_date": None, "reflection_count": 0,
            "last_updated": now
        }
        db.update_user_profile(user_id, empty_profile)
        return empty_profile

    # Собираем весь текст для анализа тем
    all_responses_text = " ".join(responses)
    reflection_full_text = " ".join(filter(None, [
        reflection_texts.get('good_moments',''),
        reflection_texts.get('gratitude',''),
        reflection_texts.get('hard_moments','')
    ]))
    full_text = all_responses_text + " " + reflection_full_text

    # Настроение (по последним 5 ответам карт дня)
    mood_source_texts = mood_trend_responses[-5:]
    mood = "unknown"
    if mood_source_texts:
        mood = analyze_mood(mood_source_texts[-1])
    elif base_profile_data:
        mood = base_profile_data.get("mood", "unknown")

    # Темы (по всему тексту)
    themes = extract_themes(full_text) if full_text.strip() else base_profile_data.get("themes", ["не определено"])

    response_count = len(responses) # Только ответы на карты
    # request_count = len(requests_texts) # Убрали

    # Активность
    days_active = 0
    if timestamps:
        unique_dates = {ts.date() for ts in timestamps}
        if unique_dates:
             first_interaction_date = min(unique_dates)
             # last_interaction_date = max(unique_dates) # Не нужно
             days_active = (now.date() - first_interaction_date).days + 1 # Дней с первого взаимодействия
    elif base_profile_data:
        days_active = base_profile_data.get("days_active", 0)

    # Тренд настроения (по последним 5 ответам карт дня)
    mood_trend = [analyze_mood(resp) for resp in mood_source_texts]

    # Форматируем дату рефлексии
    last_reflection_date_str = last_reflection_date_obj.strftime('%Y-%m-%d') if last_reflection_date_obj else None

    # --- Собираем и сохраняем обновленный профиль ---
    updated_profile = {
        "user_id": user_id,
        "mood": mood,
        "mood_trend": mood_trend,
        "themes": themes,
        "response_count": response_count, # Ответов на карты
        # "request_count": request_count, # Убрали
        # "avg_response_length": round(avg_response_length, 2), # Убрали
        "days_active": days_active,
        # "interactions_per_day": round(interactions_per_day, 2), # Убрали
        "initial_resource": last_initial_resource,   # Последний из сессии карт
        "final_resource": last_final_resource,       # Последний из сессии карт
        "recharge_method": last_recharge_method,     # Последний из БД
        "total_cards_drawn": total_cards_drawn,      # Новое
        "last_reflection_date": last_reflection_date_str, # Новое (строка)
        "reflection_count": reflection_count,         # Новое
        "last_updated": now
    }

    # Обновляем или создаем профиль в БД
    db.update_user_profile(user_id, updated_profile)
    logger.info(f"Profile rebuilt and updated for user {user_id}.")
    # logger.debug(f"Updated profile data for {user_id}: {updated_profile}")

    return updated_profile


# --- НОВАЯ ФУНКЦИЯ: РЕЗЮМЕ ДЛЯ ВЕЧЕРНЕЙ РЕФЛЕКСИИ (оставляем без изменений) ---
async def get_reflection_summary(user_id: int, reflection_data: dict, db: Database) -> str | None:
    # ... (код функции get_reflection_summary) ...
    """
    Генерирует AI-резюме для вечерней рефлексии.
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

    system_prompt = (
        f"Ты — тёплый, мудрый и эмпатичный ИИ-помощник. Твоя задача — проанализировать ответы пользователя ({name}) на вопросы вечерней рефлексии. "
        "Напиши короткое (2-4 предложения) ОБОБЩАЮЩЕЕ И ПОДДЕРЖИВАЮЩЕЕ резюме его дня. "
        "Обязательно мягко упомяни и хорошие моменты/благодарности, и трудности, признавая важность всего опыта. "
        "Подчеркни ценность того, что пользователь уделил время рефлексии. "
        "Не давай советов, не делай глубоких интерпретаций, не фокусируйся только на негативе или позитиве. "
        "Тон — спокойный, принимающий, завершающий день. "
        f"Основные темы пользователя (для твоего сведения, необязательно упоминать): {profile_themes_str}. "
        "Всегда обращайся на 'ты'. Не используй префиксы типа 'Резюме:', 'Итог:'. Начни прямо с сути."
    )

    user_prompt = (
        "Пожалуйста, напиши краткое (2-4 предложения) резюме дня на основе этих ответов:\n\n"
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
        "max_tokens": 150,
        "stream": False,
        "temperature": 0.5
    }

    fallback_summary = "Спасибо, что поделилась своими мыслями и чувствами. Важно замечать разное в своем дне."

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
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

# --- КОНЕЦ ФАЙЛА ---
