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
        # Создаем директорию, если ее нет
        db_dir = os.path.dirname(path)
        if db_dir and not os.path.exists(db_dir):
             os.makedirs(db_dir, exist_ok=True)
             logger.info(f"Created database directory: {db_dir}")

        self.conn = sqlite3.connect(path, check_same_thread=False)
        logger.info(f"Database connection initialized at path: {path}")

        # Включаем поддержку типов данных datetime для SQLite
        sqlite3.register_adapter(datetime, lambda val: val.isoformat())
        # Декодер для timestamp с обработкой None
        def decode_timestamp(val):
             if val is None:
                 return None
             try:
                 # Добавляем обработку 'Z' если нужно
                 val_str = val.decode()
                 if val_str.endswith('Z'):
                      val_str = val_str[:-1] + '+00:00'
                 return datetime.fromisoformat(val_str)
             except (ValueError, TypeError) as e:
                 logger.error(f"Error decoding timestamp '{val}': {e}")
                 return None # Возвращаем None при ошибке декодирования

        sqlite3.register_converter("timestamp", decode_timestamp)


        self.conn.row_factory = sqlite3.Row
        self.bot = None  # Для получения username в log_action и т.д. (устанавливается в main.py)
        self.create_tables()
        # Выполняем миграцию при инициализации
        self._run_migrations()

    def _run_migrations(self):
        """Добавляет новые столбцы в user_profiles, если их нет."""
        required_columns = {
            'initial_resource': 'TEXT',
            'final_resource': 'TEXT',
            'recharge_method': 'TEXT'
        }
        logger.info("Running database migrations for user_profiles table...")
        try:
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(user_profiles)")
            existing_columns = [row['name'] for row in cursor.fetchall()]
            logger.debug(f"Existing columns in user_profiles: {existing_columns}")

            for col_name, col_type in required_columns.items():
                if col_name not in existing_columns:
                    alter_sql = f"ALTER TABLE user_profiles ADD COLUMN {col_name} {col_type}"
                    logger.info(f"Executing migration: {alter_sql}")
                    cursor.execute(alter_sql)
                    logger.info(f"Successfully added column '{col_name}' to user_profiles")
                else:
                     logger.debug(f"Column '{col_name}' already exists in user_profiles.")

            self.conn.commit()
            logger.info("Database migrations completed successfully.")
        except sqlite3.Error as e:
            logger.error(f"Database migration error: {e}", exc_info=True)
            self.conn.rollback() # Откатываем изменения в случае ошибки

    def create_tables(self):
        logger.info("Creating database tables if they don't exist...")
        with self.conn:
            # Таблица users
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    last_request TEXT, -- ISO строка времени последнего вытягивания карты
                    reminder_time TEXT, -- Время напоминания HH:MM
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
                    action TEXT NOT NULL, -- Тип действия
                    details TEXT,      -- Детали в формате JSON
                    timestamp TEXT NOT NULL, -- Время действия в ISO формате
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
            # Таблица профилей пользователей (добавлены новые поля)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    mood TEXT,
                    mood_trend TEXT,  -- JSON список последних настроений
                    themes TEXT,     -- JSON список тем
                    response_count INTEGER DEFAULT 0,
                    request_count INTEGER DEFAULT 0,
                    avg_response_length REAL DEFAULT 0,
                    days_active INTEGER DEFAULT 0,
                    interactions_per_day REAL DEFAULT 0,
                    last_updated TEXT,  -- ISO строка времени последнего обновления профиля
                    initial_resource TEXT, -- НОВОЕ: Начальный ресурс (текст)
                    final_resource TEXT,   -- НОВОЕ: Конечный ресурс (текст)
                    recharge_method TEXT,  -- НОВОЕ: Способ восстановления ресурса
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )""")
            # Индексы для ускорения запросов
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_user_timestamp ON actions (user_id, timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_cards_user ON user_cards (user_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_reminder_time ON users (reminder_time)")
        logger.info("Tables checked/created.")

    def get_user(self, user_id):
        """Получает данные пользователя. Если пользователь не найден, создает запись с дефолтными значениями."""
        cursor = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            user_dict = dict(row)
            # Преобразуем строку ISO обратно в datetime при чтении
            last_request_val = user_dict.get("last_request")
            if last_request_val:
                 try:
                      # Обработка 'Z' и отсутствия таймзоны (хотя сохранять должны с ней)
                      if isinstance(last_request_val, str):
                           if 'Z' in last_request_val:
                                last_request_val = last_request_val.replace('Z', '+00:00')
                           elif '+' not in last_request_val and '-' not in last_request_val[10:]:
                                # Попытка не добавлять таймзону, если ее нет
                                pass
                           user_dict["last_request"] = datetime.fromisoformat(last_request_val)
                      else: # Если это уже datetime (маловероятно из БД)
                           user_dict["last_request"] = last_request_val
                 except (ValueError, TypeError) as e:
                      logger.error(f"Error parsing last_request '{last_request_val}' for user {user_id}: {e}")
                      user_dict["last_request"] = None # Обнуляем при ошибке
            else:
                 user_dict["last_request"] = None

            user_dict["bonus_available"] = bool(user_dict.get("bonus_available", False))
            return user_dict

        # Пользователь не найден, создаем дефолтную запись
        logger.info(f"User {user_id} not found in 'users' table, creating default entry.")
        default_user_data = {
            "user_id": user_id, "name": "", "username": "",
            "last_request": None, "reminder_time": None, "bonus_available": False
        }
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO users (user_id, name, username, last_request, reminder_time, bonus_available) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, default_user_data["name"], default_user_data["username"],
                     None, # last_request is initially None
                     default_user_data["reminder_time"], default_user_data["bonus_available"])
                )
            logger.info(f"Default user entry created for {user_id}")
            # Возвращаем только что созданные дефолтные данные
            return default_user_data
        except sqlite3.Error as e:
            logger.error(f"Failed to insert default user {user_id}: {e}", exc_info=True)
            # Возвращаем дефолтную структуру в памяти, чтобы бот не упал
            return {"user_id": user_id, "name": "", "username": "", "last_request": None, "reminder_time": None, "bonus_available": False}

    def update_user(self, user_id, data):
        """Обновляет данные пользователя (INSERT OR REPLACE)."""
        # Получаем текущие данные (или дефолтные, если пользователя не было)
        current_user_data = self.get_user(user_id)

        # Подготавливаем данные для сохранения, используя текущие значения как fallback
        user_id_to_save = user_id
        name_to_save = data.get("name", current_user_data.get("name"))
        username_to_save = data.get("username", current_user_data.get("username"))
        reminder_to_save = data.get("reminder_time", current_user_data.get("reminder_time"))
        bonus_to_save = data.get("bonus_available", current_user_data.get("bonus_available"))

        # Обработка last_request (ожидаем строку ISO или datetime)
        last_request_to_save = None
        if "last_request" in data:
            last_request_input = data["last_request"]
            if isinstance(last_request_input, datetime):
                last_request_to_save = last_request_input.isoformat()
            elif isinstance(last_request_input, str):
                try:
                    # Проверяем валидность строки ISO перед сохранением
                    datetime.fromisoformat(last_request_input.replace('Z', '+00:00'))
                    last_request_to_save = last_request_input
                except (ValueError, TypeError):
                    logger.warning(f"Invalid ISO string format provided for last_request '{last_request_input}' for user {user_id}. Saving as None.")
                    last_request_to_save = None
            else:
                logger.warning(f"Unexpected type for last_request '{type(last_request_input)}' for user {user_id}. Saving as None.")
                last_request_to_save = None
        else:
            # Если не передано, берем текущее значение из БД (которое get_user вернул как datetime)
            current_last_request_dt = current_user_data.get("last_request")
            if isinstance(current_last_request_dt, datetime):
                last_request_to_save = current_last_request_dt.isoformat()

        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO users (user_id, name, username, last_request, reminder_time, bonus_available)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id_to_save, name_to_save, username_to_save,
                    last_request_to_save, reminder_to_save, bonus_to_save
                ))
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
        """Удаляет все записи об использованных картах для пользователя (сброс колоды)."""
        try:
             with self.conn:
                 self.conn.execute("DELETE FROM user_cards WHERE user_id = ?", (user_id,))
             logger.info(f"Reset used cards for user {user_id}")
        except sqlite3.Error as e:
             logger.error(f"Failed to reset user cards for {user_id}: {e}", exc_info=True)


    def save_action(self, user_id, username, name, action, details, timestamp):
        """Сохраняет запись о действии пользователя."""
        # Преобразуем timestamp в строку ISO, если это datetime
        if isinstance(timestamp, datetime):
            timestamp_str = timestamp.isoformat()
        elif isinstance(timestamp, str):
            # Проверяем формат строки на всякий случай
            try:
                 datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                 timestamp_str = timestamp
            except (ValueError, TypeError):
                 logger.warning(f"Invalid timestamp string '{timestamp}' provided for action '{action}' for user {user_id}. Using current time.")
                 timestamp_str = datetime.now(TIMEZONE).isoformat()
        else:
            logger.warning(f"Invalid timestamp type '{type(timestamp)}' provided for action '{action}' for user {user_id}. Using current time.")
            timestamp_str = datetime.now(TIMEZONE).isoformat()

        # Преобразуем детали в JSON, обрабатывая ошибки
        details_json = None
        if details is not None:
             try:
                 details_json = json.dumps(details, ensure_ascii=False) # ensure_ascii=False для кириллицы
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


    def get_actions(self, user_id=None):
        """Получает список действий пользователя (или всех), отсортированных по времени."""
        actions = []
        try:
            sql = "SELECT * FROM actions"
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

                # Timestamp уже строка ISO из БД
                timestamp_str = row_dict.get("timestamp", datetime.min.isoformat()) # Fallback timestamp

                actions.append({
                    "id": row_dict.get("id"),
                    "user_id": row_dict["user_id"],
                    "username": row_dict.get("username"),
                    "name": row_dict.get("name"),
                    "action": row_dict["action"],
                    "details": details_dict,
                    "timestamp": timestamp_str
                })
        except sqlite3.Error as e:
             logger.error(f"Failed to get actions (user_id: {user_id}): {e}", exc_info=True)
        return actions


    def get_reminder_times(self):
        """Возвращает словарь {user_id: reminder_time} для пользователей с установленными напоминаниями."""
        try:
             cursor = self.conn.execute("SELECT user_id, reminder_time FROM users WHERE reminder_time IS NOT NULL AND reminder_time != ''")
             return {row["user_id"]: row["reminder_time"] for row in cursor.fetchall()}
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

    def is_card_available(self, user_id, today):
        """Проверяет, доступна ли карта дня для пользователя сегодня."""
        user_data = self.get_user(user_id) # Получаем данные пользователя
        if not user_data:
             return True # Если пользователя нет, карта доступна (он будет создан при первом запросе)
        last_request_dt = user_data.get("last_request") # Это уже datetime или None
        if isinstance(last_request_dt, datetime):
            # Сравниваем только даты в правильной таймзоне
            return last_request_dt.astimezone(TIMEZONE).date() < today
        return True # Если запросов не было или ошибка парсинга даты, карта доступна

    def add_referral(self, referrer_id, referred_id):
        """Добавляет запись о реферале (если такой еще не существует)."""
        try:
            with self.conn:
                 # Используем INSERT OR IGNORE чтобы избежать ошибки, если referred_id уже есть
                 self.conn.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
                 # Проверяем, была ли вставка (была ли запись изменена)
                 changes = self.conn.execute("SELECT changes()").fetchone()[0]
                 if changes > 0:
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

    def get_user_profile(self, user_id):
        """Получает профиль пользователя из таблицы user_profiles."""
        try:
            cursor = self.conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                profile_dict = dict(row)
                # Преобразуем last_updated в datetime
                last_updated_val = profile_dict.get("last_updated")
                if last_updated_val:
                    try:
                        if 'Z' in last_updated_val:
                            last_updated_val = last_updated_val.replace('Z', '+00:00')
                        profile_dict["last_updated"] = datetime.fromisoformat(last_updated_val)
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error parsing last_updated '{last_updated_val}' for profile user {user_id}: {e}")
                        profile_dict["last_updated"] = None
                else:
                     profile_dict["last_updated"] = None

                # Декодируем JSON поля
                try:
                    profile_dict["mood_trend"] = json.loads(profile_dict.get("mood_trend", '[]')) if profile_dict.get("mood_trend") else []
                except (json.JSONDecodeError, TypeError):
                    profile_dict["mood_trend"] = []
                try:
                    profile_dict["themes"] = json.loads(profile_dict.get("themes", '[]')) if profile_dict.get("themes") else []
                except (json.JSONDecodeError, TypeError):
                    profile_dict["themes"] = []

                # Гарантируем наличие новых полей (хотя миграция должна была их добавить)
                profile_dict.setdefault("initial_resource", None)
                profile_dict.setdefault("final_resource", None)
                profile_dict.setdefault("recharge_method", None)

                return profile_dict
            return None # Возвращаем None, если профиль не найден
        except sqlite3.Error as e:
             logger.error(f"Failed to get user profile for {user_id}: {e}", exc_info=True)
             return None


    def update_user_profile(self, user_id, profile_update_data):
        """Обновляет профиль пользователя (INSERT OR REPLACE)."""
        # Получаем текущий профиль, чтобы использовать его значения как дефолтные
        current_profile = self.get_user_profile(user_id) or {}

        # Обрабатываем время обновления
        last_updated_dt = profile_update_data.get("last_updated", current_profile.get("last_updated"))
        if isinstance(last_updated_dt, datetime):
            last_updated_iso = last_updated_dt.isoformat()
        else:
            # Если время не передано или некорректно, используем текущее
            if not isinstance(current_profile.get("last_updated"), datetime):
                 logger.warning(f"No valid last_updated time found for profile update user {user_id}. Using current time.")
            last_updated_iso = datetime.now(TIMEZONE).isoformat()


        # Подготавливаем данные для сохранения
        profile_to_save = {
            "user_id": user_id,
            "mood": profile_update_data.get("mood", current_profile.get("mood")),
            "mood_trend": json.dumps(profile_update_data.get("mood_trend", current_profile.get("mood_trend", []))),
            "themes": json.dumps(profile_update_data.get("themes", current_profile.get("themes", []))),
            "response_count": profile_update_data.get("response_count", current_profile.get("response_count", 0)),
            "request_count": profile_update_data.get("request_count", current_profile.get("request_count", 0)),
            "avg_response_length": profile_update_data.get("avg_response_length", current_profile.get("avg_response_length", 0)),
            "days_active": profile_update_data.get("days_active", current_profile.get("days_active", 0)),
            "interactions_per_day": profile_update_data.get("interactions_per_day", current_profile.get("interactions_per_day", 0)),
            "last_updated": last_updated_iso, # Всегда обновляем время
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
                     ) VALUES (:user_id, :mood, :mood_trend, :themes, :response_count, :request_count,
                               :avg_response_length, :days_active, :interactions_per_day, :last_updated,
                               :initial_resource, :final_resource, :recharge_method)
                 """, profile_to_save) # Используем именованные плейсхолдеры для удобства
        except sqlite3.Error as e:
            logger.error(f"Failed to update user profile for {user_id}: {e}", exc_info=True)
