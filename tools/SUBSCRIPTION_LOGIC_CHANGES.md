# Изменения в логике проверки подписки

## Обзор изменений

Реализована новая логика проверки подписки на канал `@TopPsyGame`, которая срабатывает только **после первого успешного завершения сценария "Карта дня"**.

## Что изменилось

### 1. Новая функция в базе данных

**Файл:** `database/db.py`

Добавлена функция `has_completed_scenario_first_time()`:

```python
def has_completed_scenario_first_time(self, user_id: int, scenario: str) -> bool:
    """Проверяет, завершил ли пользователь сценарий хотя бы один раз."""
    try:
        cursor = self.conn.execute(
            "SELECT COUNT(*) as count FROM user_scenarios WHERE user_id = ? AND scenario = ? AND status = 'completed'",
            (user_id, scenario)
        )
        result = cursor.fetchone()
        return result['count'] >= 1 if result else False
    except sqlite3.Error as e:
        logger.error(f"Failed to check first completion for user {user_id}, scenario {scenario}: {e}", exc_info=True)
        return False
```

### 2. Обновленная логика в SubscriptionMiddleware

**Файл:** `main.py`

Модифицирован класс `SubscriptionMiddleware`:

```python
class SubscriptionMiddleware:
    async def __call__(self, handler, event, data):
        if isinstance(event, (types.Message, types.CallbackQuery)):
            user = event.from_user
            if not user or user.is_bot or user.id == ADMIN_ID:
                return await handler(event, data)
            user_id = user.id
            try:
                # Получаем доступ к базе данных через data
                db = data.get("db")
                if not db:
                    logger.error("Database not found in middleware data")
                    return await handler(event, data)
                
                # Проверяем, завершил ли пользователь сценарий "Карта дня" впервые
                has_completed_card_scenario = db.has_completed_scenario_first_time(user_id, 'card_of_day')
                
                # Если пользователь еще не завершил сценарий "Карта дня" впервые, пропускаем проверку подписки
                if not has_completed_card_scenario:
                    return await handler(event, data)
                
                # Проверяем подписку только после первого успешного завершения сценария "Карта дня"
                user_status = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
                allowed_statuses = ["member", "administrator", "creator"]
                if user_status.status not in allowed_statuses:
                    # ... остальная логика проверки подписки ...
```

## Логика работы

1. **До завершения сценария "Карта дня":**
   - Пользователь может свободно использовать бота
   - Проверка подписки не срабатывает
   - Все функции доступны

2. **После первого успешного завершения сценария "Карта дня":**
   - При каждом взаимодействии с ботом проверяется подписка на канал `@TopPsyGame`
   - Если пользователь не подписан, показывается сообщение с просьбой подписаться
   - Доступ к функциям бота блокируется до подписки

3. **После подписки на канал:**
   - Пользователь получает полный доступ к функциям бота
   - Проверка подписки больше не срабатывает для этого пользователя

## Тестирование

Создан тестовый скрипт `simple_test.py` для проверки логики:

```bash
python simple_test.py
```

Тест проверяет:
- ✅ Пользователь не завершил сценарий → проверка подписки не срабатывает
- ✅ Пользователь завершил сценарий → проверка подписки срабатывает

## Преимущества новой логики

1. **Лучший пользовательский опыт:** Пользователи могут попробовать бота перед тем, как их попросят подписаться
2. **Более естественная воронка:** Подписка запрашивается после того, как пользователь получил ценность от бота
3. **Снижение отказов:** Меньше пользователей покидают бота на ранних этапах
4. **Соответствие требованиям:** Проверка подписки срабатывает именно после первого успешного завершения сценария "Карта дня"

## Совместимость

- ✅ Обратная совместимость с существующими пользователями
- ✅ Не влияет на других пользователей, которые уже подписаны
- ✅ Сохраняет всю существующую функциональность
- ✅ Легко откатить изменения при необходимости
