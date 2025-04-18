# код/db.py
import sqlite3
import json
from datetime import datetime
import os
from config import TIMEZONE
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, path="/data/bot.db"):
        # ... (существующий код __init__) ...
        self.create_tables()
        self._run_migrations() # Миграции для user_profiles уже есть

    def _run_migrations(self):
        """Добавляет новые столбцы в таблицы, если их нет."""
        # Миграция для user_profiles
        profile_columns = {
            'initial_resource': 'TEXT',
            'final_resource': 'TEXT',
            'recharge_method': 'TEXT'
        }
        self._add_columns_if_not_exist('user_profiles', profile_columns)

        # НОВАЯ Миграция для users (добавляем вечернее напоминание)
        users_columns = {
            'reminder_time_evening': 'TEXT' # Время вечернего напоминания HH:MM
        }
        self._add_columns_if_not_exist('users', users_columns)

    def _add_columns_if_not_exist(self, table_name, columns_to_add):
        """Вспомогательная функция для добавления столбцов."""
        logger.info(f"Running database migrations for {table_name} table...")
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [row['name'] for row in cursor.fetchall()]
            logger.debug(f"Existing columns in {table_name}: {existing_columns}")

            for col_name, col_type in columns_to_add.items():
                if col_name not in existing_columns:
                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                    logger.info(f"Executing migration: {alter_sql}")
                    cursor.execute(alter_sql)
                    logger.info(f"Successfully added column '{col_name}' to {table_name}")
                else:
                    logger.debug(f"Column '{col_name}' already exists in {table_name}.")

            self.conn.commit()
            logger.info(f"Database migrations for {table_name} completed successfully.")
        except sqlite3.Error as e:
            logger.error(f"Database migration error for {table_name}: {e}", exc_info=True)
            self.conn.rollback()

    def create_tables(self):
        logger.info("Creating database tables if they don't exist...")
        with self.conn:
            # Таблица users (ДОБАВЛЕНО ПОЛЕ reminder_time_evening)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    last_request TEXT,
                    reminder_time TEXT,          -- Время утреннего напоминания HH:MM
                    reminder_time_evening TEXT, -- НОВОЕ: Время вечернего напоминания HH:MM
                    bonus_available BOOLEAN DEFAULT FALSE
                )""")
            # Таблица использованных карт
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_cards (
                    user_id INTEGER,
                    card_number INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")
            # Таблица логов действий
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    name TEXT,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")
            # Таблица рефералов
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referrer_id INTEGER,
                    referred_id INTEGER UNIQUE,
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (referred_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")
            # Таблица для общего фидбека
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT,
                    feedback TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")
            # Таблица профилей пользователей
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    mood TEXT,
                    mood_trend TEXT,
                    themes TEXT,
                    response_count INTEGER DEFAULT 0,
                    request_count INTEGER DEFAULT 0,
                    avg_response_length REAL DEFAULT 0,
                    days_active INTEGER DEFAULT 0,
                    interactions_per_day REAL DEFAULT 0,
                    last_updated TEXT,
                    initial_resource TEXT,
                    final_resource TEXT,
                    recharge_method TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")

            # НОВАЯ Таблица для вечерней рефлексии
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS evening_reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,          -- Дата в формате YYYY-MM-DD
                    good_moments TEXT,           -- Ответ на вопрос 1
                    gratitude TEXT,              -- Ответ на вопрос 2
                    hard_moments TEXT,           -- Ответ на вопрос 3
                    created_at TEXT NOT NULL,    -- Время сохранения ISO (с таймзоной)
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")

            # Индексы
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_user_timestamp ON actions (user_id, timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_cards_user ON user_cards (user_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reminder_time ON users (reminder_time)")
            # НОВЫЙ Индекс для вечерних напоминаний
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reminder_time_evening ON users (reminder_time_evening)")
            # НОВЫЙ Индекс для рефлексий
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reflections_user_date ON evening_reflections (user_id, date)")

        logger.info("Tables checked/created.")

    def get_user(self, user_id):
        """Получает данные пользователя. Если не найден, создает запись."""
        cursor = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            user_dict = dict(row)
            # ... (существующая обработка last_request) ...
             # Обработка last_request (ожидаем строку ISO или datetime)
            last_request_val = user_dict.get("last_request")
            if last_request_val:
                try:
                    if isinstance(last_request_val, str):
                        if 'Z' in last_request_val:
                             last_request_val = last_request_val.replace('Z', '+00:00')
                        user_dict["last_request"] = datetime.fromisoformat(last_request_val)
                    else: # Если это уже datetime (маловероятно из БД)
                           user_dict["last_request"] = last_request_val
                except (ValueError, TypeError) as e:
                     logger.error(f"Error parsing last_request '{last_request_val}' for user {user_id}: {e}")
                     user_dict["last_request"] = None # Обнуляем при ошибке
            else:
                user_dict["last_request"] = None

            user_dict["bonus_available"] = bool(user_dict.get("bonus_available", False))
            # Гарантируем наличие нового поля reminder_time_evening
            user_dict.setdefault("reminder_time_evening", None)
            return user_dict

        # Пользователь не найден, создаем дефолтную запись
        logger.info(f"User {user_id} not found in 'users' table, creating default entry.")
        default_user_data = {
            "user_id": user_id, "name": "", "username": "",
            "last_request": None, "reminder_time": None,
            "reminder_time_evening": None, # НОВОЕ
            "bonus_available": False
        }
        try:
            with self.conn:
                self.conn.execute(
                    """INSERT INTO users (
                           user_id, name, username, last_request, reminder_time,
                           reminder_time_evening, bonus_available
                       ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, default_user_data["name"], default_user_data["username"],
                     None, default_user_data["reminder_time"],
                     default_user_data["reminder_time_evening"], # НОВОЕ
                     default_user_data["bonus_available"])
                )
            logger.info(f"Default user entry created for {user_id}")
            return default_user_data
        except sqlite3.Error as e:
            logger.error(f"Failed to insert default user {user_id}: {e}", exc_info=True)
            return default_user_data # Возвращаем дефолтную структуру в памяти

    def update_user(self, user_id, data):
        """Обновляет данные пользователя (INSERT OR REPLACE)."""
        current_user_data = self.get_user(user_id) # Получит или создаст

        user_id_to_save = user_id
        name_to_save = data.get("name", current_user_data.get("name"))
        username_to_save = data.get("username", current_user_data.get("username"))
        reminder_to_save = data.get("reminder_time", current_user_data.get("reminder_time"))
        # НОВОЕ: Обработка вечернего напоминания
        reminder_evening_to_save = data.get("reminder_time_evening", current_user_data.get("reminder_time_evening"))
        bonus_to_save = data.get("bonus_available", current_user_data.get("bonus_available"))

        # Обработка last_request
        last_request_to_save = None
        if "last_request" in data:
            last_request_input = data["last_request"]
            if isinstance(last_request_input, datetime):
                last_request_to_save = last_request_input.isoformat()
            elif isinstance(last_request_input, str):
                try:
                    datetime.fromisoformat(last_request_input.replace('Z', '+00:00'))
                    last_request_to_save = last_request_input
                except (ValueError, TypeError):
                    logger.warning(f"Invalid ISO string format for last_request '{last_request_input}' for user {user_id}. Saving as None.")
                    last_request_to_save = None
            else:
                 last_request_to_save = None # Оставляем None если тип не строка/datetime
        else:
            current_last_request_dt = current_user_data.get("last_request")
            if isinstance(current_last_request_dt, datetime):
                last_request_to_save = current_last_request_dt.isoformat()

        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO users (
                        user_id, name, username, last_request, reminder_time,
                        reminder_time_evening, bonus_available
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id_to_save, name_to_save, username_to_save,
                    last_request_to_save, reminder_to_save,
                    reminder_evening_to_save, # НОВОЕ
                    bonus_to_save
                ))
        except sqlite3.Error as e:
             logger.error(f"Failed to update user {user_id}: {e}", exc_info=True)

    # ... (существующие методы get_user_cards, add_user_card, reset_user_cards) ...

    def save_action(self, user_id, username, name, action, details, timestamp):
        """Сохраняет запись о действии пользователя."""
        # ... (существующая обработка timestamp) ...
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.isoformat()
        elif isinstance(timestamp, str):
             try:
                 datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                 timestamp_str = timestamp
             except (ValueError, TypeError):
                 logger.warning(f"Invalid timestamp string '{timestamp}' ... Using current time.")
                 timestamp_str = datetime.now(TIMEZONE).isoformat()
        else:
            logger.warning(f"Invalid timestamp type '{type(timestamp)}' ... Using current time.")
            timestamp_str = datetime.now(TIMEZONE).isoformat()

        # Преобразуем детали в JSON без экранирования ASCII (УЖЕ БЫЛО ПРАВИЛЬНО)
        details_json = None
        if details is not None:
            try:
                # ensure_ascii=False - это ключ к сохранению кириллицы как есть
                details_json = json.dumps(details, ensure_ascii=False, indent=2) # Добавил indent для читаемости в БД/логах
            except TypeError as e:
                logger.error(f"Failed to serialize details for action '{action}' for user {user_id}: {e}. Details: {details}")
                details_json = json.dumps({"error": "serialization_failed", "original_details_type": str(type(details))})

        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO actions (user_id, username, name, action, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, username, name, action, details_json, timestamp_str)
                )
        except sqlite3.Error as e:
            logger.error(f"Failed to save action '{action}' for user {user_id}: {e}. Details JSON: {details_json}", exc_info=True)


    # ... (существующий метод get_actions) ...

    def get_reminder_times(self):
        """Возвращает словарь {user_id: {'morning': time, 'evening': time}}"""
        reminders = {}
        try:
            cursor = self.conn.execute("SELECT user_id, reminder_time, reminder_time_evening FROM users WHERE reminder_time IS NOT NULL OR reminder_time_evening IS NOT NULL")
            for row in cursor.fetchall():
                reminders[row["user_id"]] = {
                    'morning': row["reminder_time"],
                    'evening': row["reminder_time_evening"]
                }
            return reminders
        except sqlite3.Error as e:
            logger.error(f"Failed to get reminder times: {e}", exc_info=True)
            return {}

    # ... (существующие методы get_all_users, is_card_available, add_referral, get_referrals, get_user_profile, update_user_profile) ...

    # НОВЫЙ МЕТОД для сохранения вечерней рефлексии
    async def save_evening_reflection(self, user_id, date, good_moments, gratitude, hard_moments, created_at):
        """Сохраняет данные вечерней рефлексии в БД."""
        sql = """
            INSERT INTO evening_reflections
            (user_id, date, good_moments, gratitude, hard_moments, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            with self.conn:
                self.conn.execute(sql, (user_id, date, good_moments, gratitude, hard_moments, created_at))
            logger.info(f"Saved evening reflection for user {user_id} for date {date}")
        except sqlite3.Error as e:
            logger.error(f"Failed to save evening reflection for user {user_id}: {e}", exc_info=True)
            # Возможно, стоит пробросить ошибку выше, чтобы уведомить пользователя
            raise
