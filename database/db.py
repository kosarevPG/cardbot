# код/db.py
import sqlite3
import json
from datetime import datetime, date
import os
try:
    from config_local import TIMEZONE
except ImportError:
    from config import TIMEZONE
import logging

# Импорт pytz для обработки таймзон
try:
    import pytz
except ImportError:
    pytz = None
    logging.warning("pytz library not found. Timezone conversions might be affected.")

logger = logging.getLogger(__name__)

# --- КЛАСС Database ---
class Database:
    def __init__(self, path="/data/bot.db"):
        """
        Инициализация соединения с БД.
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
            # Используем нужные detect_types
            self.conn = sqlite3.connect(path, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            logger.info(f"Database connection initialized at path: {path}")

            # Адаптеры для сохранения datetime и date как ISO строк
            sqlite3.register_adapter(datetime, lambda val: val.isoformat())
            sqlite3.register_adapter(date, lambda val: val.isoformat())

            # --- ИЗМЕНЕНИЕ: Регистрируем конвертеры как методы класса ---
            sqlite3.register_converter("timestamp", self.decode_timestamp)
            sqlite3.register_converter("DATE", self.decode_date)
            # --- КОНЕЦ ИЗМЕНЕНИЯ ---

            self.conn.row_factory = sqlite3.Row
            self.bot = None # Устанавливается в main.py

            self.create_tables()
            self._run_migrations()
            self.create_indexes()

        except sqlite3.Error as e:
            logger.critical(f"Database initialization failed: Could not connect or setup tables/migrations/indexes at {path}. Error: {e}", exc_info=True)
            raise

    # --- КОНВЕРТЕРЫ ВЫНЕСЕНЫ КАК МЕТОДЫ КЛАССА ---
    def decode_timestamp(self, val):
        if val is None: return None
        try:
            val_str = val.decode('utf-8')
            if val_str.endswith('Z'): val_str = val_str[:-1] + '+00:00'
            return datetime.fromisoformat(val_str)
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"Error decoding timestamp '{val}': {e}")
            return None

    def decode_date(self, val):
        if val is None: return None
        try:
            return date.fromisoformat(val.decode('utf-8'))
        except (ValueError, TypeError) as e:
            logger.error(f"Error decoding date '{val}': {e}")
            return None
    # --- КОНЕЦ КОНВЕРТЕРОВ ---

    # ... (остальные методы класса Database без изменений) ...
    # create_tables, _run_migrations, _add_columns_if_not_exist, create_indexes,
    # get_user, update_user, get_user_cards, count_user_cards, add_user_card,
    # reset_user_cards, save_action, get_actions, get_reminder_times,
    # get_all_users, is_card_available, add_referral, get_referrals,
    # get_user_profile, update_user_profile, save_evening_reflection,
    # get_last_reflection_date, count_reflections, get_all_reflection_texts,
    # add_recharge_method, get_last_recharge_method, close

    def create_tables(self):
        # ... (код create_tables без изменений) ...
        """Создает все необходимые таблицы с ПОЛНОЙ АКТУАЛЬНОЙ СХЕМОЙ, если они не существуют."""
        logger.info("Ensuring base table structures exist...")
        try:
            with self.conn:
                # Таблица users
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY, name TEXT, username TEXT,
                        last_request TEXT, reminder_time TEXT,
                        reminder_time_evening TEXT, bonus_available BOOLEAN DEFAULT FALSE
                    )""")
                # Таблица user_cards
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_cards (
                        user_id INTEGER, card_number INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # Таблица actions
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, name TEXT,
                        action TEXT NOT NULL, details TEXT, timestamp TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # Таблица referrals
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS referrals (
                        referrer_id INTEGER, referred_id INTEGER UNIQUE,
                        FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
                        FOREIGN KEY (referred_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # Таблица feedback
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT,
                        feedback TEXT NOT NULL, timestamp TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # Таблица user_profiles
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id INTEGER PRIMARY KEY, mood TEXT, mood_trend TEXT, themes TEXT,
                        response_count INTEGER DEFAULT 0, request_count INTEGER DEFAULT 0,
                        avg_response_length REAL DEFAULT 0, days_active INTEGER DEFAULT 0,
                        interactions_per_day REAL DEFAULT 0, last_updated TEXT,
                        initial_resource TEXT, final_resource TEXT, recharge_method TEXT,
                        total_cards_drawn INTEGER DEFAULT 0,
                        last_reflection_date TEXT,
                        reflection_count INTEGER DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # Таблица evening_reflections
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS evening_reflections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                        date TEXT NOT NULL, good_moments TEXT, gratitude TEXT, -- date здесь TEXT
                        hard_moments TEXT, created_at TEXT NOT NULL, ai_summary TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                # Таблица user_recharge_methods
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_recharge_methods (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        method TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                
                # Таблица scenario_logs - детальное логирование шагов сценариев
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS scenario_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        scenario TEXT NOT NULL,
                        step TEXT NOT NULL,
                        metadata TEXT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                
                # Таблица user_scenarios - общая статистика по сценариям
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_scenarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        scenario TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        steps_count INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'in_progress',
                        session_id TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")
                
                # Таблица user_requests - текстовые запросы пользователей к картам
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        request_text TEXT NOT NULL,
                        session_id TEXT,
                        card_number INTEGER,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )""")

            logger.info("Base table structures checked/created successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error creating base database tables: {e}", exc_info=True)
            raise

    def _run_migrations(self):
        # ... (код миграций без изменений) ...
        """Добавляет новые столбцы в СУЩЕСТВУЮЩИЕ таблицы (ALTER TABLE), если их нет."""
        logger.info("Running database migrations (checking for missing columns)...")
        try:
            profile_columns = {
                'initial_resource': 'TEXT', 'final_resource': 'TEXT', 'recharge_method': 'TEXT',
                'total_cards_drawn': 'INTEGER DEFAULT 0', 'last_reflection_date': 'TEXT',
                'reflection_count': 'INTEGER DEFAULT 0',
            }
            self._add_columns_if_not_exist('user_profiles', profile_columns)
            users_columns = { 'reminder_time_evening': 'TEXT' }
            self._add_columns_if_not_exist('users', users_columns)
            reflection_columns = { 'ai_summary': 'TEXT' }
            self._add_columns_if_not_exist('evening_reflections', reflection_columns)
            logger.info("Database migrations finished successfully.")
        except Exception as e:
            logger.error(f"Error during database migration process: {e}", exc_info=True)

    def _add_columns_if_not_exist(self, table_name, columns_to_add):
        # ... (код без изменений) ...
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
        # ... (код без изменений) ...
        """Создает все необходимые индексы, ЕСЛИ ОНИ НЕ СУЩЕСТВУЮТ."""
        logger.info("Creating database indexes if they don't exist...")
        try:
            with self.conn:
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_user_timestamp ON actions (user_id, timestamp)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_cards_user ON user_cards (user_id)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reminder_time ON users (reminder_time)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reminder_time_evening ON users (reminder_time_evening)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reflections_user_date ON evening_reflections (user_id, date)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_recharge_user_timestamp ON user_recharge_methods (user_id, timestamp)")
                
                # Индексы для новых таблиц логирования сценариев
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_scenario_logs_user_scenario ON scenario_logs (user_id, scenario)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_scenario_logs_timestamp ON scenario_logs (timestamp)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_scenarios_user_scenario ON user_scenarios (user_id, scenario)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_scenarios_status ON user_scenarios (status)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_scenarios_started_at ON user_scenarios (started_at)")
            logger.info("Indexes checked/created successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error creating database indexes: {e}", exc_info=True)

    def get_user(self, user_id):
        # ... (код метода get_user) ...
        """Получает данные пользователя. Если не найден, создает запись."""
        try:
            cursor = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_dict = dict(row)
                last_request_val = user_dict.get("last_request")
                if last_request_val and isinstance(last_request_val, str):
                    try:
                        # Декодируем явно, т.к. тип TEXT
                        user_dict["last_request"] = self.decode_timestamp(last_request_val.encode('utf-8'))
                    except Exception as e:
                         logger.error(f"Error decoding last_request '{last_request_val}' for user {user_id}: {e}")
                         user_dict["last_request"] = None
                elif not isinstance(last_request_val, datetime):
                     user_dict["last_request"] = None

                user_dict.setdefault("bonus_available", False)
                user_dict.setdefault("reminder_time_evening", None)
                user_dict["bonus_available"] = bool(user_dict["bonus_available"])
                return user_dict

            logger.info(f"User {user_id} not found in 'users' table, creating default entry.")
            default_user_data = {
                "user_id": user_id, "name": "", "username": "", "last_request": None,
                "reminder_time": None, "reminder_time_evening": None, "bonus_available": False
            }
            with self.conn:
                self.conn.execute(
                    """INSERT INTO users (user_id, name, username, last_request, reminder_time, reminder_time_evening, bonus_available)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, default_user_data["name"], default_user_data["username"], None,
                     default_user_data["reminder_time"], default_user_data["reminder_time_evening"],
                     int(default_user_data["bonus_available"]))
                )
            logger.info(f"Default user entry created for {user_id}")
            return default_user_data
        except sqlite3.Error as e:
            logger.error(f"Failed to get or create user {user_id}: {e}", exc_info=True)
            return {"user_id": user_id, "name": "", "username": "", "last_request": None, "reminder_time": None, "reminder_time_evening": None, "bonus_available": False}

    def update_user(self, user_id, data):
        # ... (код метода update_user) ...
        """Обновляет данные пользователя (INSERT OR REPLACE)."""
        current_user_data = self.get_user(user_id)
        name_to_save = data.get("name", current_user_data.get("name", ""))
        username_to_save = data.get("username", current_user_data.get("username", ""))
        reminder_to_save = data.get("reminder_time", current_user_data.get("reminder_time"))
        reminder_evening_to_save = data.get("reminder_time_evening", current_user_data.get("reminder_time_evening"))
        bonus_to_save = data.get("bonus_available", current_user_data.get("bonus_available", False))
        last_request_to_save = None
        last_request_input = data.get("last_request", current_user_data.get("last_request"))
        if isinstance(last_request_input, datetime):
            last_request_to_save = last_request_input.isoformat()
        elif isinstance(last_request_input, str):
             last_request_to_save = last_request_input
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO users (user_id, name, username, last_request, reminder_time, reminder_time_evening, bonus_available)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, ( user_id, name_to_save, username_to_save, last_request_to_save,
                       reminder_to_save, reminder_evening_to_save, int(bonus_to_save) ))
        except sqlite3.Error as e:
            logger.error(f"Failed to update user {user_id}: {e}", exc_info=True)


    def get_user_cards(self, user_id):
        # ... (код метода get_user_cards) ...
        """Возвращает список номеров карт, использованных пользователем."""
        try:
            cursor = self.conn.execute("SELECT card_number FROM user_cards WHERE user_id = ?", (user_id,))
            return [row["card_number"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get user cards for {user_id}: {e}", exc_info=True)
            return []

    def count_user_cards(self, user_id):
        # ... (код метода count_user_cards) ...
        """Возвращает количество карт, вытянутых пользователем."""
        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to count user cards for {user_id}: {e}", exc_info=True)
            return 0

    def add_user_card(self, user_id, card_number):
        # ... (код метода add_user_card) ...
        """Добавляет запись об использованной карте."""
        try:
            with self.conn:
                self.conn.execute("INSERT INTO user_cards (user_id, card_number) VALUES (?, ?)", (user_id, card_number))
        except sqlite3.Error as e:
            logger.error(f"Failed to add user card {card_number} for {user_id}: {e}", exc_info=True)

    def reset_user_cards(self, user_id):
        # ... (код метода reset_user_cards) ...
        """Удаляет все записи об использованных картах для пользователя."""
        try:
            with self.conn:
                self.conn.execute("DELETE FROM user_cards WHERE user_id = ?", (user_id,))
            logger.info(f"Reset used cards for user {user_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to reset user cards for {user_id}: {e}", exc_info=True)

    def save_action(self, user_id, username, name, action, details, timestamp):
        # ... (код метода save_action) ...
        """Сохраняет запись о действии пользователя."""
        timestamp_str = None
        if isinstance(timestamp, datetime): timestamp_str = timestamp.isoformat()
        elif isinstance(timestamp, str): timestamp_str = timestamp
        else: timestamp_str = datetime.now(TIMEZONE).isoformat()
        details_json = None
        if details is not None:
            try: details_json = json.dumps(details, ensure_ascii=False, indent=2)
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
        # ... (код метода get_actions) ...
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
                    try: details_dict = json.loads(row_dict["details"])
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to decode details JSON for action ID {row_dict.get('id')}, user {row_dict.get('user_id')}: {e}. Raw details: {row_dict['details']}")
                        details_dict = {"error": "invalid_json", "raw_details": row_dict["details"]}
                timestamp_str = row_dict.get("timestamp", datetime.min.isoformat())
                actions.append({
                    "id": row_dict.get("id"), "user_id": row_dict.get("user_id"),
                    "username": row_dict.get("username"), "name": row_dict.get("name"),
                    "action": row_dict.get("action"), "details": details_dict,
                    "timestamp": timestamp_str
                })
        except sqlite3.Error as e:
            logger.error(f"Failed to get actions (user_id: {user_id}): {e}", exc_info=True)
        return actions

    def get_reminder_times(self):
        # ... (код метода get_reminder_times) ...
        """Возвращает словарь {user_id: {'morning': time, 'evening': time}} для пользователей с установленными напоминаниями."""
        reminders = {}
        try:
            cursor = self.conn.execute("""
                SELECT user_id, reminder_time, reminder_time_evening
                FROM users WHERE reminder_time IS NOT NULL OR reminder_time_evening IS NOT NULL
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
        # ... (код метода get_all_users) ...
        """Возвращает список всех user_id."""
        try:
            cursor = self.conn.execute("SELECT user_id FROM users")
            return [row["user_id"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get all users: {e}", exc_info=True)
            return []

    def is_card_available(self, user_id, today_date: date):
        # ... (код метода is_card_available) ...
        """Проверяет, доступна ли карта дня для пользователя сегодня."""
        user_data = self.get_user(user_id)
        if not user_data: return True
        last_request_dt = user_data.get("last_request") # datetime или None
        if isinstance(last_request_dt, datetime):
            try:
                last_request_date = last_request_dt.astimezone(TIMEZONE).date() if pytz else last_request_dt.date()
            except Exception as e:
                logger.warning(f"Timezone/Date conversion error for last_request user {user_id}: {e}. Comparing naively.")
                last_request_date = last_request_dt.date()
            return last_request_date < today_date
        return True

    def add_referral(self, referrer_id, referred_id):
        # ... (код метода add_referral) ...
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
        # ... (код метода get_referrals) ...
        """Возвращает список ID пользователей, приглашенных данным пользователем."""
        try:
            cursor = self.conn.execute("SELECT referred_id FROM referrals WHERE referrer_id = ?", (referrer_id,))
            return [row["referred_id"] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get referrals for {referrer_id}: {e}", exc_info=True)
            return []

    def get_user_profile(self, user_id):
        # ... (код метода get_user_profile) ...
        """Получает профиль пользователя из таблицы user_profiles."""
        try:
            cursor = self.conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                profile_dict = dict(row)
                last_updated_val = profile_dict.get("last_updated")
                if last_updated_val and isinstance(last_updated_val, str):
                    try: profile_dict["last_updated"] = self.decode_timestamp(last_updated_val.encode('utf-8'))
                    except Exception as e:
                         logger.error(f"Error decoding last_updated '{last_updated_val}' for profile user {user_id}: {e}")
                         profile_dict["last_updated"] = None
                elif not isinstance(last_updated_val, datetime): profile_dict["last_updated"] = None

                last_reflection_str = profile_dict.get("last_reflection_date")
                if last_reflection_str and isinstance(last_reflection_str, str):
                     try: profile_dict["last_reflection_date"] = date.fromisoformat(last_reflection_str)
                     except (ValueError, TypeError) as e:
                         logger.error(f"Error parsing last_reflection_date string '{last_reflection_str}' for user {user_id}: {e}")
                         profile_dict["last_reflection_date"] = None
                elif not isinstance(last_reflection_str, date): profile_dict["last_reflection_date"] = None

                for field in ["mood_trend", "themes"]:
                    json_val = profile_dict.get(field)
                    if json_val and isinstance(json_val, str):
                        try: profile_dict[field] = json.loads(json_val)
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(f"Failed to decode JSON for field '{field}' for user {user_id}. Value: {json_val}")
                            profile_dict[field] = []
                    elif profile_dict.get(field) is None: profile_dict[field] = []

                profile_dict.setdefault("initial_resource", None)
                profile_dict.setdefault("final_resource", None)
                profile_dict.setdefault("recharge_method", None)
                profile_dict["response_count"] = profile_dict.get("response_count") or 0
                profile_dict["request_count"] = profile_dict.get("request_count") or 0
                profile_dict["avg_response_length"] = profile_dict.get("avg_response_length") or 0.0
                profile_dict["days_active"] = profile_dict.get("days_active") or 0
                profile_dict["interactions_per_day"] = profile_dict.get("interactions_per_day") or 0.0
                profile_dict["total_cards_drawn"] = profile_dict.get("total_cards_drawn") or 0
                profile_dict["reflection_count"] = profile_dict.get("reflection_count") or 0

                return profile_dict
            return None
        except sqlite3.Error as e:
            logger.error(f"Failed to get user profile for {user_id}: {e}", exc_info=True)
            return None

    def update_user_profile(self, user_id, profile_update_data):
        # ... (код метода update_user_profile) ...
        """Обновляет профиль пользователя (INSERT OR REPLACE)."""
        current_profile = self.get_user_profile(user_id) or {}
        last_updated_dt = profile_update_data.get("last_updated", datetime.now(TIMEZONE))
        last_updated_iso = last_updated_dt.isoformat() if isinstance(last_updated_dt, datetime) else datetime.now(TIMEZONE).isoformat()
        last_reflection_date_to_save = None
        last_reflection_input = profile_update_data.get("last_reflection_date", current_profile.get("last_reflection_date"))
        if isinstance(last_reflection_input, date): last_reflection_date_to_save = last_reflection_input.isoformat()
        elif isinstance(last_reflection_input, str): last_reflection_date_to_save = last_reflection_input

        profile_to_save = {
            "user_id": user_id,
            "mood": profile_update_data.get("mood", current_profile.get("mood")),
            "mood_trend": json.dumps(profile_update_data.get("mood_trend", current_profile.get("mood_trend", []))),
            "themes": json.dumps(profile_update_data.get("themes", current_profile.get("themes", []))),
            "response_count": profile_update_data.get("response_count", current_profile.get("response_count", 0)),
            "request_count": profile_update_data.get("request_count", current_profile.get("request_count", 0)),
            "avg_response_length": profile_update_data.get("avg_response_length", current_profile.get("avg_response_length", 0.0)),
            "days_active": profile_update_data.get("days_active", current_profile.get("days_active", 0)),
            "interactions_per_day": profile_update_data.get("interactions_per_day", current_profile.get("interactions_per_day", 0.0)),
            "last_updated": last_updated_iso,
            "initial_resource": profile_update_data.get("initial_resource", current_profile.get("initial_resource")),
            "final_resource": profile_update_data.get("final_resource", current_profile.get("final_resource")),
            "recharge_method": profile_update_data.get("recharge_method", current_profile.get("recharge_method")),
            "total_cards_drawn": profile_update_data.get("total_cards_drawn", current_profile.get("total_cards_drawn", 0)),
            "last_reflection_date": last_reflection_date_to_save,
            "reflection_count": profile_update_data.get("reflection_count", current_profile.get("reflection_count", 0)),
        }
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO user_profiles (
                        user_id, mood, mood_trend, themes, response_count, request_count,
                        avg_response_length, days_active, interactions_per_day, last_updated,
                        initial_resource, final_resource, recharge_method, total_cards_drawn,
                        last_reflection_date, reflection_count
                    ) VALUES (
                        :user_id, :mood, :mood_trend, :themes, :response_count, :request_count,
                        :avg_response_length, :days_active, :interactions_per_day, :last_updated,
                        :initial_resource, :final_resource, :recharge_method, :total_cards_drawn,
                        :last_reflection_date, :reflection_count
                    )
                """, profile_to_save)
        except sqlite3.Error as e:
            logger.error(f"Failed to update user profile for {user_id}: {e}", exc_info=True)

    def save_evening_reflection(self, user_id, date, good_moments, gratitude, hard_moments, created_at, ai_summary=None):
        # ... (код метода save_evening_reflection) ...
        """Сохраняет данные вечерней рефлексии в БД, включая AI резюме."""
        sql = """
            INSERT INTO evening_reflections
            (user_id, date, good_moments, gratitude, hard_moments, created_at, ai_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        created_at_str = None
        if isinstance(created_at, datetime): created_at_str = created_at.isoformat()
        elif isinstance(created_at, str): created_at_str = created_at
        else: created_at_str = datetime.now(TIMEZONE).isoformat()
        date_str = date if isinstance(date, str) else (date.isoformat() if isinstance(date, (date, datetime)) else datetime.now(TIMEZONE).strftime('%Y-%m-%d'))
        try:
            with self.conn:
                self.conn.execute(sql, (user_id, date_str, good_moments, gratitude, hard_moments, created_at_str, ai_summary))
            log_msg = f"Saved evening reflection for user {user_id} for date {date_str}"
            log_msg += " with AI summary." if ai_summary else " without AI summary."
            logger.info(log_msg)
        except sqlite3.Error as e:
            logger.error(f"Failed to save evening reflection for user {user_id}: {e}", exc_info=True)
            raise

    def get_last_reflection_date(self, user_id) -> date | None:
        # ... (код метода get_last_reflection_date) ...
        """Возвращает дату последней рефлексии пользователя как объект date."""
        try:
            cursor = self.conn.execute(
                "SELECT date FROM evening_reflections WHERE user_id = ? ORDER BY date DESC LIMIT 1",
                 (user_id,)
            )
            row = cursor.fetchone()
            if row and row["date"]:
                try: return date.fromisoformat(row["date"])
                except (ValueError, TypeError) as e:
                    logger.error(f"Could not parse date string '{row['date']}' from DB for user {user_id}: {e}")
                    return None
            return None
        except sqlite3.Error as e:
            logger.error(f"Failed to get last reflection date for {user_id}: {e}", exc_info=True)
            return None

    def count_reflections(self, user_id):
        # ... (код метода count_reflections) ...
        """Возвращает общее количество рефлексий пользователя."""
        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM evening_reflections WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to count reflections for {user_id}: {e}", exc_info=True)
            return 0

    def get_all_reflection_texts(self, user_id, limit=10) -> list[dict]:
        # ... (код метода get_all_reflection_texts) ...
        """Возвращает тексты последних N рефлексий."""
        texts = []
        try:
            cursor = self.conn.execute(
                """SELECT good_moments, gratitude, hard_moments
                   FROM evening_reflections
                   WHERE user_id = ? ORDER BY date DESC LIMIT ?""",
                (user_id, limit)
            )
            for row in cursor.fetchall(): texts.append(dict(row))
            return texts
        except sqlite3.Error as e:
            logger.error(f"Failed to get reflection texts for {user_id}: {e}", exc_info=True)
            return []

    def add_recharge_method(self, user_id, method, timestamp):
        # ... (код метода add_recharge_method) ...
        """Добавляет новый способ восстановления ресурса в таблицу user_recharge_methods."""
        timestamp_str = timestamp if isinstance(timestamp, str) else (timestamp.isoformat() if isinstance(timestamp, datetime) else datetime.now(TIMEZONE).isoformat())
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO user_recharge_methods (user_id, method, timestamp) VALUES (?, ?, ?)",
                    (user_id, method, timestamp_str)
                )
            logger.info(f"Added recharge method for user {user_id}: {method}")
        except sqlite3.Error as e:
            logger.error(f"Failed to add recharge method for user {user_id}: {e}", exc_info=True)

    def get_last_recharge_method(self, user_id) -> str | None:
        # ... (код метода get_last_recharge_method) ...
        """Возвращает последний добавленный способ восстановления ресурса."""
        try:
            cursor = self.conn.execute(
                "SELECT method FROM user_recharge_methods WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
                (user_id,)
            )
            row = cursor.fetchone()
            return row["method"] if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get last recharge method for user {user_id}: {e}", exc_info=True)
            return None

    # --- МЕТОДЫ ДЛЯ ЛОГИРОВАНИЯ СЦЕНАРИЕВ ---
    
    def log_scenario_step(self, user_id: int, scenario: str, step: str, metadata: dict = None):
        """Логирует шаг сценария с метаданными."""
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            with self.conn:
                self.conn.execute(
                    "INSERT INTO scenario_logs (user_id, scenario, step, metadata) VALUES (?, ?, ?, ?)",
                    (user_id, scenario, step, metadata_json)
                )
            logger.debug(f"Logged scenario step: user={user_id}, scenario={scenario}, step={step}")
        except sqlite3.Error as e:
            logger.error(f"Failed to log scenario step for user {user_id}: {e}", exc_info=True)

    def save_user_request(self, user_id: int, request_text: str, session_id: str = None, card_number: int = None):
        """Сохраняет текстовый запрос пользователя для анализа."""
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO user_requests (user_id, request_text, session_id, card_number, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
                    (user_id, request_text, session_id, card_number)
                )
            logger.info(f"Saved user request: user={user_id}, length={len(request_text)}")
        except sqlite3.Error as e:
            logger.error(f"Failed to save user request for user {user_id}: {e}", exc_info=True)

    def get_user_requests_stats(self, days: int = 7):
        """Получает статистику по запросам пользователей."""
        try:
            # Получаем список исключаемых пользователей
            try:
                from config_local import NO_LOGS_USERS
            except ImportError:
                from config import NO_LOGS_USERS
            
            excluded_users = NO_LOGS_USERS if NO_LOGS_USERS else []
            excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
            
            # Общая статистика
            params = list(excluded_users) if excluded_users else []
            cursor = self.conn.execute(f"""
                SELECT 
                    COUNT(*) as total_requests,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(LENGTH(request_text)) as avg_length,
                    MIN(LENGTH(request_text)) as min_length,
                    MAX(LENGTH(request_text)) as max_length
                FROM user_requests 
                WHERE timestamp >= datetime('now', '-{days} days')
                {excluded_condition}
            """, params)
            
            stats = cursor.fetchone()
            return {
                'total_requests': stats['total_requests'],
                'unique_users': stats['unique_users'],
                'avg_length': round(stats['avg_length'], 1) if stats['avg_length'] else 0,
                'min_length': stats['min_length'] or 0,
                'max_length': stats['max_length'] or 0
            }
        except sqlite3.Error as e:
            logger.error(f"Failed to get user requests stats: {e}", exc_info=True)
            return {}

    def get_user_requests_sample(self, limit: int = 10, days: int = 7):
        """Получает образец запросов пользователей для анализа."""
        try:
            # Получаем список исключаемых пользователей
            try:
                from config_local import NO_LOGS_USERS
            except ImportError:
                from config import NO_LOGS_USERS
            
            excluded_users = NO_LOGS_USERS if NO_LOGS_USERS else []
            excluded_condition = f"AND ur.user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
            
            params = list(excluded_users) if excluded_users else []
            cursor = self.conn.execute(f"""
                SELECT 
                    ur.request_text,
                    ur.timestamp,
                    ur.card_number,
                    ur.user_id,
                    u.name as user_name,
                    u.username as user_username
                FROM user_requests ur
                LEFT JOIN users u ON ur.user_id = u.user_id
                WHERE ur.timestamp >= datetime('now', '-{days} days')
                {excluded_condition}
                ORDER BY ur.timestamp DESC
                LIMIT ?
            """, params + [limit])
            
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get user requests sample: {e}", exc_info=True)
            return []

    def get_user_requests_by_user(self, user_id: int, limit: int = 10):
        """Получает запросы конкретного пользователя."""
        try:
            cursor = self.conn.execute("""
                SELECT 
                    request_text,
                    timestamp,
                    card_number,
                    session_id
                FROM user_requests
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get user requests for user {user_id}: {e}", exc_info=True)
            return []

    def start_user_scenario(self, user_id: int, scenario: str, session_id: str = None):
        """Начинает новый сценарий для пользователя."""
        try:
            if session_id is None:
                session_id = f"{user_id}_{scenario}_{datetime.now(TIMEZONE).strftime('%Y%m%d_%H%M%S')}"
            
            with self.conn:
                self.conn.execute(
                    "INSERT INTO user_scenarios (user_id, scenario, started_at, status, session_id) VALUES (?, ?, ?, ?, ?)",
                    (user_id, scenario, datetime.now(TIMEZONE).isoformat(), 'in_progress', session_id)
                )
            logger.info(f"Started scenario: user={user_id}, scenario={scenario}, session={session_id}")
            return session_id
        except sqlite3.Error as e:
            logger.error(f"Failed to start scenario for user {user_id}: {e}", exc_info=True)
            return None

    def complete_user_scenario(self, user_id: int, scenario: str, session_id: str = None):
        """Завершает сценарий пользователя."""
        try:
            # Подсчитываем количество шагов
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM scenario_logs WHERE user_id = ? AND scenario = ?",
                (user_id, scenario)
            )
            steps_count = cursor.fetchone()[0]
            
            # Обновляем статус сценария
            if session_id:
                where_clause = "user_id = ? AND scenario = ? AND session_id = ? AND status = 'in_progress'"
                params = (user_id, scenario, session_id)
            else:
                where_clause = "user_id = ? AND scenario = ? AND status = 'in_progress'"
                params = (user_id, scenario)
            
            with self.conn:
                self.conn.execute(
                    f"UPDATE user_scenarios SET completed_at = ?, status = 'completed', steps_count = ? WHERE {where_clause}",
                    (datetime.now(TIMEZONE).isoformat(), steps_count, *params)
                )
            logger.info(f"Completed scenario: user={user_id}, scenario={scenario}, steps={steps_count}")
        except sqlite3.Error as e:
            logger.error(f"Failed to complete scenario for user {user_id}: {e}", exc_info=True)

    def abandon_user_scenario(self, user_id: int, scenario: str, session_id: str = None):
        """Отмечает сценарий как брошенный."""
        try:
            if session_id:
                where_clause = "user_id = ? AND scenario = ? AND session_id = ? AND status = 'in_progress'"
                params = (user_id, scenario, session_id)
            else:
                where_clause = "user_id = ? AND scenario = ? AND status = 'in_progress'"
                params = (user_id, scenario)
            
            with self.conn:
                self.conn.execute(
                    f"UPDATE user_scenarios SET status = 'abandoned' WHERE {where_clause}",
                    params
                )
            logger.info(f"Abandoned scenario: user={user_id}, scenario={scenario}")
        except sqlite3.Error as e:
            logger.error(f"Failed to abandon scenario for user {user_id}: {e}", exc_info=True)

    def get_scenario_stats(self, scenario: str, days: int = 7):
        """Получает статистику по сценарию за последние N дней."""
        try:
            # Получаем список исключаемых пользователей
            try:
                from config_local import NO_LOGS_USERS
            except ImportError:
                from config import NO_LOGS_USERS
            
            excluded_users = NO_LOGS_USERS if NO_LOGS_USERS else []
            excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
            
            # Общее количество запусков
            params = [scenario] + (excluded_users if excluded_users else [])
            cursor = self.conn.execute(
                f"SELECT COUNT(*) FROM user_scenarios WHERE scenario = ? AND started_at >= datetime('now', '-{days} days') {excluded_condition}",
                params
            )
            total_starts = cursor.fetchone()[0]
            
            # Количество завершений
            cursor = self.conn.execute(
                f"SELECT COUNT(*) FROM user_scenarios WHERE scenario = ? AND status = 'completed' AND started_at >= datetime('now', '-{days} days') {excluded_condition}",
                params
            )
            total_completions = cursor.fetchone()[0]
            
            # Количество брошенных
            cursor = self.conn.execute(
                f"SELECT COUNT(*) FROM user_scenarios WHERE scenario = ? AND status = 'abandoned' AND started_at >= datetime('now', '-{days} days') {excluded_condition}",
                params
            )
            total_abandoned = cursor.fetchone()[0]
            
            # Среднее количество шагов для завершенных сценариев
            cursor = self.conn.execute(
                f"SELECT AVG(steps_count) FROM user_scenarios WHERE scenario = ? AND status = 'completed' AND started_at >= datetime('now', '-{days} days') {excluded_condition}",
                params
            )
            avg_steps = cursor.fetchone()[0] or 0
            
            return {
                'scenario': scenario,
                'period_days': days,
                'total_starts': total_starts,
                'total_completions': total_completions,
                'total_abandoned': total_abandoned,
                'completion_rate': (total_completions / total_starts * 100) if total_starts > 0 else 0,
                'abandonment_rate': (total_abandoned / total_starts * 100) if total_starts > 0 else 0,
                'avg_steps': round(avg_steps, 1)
            }
        except sqlite3.Error as e:
            logger.error(f"Failed to get scenario stats for {scenario}: {e}", exc_info=True)
            return None

    def get_scenario_step_stats(self, scenario: str, days: int = 7):
        """Получает статистику по шагам сценария."""
        try:
            # Получаем список исключаемых пользователей
            try:
                from config_local import NO_LOGS_USERS
            except ImportError:
                from config import NO_LOGS_USERS
            
            excluded_users = NO_LOGS_USERS if NO_LOGS_USERS else []
            excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
            
            params = [scenario] + (excluded_users if excluded_users else [])
            cursor = self.conn.execute(
                f"""SELECT step, COUNT(*) as count 
                   FROM scenario_logs 
                   WHERE scenario = ? AND timestamp >= datetime('now', '-{days} days')
                   {excluded_condition}
                   GROUP BY step 
                   ORDER BY count DESC""",
                params
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get scenario step stats for {scenario}: {e}", exc_info=True)
            return []

    def get_user_scenario_history(self, user_id: int, scenario: str = None):
        """Получает историю сценариев пользователя."""
        try:
            if scenario:
                cursor = self.conn.execute(
                    "SELECT * FROM user_scenarios WHERE user_id = ? AND scenario = ? ORDER BY started_at DESC",
                    (user_id, scenario)
                )
            else:
                cursor = self.conn.execute(
                    "SELECT * FROM user_scenarios WHERE user_id = ? ORDER BY started_at DESC",
                    (user_id,)
                )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to get user scenario history for {user_id}: {e}", exc_info=True)
            return []

    def get_user_advanced_stats(self, user_id: int):
        """Получает расширенную статистику пользователя."""
        try:
            stats = {}
            
            # 1. Максимальное количество дней подряд без пропуска
            cursor = self.conn.execute("""
                WITH RECURSIVE dates AS (
                    SELECT DATE(started_at) as date
                    FROM user_scenarios 
                    WHERE user_id = ?
                    GROUP BY DATE(started_at)
                    ORDER BY date
                ),
                consecutive_days AS (
                    SELECT date, 1 as streak
                    FROM dates
                    WHERE date = (SELECT MIN(date) FROM dates)
                    
                    UNION ALL
                    
                    SELECT d.date, 
                           CASE 
                               WHEN d.date = DATE(cd.date, '+1 day') THEN cd.streak + 1
                               ELSE 1
                           END as streak
                    FROM dates d
                    JOIN consecutive_days cd ON d.date > cd.date
                    WHERE d.date = (
                        SELECT MIN(date) FROM dates WHERE date > cd.date
                    )
                )
                SELECT MAX(streak) as max_streak
                FROM consecutive_days
            """, (user_id,))
            stats['max_consecutive_days'] = cursor.fetchone()['max_streak'] or 0
            
            # 2. Текущая серия дней подряд
            cursor = self.conn.execute("""
                WITH RECURSIVE dates AS (
                    SELECT DATE(started_at) as date
                    FROM user_scenarios 
                    WHERE user_id = ?
                    GROUP BY DATE(started_at)
                    ORDER BY date DESC
                ),
                current_streak AS (
                    SELECT date, 1 as streak
                    FROM dates
                    WHERE date = (SELECT MAX(date) FROM dates)
                    
                    UNION ALL
                    
                    SELECT d.date, cs.streak + 1
                    FROM dates d
                    JOIN current_streak cs ON d.date = DATE(cs.date, '-1 day')
                )
                SELECT MAX(streak) as current_streak
                FROM current_streak
            """, (user_id,))
            stats['current_streak'] = cursor.fetchone()['current_streak'] or 0
            
            # 3. Любимое время дня
            cursor = self.conn.execute("""
                SELECT 
                    CASE 
                        WHEN CAST(strftime('%H', started_at) AS INTEGER) BETWEEN 6 AND 11 THEN 'утро (6-12)'
                        WHEN CAST(strftime('%H', started_at) AS INTEGER) BETWEEN 12 AND 17 THEN 'день (12-18)'
                        WHEN CAST(strftime('%H', started_at) AS INTEGER) BETWEEN 18 AND 23 THEN 'вечер (18-24)'
                        ELSE 'ночь (0-6)'
                    END as time_period,
                    COUNT(*) as count
                FROM user_scenarios 
                WHERE user_id = ?
                GROUP BY time_period
                ORDER BY count DESC
                LIMIT 1
            """, (user_id,))
            time_result = cursor.fetchone()
            stats['favorite_time'] = time_result['time_period'] if time_result else "нет данных"
            
            # 4. Любимый день недели
            cursor = self.conn.execute("""
                SELECT 
                    CASE strftime('%w', started_at)
                        WHEN '0' THEN 'воскресенье'
                        WHEN '1' THEN 'понедельник'
                        WHEN '2' THEN 'вторник'
                        WHEN '3' THEN 'среда'
                        WHEN '4' THEN 'четверг'
                        WHEN '5' THEN 'пятница'
                        WHEN '6' THEN 'суббота'
                    END as day_name,
                    COUNT(*) as count
                FROM user_scenarios 
                WHERE user_id = ?
                GROUP BY day_name
                ORDER BY count DESC
                LIMIT 1
            """, (user_id,))
            day_result = cursor.fetchone()
            stats['favorite_day'] = day_result['day_name'] if day_result else "нет данных"
            
            # 5. Средняя глубина прохождения сценариев
            cursor = self.conn.execute("""
                SELECT 
                    AVG(steps_count) as avg_steps,
                    COUNT(*) as total_sessions
                FROM user_scenarios 
                WHERE user_id = ? AND status = 'completed'
            """, (user_id,))
            depth_result = cursor.fetchone()
            stats['avg_session_depth'] = round(depth_result['avg_steps'], 1) if depth_result['avg_steps'] else 0
            stats['total_completed_sessions'] = depth_result['total_sessions'] or 0
            
            # 6. Процент завершения сценариев
            cursor = self.conn.execute("""
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions
                FROM user_scenarios 
                WHERE user_id = ?
            """, (user_id,))
            completion_result = cursor.fetchone()
            total = completion_result['total_sessions'] or 0
            completed = completion_result['completed_sessions'] or 0
            stats['completion_rate'] = round((completed / total * 100), 1) if total > 0 else 0
            
            # 7. Первый и последний день использования
            cursor = self.conn.execute("""
                SELECT 
                    MIN(DATE(started_at)) as first_day,
                    MAX(DATE(started_at)) as last_day
                FROM user_scenarios 
                WHERE user_id = ?
            """, (user_id,))
            dates_result = cursor.fetchone()
            stats['first_day'] = dates_result['first_day'] if dates_result['first_day'] else None
            stats['last_day'] = dates_result['last_day'] if dates_result['last_day'] else None
            
            # 8. Общее количество дней использования
            cursor = self.conn.execute("""
                SELECT COUNT(DISTINCT DATE(started_at)) as unique_days
                FROM user_scenarios 
                WHERE user_id = ?
            """, (user_id,))
            stats['total_unique_days'] = cursor.fetchone()['unique_days'] or 0
            
            # 9. Среднее количество сессий в день
            cursor = self.conn.execute("""
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(DISTINCT DATE(started_at)) as unique_days
                FROM user_scenarios 
                WHERE user_id = ?
            """, (user_id,))
            sessions_result = cursor.fetchone()
            total_sessions = sessions_result['total_sessions'] or 0
            unique_days = sessions_result['unique_days'] or 1
            stats['avg_sessions_per_day'] = round(total_sessions / unique_days, 1)
            
            # 10. Достижения (бейджи)
            achievements = []
            if stats['max_consecutive_days'] >= 7:
                achievements.append("🔥 Неделя подряд")
            if stats['max_consecutive_days'] >= 30:
                achievements.append("⭐ Месяц подряд")
            if stats['total_completed_sessions'] >= 10:
                achievements.append("🎯 10 завершенных сессий")
            if stats['total_completed_sessions'] >= 50:
                achievements.append("🏆 50 завершенных сессий")
            if stats['completion_rate'] >= 80:
                achievements.append("💎 Высокая завершенность")
            if stats['avg_session_depth'] >= 20:
                achievements.append("🧠 Глубокие размышления")
            
            stats['achievements'] = achievements
            
            return stats
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get advanced stats for user {user_id}: {e}", exc_info=True)
            return {}

    # --- НОВЫЕ МЕТОДЫ ДЛЯ АДМИН-ПАНЕЛИ ---
    
    def get_retention_metrics(self, days: int = 7):
        """Получает метрики удержания (D1, D7)."""
        try:
            # Получаем список исключаемых пользователей
            try:
                from config_local import NO_LOGS_USERS
            except ImportError:
                from config import NO_LOGS_USERS
            
            excluded_users = NO_LOGS_USERS if NO_LOGS_USERS else []
            excluded_condition = f"AND u1.user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
            
            # D1 Retention: пользователи, вернувшиеся на следующий день
            cursor = self.conn.execute(f"""
                SELECT 
                    COUNT(DISTINCT u1.user_id) as total_users,
                    COUNT(DISTINCT u2.user_id) as returned_users
                FROM user_scenarios u1
                LEFT JOIN user_scenarios u2 ON u1.user_id = u2.user_id 
                    AND u2.started_at >= datetime(u1.started_at, '+1 day')
                    AND u2.started_at < datetime(u1.started_at, '+2 days')
                WHERE u1.started_at >= datetime('now', '-{days} days')
                {excluded_condition}
            """, list(excluded_users) if excluded_users else [])
            
            d1_data = cursor.fetchone()
            d1_retention = (d1_data['returned_users'] / d1_data['total_users'] * 100) if d1_data['total_users'] > 0 else 0
            
            # D7 Retention: пользователи, вернувшиеся на 7-й день
            cursor = self.conn.execute(f"""
                SELECT 
                    COUNT(DISTINCT u1.user_id) as total_users,
                    COUNT(DISTINCT u2.user_id) as returned_users
                FROM user_scenarios u1
                LEFT JOIN user_scenarios u2 ON u1.user_id = u2.user_id 
                    AND u2.started_at >= datetime(u1.started_at, '+7 days')
                    AND u2.started_at < datetime(u1.started_at, '+8 days')
                WHERE u1.started_at >= datetime('now', '-{days} days')
                {excluded_condition}
            """, list(excluded_users) if excluded_users else [])
            
            d7_data = cursor.fetchone()
            d7_retention = (d7_data['returned_users'] / d7_data['total_users'] * 100) if d7_data['total_users'] > 0 else 0
            
            return {
                'd1_retention': round(d1_retention, 1),
                'd7_retention': round(d7_retention, 1),
                'd1_total_users': d1_data['total_users'],
                'd1_returned_users': d1_data['returned_users'],
                'd7_total_users': d7_data['total_users'],
                'd7_returned_users': d7_data['returned_users']
            }
        except sqlite3.Error as e:
            logger.error(f"Failed to get retention metrics: {e}", exc_info=True)
            return {'d1_retention': 0, 'd7_retention': 0, 'd1_total_users': 0, 'd1_returned_users': 0, 'd7_total_users': 0, 'd7_returned_users': 0}

    def get_dau_metrics(self, days: int = 7):
        """Получает метрики DAU (Daily Active Users)."""
        try:
            # Получаем список исключаемых пользователей
            try:
                from config_local import NO_LOGS_USERS
            except ImportError:
                from config import NO_LOGS_USERS
            
            excluded_users = NO_LOGS_USERS if NO_LOGS_USERS else []
            excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
            
            cursor = self.conn.execute(f"""
                SELECT 
                    DATE(started_at) as date,
                    COUNT(DISTINCT user_id) as dau
                FROM user_scenarios 
                WHERE started_at >= datetime('now', '-{days} days')
                {excluded_condition}
                GROUP BY DATE(started_at)
                ORDER BY date DESC
            """, list(excluded_users) if excluded_users else [])
            
            daily_data = [dict(row) for row in cursor.fetchall()]
            
            # Сегодняшний DAU
            today_dau = daily_data[0]['dau'] if daily_data else 0
            
            # Средний DAU за период
            avg_dau = sum(d['dau'] for d in daily_data) / len(daily_data) if daily_data else 0
            
            return {
                'today_dau': today_dau,
                'avg_dau': round(avg_dau, 1),
                'daily_data': daily_data
            }
        except sqlite3.Error as e:
            logger.error(f"Failed to get DAU metrics: {e}", exc_info=True)
            return {'today_dau': 0, 'avg_dau': 0, 'daily_data': []}

    def get_card_funnel_metrics(self, days: int = 7):
        """Получает метрики воронки сценария 'Карта дня'."""
        try:
            # Получаем список исключаемых пользователей
            try:
                from config_local import NO_LOGS_USERS
            except ImportError:
                from config import NO_LOGS_USERS
            
            excluded_users = NO_LOGS_USERS if NO_LOGS_USERS else []
            excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
            
            # Шаг 1: Начали сессию
            cursor = self.conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = 'started'
                AND timestamp >= datetime('now', '-{days} days')
                {excluded_condition}
            """, list(excluded_users) if excluded_users else [])
            step1 = cursor.fetchone()['count']
            
            # Шаг 2: Выбрали начальный ресурс
            cursor = self.conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = 'initial_resource_selected'
                AND timestamp >= datetime('now', '-{days} days')
                {excluded_condition}
            """, list(excluded_users) if excluded_users else [])
            step2 = cursor.fetchone()['count']
            
            # Шаг 3: Согласились на углубляющий диалог
            cursor = self.conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = 'ai_reflection_choice'
                AND metadata LIKE '%"choice": "yes"%'
                AND timestamp >= datetime('now', '-{days} days')
                {excluded_condition}
            """, list(excluded_users) if excluded_users else [])
            step3 = cursor.fetchone()['count']
            
            # Шаг 4: Завершили диалог (получили AI ответы или отказались)
            cursor = self.conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND (step LIKE 'ai_response_%' OR step = 'ai_reflection_choice')
                AND timestamp >= datetime('now', '-{days} days')
                {excluded_condition}
            """, list(excluded_users) if excluded_users else [])
            step4 = cursor.fetchone()['count']
            
            # Шаг 5: Дошли до финального фидбека
            cursor = self.conn.execute(f"""
                SELECT COUNT(DISTINCT user_id) as count
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = 'completed'
                AND timestamp >= datetime('now', '-{days} days')
                {excluded_condition}
            """, list(excluded_users) if excluded_users else [])
            step5 = cursor.fetchone()['count']
            
            # Расчёт процентов
            step1_pct = 100
            step2_pct = (step2 / step1 * 100) if step1 > 0 else 0
            step3_pct = (step3 / step1 * 100) if step1 > 0 else 0
            step4_pct = (step4 / step1 * 100) if step1 > 0 else 0
            step5_pct = (step5 / step1 * 100) if step1 > 0 else 0
            
            return {
                'step1': {'count': step1, 'pct': step1_pct},
                'step2': {'count': step2, 'pct': round(step2_pct, 1)},
                'step3': {'count': step3, 'pct': round(step3_pct, 1)},
                'step4': {'count': step4, 'pct': round(step4_pct, 1)},
                'step5': {'count': step5, 'pct': round(step5_pct, 1)},
                'completion_rate': round(step5_pct, 1)
            }
        except sqlite3.Error as e:
            logger.error(f"Failed to get card funnel metrics: {e}", exc_info=True)
            return {'step1': {'count': 0, 'pct': 0}, 'step2': {'count': 0, 'pct': 0}, 'step3': {'count': 0, 'pct': 0}, 'step4': {'count': 0, 'pct': 0}, 'step5': {'count': 0, 'pct': 0}, 'completion_rate': 0}

    def get_value_metrics(self, days: int = 7):
        """Получает метрики ценности (Resource Lift, Feedback Score)."""
        try:
            # Получаем список исключаемых пользователей
            try:
                from config_local import NO_LOGS_USERS
            except ImportError:
                from config import NO_LOGS_USERS
            
            excluded_users = NO_LOGS_USERS if NO_LOGS_USERS else []
            excluded_condition = f"AND user_id NOT IN ({','.join(['?'] * len(excluded_users))})" if excluded_users else ""
            
            # Resource Lift: динамика ресурса
            cursor = self.conn.execute(f"""
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN final_resource > initial_resource THEN 1 ELSE 0 END) as positive_lift,
                    SUM(CASE WHEN final_resource < initial_resource THEN 1 ELSE 0 END) as negative_lift
                FROM (
                    SELECT 
                        user_id,
                        CAST(JSON_EXTRACT(MAX(CASE WHEN step = 'initial_resource_selected' THEN metadata END), '$.resource') AS INTEGER) as initial_resource,
                        CAST(JSON_EXTRACT(MAX(CASE WHEN step = 'mood_change_recorded' THEN metadata END), '$.resource') AS INTEGER) as final_resource
                    FROM scenario_logs 
                    WHERE scenario = 'card_of_day' 
                    AND timestamp >= datetime('now', '-{days} days')
                    {excluded_condition}
                    GROUP BY user_id
                ) sessions
                WHERE initial_resource IS NOT NULL AND final_resource IS NOT NULL
            """, list(excluded_users) if excluded_users else [])
            
            resource_data = cursor.fetchone()
            total_sessions = resource_data['total_sessions']
            positive_lift_pct = (resource_data['positive_lift'] / total_sessions * 100) if total_sessions > 0 else 0
            negative_lift_pct = (resource_data['negative_lift'] / total_sessions * 100) if total_sessions > 0 else 0
            
            # Feedback Score: позитивные отзывы
            cursor = self.conn.execute(f"""
                SELECT 
                    COUNT(*) as total_feedback,
                    SUM(CASE WHEN metadata LIKE '%"feedback": "helpful"%' THEN 1 ELSE 0 END) as positive_feedback
                FROM scenario_logs 
                WHERE scenario = 'card_of_day' 
                AND step = 'usefulness_rating'
                AND timestamp >= datetime('now', '-{days} days')
                {excluded_condition}
            """, list(excluded_users) if excluded_users else [])
            
            feedback_data = cursor.fetchone()
            feedback_score = (feedback_data['positive_feedback'] / feedback_data['total_feedback'] * 100) if feedback_data['total_feedback'] > 0 else 0
            
            return {
                'resource_lift': {
                    'positive_pct': round(positive_lift_pct, 1),
                    'negative_pct': round(negative_lift_pct, 1),
                    'total_sessions': total_sessions
                },
                'feedback_score': round(feedback_score, 1),
                'total_feedback': feedback_data['total_feedback']
            }
        except sqlite3.Error as e:
            logger.error(f"Failed to get value metrics: {e}", exc_info=True)
            return {'resource_lift': {'positive_pct': 0, 'negative_pct': 0, 'total_sessions': 0}, 'feedback_score': 0, 'total_feedback': 0}

    def get_admin_dashboard_summary(self, days: int = 7):
        """Получает сводку для главного дашборда админки."""
        try:
            # Основные метрики
            retention = self.get_retention_metrics(days)
            dau = self.get_dau_metrics(days)
            card_stats = self.get_scenario_stats('card_of_day', days)
            evening_stats = self.get_scenario_stats('evening_reflection', days)
            funnel = self.get_card_funnel_metrics(days)
            value = self.get_value_metrics(days)
            
            return {
                'retention': retention,
                'dau': dau,
                'card_stats': card_stats,
                'evening_stats': evening_stats,
                'funnel': funnel,
                'value': value,
                'period_days': days
            }
        except Exception as e:
            logger.error(f"Failed to get admin dashboard summary: {e}", exc_info=True)
            return None

    # --- КОНЕЦ НОВЫХ МЕТОДОВ ---

    def close(self):
        # ... (код метода close) ...
        """Закрывает соединение с базой данных."""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed.")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)

# --- КОНЕЦ КЛАССА ---

# Импорт pytz
# ... (как было) ...
try:
    import pytz
except ImportError:
    pytz = None
    logger.warning("pytz library not found. Timezone conversions might be affected if database stores naive datetimes or if TIMEZONE config is used.")
