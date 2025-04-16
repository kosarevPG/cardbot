# код/ai_service.py

import requests
import json
from config import GROK_API_KEY, GROK_API_URL, TIMEZONE
from datetime import datetime, timedelta
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Анализ текста (без изменений) ---
def analyze_mood(text):
    """Анализирует настроение в тексте по ключевым словам."""
    text = text.lower()
    positive_keywords = ["хорошо", "рад", "счастлив", "здорово", "круто", "отлично", "прекрасно", "вдохновлен", "доволен", "спокоен", "уверен", "лучше", "полегче", "спокойнее", "ресурсно"]
    negative_keywords = ["плохо", "грустно", "тревож", "страх", "боюсь", "злюсь", "устал", "раздражен", "обижен", "разочарован", "одиноко", "негатив", "тяжело", "сложно", "низко", "не очень", "хуже", "обессилен"]
    neutral_keywords = ["нормально", "обычно", "никак", "спокойно", "ровно", "задумался", "размышляю", "средне", "так себе", "не изменилось"] [cite: 9]

    # Приоритет негативных, затем позитивных, затем нейтральных
    if any(keyword in text for keyword in negative_keywords): return "negative"
    if any(keyword in text for keyword in positive_keywords): return "positive"
    if any(keyword in text for keyword in neutral_keywords): return "neutral"
    return "unknown"

def extract_themes(text):
    """Извлекает основные темы из текста по ключевым словам."""
    themes = {
        "отношения": ["отношения", "любовь", "партнёр", "муж", "жена", "парень", "девушка", "семья", "близкие", "друзья", "общение", "конфликт", "расставание", "свидание", "ссора", "развод"],
        "работа/карьера": ["работа", "карьера", "проект", "коллеги", "начальник", "бизнес", "профессия", "успех", "деньги", "финансы", "должность", "задача", "увольнение", "зарплата", "занятость"], [cite: 10]
        "саморазвитие/цели": ["развитие", "цель", "мечта", "рост", "обучение", "поиск себя", "смысл", "предназначение", "планы", "достижения", "мотивация", "духовность", "самооценка", "уверенность"],
        "здоровье/состояние": ["здоровье", "состояние", "энергия", "болезнь", "усталость", "самочувствие", "тело", "спорт", "питание", "сон", "отдых", "ресурс", "наполненность", "выгорание"],
        "эмоции/чувства": ["чувствую", "эмоции", "ощущения", "настроение", "страх", "радость", "грусть", "злость", "тревога", "счастье", "переживания", "вина", "стыд", "обида"],
        "творчество/хобби": ["творчество", "хобби", "увлечение", "искусство", "музыка", "рисование", "создание", "вдохновение"], [cite: 11]
        "быт/рутина": ["дом", "быт", "рутина", "повседневность", "дела", "организация", "порядок", "уборка"]
    }
    found_themes = set()
    text = text.lower()
    # Добавим обработку коротких фраз для тем
    words = set(re.findall(r'\b\w{3,}\b', text)) # Находим слова от 3 букв
    for theme, keywords in themes.items():
        # Проверяем наличие ключевых слов или отдельных слов из запроса/ответа в списке ключевых слов темы
        if any(keyword in text for keyword in keywords) or any(word in keywords for word in words): [cite: 12]
             found_themes.add(theme)
    return list(found_themes) if found_themes else ["не определено"]

# --- Генерация вопросов Grok (без существенных изменений, кроме логгирования и обработки ошибок) ---
async def get_grok_question(user_id, user_request, user_response, feedback_type, step=1, previous_responses=None, db=None):
    """
    Генерирует углубляющий вопрос от Grok на основе контекста диалога,
    истории, профиля пользователя и его настроения. [cite: 13]
    """
    if db is None:
        logger.error("Database object 'db' is required for get_grok_question")
        # Возвращаем запасной вопрос вместо падения
        universal_questions = {
            1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту?",
            2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?", [cite: 14]
            3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"
        }
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум?')}"
        return fallback_question
        # raise ValueError("Parameter 'db' is required for get_grok_question") # Старый вариант

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    # Получаем профиль пользователя
    profile = await build_user_profile(user_id, db) # Должен возвращать словарь, даже если профиля нет [cite: 15]
    profile_themes = profile.get("themes", ["не определено"])
    profile_mood_trend = " -> ".join(profile.get("mood_trend", [])) or "нет данных"
    avg_resp_len = profile.get("avg_response_length", 50) # Используем среднюю длину ответа

    current_mood = analyze_mood(user_response)

    system_prompt = (
        "Ты — тёплый, мудрый и поддерживающий коуч, работающий с метафорическими ассоциативными картами (МАК). [cite: 16]\n"
        "Твоя главная задача — помочь пользователю глубже понять себя через рефлексию над картой и своими ответами. [cite: 17]\n"
        "Не интерпретируй карту сам, фокусируйся на чувствах, ассоциациях и мыслях пользователя. [cite: 18]\n"
        f"Задай ОДИН открытый, глубокий и приглашающий к размышлению вопрос (15-25 слов). [cite: 19]\n" # Чуть увеличим лимит
        "Вопрос должен побуждать пользователя исследовать причины своих чувств, посмотреть на ситуацию под новым углом или связать увиденное с его жизнью. [cite: 20]\n"
        f"Текущее настроение пользователя по его ответу: {current_mood}. [cite: 21]\n"
        f"Основные темы из его прошлых запросов/ответов: {', '.join(profile_themes)}. [cite: 22]\n"
        f"Тренд настроения (по последним ответам): {profile_mood_trend}. [cite: 23]\n"
        # Улучшенные инструкции по адаптации:
        "Если настроение пользователя 'negative', начни вопрос с эмпатичной фразы ('Понимаю, это может быть непросто...', 'Спасибо, что делишься...', 'Сочувствую, если это отзывается болью...'), затем задай бережный, поддерживающий вопрос, возможно, сфокусированный на ресурсах или маленьких шагах. [cite: 24]\n"
        f"Если пользователь обычно отвечает кратко (средняя длина ответа ~{avg_resp_len:.0f} симв.), задай более конкретный, возможно, закрытый вопрос ('Что именно вызывает это чувство?', 'Какой аспект карты связан с этим?'). [cite: 25]\nЕсли отвечает развернуто - можно задать более открытый ('Как это перекликается с твоим опытом?', 'Что эта ассоциация говорит о твоих потребностях?'). [cite: 26]\n"
        "Постарайся связать вопрос с основными темами пользователя (отношения, работа, саморазвитие и т.д.), если это уместно и естественно вытекает из его ответа. [cite: 27]\n"
        "НЕ используй нумерацию или префиксы вроде 'Вопрос X:' - это будет добавлено позже. [cite: 28]\n"
        "Избегай прямых советов или решений. [cite: 29]\nНе задавай вопросы, на которые пользователь уже ответил.\n"
        "НЕ повторяй вопросы из предыдущих шагов." # Добавлено важное уточнение
    )

    # Формируем пользовательский промпт с контекстом
    actions = db.get_actions(user_id) # Получаем всю историю для лучшего контекста
    # Собираем контекст текущей сессии (используем данные из state, переданные в previous_responses)
    session_context = []
    if user_request: session_context.append(f"Начальный запрос: '{user_request}'")
    # Добавляем предыдущие шаги из previous_responses
    initial_response = previous_responses.get("initial_response") if previous_responses else None
    if initial_response: session_context.append(f"Первая ассоциация на карту: '{initial_response}'") [cite: 30]

    if step > 1 and previous_responses:
        # Используем ключи, как они сохраняются в card_of_the_day.py
        if 'first_grok_question' in previous_responses:
             session_context.append(f"Вопрос ИИ (1/3): '{previous_responses['first_grok_question']}'")
        if 'first_grok_response' in previous_responses: # Имя ответа на первый вопрос
             session_context.append(f"Ответ пользователя 1: '{previous_responses['first_grok_response']}'")
    if step > 2 and previous_responses: [cite: 31]
        if 'second_grok_question' in previous_responses:
             session_context.append(f"Вопрос ИИ (2/3): '{previous_responses['second_grok_question']}'")
        if 'second_grok_response' in previous_responses: # Имя ответа на второй вопрос
             session_context.append(f"Ответ пользователя 2: '{previous_responses['second_grok_response']}'")

    # Текущий ответ пользователя, на который нужен вопрос
    session_context.append(f"ПОСЛЕДНИЙ ответ пользователя (на него нужен вопрос {step}/3): '{user_response}'")

    user_prompt = "Контекст текущей сессии:\n" + "\n".join(session_context)

    payload = { [cite: 32]
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest", # Проверьте актуальность модели
        "max_tokens": 100, # Достаточно для вопроса + эмпатии
        "stream": False,
        "temperature": 0.5 # Немного увеличим вариативность
    } [cite: 33]

    universal_questions = {
        1: "Какие самые сильные чувства или ощущения возникают, глядя на эту карту в контексте твоего запроса?",
        2: "Если бы эта карта могла говорить, какой главный совет она бы дала тебе сейчас?",
        3: "Какой один маленький шаг ты могла бы сделать сегодня, вдохновившись этими размышлениями?"
    }

    try:
        logger.info(f"Sending Q{step} request to Grok API for user {user_id}. Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}") [cite: 34]
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=20) # Увеличен таймаут
        response.raise_for_status()
        data = response.json()
        logger.info(f"Received Q{step} response from Grok API: {json.dumps(data, ensure_ascii=False, indent=2)}")

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
             raise ValueError("Invalid response structure from Grok API (choices or content missing)")

        question_text = data["choices"][0]["message"]["content"].strip() [cite: 35]
        question_text = re.sub(r'^(Хорошо|Вот ваш вопрос|Конечно|Отлично|Понятно)[,.:]?\s*', '', question_text, flags=re.IGNORECASE).strip()
        # Убираем кавычки в начале/конце, если модель их добавляет
        question_text = re.sub(r'^"|"$', '', question_text).strip()
        # Убираем префиксы вопросов, если модель их добавила
        question_text = re.sub(r'^Вопрос\s*\d/\d[:.]?\s*', '', question_text).strip()


        if not question_text or len(question_text) < 5: # Проверка на пустой или слишком короткий вопрос
             raise ValueError("Empty or too short question content after cleaning") [cite: 36]

        # Проверка на повторение предыдущих вопросов (если есть previous_responses)
        if previous_responses:
            prev_q1 = previous_responses.get('first_grok_question','').split(':')[-1].strip()
            prev_q2 = previous_responses.get('second_grok_question','').split(':')[-1].strip()
            if question_text.lower() == prev_q1.lower() or question_text.lower() == prev_q2.lower():
                 logger.warning(f"Grok generated a repeated question for step {step}, user {user_id}. Using fallback.") [cite: 37]
                 raise ValueError("Repeated question generated")


        final_question = f"Вопрос ({step}/3): {question_text}"
        return final_question

    except requests.exceptions.Timeout:
        logger.error(f"Grok API request timed out for user {user_id}, step {step}.")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Что ещё приходит на ум, когда ты смотришь на эту карту?')}"
        return fallback_question
    except requests.exceptions.RequestException as e: [cite: 39]
        logger.error(f"Grok API request failed for user {user_id}, step {step}: {e}")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Какие детали карты привлекают твоё внимание больше всего?')}"
        return fallback_question
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API response or invalid data for user {user_id}, step {step}: {e}")
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Как твои ощущения изменились за время размышления над картой?')}" [cite: 40]
        return fallback_question
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_grok_question for user {user_id}, step {step}: {e}", exc_info=True)
        fallback_question = f"Вопрос ({step}/3): {universal_questions.get(step, 'Попробуй описать свои мысли одним словом. Что это за слово?')}" [cite: 41]
        return fallback_question


# --- Генерация саммари (без существенных изменений) ---
async def get_grok_summary(user_id, interaction_data, db=None):
    """
    Генерирует краткое резюме/инсайт по завершении сессии с картой,
    используя весь контекст взаимодействия. [cite: 42]
    """
    if db is None:
        logger.error("Database object 'db' is required for get_grok_summary")
        return "Ошибка: Не удалось получить доступ к базе данных для генерации резюме."

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    profile = await build_user_profile(user_id, db)
    profile_themes = profile.get("themes", [])

    system_prompt = (
        "Ты — внимательный и проницательный ИИ-помощник. Твоя задача — проанализировать завершенный диалог пользователя с метафорической картой. \n"
         "На основе запроса (если был), ответов пользователя на карту и на уточняющие вопросы, сформулируй краткое (2-4 предложения) резюме или основной инсайт сессии. [cite: 43]\n"
        "Резюме должно отражать ключевые чувства, мысли или возможные направления для дальнейших размышлений пользователя, которые проявились в диалоге. \n"
        "Будь поддерживающим и НЕ давай прямых советов. Фокусируйся на том, что сказал сам пользователь. \n"
        "Можешь мягко подсветить связь с его основными темами, если она явно прослеживается: " + ", ".join(profile_themes) + ".\n"
         "Не используй фразы вроде 'Ваше резюме:', 'Итог:'.\nНачни прямо с сути. [cite: 44] "
        "Избегай общих фраз, старайся быть конкретным по содержанию диалога." [cite: 45]
    )

    # Собираем текст диалога, пропуская пустые вопросы/ответы
    qna_items = []
    if interaction_data.get("initial_response"):
         qna_items.append(f"Первый ответ на карту: {interaction_data['initial_response']}")
    for item in interaction_data.get("qna", []):
        question = item.get('question','').split(':')[-1].strip() # Убираем префикс "Вопрос (X/3):"
        answer = item.get('answer','').strip()
        if question and answer: [cite: 46]
             qna_items.append(f"Вопрос ИИ: {question}\nОтвет: {answer}")

    qna_text = "\n\n".join(qna_items)

    user_prompt = (
        "Проанализируй следующий диалог:\n"
        f"Запрос пользователя: '{interaction_data.get('user_request', 'не указан')}'\n"
        # f"Номер карты: {interaction_data.get('card_number', 'N/A')}\n" # Номер карты может быть не нужен для саммари
        f"Диалог:\n{qna_text}\n\n"
        "Сформулируй краткое резюме или основной инсайт этой сессии (2-4 предложения)."
    ) [cite: 47]

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest",
        "max_tokens": 180, # Немного больше места
        "stream": False,
        "temperature": 0.4 # Чуть выше для более живого резюме [cite: 48]
    }

    try:
        logger.info(f"Sending SUMMARY request to Grok API for user {user_id}. Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}") [cite: 49]
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=25) # Таймаут чуть больше
        response.raise_for_status()
        data = response.json()
        logger.info(f"Received SUMMARY response from Grok API: {json.dumps(data, ensure_ascii=False, indent=2)}")

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"):
             raise ValueError("Invalid response structure for summary from Grok API")

        summary_text = data["choices"][0]["message"]["content"].strip() [cite: 50]
        summary_text = re.sub(r'^(Хорошо|Вот резюме|Конечно|Отлично|Итог|Итак)[,.:]?\s*', '', summary_text, flags=re.IGNORECASE).strip()
        summary_text = re.sub(r'^"|"$', '', summary_text).strip() # Убираем кавычки

        if not summary_text or len(summary_text) < 10:
             raise ValueError("Empty or too short summary content after cleaning")

        return summary_text

    except requests.exceptions.Timeout:
        logger.error(f"Grok API summary request timed out for user {user_id}.")
        return "К сожалению, не удалось сгенерировать резюме сессии (таймаут). [cite: 51] Но твои размышления очень ценны!" [cite: 52]
    except requests.exceptions.RequestException as e:
        logger.error(f"Grok API summary request failed for user {user_id}: {e}")
        return "К сожалению, не удалось сгенерировать резюме сессии из-за технической проблемы. [cite: 53] Но твои размышления очень ценны!"
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API summary response or invalid data for user {user_id}: {e}")
        return "Не получилось сформулировать итог сессии. [cite: 54] Главное — те мысли и чувства, которые возникли у тебя."
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_grok_summary for user {user_id}: {e}", exc_info=True)
        return "Произошла неожиданная ошибка при подведении итогов. [cite: 55] Пожалуйста, попробуй позже."


# --- НОВАЯ ФУНКЦИЯ: Генерация поддерживающего сообщения ---

async def get_grok_supportive_message(user_id, db=None):
    """
    Генерирует поддерживающее сообщение для пользователя,
    если его ресурсное состояние низкое после сессии. [cite: 56]
    """
    if db is None:
        logger.error("Database object 'db' is required for get_grok_supportive_message")
        return "Пожалуйста, позаботься о себе. Ты важен(на). ✨" # Запасной вариант [cite: 57]

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    profile = await build_user_profile(user_id, db)
    name = db.get_user(user_id).get("name", "Друг") # Получаем имя пользователя
    profile_themes = profile.get("themes", [])
    recharge_method = profile.get("recharge_method", "") # Получаем известный способ подзарядки

    # --- ИСПРАВЛЕННЫЙ БЛОК ---
    # 1. Формируем основную часть системного промпта
    system_prompt_base = (
        f"Ты — очень тёплый, эмпатичный и заботливый друг-помощник. Твоя задача — поддержать пользователя ({name}), который сообщил о низком уровне внутреннего ресурса после работы с картой. [cite: 58]\n"
        "Напиши короткое (2-3 предложения), искреннее и ободряющее сообщение. \n"
        "Признай его чувства, напомни о его ценности и силе. \n"
        "Избегай банальностей и ложного позитива. Не давай советов, если не просят. \n"
        "Тон должен быть мягким, принимающим и обнимающим.\n"
        # Добавляем контекст, если есть
        f" Основные темы, которые волнуют пользователя: {', '.join(profile_themes)}. [cite: 59]\n"
    ) # <-- Закрывающая скобка здесь

    # 2. Добавляем опциональную часть, если есть recharge_method
    system_prompt_optional = ""
    if recharge_method:
        system_prompt_optional = f" Известно, что ему обычно помогает восстанавливаться: {recharge_method}. [cite: 60]\nМожно мягко напомнить об этом или похожих способах заботы о себе, если это уместно."

    # 3. Соединяем части
    system_prompt = system_prompt_base + system_prompt_optional
    # --- КОНЕЦ ИСПРАВЛЕННОГО БЛОКА ---


    # 2. Пользовательский промпт (краткий, т.к. основное в system)
    user_prompt = f"Пользователь {name} сообщил, что его ресурсное состояние сейчас низкое (😔). [cite: 61]\nНапиши для него поддерживающее сообщение."

    # 3. Payload
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt}, # Используем собранный system_prompt
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-3-latest",
        "max_tokens": 120, # Достаточно для теплого сообщения
        "stream": False,
        "temperature": 0.6 # Чуть выше для более душевного ответа [cite: 62]
    }

    # 4. Запрос и обработка
    try:
        logger.info(f"Sending SUPPORTIVE request to Grok API for user {user_id}. Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        response = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Received SUPPORTIVE response from Grok API: {json.dumps(data, ensure_ascii=False, indent=2)}")

        if not data.get("choices") or not data["choices"][0].get("message") or not data["choices"][0]["message"].get("content"): [cite: 63]
             raise ValueError("Invalid response structure for supportive message from Grok API")

        support_text = data["choices"][0]["message"]["content"].strip()
        support_text = re.sub(r'^(Хорошо|Вот сообщение|Конечно|Понятно)[,.:]?\s*', '', support_text, flags=re.IGNORECASE).strip()
        support_text = re.sub(r'^"|"$', '', support_text).strip()

        if not support_text or len(support_text) < 10:
             raise ValueError("Empty or too short support message content after cleaning") [cite: 64]

        # Добавляем вопрос о способе восстановления
        question_about_recharge = "\n\nПоделись, пожалуйста, что обычно помогает тебе восстановить силы и позаботиться о себе в такие моменты?"
        # Если уже знаем способ, можно спросить иначе:
        if recharge_method:
             question_about_recharge = f"\n\nПомнишь, ты упоминал(а), что тебе помогает '{recharge_method}'? [cite: 65]\nМожет, стоит уделить этому время сейчас? Или есть что-то другое, что поддержит тебя сегодня?"

        return support_text + question_about_recharge

    except requests.exceptions.Timeout:
        logger.error(f"Grok API supportive message request timed out for user {user_id}.")
        return "Мне очень жаль, что ты сейчас так себя чувствуешь... Пожалуйста, будь к себе особенно бережен(на). ✨\n\nЧто обычно помогает тебе восстановить силы?" # Запасной вариант + вопрос [cite: 66]
    except requests.exceptions.RequestException as e:
        logger.error(f"Grok API supportive message request failed for user {user_id}: {e}")
        return "Очень сочувствую твоему состоянию... Помни, что любые чувства важны и имеют право быть. Позаботься о себе. 🙏\n\nКак ты обычно восстанавливаешь ресурс?" # Запасной вариант + вопрос [cite: 67]
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Grok API supportive message response for user {user_id}: {e}")
        return "Слышу тебя... Иногда бывает тяжело. Помни, ты не один(на) в своих переживаниях. ❤️\n\nЧто могло бы тебя сейчас поддержать?" # Запасной вариант + вопрос [cite: 68]
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_grok_supportive_message for user {user_id}: {e}", exc_info=True)
        return "Мне жаль, что тебе сейчас нелегко... Пожалуйста, найди минутку для себя, сделай что-то приятное. ☕️\n\nРасскажешь, что тебе помогает в такие моменты?" # Запасной вариант + вопрос [cite: 69]


# --- Построение профиля пользователя (доработанное) ---
async def build_user_profile(user_id, db):
    """Строит или обновляет профиль пользователя на основе его истории действий и данных из БД."""
    profile_data = db.get_user_profile(user_id) # Получаем профиль из БД (может быть None)
    now = datetime.now(TIMEZONE)

    # Проверка на актуальность профиля (например, обновлять не чаще раза в 30 минут)
    if profile_data and isinstance(profile_data.get("last_updated"), datetime):
        last_updated_dt = profile_data["last_updated"].astimezone(TIMEZONE)
        if (now - last_updated_dt).total_seconds() < 1800:  # 30 минут [cite: 70]
            logger.info(f"Using cached profile for user {user_id}, updated at {last_updated_dt}")
            # Убедимся, что все ключи существуют при возврате кэша
            profile_data.setdefault("mood", "unknown")
            profile_data.setdefault("mood_trend", [])
            profile_data.setdefault("themes", ["не определено"])
            profile_data.setdefault("response_count", 0) [cite: 71]
            profile_data.setdefault("request_count", 0)
            profile_data.setdefault("avg_response_length", 0)
            profile_data.setdefault("days_active", 0)
            profile_data.setdefault("interactions_per_day", 0)
            profile_data.setdefault("initial_resource", None)
            profile_data.setdefault("final_resource", None)
            profile_data.setdefault("recharge_method", None)
            # last_updated уже datetime объект [cite: 72]
            return profile_data
    elif profile_data is None:
         logger.info(f"No existing profile found for user {user_id}. Creating new one.") [cite: 73]
         profile_data = {"user_id": user_id} # Начинаем с пустого словаря, если профиля нет
    else:
         # Если профиль есть, но last_updated некорректный, используем его как базу
         logger.warning(f"Invalid or missing last_updated time in profile for user {user_id}. Rebuilding.")


    logger.info(f"Rebuilding profile for user {user_id}")
    actions = db.get_actions(user_id)
    if not actions:
        logger.info(f"No actions found for user {user_id}, returning/creating empty profile.") [cite: 74]
        empty_profile = {
            "user_id": user_id, "mood": "unknown", "mood_trend": [], "themes": ["не определено"],
            "response_count": 0, "request_count": 0, "avg_response_length": 0,
            "days_active": 0, "interactions_per_day": 0,
            "initial_resource": profile_data.get("initial_resource"), # Сохраняем старые значения, если были
            "final_resource": profile_data.get("final_resource"),
            "recharge_method": profile_data.get("recharge_method"), [cite: 75]
            "last_updated": now # Обновляем время
        }
        db.update_user_profile(user_id, empty_profile) # Сохраняем/обновляем профиль
        return empty_profile

    # --- Извлечение данных из действий ---
    requests_texts = []
    responses = []
    mood_trend_responses = []
    timestamps = []
    # Новые данные из логов
    last_initial_resource = profile_data.get("initial_resource") # Берем из старого профиля как дефолт [cite: 76]
    last_final_resource = profile_data.get("final_resource")
    last_recharge_method = profile_data.get("recharge_method")

    for action in actions:
        details = action.get("details", {})
        action_type = action.get("action", "")

        # Запросы
        if action_type == "card_drawn_with_request" and "request" in details:
            requests_texts.append(details["request"])

        # Ответы
        if action_type in ["initial_response", "first_grok_response", "second_grok_response", "third_grok_response"] and "response" in details: [cite: 77]
            responses.append(details["response"])
            mood_trend_responses.append(details["response"]) # Для тренда настроения

        # Ресурсы и методы восстановления
        if action_type == "initial_resource_selected" and "resource" in details:
             last_initial_resource = details["resource"] # Обновляем последним значением из логов
        if action_type == "final_resource_selected" and "resource" in details: [cite: 78]
             last_final_resource = details["resource"]
        if action_type == "recharge_method_provided" and "recharge_method" in details:
             last_recharge_method = details["recharge_method"]

        # Временные метки
        try:
            ts_str = action.get("timestamp")
            if ts_str:
                 ts = datetime.fromisoformat(ts_str).astimezone(TIMEZONE) [cite: 79]
                 timestamps.append(ts)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse timestamp {action.get('timestamp')} for user {user_id}, action {action_type}")
            continue

    # --- Расчет метрик ---
    all_responses_text = " ".join(responses)
    all_requests_text = " ".join(requests_texts)
    full_text = all_requests_text + " " + all_responses_text [cite: 80]

    # Настроение по последним 500 символам или последнему ответу
    mood_source = all_responses_text[-500:] if all_responses_text else ""
    mood = analyze_mood(mood_source) if mood_source else profile_data.get("mood", "unknown")

    themes = extract_themes(full_text) if full_text.strip() else profile_data.get("themes", ["не определено"])

    response_count = len(responses)
    request_count = len(requests_texts)
    avg_response_length = sum(len(r) for r in responses) / response_count if response_count > 0 else 0

    days_active = 0
    interactions_per_day = 0
    if timestamps:
        first_interaction = min(timestamps) [cite: 81]
        last_interaction = max(timestamps)
        # Считаем дни правильно (даже если < 24 часов, но разные даты)
        days_active = (last_interaction.date() - first_interaction.date()).days + 1
        # Считаем взаимодействия только релевантные (опционально)
        relevant_actions_count = len([a for a in actions if a.get("action","").startswith("card_") or a.get("action","").endswith("_response") or "grok" in a.get("action","")])
        interactions_per_day = relevant_actions_count / days_active if days_active > 0 else relevant_actions_count [cite: 82]

    # Тренд настроения по последним 3-5 ответам
    mood_trend = [analyze_mood(resp) for resp in mood_trend_responses[-5:]] # Берем последние 5

    # --- Собираем обновленный профиль ---
    updated_profile = {
        "user_id": user_id,
        "mood": mood,
        "mood_trend": mood_trend,
        "themes": themes,
        "response_count": response_count,
        "request_count": request_count,
        "avg_response_length": round(avg_response_length, 2), [cite: 83]
        "days_active": days_active,
        "interactions_per_day": round(interactions_per_day, 2),
        "initial_resource": last_initial_resource, # Сохраняем последние значения
        "final_resource": last_final_resource,
        "recharge_method": last_recharge_method,
        "last_updated": now # Новое время обновления
    }

    db.update_user_profile(user_id, updated_profile) # Сохраняем обновленный профиль в БД
    logger.info(f"Profile updated for user {user_id}: {updated_profile}")

    return updated_profile
