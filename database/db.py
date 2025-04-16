# код/db.py
import sqlite3
import json
from datetime import datetime
import os
from config import TIMEZONE # Убедись, что TIMEZONE импортирован правильно
import logging # Добавим логирование

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, path="/data/bot.db"):  # Используем путь, соответствующий Amvera
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        # Включаем поддержку типов данных datetime для SQLite
        sqlite3.register_adapter(datetime, lambda val: val.isoformat())
        sqlite3.register_converter("timestamp", lambda val: datetime.fromisoformat(val.decode()))

        self.conn.row_factory = sqlite3.Row
        self.bot = None  # Для обратной совместимости
        self.create_tables()
        # Выполняем миграцию при инициализации
        self._run_migrations()

    def _run_migrations(self):
        """Добавляет новые столбцы, если их нет."""
        try:
            cursor = self.conn.cursor()
            # Проверяем и добавляем столбцы в user_profiles
            profile_columns = [desc[1] for desc in cursor.execute("PRAGMA table_info(user_profiles)").fetchall()]
            if 'initial_resource' not in profile_columns:
                cursor.execute("ALTER TABLE user_profiles ADD COLUMN initial_resource TEXT")
                logger.info("Added column 'initial_resource' to user_profiles")
            if 'final_resource' not in profile_columns:
                cursor.execute("ALTER TABLE user_profiles ADD COLUMN final_resource TEXT")
                logger.info("Added column 'final_resource' to user_profiles")
            if 'recharge_method' not in profile_columns:
                cursor.execute("ALTER TABLE user_profiles ADD COLUMN recharge_method TEXT")
                logger.info("Added column 'recharge_method' to user_profiles")
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database migration error: {e}")
            self.conn.rollback() # Откатываем изменения в случае ошибки

    def create_tables(self):
        with self.conn:
            # Таблица users: last_request теперь TEXT для хранения ISO строки
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    last_request TEXT, -- Изменен на TEXT
                    reminder_time TEXT,
                    bonus_available BOOLEAN DEFAULT FALSE
                )""")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_cards (
                    user_id INTEGER,
                    card_number INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            # Таблица actions: timestamp теперь TEXT
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    name TEXT,
                    action TEXT,
                    details TEXT,
                    timestamp TEXT, -- Изменен на TEXT
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_id) REFERENCES users(user_id)
                )""")
            # Эта таблица больше не используется для нового фидбека, но оставим для истории
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS card_feedback (
                    user_id INTEGER,
                    card_number INTEGER,
                    answer TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            # Таблица feedback: timestamp теперь TEXT
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    user_id INTEGER,
                    name TEXT,
                    feedback TEXT,
                    timestamp TEXT, -- Изменен на TEXT
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            # Эта таблица, возможно, дублируется логикой actions, но оставим
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_requests (
                    user_id INTEGER,
                    request TEXT,
                    timestamp TEXT, -- Изменен на TEXT
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            # Таблица user_profiles: last_updated теперь TEXT, добавлены новые поля
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    mood TEXT,
                    mood_trend TEXT,  -- Храним как JSON
                    themes TEXT,     -- Храним как JSON
                    response_count INTEGER,
                    request_count INTEGER,
                    avg_response_length REAL,
                    days_active INTEGER,
                    interactions_per_day REAL,
                    last_updated TEXT,  -- Изменен на TEXT
                    initial_resource TEXT, -- НОВОЕ ПОЛЕ: Начальный ресурс (эмодзи/текст)
                    final_resource TEXT,   -- НОВОЕ ПОЛЕ: Конечный ресурс (эмодзи/текст)
                    recharge_method TEXT  -- НОВОЕ ПОЛЕ: Способ восстановления ресурса
                )""")

    def get_user(self, user_id):
        cursor = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            last_request_val = row["last_request"]
            # Преобразуем строку ISO обратно в datetime при чтении
            last_request_dt = None
            if last_request_val:
                try:
                    # Убираем возможное 'Z' и добавляем +00:00, если нет часового пояса
                    if 'Z' in last_request_val:
                         last_request_val = last_request_val.replace('Z', '+00:00')
                    elif '+' not in last_request_val and '-' not in last_request_val[10:]: # Проверка на наличие таймзоны
                         pass # Оставим как есть, если нет таймзоны - fromisoformat справится
                    last_request_dt = datetime.fromisoformat(last_request_val)
                except ValueError as e:
                    logger.error(f"Error parsing last_request '{last_request_val}' for user {user_id}: {e}") # Логирование ошибки
                    last_request_dt = None

            return {
                "user_id": row["user_id"],
                "name": row["name"],
                "username": row["username"],
                "last_request": last_request_dt, # Возвращаем datetime или None
                "reminder_time": row["reminder_time"],
                "bonus_available": bool(row["bonus_available"])
            }
        # Возвращаем дефолтную структуру, если пользователь не найден
        # Добавляем дефолтную запись о пользователе, если его нет
        logger.info(f"User {user_id} not found, creating default entry.")
        default_user_data = {"user_id": user_id, "name": "", "username": "", "last_request": None, "reminder_time": None, "bonus_available": False}
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO users (user_id, name, username, last_request, reminder_time, bonus_available) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, default_user_data["name"], default_user_data["username"],
                     default_user_data["last_request"].isoformat() if default_user_data["last_request"] else None,
                     default_user_data["reminder_time"], default_user_data["bonus_available"])
                )
            logger.info(f"Default user entry created for {user_id}")
            return default_user_data
        except sqlite3.Error as e:
            logger.error(f"Failed to insert default user {user_id}: {e}")
            # Возвращаем дефолтную структуру, чтобы не сломать дальнейшую логику
            return {"user_id": user_id, "name": "", "username": "", "last_request": None, "reminder_time": None, "bonus_available": False}

    def update_user(self, user_id, data):
        current_user_data = self.get_user(user_id) # Получаем текущие данные (или дефолтные)

        last_request_to_save = None
        if "last_request" in data:
            last_request_input = data["last_request"]
            if isinstance(last_request_input, datetime):
                last_request_to_save = last_request_input.isoformat()
            elif isinstance(last_request_input, str):
                 try:
                     # Проверяем, что строка валидна, прежде чем сохранить
                     datetime.fromisoformat(last_request_input.replace('Z', '+00:00'))
                     last_request_to_save = last_request_input
                 except ValueError:
                      logger.warning(f"Invalid ISO string format for last_request '{last_request_input}' for user {user_id}. Using None.")
                      last_request_to_save = None
            else:
                 logger.warning(f"Unexpected type for last_request '{type(last_request_input)}' for user {user_id}. Using None.")
                 last_request_to_save = None
        else:
            current_last_request_dt = current_user_data.get("last_request")
            if isinstance(current_last_request_dt, datetime):
                last_request_to_save = current_last_request_dt.isoformat()
            else:
                last_request_to_save = None

        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO users (user_id, name, username, last_request, reminder_time, bonus_available)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data.get("name", current_user_data.get("name")), # Используем .get() для безопасности
                data.get("username", current_user_data.get("username")),
                last_request_to_save,
                data.get("reminder_time", current_user_data.get("reminder_time")),
                data.get("bonus_available", current_user_data.get("bonus_available"))
            ))

    def get_user_cards(self, user_id):
        cursor = self.conn.execute("SELECT card_number FROM user_cards WHERE user_id = ?", (user_id,))
        return [row["card_number"] for row in cursor.fetchall()]

    def add_user_card(self, user_id, card_number):
        with self.conn:
            self.conn.execute("INSERT INTO user_cards (user_id, card_number) VALUES (?, ?)", (user_id, card_number))

    def reset_user_cards(self, user_id):
        with self.conn:
            self.conn.execute("DELETE FROM user_cards WHERE user_id = ?", (user_id,))

    def save_action(self, user_id, username, name, action, details, timestamp):
         if isinstance(timestamp, datetime):
             timestamp_str = timestamp.isoformat()
         elif isinstance(timestamp, str):
             timestamp_str = timestamp
         else:
             timestamp_str = datetime.now(TIMEZONE).isoformat()

         # Преобразуем детали в JSON, обрабатывая ошибки
         try:
             details_json = json.dumps(details, ensure_ascii=False) # ensure_ascii=False для корректного отображения кириллицы
         except TypeError as e:
             logger.error(f"Failed to serialize details for action '{action}' for user {user_id}: {e}. Details: {details}")
             details_json = json.dumps({"error": "serialization_failed", "original_details": str(details)}) # Сохраняем как строку в случае ошибки

         with self.conn:
            self.conn.execute(
                "INSERT INTO actions (user_id, username, name, action, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, name, action, details_json, timestamp_str)
            )

    def get_actions(self, user_id=None):
        if user_id:
            cursor = self.conn.execute("SELECT * FROM actions WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
        else:
            cursor = self.conn.execute("SELECT * FROM actions ORDER BY timestamp ASC")
        actions = []
        for row in cursor.fetchall():
            try:
                # ensure_ascii=False не нужен при загрузке, json.loads работает с unicode
                details_dict = json.loads(row["details"])
            except json.JSONDecodeError:
                details_dict = {"error": "invalid_json", "raw_details": row["details"]}
            except TypeError: # Если details == None
                 details_dict = {}

            timestamp_str = row["timestamp"]

            actions.append({
                "user_id": row["user_id"],
                "username": row["username"],
                "name": row["name"],
                "action": row["action"],
                "details": details_dict,
                "timestamp": timestamp_str
            })
        return actions


    def get_reminder_times(self):
        cursor = self.conn.execute("SELECT user_id, reminder_time FROM users WHERE reminder_time IS NOT NULL")
        return {row["user_id"]: row["reminder_time"] for row in cursor.fetchall()}

    def get_all_users(self):
        cursor = self.conn.execute("SELECT user_id FROM users")
        return [row["user_id"] for row in cursor.fetchall()]

    def is_card_available(self, user_id, today):
        user_data = self.get_user(user_id) # Получаем данные пользователя
        if not user_data: # Если пользователя нет в БД (хотя get_user теперь создает дефолт)
            return True
        last_request_dt = user_data.get("last_request") # Используем .get()
        if last_request_dt and isinstance(last_request_dt, datetime):
            return last_request_dt.astimezone(TIMEZONE).date() < today
        return True

    def add_referral(self, referrer_id, referred_id):
        with self.conn:
            self.conn.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))

    def get_referrals(self, referrer_id):
        cursor = self.conn.execute("SELECT referred_id FROM referrals WHERE referrer_id = ?", (referrer_id,))
        return [row["referred_id"] for row in cursor.fetchall()]

    def get_user_profile(self, user_id):
        cursor = self.conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            last_updated_val = row["last_updated"]
            last_updated_dt = None
            if last_updated_val:
                 try:
                     if 'Z' in last_updated_val:
                          last_updated_val = last_updated_val.replace('Z', '+00:00')
                     last_updated_dt = datetime.fromisoformat(last_updated_val)
                 except ValueError as e:
                     logger.error(f"Error parsing last_updated '{last_updated_val}' for profile user {user_id}: {e}")
                     last_updated_dt = None

            try:
                 mood_trend_list = json.loads(row["mood_trend"]) if row["mood_trend"] else []
            except (json.JSONDecodeError, TypeError):
                 mood_trend_list = []
            try:
                 themes_list = json.loads(row["themes"]) if row["themes"] else []
            except (json.JSONDecodeError, TypeError):
                 themes_list = []

            # Добавляем новые поля с дефолтными значениями None, если их нет в строке
            # row_keys = row.keys() # Получаем ключи из конкретной строки

            return {
                "user_id": row["user_id"],
                "mood": row["mood"],
                "mood_trend": mood_trend_list,
                "themes": themes_list,
                "response_count": row["response_count"],
                "request_count": row["request_count"],
                "avg_response_length": row["avg_response_length"],
                "days_active": row["days_active"],
                "interactions_per_day": row["interactions_per_day"],
                "last_updated": last_updated_dt, # Возвращаем datetime или None
                # Используем row['column'] вместо row.get() т.к. миграция должна была добавить столбцы
                "initial_resource": row["initial_resource"], # Ожидаем, что столбец есть
                "final_resource": row["final_resource"],     # Ожидаем, что столбец есть
                "recharge_method": row["recharge_method"]   # Ожидаем, что столбец есть
            }
        return None

    def update_user_profile(self, user_id, profile):
         last_updated_dt = profile.get("last_updated")
         if isinstance(last_updated_dt, datetime):
             last_updated_iso = last_updated_dt.isoformat()
         else:
             logger.warning(f"last_updated in profile for user {user_id} is not datetime. Using current time.")
             last_updated_iso = datetime.now(TIMEZONE).isoformat()

         # Получаем текущий профиль, чтобы не перезаписать существующие значения новыми None, если они не переданы
         current_profile = self.get_user_profile(user_id) or {}

         with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO user_profiles (
                    user_id, mood, mood_trend, themes, response_count, request_count,
                    avg_response_length, days_active, interactions_per_day, last_updated,
                    initial_resource, final_resource, recharge_method -- Новые поля
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                profile.get("mood", current_profile.get("mood")),
                json.dumps(profile.get("mood_trend", current_profile.get("mood_trend", []))),
                json.dumps(profile.get("themes", current_profile.get("themes", []))),
                profile.get("response_count", current_profile.get("response_count")),
                profile.get("request_count", current_profile.get("request_count")),
                profile.get("avg_response_length", current_profile.get("avg_response_length")),
                profile.get("days_active", current_profile.get("days_active")),
                profile.get("interactions_per_day", current_profile.get("interactions_per_day")),
                last_updated_iso, # Всегда обновляем время
                profile.get("initial_resource", current_profile.get("initial_resource")), # Новое
                profile.get("final_resource", current_profile.get("final_resource")),     # Новое
                profile.get("recharge_method", current_profile.get("recharge_method"))    # Новое
            ))
