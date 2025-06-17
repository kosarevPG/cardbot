# код/ai_service.py

import httpx
import json
import random
import asyncio # <-- Добавлен импорт asyncio
from config import GROK_API_KEY, GROK_API_URL, TIMEZONE
from datetime import datetime, date # Убедимся что date импортирован
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

# --- ПЕРЕМЕЩЕНО ВВЕРХ: Анализ текста ---
def analyze_mood(text):
    """Анализирует настроение в тексте по ключевым словам."""
    if not isinstance(text, str): # Добавим проверку типа на всякий случай
        logger.warning(f"analyze_mood received non-string input: {type(text)}. Returning 'unknown'.")
        return "unknown"
    text = text.lower()
    # Расширенные списки ключевых слов для лучшего распознавания
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
        "нормально", "обычно", "никак", "спокойно", "ровно", "задумался", "интересно", # интересно может быть и нейтральным
        "размышляю", "средне", "так себе", "не изменилось", "нейтрально", "понятно",
        "запрос", "тема", "мысли", "воспоминания", "чувства", "образы" # Общие слова рефлексии
    ]

    # Приоритет негативных, затем позитивных, затем нейтральных
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
        "отношения": [
            "отношения", "любовь", "партнёр", "муж", "жена", "парень", "девушка",
            "семья", "близкие", "друзья", "общение", "конфликт", "расставание",
            "свидание", "ссора", "развод", "одиночество", "связь", "поддержка", "понимание"
        ],
        "работа/карьера": [
            "работа", "карьера", "проект", "коллеги", "начальник", "бизнес", "задачи",
            "профессия", "успех", "деньги", "финансы", "должность", "задача", "нагрузка",
            "увольнение", "зарплата", "занятость", "нагрузка", "офис", "признание", "коллектив"
        ],
        "саморазвитие/цели": [
            "развитие", "цель", "мечта", "рост", "обучение", "поиск себя", "смысл", "книга",
            "предназначение", "планы", "достижения", "мотивация", "духовность", "желания",
            "самооценка", "уверенность", "призвание", "реализация", "ценности", "потенциал"
        ],
        "здоровье/состояние": [
            "здоровье", "состояние", "энергия", "болезнь", "усталость", "самочувствие", "сон",
            "тело", "спорт", "питание", "сон", "отдых", "ресурс", "наполненность", "упадок",
            "выгорание", "сила", "слабость", "бодрость", "расслабление", "баланс", "телесное"
        ],
        "эмоции/чувства": [
            "чувствую", "эмоции", "ощущения", "настроение", "страх", "радость", "тепло",
            "грусть", "злость", "тревога", "счастье", "переживания", "вина", "весна",
            "стыд", "обида", "гнев", "любовь", "интерес", "апатия", "спокойствие", "вдохновение"
        ],
        "творчество/хобби": [
            "творчество", "хобби", "увлечение", "искусство", "музыка", "рисование", "цветы",
            "создание", "вдохновение", "креатив", "рукоделие", "природа", "солнце", "красота"
        ],
        "быт/рутина": [
            "дом", "быт", "рутина", "повседневность", "дела", "организация", "время",
            "порядок", "уборка", "ремонт", "переезд", "планирование"
        ]
    }
    found_themes = set()
    text_lower = text.lower()
    # Используем регулярное выражение для поиска слов (более надежно)
    words = set(re.findall(r'\b[а-яё]{3,}\b', text_lower)) # Находим русские слова от 3 букв

    for theme, keywords in themes.items():
        # Проверяем вхождение ключевых слов/фраз ИЛИ отдельных слов из текста в список темы
        if any(keyword in text_lower for keyword in keywords) or any(word in keywords for word in words):
             found_themes.add(theme)

    # Дополнительная проверка по настроению, если темы не найдены
    if not found_themes:
        mood = analyze_mood(text_lower) # Вызываем функцию, которая теперь определена выше
        if mood in ["positive", "negative", "neutral"]:
            found_themes.add("эмоции/чувства")

    return list(found_themes) if found_themes else ["не определено"]
# --- КОНЕЦ ПЕРЕМЕЩЕННОГО БЛОКА ---


# --- Генерация вопросов Grok ---
async def get_grok_question(user_id, user_request, user_response, feedback_type, step=1, previous_responses=None, db: Database = None):
    """
    Генерирует углубляющий вопрос от Grok с механизмом повторных попыток.
    Учитывает профиль пользователя, включая начальный ресурс.
    """
    if db is None:
        logger.error("Database object 'db' is required for get_grok_question")
        universal_questions = {
            1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту?",
            2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?",
            3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"
        }
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум?')}"
        return fallback_question

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    profile = await build_user_profile(user_id, db)

    # --- Добавляем значения по умолчанию ---
    profile_themes = profile.get("themes", []) if profile.get("themes") is not None else ["не определено"] # Исправлено: проверяем не None
    profile_mood_trend_list = profile.get("mood_trend", []) if profile.get("mood_trend") is not None else [] # Исправлено: проверяем не None
    profile_mood_trend = " -> ".join(profile_mood_trend_list) if profile_mood_trend_list else "нет данных"
    avg_resp_len = profile.get("avg_response_length", 50.0) if profile.get("avg_response_length") is not None else 50.0 # Исправлено: проверяем не None
    initial_resource = profile.get("initial_resource", "неизвестно") if profile.get("initial_resource") is not None else "неизвестно" # Исправлено: проверяем не None
    # --- КОНЕЦ Добавления значений по умолчанию ---


    current_mood = analyze_mood(user_response)

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
        "model": "grok-3-fast",
        "max_tokens": 100,
        "stream": False,
        "temperature": 0.5
    }

    universal_questions = {
        1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту?",
        2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?",
        3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"
    }

    # --- НАЧАЛО БЛОКА ПОВТОРНЫХ ПОПЫТОК ---
    max_retries = 3
    base_delay = 1.0 # Секунды для первой задержки
    final_question = None # Переменная для хранения результата

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                logger.info(f"Sending Q{step} request to Grok API for user {user_id} (Attempt {attempt + 1})")
                response = await client.post(GROK_API_URL, headers=headers, json=payload)
                response.raise_for_status() # Проверяем ошибки 4xx/5xx
                data = response.json()
                logger.info(f"Received Q{step} response from Grok API for user {user_id}.")

            if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
                 raise ValueError("Invalid response structure from Grok API (choices or content missing)")

            question_text = data["choices"][0]["message"]["content"].strip()
            # Очистка question_text от префиксов и кавычек
            question_text = re.sub(r'^(Хорошо|Вот ваш вопрос|Конечно|Отлично|Понятно)[,.:]?\s*', '', question_text, flags=re.IGNORECASE).strip()
            question_text = re.sub(r'^"|"$', '', question_text).strip()
            question_text = re.sub(r'^Вопрос\s*\d/\d[:.]?\s*', '', question_text).strip()

            if not question_text or len(question_text) < 5:
                 raise ValueError("Empty or too short question content after cleaning")

            # Проверка на повторение вопроса
            if previous_responses:
                prev_q_texts = []
                if previous_responses.get('grok_question_1'): prev_q_texts.append(previous_responses['grok_question_1'].split(':')[-1].strip().lower())
                if previous_responses.get('grok_question_2'): prev_q_texts.append(previous_responses['grok_question_2'].split(':')[-1].strip().lower())
                if question_text.lower() in prev_q_texts:
                    logger.warning(f"Grok generated a repeated question for step {step}, user {user_id}. Question: '{question_text}'. Using fallback.")
                    raise ValueError("Repeated question generated")

            final_question = f"Вопрос ({step}/3): {question_text}"
            break # <-- Успешно, выходим из цикла повторов

        except httpx.TimeoutException:
            logger.warning(f"Grok API request Q{step} timed out for user {user_id} (Attempt {attempt + 1})")
            if attempt == max_retries - 1: # Если последняя попытка
                final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум, когда ты смотришь на эту карту?')}"
        except httpx.HTTPStatusError as e:
             # Повторяем при 403, 429 (Too Many Requests) или 5xx (Server Error)
             if e.response.status_code in [403, 429] or e.response.status_code >= 500:
                 logger.warning(f"Grok API returned {e.response.status_code} for Q{step} (User: {user_id}, Attempt: {attempt + 1}). Retrying...")
                 if attempt == max_retries - 1: # Если последняя попытка
                     final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Какие детали карты привлекают твоё внимание больше всего?')}"
             else: # Другие ошибки 4xx не повторяем
                 logger.error(f"Grok API request Q{step} failed with unrecoverable status {e.response.status_code} for user {user_id}: {e}")
                 final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Как твои ощущения изменились за время размышления над картой?')}"
                 break # Выходим из цикла при невосстановимой ошибке
        except (ValueError, KeyError, IndexError) as e: # Добавлена обработка ValueError на случай генерации повторного вопроса
            logger.error(f"Failed to parse Grok API response Q{step} or invalid data/repeat for user {user_id}: {e}")
            final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Как твои ощущения изменились за время размышления над картой?')}"
            break # Выходим из цикла
        except Exception as e:
            # Логируем ЛЮБУЮ другую неожиданную ошибку
            logger.exception(f"An unexpected error occurred in get_grok_question Q{step} for user {user_id} during attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1: # Если последняя попытка
                final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Попробуй описать свои мысли одним словом. Что это за слово?')}"
            # Не выходим из цикла здесь, даем сработать задержке и следующей попытке

        # Если нужно повторить, ждем перед следующей попыткой
        if attempt < max_retries - 1 and final_question is None: # Убедимся что не вышли из цикла и результат еще не установлен
            delay = base_delay * (2 ** attempt) # Экспоненциальная задержка
            logger.info(f"Waiting {delay:.1f}s before retrying Grok request Q{step}...")
            await asyncio.sleep(delay)
        elif final_question is None: # Если это была последняя попытка и final_question все еще не установлен (например, после unexpected error)
             logger.error(f"Grok API request Q{step} failed after {max_retries} attempts for user {user_id}.")
             # Установим fallback здесь на всякий случай, если он не был установлен в блоках except
             final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Как бы ты описала свои чувства сейчас?')}"

    # --- КОНЕЦ БЛОКА ПОВТОРНЫХ ПОПЫТОК ---

    # Гарантируем, что final_question не None перед возвратом
    if final_question is None:
        logger.error(f"Critical logic error: final_question is None after retry loop for Q{step}, user {user_id}. Returning default fallback.")
        final_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что еще важно для тебя в этой ситуации?')}"

    return final_question


# --- Генерация саммари карты дня ---
async def get_grok_summary(user_id, interaction_data, db: Database = None):
    """
    Генерирует краткое резюме сессии с картой с механизмом повторных попыток.
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
        "model": "grok-3-fast",
        "max_tokens": 180,
        "stream": False,
        "temperature": 0.4
    }

    # --- Блок повторных попыток ---
    max_retries = 3
    base_delay = 1.0
    summary_text = None
    fallback_summary = "Не получилось сформулировать итог сессии. Главное — те мысли и чувства, которые возникли у тебя." # Определяем fallback здесь

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                logger.info(f"Sending SUMMARY request to Grok API for user {user_id} (Attempt {attempt + 1})")
                response = await client.post(GROK_API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Received SUMMARY response from Grok API for user {user_id}.")

            if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
                 raise ValueError("Invalid response structure for summary from Grok API")

            summary_text_raw = data["choices"][0]["message"]["content"].strip()
            # Очистка текста резюме
            summary_text_raw = re.sub(r'^(Хорошо|Вот резюме|Конечно|Отлично|Итог|Итак)[,.:]?\s*', '', summary_text_raw, flags=re.IGNORECASE).strip()
            summary_text_raw = re.sub(r'^"|"$', '', summary_text_raw).strip()

            if not summary_text_raw or len(summary_text_raw) < 10:
                 raise ValueError("Empty or too short summary content after cleaning")

            summary_text = summary_text_raw
            break # Успешно, выходим

        except httpx.TimeoutException:
            logger.warning(f"Grok API summary request timed out for user {user_id} (Attempt {attempt + 1})")
            if attempt == max_retries - 1:
                summary_text = "К сожалению, не удалось сгенерировать резюме сессии (таймаут). Но твои размышления очень ценны!"
        except httpx.HTTPStatusError as e:
             if e.response.status_code in [403, 429] or e.response.status_code >= 500:
                 logger.warning(f"Grok API returned {e.response.status_code} for SUMMARY (User: {user_id}, Attempt: {attempt + 1}). Retrying...")
                 if attempt == max_retries - 1:
                     summary_text = "К сожалению, не удалось сгенерировать резюме сессии из-за временной ошибки сервера. Но твои размышления очень ценны!"
             else:
                 logger.error(f"Grok API summary request failed with unrecoverable status {e.response.status_code} for user {user_id}: {e}")
                 summary_text = fallback_summary # Используем fallback для невосстановимых ошибок
                 break
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse Grok API summary response or invalid data for user {user_id}: {e}")
            summary_text = fallback_summary
            break
        except Exception as e:
            logger.exception(f"An unexpected error occurred in get_grok_summary for user {user_id} during attempt {attempt+1}: {e}")
            if attempt == max_retries - 1:
                summary_text = "Произошла неожиданная ошибка при подведении итогов. Пожалуйста, попробуй позже."
            # Не выходим из цикла, даем сработать задержке

        # Задержка перед следующей попыткой, если нужно
        if attempt < max_retries - 1 and summary_text is None:
            delay = base_delay * (2 ** attempt)
            logger.info(f"Waiting {delay:.1f}s before retrying Grok SUMMARY request...")
            await asyncio.sleep(delay)
        elif summary_text is None: # Если последняя попытка и все еще None
            logger.error(f"Grok API summary request failed after {max_retries} attempts for user {user_id}.")
            if summary_text is None: # Убедимся, что fallback установлен
                 summary_text = fallback_summary


    # Гарантируем возврат строки
    return summary_text if summary_text is not None else fallback_summary


# --- Поддержка при низком ресурсе ---
async def get_grok_supportive_message(user_id, db: Database = None):
    """
    Генерирует поддерживающее сообщение и вопрос о способе восстановления
    для пользователя с низким уровнем ресурса после сессии, с механизмом повторных попыток.
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

    system_prompt = (
        f"Ты — очень тёплый, эмпатичный и заботливый друг-помощник. Твоя задача — поддержать пользователя ({name}), который сообщил о низком уровне внутреннего ресурса (😔) после работы с метафорической картой. "
        "Напиши короткое (2-3 предложения), искреннее и ободряющее сообщение. "
        "Признай его чувства ('Слышу тебя...', 'Мне жаль, что сейчас так...', 'Понимаю, это непросто...'), напомни о его ценности и силе. "
        "Избегай банальностей ('все будет хорошо') и ложного позитива. "
        "Не давай советов, кроме мягкого напоминания о заботе о себе. "
        "Тон должен быть мягким, принимающим и обнимающим."
        f" Основные темы, которые волнуют пользователя: {', '.join(profile_themes)}. "
    )

    user_prompt = f"Пользователь {name} сообщил, что его ресурсное состояние сейчас низкое (😔). Напиши для него короткое поддерживающее сообщение."

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-fast",
        "max_tokens": 120,
        "stream": False,
        "temperature": 0.6
    }

    question_about_recharge = "\n\nПоделись, пожалуйста, что обычно помогает тебе восстановить силы и позаботиться о себе в такие моменты?"

    fallback_texts = [
        f"Мне очень жаль, что ты сейчас так себя чувствуешь... Пожалуйста, будь к себе особенно бережен(на). ✨{question_about_recharge}",
        f"Очень сочувствую твоему состоянию... Помни, что любые чувства важны и имеют право быть. Позаботься о себе. 🙏{question_about_recharge}",
        f"Слышу тебя... Иногда бывает тяжело. Помни, ты не один(на) в своих переживаниях. ❤️{question_about_recharge}",
        f"Мне жаль, что тебе сейчас нелегко... Пожалуйста, найди минутку для себя, сделай что-то приятное. ☕️{question_about_recharge}"
    ]

    # --- НАЧАЛО БЛОКА ПОВТОРНЫХ ПОПЫТОК ---
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
                logger.info(f"Received SUPPORTIVE response from Grok API for user {user_id}.")

            if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
                 raise ValueError("Invalid response structure for supportive message from Grok API")

            support_text = data["choices"][0]["message"]["content"].strip()
            # Очистка текста
            support_text = re.sub(r'^(Хорошо|Вот сообщение|Конечно|Понятно)[,.:]?\s*', '', support_text, flags=re.IGNORECASE).strip()
            support_text = re.sub(r'^"|"$', '', support_text).strip()

            if not support_text or len(support_text) < 10:
                 raise ValueError("Empty or too short support message content after cleaning")

            final_message = support_text + question_about_recharge
            break # Успешно

        except httpx.TimeoutException:
            logger.warning(f"Grok API supportive message request timed out for user {user_id} (Attempt {attempt + 1})")
            if attempt == max_retries - 1:
                 final_message = random.choice(fallback_texts)
        except httpx.HTTPStatusError as e:
             if e.response.status_code in [403, 429] or e.response.status_code >= 500:
                 logger.warning(f"Grok API returned {e.response.status_code} for SUPPORTIVE (User: {user_id}, Attempt: {attempt + 1}). Retrying...")
                 if attempt == max_retries - 1:
                     final_message = random.choice(fallback_texts)
             else:
                 logger.error(f"Grok API supportive message request failed with unrecoverable status {e.response.status_code} for user {user_id}: {e}")
                 final_message = random.choice(fallback_texts)
                 break
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse Grok API supportive message response for user {user_id}: {e}")
            final_message = random.choice(fallback_texts)
            break
        except Exception as e:
            logger.exception(f"An unexpected error occurred in get_grok_supportive_message for user {user_id} during attempt {attempt+1}: {e}")
            if attempt == max_retries - 1:
                final_message = random.choice(fallback_texts)
            # Не выходим, даем сработать задержке

        # Задержка перед следующей попыткой
        if attempt < max_retries - 1 and final_message is None:
            delay = base_delay * (2 ** attempt)
            logger.info(f"Waiting {delay:.1f}s before retrying Grok SUPPORTIVE request...")
            await asyncio.sleep(delay)
        elif final_message is None: # Последняя попытка не удалась
            logger.error(f"Grok API supportive message request failed after {max_retries} attempts for user {user_id}.")
            if final_message is None: # Устанавливаем fallback, если не был установлен
                 final_message = random.choice(fallback_texts)

    # --- КОНЕЦ БЛОКА ПОВТОРНЫХ ПОПЫТОК ---

    return final_message if final_message is not None else random.choice(fallback_texts)


# --- Построение профиля пользователя (ОБНОВЛЕНО) ---
async def build_user_profile(user_id, db: Database):
    # ... (код функции без изменений) ...
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
            profile_data.setdefault("days_active", 0)
            profile_data.setdefault("initial_resource", None)
            profile_data.setdefault("final_resource", None)
            profile_data.setdefault("recharge_method", None) # Последний метод
            profile_data.setdefault("total_cards_drawn", 0) # Новая метрика
            profile_data.setdefault("last_reflection_date", None) # Новая метрика
            profile_data.setdefault("reflection_count", 0) # Новая метрика
            profile_data.setdefault("request_count", None)
            profile_data.setdefault("avg_response_length", None)
            profile_data.setdefault("interactions_per_day", None)
            return profile_data

    logger.info(f"Rebuilding profile for user {user_id} (Cache expired or profile missing/invalid)")
    base_profile_data = profile_data if profile_data else {"user_id": user_id}

    # --- Получаем данные из БД ---
    actions = db.get_actions(user_id)
    reflection_texts_list = db.get_all_reflection_texts(user_id)
    last_recharge_method = db.get_last_recharge_method(user_id)
    last_reflection_date_obj = db.get_last_reflection_date(user_id) # Теперь должен быть date или None
    reflection_count = db.count_reflections(user_id)
    total_cards_drawn = db.count_user_cards(user_id)

    # --- Извлечение данных из логов действий ---
    responses = []
    mood_trend_responses = []
    timestamps = []
    last_initial_resource = base_profile_data.get("initial_resource")
    last_final_resource = base_profile_data.get("final_resource")

    for action in actions:
        details = action.get("details", {})
        action_type = action.get("action", "")

        # Ответы
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

        # Ресурсы
        if action_type == "initial_resource_selected" and "resource" in details:
             last_initial_resource = details["resource"]
        if action_type == "final_resource_selected" and "resource" in details:
             last_final_resource = details["resource"]

        # Временные метки
        raw_timestamp = action.get("timestamp")
        if isinstance(raw_timestamp, str):
            try:
                # Пытаемся распарсить с учетом 'Z' или без
                if raw_timestamp.endswith('Z'):
                    dt_naive = datetime.fromisoformat(raw_timestamp[:-1])
                    dt_aware = pytz.utc.localize(dt_naive) if pytz else dt_naive.replace(tzinfo=datetime.timezone.utc) # Используем pytz если есть
                elif '+' in raw_timestamp:
                    dt_aware = datetime.fromisoformat(raw_timestamp)
                else: # Если формат без смещения (предполагаем UTC или локальное?) - безопаснее считать UTC
                    dt_naive = datetime.fromisoformat(raw_timestamp)
                    dt_aware = pytz.utc.localize(dt_naive) if pytz else dt_naive.replace(tzinfo=datetime.timezone.utc)

                ts = dt_aware.astimezone(TIMEZONE) if pytz else dt_aware # Конвертируем в TIMEZONE если pytz есть
                timestamps.append(ts)
            except ValueError as e:
                logger.warning(f"Could not parse ISO timestamp string '{raw_timestamp}' for user {user_id}, action '{action.get('action')}': {e}")
            except Exception as e:
                 logger.warning(f"Error converting timestamp '{raw_timestamp}' for user {user_id}, action '{action.get('action')}': {e}")
        elif isinstance(raw_timestamp, datetime):
             try:
                 ts = raw_timestamp.astimezone(TIMEZONE) if raw_timestamp.tzinfo and pytz else (TIMEZONE.localize(raw_timestamp) if pytz and not raw_timestamp.tzinfo else raw_timestamp) # Добавлена проверка на наивность перед localize
                 timestamps.append(ts)
             except Exception as e:
                 logger.warning(f"Error converting datetime timestamp '{raw_timestamp}' for user {user_id}, action '{action.get('action')}': {e}")
        else:
             logger.warning(f"Skipping action due to invalid timestamp type: {type(raw_timestamp)} in action: {action.get('action')}")


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
    reflection_full_text = " ".join(
        filter(None, [item.get(key) for item in reflection_texts_list for key in ['good_moments', 'gratitude', 'hard_moments']])
    )
    full_text = all_responses_text + " " + reflection_full_text

    # Настроение
    mood_source_texts = mood_trend_responses[-5:]
    mood = "unknown"
    if mood_source_texts:
        mood = analyze_mood(mood_source_texts[-1])
    elif base_profile_data:
        mood = base_profile_data.get("mood", "unknown")

    # Темы
    themes = extract_themes(full_text) if full_text.strip() else base_profile_data.get("themes", ["не определено"])

    response_count = len(responses)

    # Активность
    days_active = 0
    if timestamps:
        unique_dates = {ts.date() for ts in timestamps}
        if unique_dates:
             first_interaction_date = min(unique_dates)
             # Убедимся что дата now тоже date()
             days_active = (now.date() - first_interaction_date).days + 1
    elif base_profile_data:
        days_active = base_profile_data.get("days_active", 0)


    # Тренд настроения
    mood_trend = [analyze_mood(resp) for resp in mood_source_texts]

    # Форматируем дату рефлексии
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


    # Собираем и сохраняем обновленный профиль
    updated_profile = {
        "user_id": user_id,
        "mood": mood,
        "mood_trend": mood_trend,
        "themes": themes,
        "response_count": response_count,
        "days_active": days_active,
        "initial_resource": last_initial_resource,
        "final_resource": last_final_resource,
        "recharge_method": last_recharge_method,
        "total_cards_drawn": total_cards_drawn,
        "last_reflection_date": last_reflection_date_str, # Сохраняем строку
        "reflection_count": reflection_count,
        "last_updated": now
    }

    db.update_user_profile(user_id, updated_profile)
    logger.info(f"Profile rebuilt and updated for user {user_id}.")

    return updated_profile


# --- Резюме для Вечерней Рефлексии ---
async def get_reflection_summary(user_id: int, reflection_data: dict, db: Database) -> str | None:
    """
    Генерирует AI-резюме для вечерней рефлексии с механизмом повторных попыток.
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
        "model": "grok-3-fast",
        "max_tokens": 150,
        "stream": False,
        "temperature": 0.5
    }

    fallback_summary = "Спасибо, что поделилась своими мыслями и чувствами. Важно замечать разное в своем дне."

    # --- Используем блок с повторными попытками ---
    max_retries = 3
    base_delay = 1.0 # Секунды
    summary_text = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                logger.info(f"Sending REFLECTION SUMMARY request to Grok API for user {user_id} (Attempt {attempt + 1})")
                response = await client.post(GROK_API_URL, headers=headers, json=payload)
                response.raise_for_status() # Проверяем ошибки 4xx/5xx
                data = response.json()
                logger.info(f"Received REFLECTION SUMMARY response from Grok API for user {user_id}.")

            if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
                 raise ValueError("Invalid response structure for reflection summary from Grok API")

            summary_text_raw = data["choices"][0]["message"]["content"].strip()
            summary_text_raw = re.sub(r'^(Хорошо|Вот резюме|Конечно|Отлично|Итог|Итак)[,.:]?\s*', '', summary_text_raw, flags=re.IGNORECASE).strip()
            summary_text_raw = re.sub(r'^"|"$', '', summary_text_raw).strip()

            if not summary_text_raw or len(summary_text_raw) < 10:
                 raise ValueError("Empty or too short reflection summary content after cleaning")

            summary_text = summary_text_raw # Сохраняем успешный результат
            break # Выходим из цикла, если успешно

        except httpx.TimeoutException:
            logger.warning(f"Grok API reflection summary request timed out for user {user_id} (Attempt {attempt + 1})")
            if attempt == max_retries - 1:
                summary_text = "К сожалению, не удалось сгенерировать резюме дня (таймаут)." # Обновлен fallback
        except httpx.HTTPStatusError as e:
             # Повторяем только при 403, 429 или 5xx
             if e.response.status_code in [403, 429] or e.response.status_code >= 500:
                 logger.warning(f"Grok API returned {e.response.status_code} for reflection summary (User: {user_id}, Attempt: {attempt + 1}). Retrying...")
                 if attempt == max_retries - 1: # Если последняя попытка
                     summary_text = "К сожалению, не удалось сгенерировать резюме дня из-за временной ошибки сервера." # Обновлен fallback
             else: # Другие ошибки 4xx/5xx не повторяем
                 logger.error(f"Grok API reflection summary request failed with status {e.response.status_code} for user {user_id}: {e}")
                 summary_text = fallback_summary # Используем запасной текст
                 break # Выходим из цикла при невосстановимой ошибке
        except (ValueError, KeyError, IndexError) as e:
            logger.error(f"Failed to parse Grok API reflection summary response for user {user_id}: {e}")
            summary_text = fallback_summary
            break
        except Exception as e:
            logger.exception(f"An unexpected error occurred in get_reflection_summary for user {user_id} during attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                summary_text = "Произошла неожиданная ошибка при генерации резюме дня." # Обновлен fallback
            # Не выходим, даем сработать задержке

        # Если не вышли из цикла (т.е. была ошибка для повтора), ждем перед следующей попыткой
        if attempt < max_retries - 1 and summary_text is None:
            delay = base_delay * (2 ** attempt) # Экспоненциальная задержка
            logger.info(f"Waiting {delay:.1f}s before retrying Grok REFLECTION SUMMARY request...")
            await asyncio.sleep(delay)
        elif summary_text is None: # Если это была последняя попытка и все еще None
             logger.error(f"Grok API reflection summary request failed after {max_retries} attempts for user {user_id}.")
             if summary_text is None: # Если не установили fallback при других ошибках
                 summary_text = fallback_summary


    # Гарантируем возврат строки
    return summary_text if summary_text is not None else fallback_summary


# --- КОНЕЦ ФАЙЛА ---
