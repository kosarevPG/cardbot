# код/db.py
import sqlite3
import json
from datetime import datetime
import os
# Убедись, что TIMEZONE импортирован правильно из твоего config файла
# Пример: from config import TIMEZONE
# Оставляем, т.к. используется в save_action и др. косвенно через now()
from config import TIMEZONE # Убедитесь, что этот импорт работает
import logging

# Настраиваем логгер для этого модуля
logger = logging.getLogger(__name__)

# --- КЛАСС Database ---
class Database:
    def __init__(self, path="/data/bot.db"):
        """
        Инициализация соединения с БД.
        Порядок:
        1. Соединение.
        2. Создание базовых таблиц (если не существуют).
        3. Запуск миграций (добавление столбцов в существующие таблицы).
        4. Создание индексов.
        """
        db_dir = os.path.dirname(path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Created database directory: {db_dir}")
            except OSError as e:
                logger.error(f"Failed to create database directory {db_dir}: {e}")
                path = os.path.basename(path)
                logger.warning(f"Attempting to use database in current directory: {path}")

        try:
            self.conn = sqlite3.connect(path, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            logger.info(f"Database connection initialized at path: {path}")

            # Включаем поддержку типов данных datetime для SQLite
            sqlite3.register_adapter(datetime, lambda val: val.isoformat())

            # Декодер для timestamp с обработкой None и 'Z'
            def decode_timestamp(val):
                if val is None:
                    return None
                try:
                    val_str = val.decode('utf-8')
                    if val_str.endswith('Z'):
                        val_str = val_str[:-1] + '+00:00'
                    dt_obj = datetime.fromisoformat(val_str)
                    return dt_obj
                except (ValueError, TypeError, AttributeError) as e:
                    logger.error(f"Error decoding timestamp '{val}': {e}")
                    return None

            sqlite3.register_converter("timestamp", decode_timestamp)

            self.conn.row_factory = sqlite3.Row
            self.bot = None # Устанавливается в main.py

            # --- Порядок инициализации ---
            self.create_tables()      # Шаг 1: Создать таблицы с полным текущим набором столбцов
            self._run_migrations()    # Шаг 2: Добавить столбцы в таблицы, если они были созданы старой версией кода
            self.create_indexes()     # Шаг 3: Создать индексы для всех столбцов

        except sqlite3.Error as e:
            logger.critical(f"Database initialization failed: Could not connect or setup tables/migrations/indexes at {path}. Error: {e}", exc_info=True)
            raise # Критическая ошибка, бот не может работать без БД

    def create_tables(self):
        """Создает все необходимые таблицы с ПОЛНОЙ АКТУАЛЬНОЙ СХЕМОЙ, если они не существуют."""
        logger.info("Ensuring base table structures exist...")
        try:
            with self.conn:
                # Таблица users (с полем reminder_time_evening)
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        username TEXT,
                        last_request TEXT,          -- ISO строка времени последнего вытягивания карты
                        reminder_time TEXT,         -- Время утреннего напоминания HH:MM
                        reminder_time_evening TEXT, -- Время вечернего напоминания HH:MM (Определено здесь!)
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
                        action TEXT NOT NULL,       -- Тип действия
                        details TEXT,               -- Детали в формате JSON
                        timestamp TEXT NOT NULL,    -- Время действия в ISO формате
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # Таблица рефералов
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS referrals (
                        referrer_id INTEGER,
                        referred_id INTEGER UNIQUE, -- Один пользователь может быть приглашен только один раз
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
                # Таблица профилей пользователей (с новыми полями)
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id INTEGER PRIMARY KEY,
                        mood TEXT,
                        mood_trend TEXT,            -- JSON список последних настроений
                        themes TEXT,                -- JSON список тем
                        response_count INTEGER DEFAULT 0,
                        request_count INTEGER DEFAULT 0,
                        avg_response_length REAL DEFAULT 0,
                        days_active INTEGER DEFAULT 0,
                        interactions_per_day REAL DEFAULT 0,
                        last_updated TEXT,          -- ISO строка времени последнего обновления профиля
                        initial_resource TEXT,      -- (Определено здесь!)
                        final_resource TEXT,        -- (Определено здесь!)
                        recharge_method TEXT,       -- (Определено здесь!)
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # Таблица для вечерней рефлексии
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS evening_reflections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        date TEXT NOT NULL,             -- Дата в формате YYYY-MM-DD
                        good_moments TEXT,              -- Ответ на вопрос 1
                        gratitude TEXT,                 -- Ответ на вопрос 2
                        hard_moments TEXT,              -- Ответ на вопрос 3
                        created_at TEXT NOT NULL,       -- Время сохранения ISO (с таймзоной)
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")

            logger.info("Base table structures checked/created successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error creating base database tables: {e}", exc_info=True)
            raise # Пробрасываем ошибку, если таблицы создать не удалось

    def _run_migrations(self):
        """Добавляет новые столбцы в СУЩЕСТВУЮЩИЕ таблицы (ALTER TABLE), если их нет."""
        logger.info("Running database migrations (checking for missing columns)...")
        try:
            # Миграция для user_profiles
            profile_columns = {
                'initial_resource': 'TEXT',
                'final_resource': 'TEXT',
                'recharge_method': 'TEXT'
            }
            self._add_columns_if_not_exist('user_profiles', profile_columns)

            # Миграция для users
            users_columns = {
                'reminder_time_evening': 'TEXT' # Этот столбец добавится, только если таблица была создана старой версией кода
            }
            self._add_columns_if_not_exist('users', users_columns)

            logger.info("Database migrations finished successfully.")
        except Exception as e:
            logger.error(f"Error during database migration process: {e}", exc_info=True)
            # Решаем, критична ли ошибка миграции для запуска
            # Можно пробросить ошибку: raise e
            # Или просто залогировать и продолжить

    def _add_columns_if_not_exist(self, table_name, columns_to_add):
        """Вспомогательная функция для добавления столбцов через ALTER TABLE."""
        logger.debug(f"Checking/Adding columns for table '{table_name}'...")
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [row['name'] for row in cursor.fetchall()]
            logger.debug(f"Existing columns in {table_name}: {existing_columns}")

            added_count = 0
            for col_name, col_type in columns_to_add.items():
                if col_name not in existing_columns:
                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                    logger.info(f"Executing migration: {alter_sql}")
                    cursor.execute(alter_sql)
                    logger.info(f"Successfully added column '{col_name}' to {table_name}")
                    added_count += 1
                # else: # Отладка
                #     logger.debug(f"Column '{col_name}' already exists in {table_name}.")

            if added_count > 0:
                self.conn.commit()
                logger.info(f"Committed {added_count} column additions for {table_name}.")
            # else: # Отладка
            #     logger.debug(f"No new columns needed for {table_name}.")

        except sqlite3.Error as e:
            logger.error(f"Database migration error for {table_name} adding columns: {e}", exc_info=True)
            self.conn.rollback() # Откатываем изменения в рамках этой таблицы при ошибке
            raise e # Пробрасываем ошибку миграции выше

    def create_indexes(self):
        """Создает все необходимые индексы, ЕСЛИ ОНИ НЕ СУЩЕСТВУЮТ."""
        logger.info("Creating database indexes if they don't exist...")
        try:
            with self.conn:
                # Индексы для ускорения запросов
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_user_timestamp ON actions (user_id, timestamp)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_cards_user ON user_cards (user_id)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reminder_time ON users (reminder_time)")
                # Теперь эта команда должна выполняться без ошибок
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reminder_time_evening ON users (reminder_time_evening)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reflections_user_date ON evening_reflections (user_id, date)")

            logger.info("Indexes checked/created successfully.")
        except sqlite3.Error as e:
            # Не критично для запуска, но важно для производительности
            logger.error(f"Error creating database indexes: {e}", exc_info=True)
            # Не пробрасываем ошибку по умолчанию, чтобы бот мог запуститься
            # raise # Раскомментируйте, если индексы абсолютно критичны

    def get_user(self, user_id):
        """Получает данные пользователя. Если не найден, создает запись."""
        try:
            cursor = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_dict = dict(row)
                # Обработка last_request (преобразование строки ISO в datetime)
                last_request_val = user_dict.get("last_request")
                if last_request_val and isinstance(last_request_val, str):
                    try:
                        if last_request_val.endswith('Z'):
                             last_request_val = last_request_val[:-1] + '+00:00'
                        user_dict["last_request"] = datetime.fromisoformat(last_request_val)
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error parsing last_request '{last_request_val}' for user {user_id}: {e}")
                        user_dict["last_request"] = None
                elif not isinstance(last_request_val, datetime):
                    user_dict["last_request"] = None

                # Гарантируем наличие полей (хотя схема и миграции должны это делать)
                user_dict.setdefault("bonus_available", False)
                user_dict.setdefault("reminder_time_evening", None)
                # Конвертируем BOOLEAN из БД (0/1) в Python bool
                user_dict["bonus_available"] = bool(user_dict["bonus_available"])
                return user_dict

            # Пользователь не найден, создаем дефолтную запись
            logger.info(f"User {user_id} not found in 'users' table, creating default entry.")
            default_user_data = {
                "user_id": user_id, "name": "", "username": "",
                "last_request": None, "reminder_time": None,
                "reminder_time_evening": None, # НОВОЕ поле
                "bonus_available": False
            }
            with self.conn:
                self.conn.execute(
                    """INSERT INTO users (
                            user_id, name, username, last_request, reminder_time,
                            reminder_time_evening, bonus_available
                       ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, default_user_data["name"], default_user_data["username"],
                     None, default_user_data["reminder_time"],
                     default_user_data["reminder_time_evening"], # НОВОЕ
                     int(default_user_data["bonus_available"])) # Сохраняем как 0/1
                )
            logger.info(f"Default user entry created for {user_id}")
            return default_user_data
        except sqlite3.Error as e:
            logger.error(f"Failed to get or create user {user_id}: {e}", exc_info=True)
            # Возвращаем дефолтную структуру в памяти в случае ошибки БД
            return {"user_id": user_id, "name": "", "username": "", "last_request": None, "reminder_time": None, "reminder_time_evening": None, "bonus_available": False}


    def update_user(self, user_id, data):
        """Обновляет данные пользователя (INSERT OR REPLACE)."""
        current_user_data = self.get_user(user_id) # Получит или создаст

        # Подготовка данных для сохранения
        name_to_save = data.get("name", current_user_data.get("name", ""))
        username_to_save = data.get("username", current_user_data.get("username", ""))
        reminder_to_save = data.get("reminder_time", current_user_data.get("reminder_time"))
        reminder_evening_to_save = data.get("reminder_time_evening", current_user_data.get("reminder_time_evening"))
        bonus_to_save = data.get("bonus_available", current_user_data.get("bonus_available", False))

        # Обработка last_request (сохраняем как строку ISO)
        last_request_to_save = None
        last_request_input = data.get("last_request", current_user_data.get("last_request"))
        if isinstance(last_request_input, datetime):
            last_request_to_save = last_request_input.isoformat()
        elif isinstance(last_request_input, str):
            try:
                # Проверяем валидность строки ISO перед сохранением
                datetime.fromisoformat(last_request_input.replace('Z', '+00:00'))
                last_request_to_save = last_request_input
            except (ValueError, TypeError):
                logger.warning(f"Invalid ISO string provided for last_request '{last_request_input}' for user {user_id}. Saving as None.")
                last_request_to_save = None
        # else: last_request_to_save остается None

        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO users (
                        user_id, name, username, last_request, reminder_time,
                        reminder_time_evening, bonus_available
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, name_to_save, username_to_save,
                    last_request_to_save, reminder_to_save,
                    reminder_evening_to_save,
                    int(bonus_to_save) # SQLite BOOLEAN лучше хранить как 0/1
                ))
            # logger.debug(f"User {user_id} updated successfully.") # Опционально для отладки
        except sqlite3.Error as e:
            logger.error(f"Failed to update user {user_id}: {e}", exc_info=True)

    def get_user_cards(self, user_id):
        """Возвращает список номеров карт, использованных пользователем."""
        try:
            cursor = self.conn.execute("SELECT card_number FROM user_cards WHERE user_id = ?", (user_id,))
            return [row["card_number"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get user cards for {user_id}: {e}", exc_info=True)
            return []

    def add_user_card(self, user_id, card_number):
        """Добавляет запись об использованной карте."""
        try:
            with self.conn:
                self.conn.execute("INSERT INTO user_cards (user_id, card_number) VALUES (?, ?)", (user_id, card_number))
        except sqlite3.Error as e:
            logger.error(f"Failed to add user card {card_number} for {user_id}: {e}", exc_info=True)

    def reset_user_cards(self, user_id):
        """Удаляет все записи об использованных картах для пользователя."""
        try:
            with self.conn:
                self.conn.execute("DELETE FROM user_cards WHERE user_id = ?", (user_id,))
            logger.info(f"Reset used cards for user {user_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to reset user cards for {user_id}: {e}", exc_info=True)


    def save_action(self, user_id, username, name, action, details, timestamp):
        """Сохраняет запись о действии пользователя."""
        timestamp_str = None
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.isoformat()
        elif isinstance(timestamp, str):
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_str = timestamp
            except (ValueError, TypeError):
                 logger.warning(f"Invalid timestamp string '{timestamp}' for action '{action}', user {user_id}. Using current time.")
        if timestamp_str is None: # Если timestamp не был datetime или валидной строкой
            timestamp_str = datetime.now(TIMEZONE).isoformat()

        details_json = None
        if details is not None:
            try:
                details_json = json.dumps(details, ensure_ascii=False, indent=2)
            except TypeError as e:
                logger.error(f"Failed to serialize details for action '{action}', user {user_id}: {e}. Details: {details}")
                details_json = json.dumps({"error": "serialization_failed", "original_details_type": str(type(details))})

        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO actions (user_id, username, name, action, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, username, name, action, details_json, timestamp_str)
                )
        except sqlite3.Error as e:
            logger.error(f"Failed to save action '{action}' for user {user_id}: {e}. Details JSON: {details_json}", exc_info=True)


    def get_actions(self, user_id=None):
        """Получает список действий пользователя (или всех), отсортированных по времени."""
        actions = []
        try:
            sql = "SELECT id, user_id, username, name, action, details, timestamp FROM actions"
            params = []
            if user_id:
                sql += " WHERE user_id = ?"
                params.append(user_id)
            sql += " ORDER BY timestamp ASC" # Сортируем по возрастанию

            cursor = self.conn.execute(sql, params)

            for row in cursor.fetchall():
                row_dict = dict(row)
                details_dict = {}
                if row_dict.get("details"):
                    try:
                        details_dict = json.loads(row_dict["details"])
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to decode details JSON for action ID {row_dict.get('id')}, user {row_dict.get('user_id')}: {e}. Raw details: {row_dict['details']}")
                        details_dict = {"error": "invalid_json", "raw_details": row_dict["details"]}

                # Timestamp должен быть строкой ISO из БД
                timestamp_str = row_dict.get("timestamp", datetime.min.isoformat())

                actions.append({
                    "id": row_dict.get("id"),
                    "user_id": row_dict.get("user_id"),
                    "username": row_dict.get("username"),
                    "name": row_dict.get("name"),
                    "action": row_dict.get("action"),
                    "details": details_dict,
                    "timestamp": timestamp_str # Возвращаем строку ISO
                })
        except sqlite3.Error as e:
            logger.error(f"Failed to get actions (user_id: {user_id}): {e}", exc_info=True)
        return actions


    def get_reminder_times(self):
        """Возвращает словарь {user_id: {'morning': time, 'evening': time}} для пользователей с установленными напоминаниями."""
        reminders = {}
        try:
            cursor = self.conn.execute("""
                SELECT user_id, reminder_time, reminder_time_evening
                FROM users
                WHERE reminder_time IS NOT NULL OR reminder_time_evening IS NOT NULL
            """)
            for row in cursor.fetchall():
                reminders[row["user_id"]] = {
                    'morning': row["reminder_time"],
                    'evening': row["reminder_time_evening"]
                }
            return reminders
        except sqlite3.Error as e:
            logger.error(f"Failed to get reminder times: {e}", exc_info=True)
            return {}

    def get_all_users(self):
        """Возвращает список всех user_id."""
        try:
            cursor = self.conn.execute("SELECT user_id FROM users")
            return [row["user_id"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get all users: {e}", exc_info=True)
            return []

    def is_card_available(self, user_id, today_date: datetime.date):
        """Проверяет, доступна ли карта дня для пользователя сегодня."""
        user_data = self.get_user(user_id) # Получит datetime объект или None для last_request
        if not user_data:
            return True # Пользователя нет - карта доступна

        last_request_dt = user_data.get("last_request") # Это уже datetime или None

        if isinstance(last_request_dt, datetime):
            # Убедимся, что last_request_dt имеет таймзону для корректного сравнения
            # Конвертеры должны возвращать aware datetime, если возможно
            if last_request_dt.tzinfo is None:
                 # Если таймзоны нет (маловероятно с конвертером), предполагаем UTC
                 # и конвертируем в нужную таймзону для сравнения дат
                 try:
                    last_request_date = last_request_dt.replace(tzinfo=pytz.utc).astimezone(TIMEZONE).date()
                 except NameError: # Если pytz не импортирован
                    logger.warning("pytz not available for timezone conversion in is_card_available. Comparing dates naively.")
                    last_request_date = last_request_dt.date()
            else:
                 # Если таймзона есть, просто конвертируем в нужную
                 try:
                    last_request_date = last_request_dt.astimezone(TIMEZONE).date()
                 except NameError:
                    logger.warning("pytz not available for timezone conversion in is_card_available. Comparing dates naively.")
                    last_request_date = last_request_dt.date()

            return last_request_date < today_date
        return True # Если время не установлено или ошибка парсинга

    # --- Методы для Рефералов ---
    def add_referral(self, referrer_id, referred_id):
        """Добавляет запись о реферале (если такой еще не существует)."""
        try:
            with self.conn:
                cursor = self.conn.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
                if cursor.rowcount > 0:
                    logger.info(f"Referral added: referrer {referrer_id}, referred {referred_id}")
                    return True
                else:
                    logger.info(f"Referral already exists or failed: referrer {referrer_id}, referred {referred_id}")
                    return False
        except sqlite3.Error as e:
            logger.error(f"Failed to add referral ({referrer_id} -> {referred_id}): {e}", exc_info=True)
            return False

    def get_referrals(self, referrer_id):
        """Возвращает список ID пользователей, приглашенных данным пользователем."""
        try:
            cursor = self.conn.execute("SELECT referred_id FROM referrals WHERE referrer_id = ?", (referrer_id,))
            return [row["referred_id"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get referrals for {referrer_id}: {e}", exc_info=True)
            return []

    # --- Методы для Профиля Пользователя ---
    def get_user_profile(self, user_id):
        """Получает профиль пользователя из таблицы user_profiles."""
        try:
            cursor = self.conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                profile_dict = dict(row)
                # Преобразуем last_updated в datetime (если строка)
                last_updated_val = profile_dict.get("last_updated")
                if last_updated_val and isinstance(last_updated_val, str):
                    try:
                        if last_updated_val.endswith('Z'):
                            last_updated_val = last_updated_val[:-1] + '+00:00'
                        profile_dict["last_updated"] = datetime.fromisoformat(last_updated_val)
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error parsing last_updated '{last_updated_val}' for profile user {user_id}: {e}")
                        profile_dict["last_updated"] = None
                elif not isinstance(last_updated_val, datetime):
                    profile_dict["last_updated"] = None

                # Декодируем JSON поля
                for field in ["mood_trend", "themes"]:
                    json_val = profile_dict.get(field)
                    if json_val and isinstance(json_val, str):
                        try:
                            profile_dict[field] = json.loads(json_val)
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(f"Failed to decode JSON for field '{field}' for user {user_id}. Value: {json_val}")
                            profile_dict[field] = [] # Возвращаем пустой список при ошибке
                    elif profile_dict.get(field) is None: # Инициализация пустым списком, если None
                        profile_dict[field] = []

                # Гарантируем наличие новых полей (хотя миграция/схема должны это делать)
                profile_dict.setdefault("initial_resource", None)
                profile_dict.setdefault("final_resource", None)
                profile_dict.setdefault("recharge_method", None)

                return profile_dict
            return None # Профиль не найден
        except sqlite3.Error as e:
            logger.error(f"Failed to get user profile for {user_id}: {e}", exc_info=True)
            return None # Возвращаем None в случае ошибки БД


    def update_user_profile(self, user_id, profile_update_data):
        """Обновляет профиль пользователя (INSERT OR REPLACE)."""
        current_profile = self.get_user_profile(user_id) or {} # Получаем текущий или пустой словарь

        # Обрабатываем время обновления (если не передано, используем текущее)
        last_updated_dt = profile_update_data.get("last_updated", datetime.now(TIMEZONE))
        last_updated_iso = last_updated_dt.isoformat() if isinstance(last_updated_dt, datetime) else datetime.now(TIMEZONE).isoformat()

        # Подготавливаем данные для сохранения, используя текущие значения как fallback
        profile_to_save = {
            "user_id": user_id,
            "mood": profile_update_data.get("mood", current_profile.get("mood")),
            # Обрабатываем JSON поля
            "mood_trend": json.dumps(profile_update_data.get("mood_trend", current_profile.get("mood_trend", []))),
            "themes": json.dumps(profile_update_data.get("themes", current_profile.get("themes", []))),
            # Числовые поля
            "response_count": profile_update_data.get("response_count", current_profile.get("response_count", 0)),
            "request_count": profile_update_data.get("request_count", current_profile.get("request_count", 0)),
            "avg_response_length": profile_update_data.get("avg_response_length", current_profile.get("avg_response_length", 0)),
            "days_active": profile_update_data.get("days_active", current_profile.get("days_active", 0)),
            "interactions_per_day": profile_update_data.get("interactions_per_day", current_profile.get("interactions_per_day", 0)),
            # Время обновления
            "last_updated": last_updated_iso,
            # Новые поля
            "initial_resource": profile_update_data.get("initial_resource", current_profile.get("initial_resource")),
            "final_resource": profile_update_data.get("final_resource", current_profile.get("final_resource")),
            "recharge_method": profile_update_data.get("recharge_method", current_profile.get("recharge_method")),
        }

        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO user_profiles (
                        user_id, mood, mood_trend, themes, response_count, request_count,
                        avg_response_length, days_active, interactions_per_day, last_updated,
                        initial_resource, final_resource, recharge_method
                    ) VALUES (
                        :user_id, :mood, :mood_trend, :themes, :response_count, :request_count,
                        :avg_response_length, :days_active, :interactions_per_day, :last_updated,
                        :initial_resource, :final_resource, :recharge_method
                    )
                """, profile_to_save)
        except sqlite3.Error as e:
            logger.error(f"Failed to update user profile for {user_id}: {e}", exc_info=True)

    # --- Метод для Вечерней Рефлексии ---
    async def save_evening_reflection(self, user_id, date, good_moments, gratitude, hard_moments, created_at):
        """Сохраняет данные вечерней рефлексии в БД."""
        sql = """
            INSERT INTO evening_reflections
            (user_id, date, good_moments, gratitude, hard_moments, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        created_at_str = None
        if isinstance(created_at, datetime):
            created_at_str = created_at.isoformat()
        elif isinstance(created_at, str):
            # Проверяем формат строки ISO
            try:
                datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_at_str = created_at
            except ValueError:
                logger.error(f"Invalid ISO string format for created_at: {created_at}")
        if created_at_str is None:
            logger.error(f"Invalid type or format for created_at in save_evening_reflection: {type(created_at)}. Using current time.")
            created_at_str = datetime.now(TIMEZONE).isoformat() # Fallback

        try:
            with self.conn:
                self.conn.execute(sql, (user_id, date, good_moments, gratitude, hard_moments, created_at_str))
            logger.info(f"Saved evening reflection for user {user_id} for date {date}")
        except sqlite3.Error as e:
            logger.error(f"Failed to save evening reflection for user {user_id}: {e}", exc_info=True)
            raise # Пробрасываем ошибку, чтобы ее можно было обработать выше

    def close(self):
        """Закрывает соединение с базой данных."""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed.")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)

# Импорт pytz нужен здесь для is_card_available и потенциально для других мест
# Делаем его безопасным, если библиотека не установлена
try:
    import pytz
except ImportError:
    pytz = None
    logger.warning("pytz library not found. Timezone conversions might be affected if database stores naive datetimes or if TIMEZONE config is used.")
