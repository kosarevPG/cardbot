# код/ai_service.py

import httpx  # <--- ИЗМЕНЕНИЕ: Импортируем httpx
import json
import random # <--- ИЗМЕНЕНИЕ: Добавляем импорт random
from config import GROK_API_KEY, GROK_API_URL, TIMEZONE
from datetime import datetime, timedelta
import re
import logging

# Настройка базового логирования
# Уровень INFO будет показывать запросы/ответы API, DEBUG - еще больше деталей
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Анализ текста (расширенные ключевые слова из предоставленной версии) ---
def analyze_mood(text):
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

# --- Генерация вопросов Grok ---
async def get_grok_question(user_id, user_request, user_response, feedback_type, step=1, previous_responses=None, db=None):
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
        # <--- ИЗМЕНЕНИЕ: Используем httpx ---
        async with httpx.AsyncClient(timeout=20.0) as client:
            logger.info(f"Sending Q{step} request to Grok API for user {user_id}.")
            # logger.debug(f"Payload Q{step} for user {user_id}: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            response = await client.post(GROK_API_URL, headers=headers, json=payload) # Используем await client.post
            response.raise_for_status() # Проверка HTTP ошибок
            data = response.json()
            logger.info(f"Received Q{step} response from Grok API for user {user_id}.")
            # logger.debug(f"Response data Q{step} for user {user_id}: {json.dumps(data, ensure_ascii=False, indent=2)}")
        # --- Конец изменений httpx ---

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
             raise ValueError("Invalid response structure from Grok API (choices or content missing)")

        question_text = data["choices"][0]["message"]["content"].strip()
        # Очистка ответа модели
        question_text = re.sub(r'^(Хорошо|Вот ваш вопрос|Конечно|Отлично|Понятно)[,.:]?\s*', '', question_text, flags=re.IGNORECASE).strip()
        question_text = re.sub(r'^"|"$', '', question_text).strip()
        question_text = re.sub(r'^Вопрос\s*\d/\d[:.]?\s*', '', question_text).strip()

        if not question_text or len(question_text) < 5:
             raise ValueError("Empty or too short question content after cleaning")

        # Проверка на повторение предыдущих вопросов
        if previous_responses:
            prev_q_texts = []
            if previous_responses.get('grok_question_1'): prev_q_texts.append(previous_responses['grok_question_1'].split(':')[-1].strip().lower())
            if previous_responses.get('grok_question_2'): prev_q_texts.append(previous_responses['grok_question_2'].split(':')[-1].strip().lower())
            if question_text.lower() in prev_q_texts:
                logger.warning(f"Grok generated a repeated question for step {step}, user {user_id}. Question: '{question_text}'. Using fallback.")
                raise ValueError("Repeated question generated")

        final_question = f"Вопрос ({step}/3): {question_text}"
        return final_question

    # <--- ИЗМЕНЕНИЕ: Обработка ошибок httpx ---
    except httpx.TimeoutException:
        logger.error(f"Grok API request Q{step} timed out for user {user_id}.")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум, когда ты смотришь на эту карту?')}"
        return fallback_question
    except httpx.RequestError as e:
        logger.error(f"Grok API request Q{step} failed for user {user_id}: {e}")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Какие детали карты привлекают твоё внимание больше всего?')}"
        return fallback_question
    # --- Конец изменений ошибок httpx ---
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API response Q{step} or invalid data for user {user_id}: {e}")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Как твои ощущения изменились за время размышления над картой?')}"
        return fallback_question
    except Exception as e:
        logger.exception(f"An unexpected error occurred in get_grok_question Q{step} for user {user_id}: {e}") # Используем exception для stacktrace
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Попробуй описать свои мысли одним словом. Что это за слово?')}"
        return fallback_question


# --- Генерация саммари ---
async def get_grok_summary(user_id, interaction_data, db=None):
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
        # <--- ИЗМЕНЕНИЕ: Используем httpx ---
        async with httpx.AsyncClient(timeout=25.0) as client:
            logger.info(f"Sending SUMMARY request to Grok API for user {user_id}.")
            # logger.debug(f"Payload SUMMARY for user {user_id}: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            response = await client.post(GROK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Received SUMMARY response from Grok API for user {user_id}.")
            # logger.debug(f"Response data SUMMARY for user {user_id}: {json.dumps(data, ensure_ascii=False, indent=2)}")
        # --- Конец изменений httpx ---

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
             raise ValueError("Invalid response structure for summary from Grok API")

        summary_text = data["choices"][0]["message"]["content"].strip()
        summary_text = re.sub(r'^(Хорошо|Вот резюме|Конечно|Отлично|Итог|Итак)[,.:]?\s*', '', summary_text, flags=re.IGNORECASE).strip()
        summary_text = re.sub(r'^"|"$', '', summary_text).strip()

        if not summary_text or len(summary_text) < 10:
             raise ValueError("Empty or too short summary content after cleaning")

        return summary_text

    # <--- ИЗМЕНЕНИЕ: Обработка ошибок httpx ---
    except httpx.TimeoutException:
        logger.error(f"Grok API summary request timed out for user {user_id}.")
        return "К сожалению, не удалось сгенерировать резюме сессии (таймаут). Но твои размышления очень ценны!"
    except httpx.RequestError as e:
        logger.error(f"Grok API summary request failed for user {user_id}: {e}")
        return "К сожалению, не удалось сгенерировать резюме сессии из-за технической проблемы. Но твои размышления очень ценны!"
    # --- Конец изменений ошибок httpx ---
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API summary response or invalid data for user {user_id}: {e}")
        return "Не получилось сформулировать итог сессии. Главное — те мысли и чувства, которые возникли у тебя."
    except Exception as e:
        logger.exception(f"An unexpected error occurred in get_grok_summary for user {user_id}: {e}")
        return "Произошла неожиданная ошибка при подведении итогов. Пожалуйста, попробуй позже."

# --- НОВАЯ ФУНКЦИЯ: Генерация поддерживающего сообщения при низком ресурсе ---
async def get_grok_supportive_message(user_id, db=None):
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

    # Получаем профиль для контекста
    profile = await build_user_profile(user_id, db)
    name = db.get_user(user_id).get("name", "Друг") # Имя пользователя
    profile_themes = profile.get("themes", [])
    recharge_method = profile.get("recharge_method", "") # Известный способ подзарядки

    # Промпт для Grok
    system_prompt = (
        f"Ты — очень тёплый, эмпатичный и заботливый друг-помощник. Твоя задача — поддержать пользователя ({name}), который сообщил о низком уровне внутреннего ресурса (😔) после работы с метафорической картой. "
        "Напиши короткое (2-3 предложения), искреннее и ободряющее сообщение. "
        "Признай его чувства ('Слышу тебя...', 'Мне жаль, что сейчас так...', 'Понимаю, это непросто...'), напомни о его ценности и силе. "
        "Избегай банальностей ('все будет хорошо') и ложного позитива. "
        "Не давай советов, кроме мягкого напоминания о заботе о себе. "
        "Тон должен быть мягким, принимающим и обнимающим."
        # Добавляем контекст, если есть
        f" Основные темы, которые волнуют пользователя: {', '.join(profile_themes)}. "
    )
    if recharge_method:
        system_prompt += f" Известно, что ему обычно помогает восстанавливаться: {recharge_method}. Можно мягко упомянуть это или похожие способы заботы о себе, если это уместно."

    user_prompt = f"Пользователь {name} сообщил, что его ресурсное состояние сейчас низкое (😔). Напиши для него короткое поддерживающее сообщение."

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest",
        "max_tokens": 120,
        "stream": False,
        "temperature": 0.6 # Для более "человечного" ответа
    }

    # Формулируем вопрос о восстановлении
    if recharge_method:
        question_about_recharge = (f"\n\nПомнишь, ты упоминала, что тебе обычно помогает '{recharge_method}'? "
                                   "Может, стоит уделить этому время сейчас? Или есть что-то другое, что могло бы поддержать тебя сегодня? Поделись, пожалуйста.")
    else:
        question_about_recharge = "\n\nПоделись, пожалуйста, что обычно помогает тебе восстановить силы и позаботиться о себе в такие моменты?"

    # Запасные сообщения + вопрос на случай ошибки API
    fallback_texts = [
        f"Мне очень жаль, что ты сейчас так себя чувствуешь... Пожалуйста, будь к себе особенно бережен(на). ✨{question_about_recharge}",
        f"Очень сочувствую твоему состоянию... Помни, что любые чувства важны и имеют право быть. Позаботься о себе. 🙏{question_about_recharge}",
        f"Слышу тебя... Иногда бывает тяжело. Помни, ты не один(на) в своих переживаниях. ❤️{question_about_recharge}",
        f"Мне жаль, что тебе сейчас нелегко... Пожалуйста, найди минутку для себя, сделай что-то приятное. ☕️{question_about_recharge}"
    ]

    try:
        # <--- ИЗМЕНЕНИЕ: Используем httpx ---
        async with httpx.AsyncClient(timeout=15.0) as client:
            logger.info(f"Sending SUPPORTIVE request to Grok API for user {user_id}.")
            # logger.debug(f"Payload SUPPORTIVE for user {user_id}: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            response = await client.post(GROK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Received SUPPORTIVE response from Grok API for user {user_id}.")
            # logger.debug(f"Response data SUPPORTIVE for user {user_id}: {json.dumps(data, ensure_ascii=False, indent=2)}")
        # --- Конец изменений httpx ---

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
             raise ValueError("Invalid response structure for supportive message from Grok API")

        support_text = data["choices"][0]["message"]["content"].strip()
        # Очистка
        support_text = re.sub(r'^(Хорошо|Вот сообщение|Конечно|Понятно)[,.:]?\s*', '', support_text, flags=re.IGNORECASE).strip()
        support_text = re.sub(r'^"|"$', '', support_text).strip()

        if not support_text or len(support_text) < 10:
             raise ValueError("Empty or too short support message content after cleaning")

        # Добавляем вопрос к сообщению от Grok
        return support_text + question_about_recharge

    # <--- ИЗМЕНЕНИЕ: Обработка ошибок httpx ---
    except httpx.TimeoutException:
        logger.error(f"Grok API supportive message request timed out for user {user_id}.")
        return random.choice(fallback_texts) # Возвращаем случайный запасной вариант
    except httpx.RequestError as e:
        logger.error(f"Grok API supportive message request failed for user {user_id}: {e}")
        return random.choice(fallback_texts)
    # --- Конец изменений ошибок httpx ---
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API supportive message response for user {user_id}: {e}")
        return random.choice(fallback_texts)
    except Exception as e:
        logger.exception(f"An unexpected error occurred in get_grok_supportive_message for user {user_id}: {e}")
        return random.choice(fallback_texts)


# --- Построение профиля пользователя (ДОРАБОТАННОЕ) ---
async def build_user_profile(user_id, db):
    """
    Строит или обновляет профиль пользователя.
    Теперь включает initial_resource, final_resource, recharge_method.
    """
    profile_data = db.get_user_profile(user_id) # Получаем профиль из БД (может быть None)
    now = datetime.now(TIMEZONE)

    # Проверка кэша (обновление раз в 30 минут)
    cache_ttl = 1800 # 30 минут
    if profile_data and isinstance(profile_data.get("last_updated"), datetime):
        last_updated_dt = profile_data["last_updated"].astimezone(TIMEZONE)
        if (now - last_updated_dt).total_seconds() < cache_ttl:
            logger.info(f"Using cached profile for user {user_id}, updated at {last_updated_dt}")
            # Гарантируем наличие всех ключей при возврате кэша
            profile_data.setdefault("mood", "unknown")
            profile_data.setdefault("mood_trend", [])
            profile_data.setdefault("themes", ["не определено"])
            profile_data.setdefault("response_count", 0)
            profile_data.setdefault("request_count", 0)
            profile_data.setdefault("avg_response_length", 0)
            profile_data.setdefault("days_active", 0)
            profile_data.setdefault("interactions_per_day", 0)
            profile_data.setdefault("initial_resource", None) # << НОВОЕ
            profile_data.setdefault("final_resource", None)   # << НОВОЕ
            profile_data.setdefault("recharge_method", None) # << НОВОЕ
            return profile_data # Возвращаем кэш

    # Если кэш устарел или профиля нет, перестраиваем
    logger.info(f"Rebuilding profile for user {user_id} (Cache expired or profile missing/invalid)")
    base_profile_data = profile_data if profile_data else {"user_id": user_id} # Используем старый профиль как основу или создаем новый

    actions = db.get_actions(user_id) # Получаем логи действий

    # --- Извлечение данных из логов ---
    requests_texts = []
    responses = []
    mood_trend_responses = []
    timestamps = []
    # << НОВОЕ: Инициализируем значениями из существующего профиля или None
    last_initial_resource = base_profile_data.get("initial_resource")
    last_final_resource = base_profile_data.get("final_resource")
    last_recharge_method = base_profile_data.get("recharge_method")

    for action in actions:
        details = action.get("details", {})
        action_type = action.get("action", "")

        # Запросы
        if action_type == "request_text_provided" and "request" in details:
             requests_texts.append(details["request"])
        # Старый формат (на всякий случай)
        elif action_type == "card_drawn_with_request" and "request" in details:
             requests_texts.append(details["request"])

        # Ответы (из нового флоу и старого)
        relevant_response_actions = [
            "initial_response_provided", "grok_response_provided", # Новый флоу
            "initial_response", "first_grok_response", # Старый флоу (если есть)
            "second_grok_response", "third_grok_response"
        ]
        if action_type in relevant_response_actions and "response" in details:
            responses.append(details["response"])
            mood_trend_responses.append(details["response"]) # Для тренда настроения

        # << НОВОЕ: Извлечение ресурсов и метода восстановления из логов
        if action_type == "initial_resource_selected" and "resource" in details:
             last_initial_resource = details["resource"] # Обновляем последним значением
        if action_type == "final_resource_selected" and "resource" in details:
             last_final_resource = details["resource"]
        if action_type == "recharge_method_provided" and "recharge_method" in details:
             last_recharge_method = details["recharge_method"]

        # Временные метки
        try:
            # <<< НАЧАЛО ИЗМЕНЕНИЯ >>>
            raw_timestamp = action.get("timestamp") # Получаем значение
            ts = None # Инициализируем ts

            if isinstance(raw_timestamp, datetime):
                # Если это уже datetime, используем его и добавляем таймзону, если она aware
                ts = raw_timestamp.astimezone(TIMEZONE) if raw_timestamp.tzinfo else TIMEZONE.localize(raw_timestamp) # Используем TIMEZONE
            elif isinstance(raw_timestamp, str):
                # Если это строка, парсим
                ts = datetime.fromisoformat(raw_timestamp.replace('Z', '+00:00')).astimezone(TIMEZONE)
            else:
                logger.warning(f"Skipping action due to invalid timestamp type: {type(raw_timestamp)} in action: {action.get('action')}")
                continue # Пропускаем это действие, если время некорректное

            if ts: # Добавляем в список, только если успешно обработали
                timestamps.append(ts)
            # <<< КОНЕЦ ИЗМЕНЕНИЯ >>>

        except (ValueError, TypeError) as e:
             # Этот блок теперь будет ловить ошибки только при парсинге строки (fromisoformat)
             logger.warning(f"Could not parse timestamp string {action.get('timestamp')} for user {user_id}, action {action.get('action')}, error: {e}")
             continue

    # --- Расчет метрик ---
    if not actions and not base_profile_data.get("last_updated"): # Если нет ни действий, ни существующего профиля
        logger.info(f"No actions or existing profile data for user {user_id}. Creating empty profile.")
        empty_profile = {
            "user_id": user_id, "mood": "unknown", "mood_trend": [], "themes": ["не определено"],
            "response_count": 0, "request_count": 0, "avg_response_length": 0,
            "days_active": 0, "interactions_per_day": 0,
            "initial_resource": None, "final_resource": None, "recharge_method": None,
            "last_updated": now
        }
        db.update_user_profile(user_id, empty_profile)
        return empty_profile

    # Расчеты на основе собранных данных
    all_responses_text = " ".join(responses)
    all_requests_text = " ".join(requests_texts)
    full_text = all_requests_text + " " + all_responses_text

    # Настроение (по последним 5 ответам или последнему ответу)
    mood_source_texts = mood_trend_responses[-5:] # Берем до 5 последних ответов
    mood = "unknown"
    if mood_source_texts:
        # Анализируем самый последний ответ для текущего настроения
        mood = analyze_mood(mood_source_texts[-1])
    elif base_profile_data: # Если ответов нет, берем старое значение
        mood = base_profile_data.get("mood", "unknown")

    # Темы (по всему тексту или старые)
    themes = extract_themes(full_text) if full_text.strip() else base_profile_data.get("themes", ["не определено"])

    response_count = len(responses)
    request_count = len(requests_texts) # Считаем только запросы, введенные текстом
    avg_response_length = sum(len(r) for r in responses) / response_count if response_count > 0 else 0

    # Активность
    days_active = 0
    interactions_per_day = 0
    if timestamps:
        first_interaction = min(timestamps)
        last_interaction = max(timestamps)
        days_active = (last_interaction.date() - first_interaction.date()).days + 1
        # Считаем все действия для общего показателя активности
        interactions_per_day = len(actions) / days_active if days_active > 0 else len(actions)
    elif base_profile_data: # Если нет временных меток, берем старые значения
        days_active = base_profile_data.get("days_active", 0)
        interactions_per_day = base_profile_data.get("interactions_per_day", 0)


    # Тренд настроения по последним 5 ответам
    mood_trend = [analyze_mood(resp) for resp in mood_source_texts]

    # --- Собираем и сохраняем обновленный профиль ---
    updated_profile = {
        "user_id": user_id,
        "mood": mood,
        "mood_trend": mood_trend,
        "themes": themes,
        "response_count": response_count,
        "request_count": request_count,
        "avg_response_length": round(avg_response_length, 2),
        "days_active": days_active,
        "interactions_per_day": round(interactions_per_day, 2),
        "initial_resource": last_initial_resource,   # << НОВОЕ
        "final_resource": last_final_resource,       # << НОВОЕ
        "recharge_method": last_recharge_method,     # << НОВОЕ
        "last_updated": now # Новое время обновления
    }

    db.update_user_profile(user_id, updated_profile) # Сохраняем обновленный профиль в БД
    logger.info(f"Profile updated for user {user_id}.")
    # logger.debug(f"Updated profile data for {user_id}: {updated_profile}")

    return updated_profile
