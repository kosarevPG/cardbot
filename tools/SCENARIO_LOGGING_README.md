# 📊 Система логирования сценариев

Система для отслеживания использования и анализа сценариев бота "Ресурсный помощник".

## 🎯 Цели системы

- **Измерение частотности использования** каждого сценария (DAU по сценариям)
- **Анализ глубины прохождения** (дошел ли пользователь до конца или бросил)
- **Выявление узких мест** в сценариях
- **Отслеживание последовательности шагов** для оптимизации UX

## 🎯 Новые детальные метрики для "Карта дня"

Система теперь отслеживает 5 ключевых аспектов пользовательского опыта:

### 1. 📝 Тип запроса к карте
- **Текстовые запросы** - пользователь формулирует запрос письменно
- **Мысленные запросы** - пользователь держит запрос в уме

### 2. 🤖 Выбор рефлексии с ИИ
- **Выбрали** - пользователь согласился на углубленную рефлексию
- **Отказались** - пользователь предпочел завершить сессию

### 3. 💬 Глубина ИИ-взаимодействия
- **Количество ответов** на ИИ-вопросы (1-й, 2-й, 3-й)
- **Процент завершения** каждого этапа рефлексии

### 4. 😊 Изменение самочувствия
- **Улучшилось** - самочувствие стало лучше после сессии
- **Ухудшилось** - самочувствие стало хуже
- **Осталось тем же** - самочувствие не изменилось

### 5. ⭐ Оценка полезности
- **Помогло** - сессия была полезной и эффективной
- **Было интересно** - сессия была интересной, но не очень глубокой
- **Недостаточно глубоко** - пользователь хотел бы более глубокой работы

## 🗃️ Структура базы данных

### Таблица `scenario_logs`
Детальное логирование каждого шага сценария:
```sql
CREATE TABLE scenario_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    scenario TEXT NOT NULL,
    step TEXT NOT NULL,
    metadata TEXT,  -- JSON с дополнительными данными
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### Таблица `user_scenarios`
Общая статистика по сценариям:
```sql
CREATE TABLE user_scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    scenario TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    steps_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'in_progress',  -- 'in_progress', 'completed', 'abandoned'
    session_id TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

## 🔧 Методы для работы с логированием

### Основные методы в `database/db.py`:

```python
# Логирование шага сценария
db.log_scenario_step(user_id, scenario, step, metadata=None)

# Начало сценария
session_id = db.start_user_scenario(user_id, scenario)

# Завершение сценария
db.complete_user_scenario(user_id, scenario, session_id)

# Отметка сценария как брошенного
db.abandon_user_scenario(user_id, scenario, session_id)

# Получение статистики
stats = db.get_scenario_stats(scenario, days=7)

# Получение статистики по шагам
steps = db.get_scenario_step_stats(scenario, days=7)

# История сценариев пользователя
history = db.get_user_scenario_history(user_id)
```

## 📈 Поддерживаемые сценарии

### 1. 🎴 "Карта дня" (`card_of_day`)

**Ключевые шаги:**
- `started` - начало сценария
- `already_used_today` - попытка повторного использования
- `initial_resource_selected` - выбран начальный ресурс
- `request_type_selected` - выбор типа запроса (мысленный/текстовый)
- `text_request_provided` - предоставлен текстовый запрос
- `card_drawn` - вытянута карта
- `initial_response_provided` - предоставлен начальный ответ
- `ai_reflection_choice` - выбор рефлексии с ИИ
- `ai_response_1_provided` - ответ на первый ИИ-вопрос
- `ai_response_2_provided` - ответ на второй ИИ-вопрос
- `ai_response_3_provided` - ответ на третий ИИ-вопрос
- `mood_change_recorded` - записано изменение самочувствия
- `usefulness_rating` - оценка полезности сессии
- `completed` - сценарий завершен

**Метаданные:**
- `card_number` - номер карты
- `user_request` - запрос пользователя
- `request_type` - тип запроса ('mental' или 'typed')
- `request_length` - длина текстового запроса
- `choice` - выбор рефлексии с ИИ ('yes' или 'no')
- `response_length` - длина ответа на ИИ-вопрос
- `initial_resource` - начальный ресурс
- `final_resource` - конечный ресурс
- `change_direction` - направление изменения самочувствия ('better', 'worse', 'same')
- `rating` - оценка полезности ('helped', 'interesting', 'notdeep')

### 2. 🌙 "Вечерняя рефлексия" (`evening_reflection`)

**Ключевые шаги:**
- `started` - начало сценария
- `good_moments_provided` - ответ на вопрос о хороших моментах
- `gratitude_provided` - ответ на вопрос о благодарности
- `hard_moments_provided` - ответ на вопрос о непростых моментах
- `completed` - сценарий завершен

**Метаданные:**
- `answer_length` - длина ответа
- `ai_summary_generated` - был ли сгенерирован AI-итог

## 🛠️ Интеграция в код

### Пример для сценария "Карта дня":

```python
# Начало сценария
session_id = db.start_user_scenario(user_id, 'card_of_day')
db.log_scenario_step(user_id, 'card_of_day', 'started', {
    'session_id': session_id,
    'today': today.isoformat()
})

# Сохраняем session_id в состоянии
await state.update_data(session_id=session_id)

# Логирование шагов
db.log_scenario_step(user_id, 'card_of_day', 'initial_resource_selected', {
    'resource': resource_choice_label,
    'session_id': session_id
})

# Завершение сценария
db.complete_user_scenario(user_id, 'card_of_day', session_id)
db.log_scenario_step(user_id, 'card_of_day', 'completed', {
    'card_number': card_number,
    'session_id': session_id
})
```

## 📊 Команды для администратора

### `/scenario_stats [дни]`
Показывает статистику использования сценариев за указанное количество дней (по умолчанию 7).

**Пример вывода:**
```
📊 Статистика сценариев за последние 7 дней:

🎴 Карта дня:
  • Запусков: 45
  • Завершений: 38
  • Брошено: 7
  • Процент завершения: 84.4%
  • Среднее шагов: 8.2

🎴 Детальные метрики 'Карта дня':
  📝 Запросы: 25 текстовых, 20 мысленных
  🤖 ИИ-рефлексия: 30 выбрали, 15 отказались
  💬 ИИ-ответы: 30→25→20
  😊 Самочувствие: +15 -5 =20
  ⭐ Оценка: 20👍 10🤔 8😕

🌙 Вечерняя рефлексия:
  • Запусков: 23
  • Завершений: 21
  • Брошено: 2
  • Процент завершения: 91.3%
  • Среднее шагов: 4.1
```

## 🧪 Тестирование

Запустите тестовый скрипт для проверки системы:

```bash
python test_scenario_logging.py
```

Скрипт создаст тестовую БД и покажет примеры использования всех методов.

## 📋 Примеры SQL-запросов для анализа

### Частотность использования за последние 7 дней:
```sql
SELECT DATE(timestamp), COUNT(DISTINCT user_id)
FROM scenario_logs
WHERE scenario = 'card_of_day' AND step = 'started'
GROUP BY DATE(timestamp);
```

### Процент завершения сценариев:
```sql
SELECT 
  (COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0) / COUNT(*) AS completion_rate
FROM user_scenarios
WHERE scenario = 'card_of_day';
```

### Узкие места (на каких шагах бросают):
```sql
SELECT step, COUNT(*) AS step_count
FROM scenario_logs
WHERE scenario = 'card_of_day'
GROUP BY step
ORDER BY step_count DESC;
```

### Среднее время прохождения сценария:
```sql
SELECT AVG(
  (julianday(completed_at) - julianday(started_at)) * 24 * 60
) as avg_minutes
FROM user_scenarios
WHERE scenario = 'card_of_day' AND status = 'completed';
```

## 🔄 Миграция данных

Система автоматически создает необходимые таблицы при первом запуске. Если нужно добавить новые поля:

1. Добавьте новые столбцы в метод `create_tables()`
2. Добавьте миграцию в метод `_run_migrations()`
3. Добавьте индексы в метод `create_indexes()`

## 📝 Лучшие практики

1. **Всегда используйте session_id** для связывания шагов одного сценария
2. **Логируйте метаданные** для детального анализа
3. **Обрабатывайте ошибки** при логировании (не прерывайте основной флоу)
4. **Используйте осмысленные названия шагов** для удобства анализа
5. **Регулярно анализируйте метрики** для оптимизации UX

## 🚀 Планы развития

- [ ] Дашборд с визуализацией метрик
- [ ] Автоматические алерты при падении метрик
- [ ] A/B тестирование разных версий сценариев
- [ ] Интеграция с внешними аналитическими системами 