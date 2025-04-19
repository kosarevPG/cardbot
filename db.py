# код/db.py
import sqlite3
import json
from datetime import datetime
import os
from config import TIMEZONE
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
        3. Запуск миграций (добавление столбцов/таблиц).
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

            sqlite3.register_adapter(datetime, lambda val: val.isoformat())

            def decode_timestamp(val):
                if val is None: return None
                try:
                    val_str = val.decode('utf-8')
                    if val_str.endswith('Z'): val_str = val_str[:-1] + '+00:00'
                    dt_obj = datetime.fromisoformat(val_str)
                    return dt_obj
                except (ValueError, TypeError, AttributeError) as e:
                    logger.error(f"Error decoding timestamp '{val}': {e}")
                    return None
            sqlite3.register_converter("timestamp", decode_timestamp)

            self.conn.row_factory = sqlite3.Row
            self.bot = None

            # --- Порядок инициализации ---
            self.create_tables()
            self._run_migrations()
            self.create_indexes()

        except sqlite3.Error as e:
            logger.critical(f"Database initialization failed: {e}", exc_info=True)
            raise

    def create_tables(self):
        """Создает все необходимые таблицы с ПОЛНОЙ АКТУАЛЬНОЙ СХЕМОЙ, если они не существуют."""
        logger.info("Ensuring base table structures exist...")
        try:
            with self.conn:
                # --- Users ---
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY, name TEXT, username TEXT,
                        last_request TEXT, reminder_time TEXT, reminder_time_evening TEXT,
                        bonus_available BOOLEAN DEFAULT FALSE
                    )""")
                # --- User Cards ---
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_cards (
                        user_id INTEGER, card_number INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # --- Actions ---
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, name TEXT,
                        action TEXT NOT NULL, details TEXT, timestamp TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # --- Referrals ---
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS referrals (
                        referrer_id INTEGER, referred_id INTEGER UNIQUE,
                        FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
                        FOREIGN KEY (referred_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # --- Feedback ---
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT,
                        feedback TEXT NOT NULL, timestamp TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # --- User Profiles ---
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id INTEGER PRIMARY KEY, mood TEXT, mood_trend TEXT, themes TEXT,
                        response_count INTEGER DEFAULT 0, request_count INTEGER DEFAULT 0,
                        avg_response_length REAL DEFAULT 0, days_active INTEGER DEFAULT 0,
                        interactions_per_day REAL DEFAULT 0, last_updated TEXT,
                        initial_resource TEXT, final_resource TEXT, recharge_method TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # --- Evening Reflections ---
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS evening_reflections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, date TEXT NOT NULL,
                        good_moments TEXT, gratitude TEXT, hard_moments TEXT,
                        created_at TEXT NOT NULL, ai_summary TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # --- <<< НОВАЯ ТАБЛИЦА >>> ---
                # --- User Recharge Methods ---
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_recharge_methods (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        method TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # --- <<< КОНЕЦ НОВОЙ ТАБЛИЦЫ >>> ---

            logger.info("Base table structures checked/created successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error creating base database tables: {e}", exc_info=True)
            raise

    def _run_migrations(self):
        """Добавляет новые столбцы/таблицы в СУЩЕСТВУЮЩИЕ БД."""
        logger.info("Running database migrations...")
        try:
            # --- Добавление столбцов ---
            profile_columns = {'initial_resource': 'TEXT', 'final_resource': 'TEXT', 'recharge_method': 'TEXT'}
            self._add_columns_if_not_exist('user_profiles', profile_columns)
            users_columns = {'reminder_time_evening': 'TEXT'}
            self._add_columns_if_not_exist('users', users_columns)
            reflection_columns = {'ai_summary': 'TEXT'}
            self._add_columns_if_not_exist('evening_reflections', reflection_columns)

            # --- Создание новых таблиц (если их нет в существующей БД) ---
            with self.conn:
                 # Создаем таблицу методов восстановления, если ее еще нет
                 self.conn.execute("""
                     CREATE TABLE IF NOT EXISTS user_recharge_methods (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id INTEGER NOT NULL,
                         method TEXT NOT NULL,
                         timestamp TEXT NOT NULL,
                         FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                     )""")
                 logger.info("Checked/Created 'user_recharge_methods' table during migration.")

            logger.info("Database migrations finished successfully.")
        except Exception as e:
            logger.error(f"Error during database migration process: {e}", exc_info=True)


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
                    try:
                        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                        logger.info(f"Executing migration: {alter_sql}")
                        cursor.execute(alter_sql)
                        logger.info(f"Successfully added column '{col_name}' to {table_name}")
                        added_count += 1
                    except sqlite3.OperationalError as oe:
                        # Игнорируем ошибку "duplicate column name", если миграция запускается повторно
                        if "duplicate column name" in str(oe).lower():
                            logger.warning(f"Column '{col_name}' likely already exists in {table_name} despite PRAGMA result. Ignoring error: {oe}")
                        else:
                            raise oe # Поднимаем другие OperationalError
                else:
                    logger.debug(f"Column '{col_name}' already exists in {table_name}.")

            if added_count > 0:
                self.conn.commit()
                logger.info(f"Committed {added_count} column additions for {table_name}.")

        except sqlite3.Error as e:
            logger.error(f"Database migration error for {table_name} adding columns: {e}", exc_info=True)
            self.conn.rollback()
            raise e

    def create_indexes(self):
        """Создает все необходимые индексы, ЕСЛИ ОНИ НЕ СУЩЕСТВУЮТ."""
        logger.info("Creating database indexes if they don't exist...")
        try:
            with self.conn:
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_user_timestamp ON actions (user_id, timestamp)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_cards_user ON user_cards (user_id)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reminder_time ON users (reminder_time)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reminder_time_evening ON users (reminder_time_evening)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reflections_user_date ON evening_reflections (user_id, date)")
                # --- <<< НОВЫЙ ИНДЕКС >>> ---
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_recharge_user_timestamp ON user_recharge_methods (user_id, timestamp)")
                # --- <<< КОНЕЦ НОВОГО ИНДЕКСА >>> ---

            logger.info("Indexes checked/created successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error creating database indexes: {e}", exc_info=True)

    # --- Методы get_user, update_user, get_user_cards, add_user_card, reset_user_cards ---
    # --- ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ ---
    def get_user(self, user_id):
        # ... (код без изменений) ...
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

                # Гарантируем наличие полей
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
                "reminder_time_evening": None,
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
                     default_user_data["reminder_time_evening"],
                     int(default_user_data["bonus_available"]))
                )
            logger.info(f"Default user entry created for {user_id}")
            return default_user_data
        except sqlite3.Error as e:
            logger.error(f"Failed to get or create user {user_id}: {e}", exc_info=True)
            # Возвращаем дефолтную структуру в памяти в случае ошибки БД
            return {"user_id": user_id, "name": "", "username": "", "last_request": None, "reminder_time": None, "reminder_time_evening": None, "bonus_available": False}

    def update_user(self, user_id, data):
        # ... (код без изменений) ...
        """Обновляет данные пользователя (INSERT OR REPLACE)."""
        current_user_data = self.get_user(user_id)

        # Подготовка данных для сохранения
        name_to_save = data.get("name", current_user_data.get("name", ""))
        username_to_save = data.get("username", current_user_data.get("username", ""))
        reminder_to_save = data.get("reminder_time", current_user_data.get("reminder_time"))
        reminder_evening_to_save = data.get("reminder_time_evening", current_user_data.get("reminder_time_evening"))
        bonus_to_save = data.get("bonus_available", current_user_data.get("bonus_available", False))

        # Обработка last_request
        last_request_to_save = None
        last_request_input = data.get("last_request", current_user_data.get("last_request"))
        if isinstance(last_request_input, datetime):
            last_request_to_save = last_request_input.isoformat()
        elif isinstance(last_request_input, str):
            try:
                datetime.fromisoformat(last_request_input.replace('Z', '+00:00'))
                last_request_to_save = last_request_input
            except (ValueError, TypeError):
                logger.warning(f"Invalid ISO string provided for last_request '{last_request_input}' for user {user_id}. Saving as None.")
                last_request_to_save = None

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
                    int(bonus_to_save)
                ))
        except sqlite3.Error as e:
            logger.error(f"Failed to update user {user_id}: {e}", exc_info=True)

    def get_user_cards(self, user_id):
        # ... (код без изменений) ...
        """Возвращает список номеров карт, использованных пользователем."""
        try:
            cursor = self.conn.execute("SELECT card_number FROM user_cards WHERE user_id = ?", (user_id,))
            return [row["card_number"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get user cards for {user_id}: {e}", exc_info=True)
            return []

    def add_user_card(self, user_id, card_number):
        # ... (код без изменений) ...
        """Добавляет запись об использованной карте."""
        try:
            with self.conn:
                self.conn.execute("INSERT INTO user_cards (user_id, card_number) VALUES (?, ?)", (user_id, card_number))
        except sqlite3.Error as e:
            logger.error(f"Failed to add user card {card_number} for {user_id}: {e}", exc_info=True)

    def reset_user_cards(self, user_id):
        # ... (код без изменений) ...
        """Удаляет все записи об использованных картах для пользователя."""
        try:
            with self.conn:
                self.conn.execute("DELETE FROM user_cards WHERE user_id = ?", (user_id,))
            logger.info(f"Reset used cards for user {user_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to reset user cards for {user_id}: {e}", exc_info=True)

    # --- Методы save_action, get_actions, get_reminder_times, get_all_users, is_card_available ---
    # --- ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ ---
    def save_action(self, user_id, username, name, action, details, timestamp):
        # ... (код без изменений) ...
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
        if timestamp_str is None:
            timestamp_str = datetime.now(TIMEZONE).isoformat()

        details_json = None
        if details is not None:
            try:
                # Улучшенная сериализация для datetime внутри details
                def default_serializer(o):
                    if isinstance(o, datetime):
                        return o.isoformat()
                    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
                details_json = json.dumps(details, ensure_ascii=False, indent=2, default=default_serializer)
            except TypeError as e:
                logger.error(f"Failed to serialize details for action '{action}', user {user_id}: {e}. Details: {details}")
                try:
                     # Попытка сериализовать без datetime
                     safe_details = {k: v for k, v in details.items() if not isinstance(v, datetime)}
                     details_json = json.dumps(safe_details, ensure_ascii=False, indent=2)
                     logger.warning("Serialized details excluding datetime objects.")
                except Exception as final_e:
                     logger.error(f"Final attempt to serialize details failed: {final_e}")
                     details_json = json.dumps({"error": "serialization_failed", "original_details_repr": repr(details)})

        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO actions (user_id, username, name, action, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, username, name, action, details_json, timestamp_str)
                )
        except sqlite3.Error as e:
            logger.error(f"Failed to save action '{action}' for user {user_id}: {e}. Details JSON: {details_json}", exc_info=True)

    def get_actions(self, user_id=None):
        # ... (код без изменений) ...
        """Получает список действий пользователя (или всех), отсортированных по времени."""
        actions = []
        try:
            sql = "SELECT id, user_id, username, name, action, details, timestamp FROM actions"
            params = []
            if user_id:
                sql += " WHERE user_id = ?"
                params.append(user_id)
            sql += " ORDER BY timestamp ASC"

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

                timestamp_str = row_dict.get("timestamp", datetime.min.isoformat())

                actions.append({
                    "id": row_dict.get("id"),
                    "user_id": row_dict.get("user_id"),
                    "username": row_dict.get("username"),
                    "name": row_dict.get("name"),
                    "action": row_dict.get("action"),
                    "details": details_dict,
                    "timestamp": timestamp_str
                })
        except sqlite3.Error as e:
            logger.error(f"Failed to get actions (user_id: {user_id}): {e}", exc_info=True)
        return actions

    def get_reminder_times(self):
        # ... (код без изменений) ...
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
        # ... (код без изменений) ...
        """Возвращает список всех user_id."""
        try:
            cursor = self.conn.execute("SELECT user_id FROM users")
            return [row["user_id"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get all users: {e}", exc_info=True)
            return []

    def is_card_available(self, user_id, today_date: datetime.date):
        # ... (код без изменений) ...
        """Проверяет, доступна ли карта дня для пользователя сегодня."""
        user_data = self.get_user(user_id)
        if not user_data:
            return True

        last_request_dt = user_data.get("last_request")

        if isinstance(last_request_dt, datetime):
            try:
                # Используем TIMEZONE из config
                last_request_date = last_request_dt.astimezone(TIMEZONE).date()
            except Exception as e: # Обработка ошибок таймзоны
                logger.warning(f"Timezone conversion error for user {user_id} in is_card_available: {e}. Comparing naively.")
                last_request_date = last_request_dt.date()
            return last_request_date < today_date
        return True


    # --- Методы для Рефералов (без изменений) ---
    def add_referral(self, referrer_id, referred_id):
        # ... (код без изменений) ...
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
        # ... (код без изменений) ...
        """Возвращает список ID пользователей, приглашенных данным пользователем."""
        try:
            cursor = self.conn.execute("SELECT referred_id FROM referrals WHERE referrer_id = ?", (referrer_id,))
            return [row["referred_id"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get referrals for {referrer_id}: {e}", exc_info=True)
            return []

    # --- Методы для Профиля Пользователя (get_user_profile, update_user_profile) ---
    # --- ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ (update будет вызываться из ai_service с новыми данными) ---
    def get_user_profile(self, user_id):
        # ... (код без изменений) ...
        """Получает профиль пользователя из таблицы user_profiles."""
        try:
            cursor = self.conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                profile_dict = dict(row)
                # Преобразуем last_updated в datetime
                last_updated_val = profile_dict.get("last_updated")
                if last_updated_val and isinstance(last_updated_val, str):
                    try:
                        if last_updated_val.endswith('Z'):
                            last_updated_val = last_updated_val[:-1] + '+00:00'
                        # Делаем aware datetime
                        dt_obj = datetime.fromisoformat(last_updated_val)
                        if dt_obj.tzinfo is None:
                             # Если таймзона отсутствует после парсинга ISO (маловероятно, но возможно)
                             # Лучше считать UTC и конвертировать, чем делать localize
                             profile_dict["last_updated"] = dt_obj.replace(tzinfo=pytz.utc).astimezone(TIMEZONE)
                             logger.warning(f"Parsed naive ISO timestamp for last_updated user {user_id}. Assuming UTC.")
                        else:
                             profile_dict["last_updated"] = dt_obj.astimezone(TIMEZONE) # Конвертируем в TIMEZONE
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error parsing last_updated '{last_updated_val}' for profile user {user_id}: {e}")
                        profile_dict["last_updated"] = None
                elif not isinstance(last_updated_val, datetime):
                    profile_dict["last_updated"] = None
                elif isinstance(last_updated_val, datetime) and last_updated_val.tzinfo is None:
                     # Если в БД сохранился naive datetime (старые данные), локализуем его
                     try:
                         profile_dict["last_updated"] = TIMEZONE.localize(last_updated_val)
                     except Exception as tz_err:
                          logger.error(f"Could not localize naive last_updated from DB for user {user_id}: {tz_err}")
                          # Оставляем naive, build_user_profile должен это учесть

                # Декодируем JSON поля
                for field in ["mood_trend", "themes"]:
                    json_val = profile_dict.get(field)
                    if json_val and isinstance(json_val, str):
                        try:
                            profile_dict[field] = json.loads(json_val)
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(f"Failed to decode JSON for field '{field}' for user {user_id}. Value: {json_val}")
                            profile_dict[field] = []
                    elif profile_dict.get(field) is None:
                        profile_dict[field] = []

                # Гарантируем наличие полей
                profile_dict.setdefault("initial_resource", None)
                profile_dict.setdefault("final_resource", None)
                profile_dict.setdefault("recharge_method", None) # Это поле теперь кэш/старое значение

                return profile_dict
            return None
        except sqlite3.Error as e:
            logger.error(f"Failed to get user profile for {user_id}: {e}", exc_info=True)
            return None

    def update_user_profile(self, user_id, profile_update_data):
        # ... (код без изменений, но теперь обновляет меньше полей напрямую) ...
        """Обновляет профиль пользователя (INSERT OR REPLACE)."""
        current_profile = self.get_user_profile(user_id) or {}

        last_updated_dt = profile_update_data.get("last_updated", datetime.now(TIMEZONE))
        last_updated_iso = last_updated_dt.isoformat() if isinstance(last_updated_dt, datetime) else datetime.now(TIMEZONE).isoformat()

        profile_to_save = {
            "user_id": user_id,
            "mood": profile_update_data.get("mood", current_profile.get("mood")),
            "mood_trend": json.dumps(profile_update_data.get("mood_trend", current_profile.get("mood_trend", []))),
            "themes": json.dumps(profile_update_data.get("themes", current_profile.get("themes", []))),
            "response_count": profile_update_data.get("response_count", current_profile.get("response_count", 0)),
            # request_count, avg_response_length, interactions_per_day УБРАНЫ из этого обновления
            # они будут расчитаны в build_user_profile и сохранены там же, если нужно будет их кэшировать
            "days_active": profile_update_data.get("days_active", current_profile.get("days_active", 0)),
            "last_updated": last_updated_iso,
            "initial_resource": profile_update_data.get("initial_resource", current_profile.get("initial_resource")),
            "final_resource": profile_update_data.get("final_resource", current_profile.get("final_resource")),
            # Обновляем поле recharge_method последним известным значением из build_user_profile
            "recharge_method": profile_update_data.get("recharge_method", current_profile.get("recharge_method")),
        }

        # --- УДАЛЕНИЕ НЕНУЖНЫХ КЛЮЧЕЙ ПЕРЕД ЗАПИСЬЮ ---
        # Убираем поля, которые больше не хранятся или не обновляются напрямую
        keys_to_remove_from_save = ['request_count', 'avg_response_length', 'interactions_per_day']
        for key in keys_to_remove_from_save:
            profile_to_save.pop(key, None) # Удаляем ключ, если он есть

        # --- ФОРМИРОВАНИЕ SQL ---
        columns = ', '.join(profile_to_save.keys())
        placeholders = ', '.join(f':{key}' for key in profile_to_save.keys())
        sql = f"INSERT OR REPLACE INTO user_profiles ({columns}) VALUES ({placeholders})"


        try:
            with self.conn:
                self.conn.execute(sql, profile_to_save)
        except sqlite3.Error as e:
            logger.error(f"Failed to update user profile for {user_id}: {e}. SQL: {sql} Data: {profile_to_save}", exc_info=True)


    # --- Метод для Вечерней Рефлексии (без изменений) ---
    def save_evening_reflection(self, user_id, date, good_moments, gratitude, hard_moments, created_at, ai_summary=None):
        # ... (код без изменений) ...
        """Сохраняет данные вечерней рефлексии в БД, включая AI резюме."""
        sql = """
            INSERT INTO evening_reflections
            (user_id, date, good_moments, gratitude, hard_moments, created_at, ai_summary) -- Добавлено поле
            VALUES (?, ?, ?, ?, ?, ?, ?) -- Добавлен плейсхолдер
        """
        created_at_str = None
        if isinstance(created_at, datetime):
            created_at_str = created_at.isoformat()
        elif isinstance(created_at, str):
            try:
                datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_at_str = created_at
            except ValueError:
                logger.error(f"Invalid ISO string format for created_at: {created_at}")
        if created_at_str is None:
            logger.error(f"Invalid type or format for created_at in save_evening_reflection: {type(created_at)}. Using current time.")
            created_at_str = datetime.now(TIMEZONE).isoformat()

        try:
            with self.conn:
                # Передаем ai_summary (может быть None) как последний параметр
                self.conn.execute(sql, (user_id, date, good_moments, gratitude, hard_moments, created_at_str, ai_summary))
            log_msg = f"Saved evening reflection for user {user_id} for date {date}"
            if ai_summary:
                log_msg += " with AI summary."
            else:
                log_msg += " without AI summary."
            logger.info(log_msg)
        except sqlite3.Error as e:
            logger.error(f"Failed to save evening reflection for user {user_id}: {e}", exc_info=True)
            raise

    # --- <<< НОВЫЕ МЕТОДЫ ДЛЯ СПОСОБОВ ВОССТАНОВЛЕНИЯ >>> ---
    def add_recharge_method(self, user_id: int, method: str, timestamp: str):
        """Добавляет новый способ восстановления ресурса для пользователя."""
        sql = "INSERT INTO user_recharge_methods (user_id, method, timestamp) VALUES (?, ?, ?)"
        try:
            # Проверяем timestamp на валидность ISO формата
            try:
                 datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                 logger.error(f"Invalid timestamp format '{timestamp}' provided to add_recharge_method for user {user_id}. Using current time.")
                 timestamp = datetime.now(TIMEZONE).isoformat()

            with self.conn:
                self.conn.execute(sql, (user_id, method, timestamp))
            logger.info(f"Added recharge method for user {user_id}: '{method}'")
        except sqlite3.Error as e:
            logger.error(f"Failed to add recharge method for user {user_id}: {e}", exc_info=True)

    def get_last_recharge_method(self, user_id: int) -> dict | None:
        """Возвращает последний добавленный способ восстановления для пользователя."""
        sql = "SELECT method, timestamp FROM user_recharge_methods WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1"
        try:
            cursor = self.conn.execute(sql, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get last recharge method for user {user_id}: {e}", exc_info=True)
            return None

    def get_all_recharge_methods(self, user_id: int) -> list[dict]:
         """Возвращает все способы восстановления для пользователя, отсортированные по времени."""
         sql = "SELECT method, timestamp FROM user_recharge_methods WHERE user_id = ? ORDER BY timestamp DESC"
         methods = []
         try:
             cursor = self.conn.execute(sql, (user_id,))
             for row in cursor.fetchall():
                 methods.append(dict(row))
         except sqlite3.Error as e:
             logger.error(f"Failed to get all recharge methods for user {user_id}: {e}", exc_info=True)
         return methods
    # --- <<< КОНЕЦ НОВЫХ МЕТОДОВ >>> ---


    # --- <<< НОВЫЕ МЕТОДЫ ДЛЯ СТАТИСТИКИ РЕФЛЕКСИЙ >>> ---
    def get_last_reflection_date(self, user_id: int) -> str | None:
         """Возвращает дату ('YYYY-MM-DD') последней рефлексии пользователя."""
         sql = "SELECT date FROM evening_reflections WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 1"
         try:
              cursor = self.conn.execute(sql, (user_id,))
              row = cursor.fetchone()
              return row['date'] if row else None
         except sqlite3.Error as e:
              logger.error(f"Failed to get last reflection date for user {user_id}: {e}", exc_info=True)
              return None

    def count_reflections(self, user_id: int) -> int:
         """Возвращает общее количество рефлексий пользователя."""
         sql = "SELECT COUNT(id) as count FROM evening_reflections WHERE user_id = ?"
         try:
              cursor = self.conn.execute(sql, (user_id,))
              row = cursor.fetchone()
              return row['count'] if row else 0
         except sqlite3.Error as e:
              logger.error(f"Failed to count reflections for user {user_id}: {e}", exc_info=True)
              return 0

    def get_all_reflection_texts(self, user_id: int, limit: int = 10) -> list[dict]:
         """Возвращает тексты последних N рефлексий для анализа."""
         sql = """
             SELECT good_moments, gratitude, hard_moments
             FROM evening_reflections
             WHERE user_id = ?
             ORDER BY date DESC, id DESC
             LIMIT ?
         """
         texts = []
         try:
             cursor = self.conn.execute(sql, (user_id, limit))
             for row in cursor.fetchall():
                 texts.append(dict(row))
         except sqlite3.Error as e:
             logger.error(f"Failed to get reflection texts for user {user_id}: {e}", exc_info=True)
         return texts
    # --- <<< КОНЕЦ НОВЫХ МЕТОДОВ >>> ---


    def close(self):
        # ... (код без изменений) ...
        """Закрывает соединение с базой данных."""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed.")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)

# Импорт pytz (без изменений)
try:
    import pytz
except ImportError:
    pytz = None
    logger.warning("pytz library not found. Timezone conversions might be affected.")
