# код/db.py
import sqlite3
import json
from datetime import datetime, date # Убедимся что date импортирован
import os
from config import TIMEZONE
import logging

logger = logging.getLogger(__name__)

# --- КЛАСС Database ---
class Database:
    def __init__(self, path="/data/bot.db"):
        # ... (код __init__ без изменений, включая конвертеры) ...
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
            sqlite3.register_adapter(date, lambda val: val.isoformat())
            # Конвертер для date остается, но так как тип колонки TEXT, он не сработает автоматически
            sqlite3.register_converter("date", lambda val: date.fromisoformat(val.decode('utf-8')) if val else None)

            self.conn.row_factory = sqlite3.Row
            self.bot = None

            self.create_tables()
            self._run_migrations()
            self.create_indexes()

        except sqlite3.Error as e:
            logger.critical(f"Database initialization failed: Could not connect or setup tables/migrations/indexes at {path}. Error: {e}", exc_info=True)
            raise

    # ... (методы create_tables, _run_migrations, create_indexes, get_user, update_user, ...)
    # ... (get_user_cards, count_user_cards, add_user_card, reset_user_cards, ...)
    # ... (save_action, get_actions, get_reminder_times, get_all_users, is_card_available, ...)
    # ... (add_referral, get_referrals, get_user_profile, update_user_profile, ...)
    # ... (save_evening_reflection, count_reflections, get_all_reflection_texts, ...)
    # ... (add_recharge_method, get_last_recharge_method) ...

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
            logger.info("Indexes checked/created successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error creating database indexes: {e}", exc_info=True)

    # --- Метод get_last_reflection_date ИЗМЕНЕН ---
    def get_last_reflection_date(self, user_id) -> date | None:
        """Возвращает дату последней рефлексии пользователя как объект date."""
        try:
            cursor = self.conn.execute(
                "SELECT date FROM evening_reflections WHERE user_id = ? ORDER BY date DESC LIMIT 1",
                 (user_id,)
            )
            row = cursor.fetchone()
            if row and row["date"]:
                try:
                    # Явно преобразуем строку в date
                    return date.fromisoformat(row["date"])
                except (ValueError, TypeError) as e:
                    logger.error(f"Could not parse date string '{row['date']}' from DB for user {user_id}: {e}")
                    return None
            return None # Если записи нет или дата NULL
        except sqlite3.Error as e:
            logger.error(f"Failed to get last reflection date for {user_id}: {e}", exc_info=True)
            return None
    # --- КОНЕЦ ИЗМЕНЕНИЙ get_last_reflection_date ---

    def count_reflections(self, user_id):
        # ... (код без изменений) ...
        """Возвращает общее количество рефлексий пользователя."""
        try:
            cursor = self.conn.execute("SELECT COUNT(*) FROM evening_reflections WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to count reflections for {user_id}: {e}", exc_info=True)
            return 0

    def get_all_reflection_texts(self, user_id, limit=10) -> list[dict]:
        # ... (код без изменений) ...
        """Возвращает тексты последних N рефлексий."""
        texts = []
        try:
            cursor = self.conn.execute(
                """SELECT good_moments, gratitude, hard_moments
                   FROM evening_reflections
                   WHERE user_id = ? ORDER BY date DESC LIMIT ?""",
                (user_id, limit)
            )
            for row in cursor.fetchall():
                texts.append(dict(row))
            return texts
        except sqlite3.Error as e:
            logger.error(f"Failed to get reflection texts for {user_id}: {e}", exc_info=True)
            return []

    def add_recharge_method(self, user_id, method, timestamp):
        # ... (код без изменений) ...
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
        # ... (код без изменений) ...
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

    def close(self):
        # ... (код без изменений) ...
        """Закрывает соединение с базой данных."""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed.")
            except sqlite3.Error as e:
                logger.error(f"Error closing database connection: {e}", exc_info=True)

# Импорт pytz
try:
    import pytz
except ImportError:
    pytz = None
    logger.warning("pytz library not found. Timezone conversions might be affected if database stores naive datetimes or if TIMEZONE config is used.")

# --- КОНЕЦ ФАЙЛА ---
