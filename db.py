import sqlite3
import json
from datetime import datetime
import os
from config import TIMEZONE # Убедись, что TIMEZONE импортирован правильно

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
            # Таблица user_profiles: last_updated теперь TEXT
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
                    last_updated TEXT  -- Изменен на TEXT
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
                         # Попытка добавить UTC, если таймзона отсутствует (опасно, если время локальное)
                         # Лучше всегда сохранять с таймзоной из TIMEZONE
                         # last_request_val += '+00:00'
                         pass # Оставим как есть, если нет таймзоны - fromisoformat справится
                    last_request_dt = datetime.fromisoformat(last_request_val)
                except ValueError as e:
                    print(f"Error parsing last_request '{last_request_val}' for user {user_id}: {e}") # Логирование ошибки
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
        return {"user_id": user_id, "name": "", "username": "", "last_request": None, "reminder_time": None, "bonus_available": False}

   def update_user(self, user_id, data):
        # Получаем текущие данные пользователя ОДИН РАЗ, чтобы избежать лишних запросов
        # Используем try-except на случай, если get_user вернет None или вызовет ошибку
        try:
            current_user_data = self.get_user(user_id)
            if current_user_data is None: # get_user может вернуть None, если использовать другую логику
                 # Создаем дефолтную структуру, если пользователя нет, чтобы избежать ошибок ниже
                 current_user_data = {"user_id": user_id, "name": "", "username": "", "last_request": None, "reminder_time": None, "bonus_available": False}
        except Exception as e:
             print(f"Error fetching current user data for {user_id} in update_user: {e}")
             # В случае ошибки используем дефолтную структуру
             current_user_data = {"user_id": user_id, "name": "", "username": "", "last_request": None, "reminder_time": None, "bonus_available": False}


        # --- Начало исправления для last_request ---
        last_request_to_save = None
        if "last_request" in data:
            # Если передано новое значение (ожидается строка ISO)
            new_last_request_value = data["last_request"]
            if isinstance(new_last_request_value, str):
                 last_request_to_save = new_last_request_value # Используем строку напрямую
            elif isinstance(new_last_request_value, datetime):
                 # Если вдруг передали datetime, конвертируем (но это не ожидается из card_of_the_day)
                 print(f"Warning: last_request passed as datetime to update_user for {user_id}. Converting.")
                 last_request_to_save = new_last_request_value.isoformat()
            else:
                 print(f"Error: Invalid type for last_request passed to update_user for {user_id}. Type: {type(new_last_request_value)}. Using None.")
                 last_request_to_save = None # Обнуляем при неверном типе
        else:
            # Если новое значение НЕ передано, используем текущее из БД (get_user вернул datetime или None)
            current_last_request_dt = current_user_data.get("last_request") # Используем .get для безопасности
            if isinstance(current_last_request_dt, datetime):
                last_request_to_save = current_last_request_dt.isoformat() # Преобразуем в строку ISO
            else:
                # Если текущего значения нет или оно не datetime (например, None или старая строка), сохраняем None
                last_request_to_save = None
        # --- Конец исправления для last_request ---

        # Используем текущие данные как основу и обновляем их из data
        name_to_save = data.get("name", current_user_data.get("name"))
        username_to_save = data.get("username", current_user_data.get("username"))
        reminder_time_to_save = data.get("reminder_time", current_user_data.get("reminder_time"))
        bonus_available_to_save = data.get("bonus_available", current_user_data.get("bonus_available"))

        # Преобразуем boolean в integer для SQLite
        bonus_available_int = 1 if bonus_available_to_save else 0

        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO users (user_id, name, username, last_request, reminder_time, bonus_available)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                name_to_save,
                username_to_save,
                last_request_to_save, # Используем подготовленное значение (строка ISO или None)
                reminder_time_to_save,
                bonus_available_int # Сохраняем 0 или 1
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
         # Убедимся, что timestamp это строка ISO
         if isinstance(timestamp, datetime):
             timestamp_str = timestamp.isoformat()
         elif isinstance(timestamp, str):
             timestamp_str = timestamp # Уже строка
         else:
             timestamp_str = datetime.now(TIMEZONE).isoformat() # Fallback

         with self.conn:
            self.conn.execute(
                "INSERT INTO actions (user_id, username, name, action, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, name, action, json.dumps(details), timestamp_str) # Сохраняем строку
            )

    def get_actions(self, user_id=None):
        if user_id:
            cursor = self.conn.execute("SELECT * FROM actions WHERE user_id = ? ORDER BY timestamp ASC", (user_id,)) # Добавил сортировку
        else:
            cursor = self.conn.execute("SELECT * FROM actions ORDER BY timestamp ASC") # Добавил сортировку
        actions = []
        for row in cursor.fetchall():
            try:
                details_dict = json.loads(row["details"])
            except json.JSONDecodeError:
                details_dict = {"error": "invalid_json"}

            # timestamp уже строка из БД (тип TEXT)
            timestamp_str = row["timestamp"]

            actions.append({
                "user_id": row["user_id"],
                "username": row["username"],
                "name": row["name"],
                "action": row["action"],
                "details": details_dict,
                "timestamp": timestamp_str # Возвращаем строку ISO
            })
        return actions


    def get_reminder_times(self):
        cursor = self.conn.execute("SELECT user_id, reminder_time FROM users WHERE reminder_time IS NOT NULL")
        return {row["user_id"]: row["reminder_time"] for row in cursor.fetchall()}

    def get_all_users(self):
        cursor = self.conn.execute("SELECT user_id FROM users")
        return [row["user_id"] for row in cursor.fetchall()]

    def is_card_available(self, user_id, today):
        # get_user уже возвращает datetime или None
        last_request_dt = self.get_user(user_id)["last_request"]
        if last_request_dt:
            # Сравниваем только даты
            return last_request_dt.astimezone(TIMEZONE).date() < today
        return True # Если запросов не было, карта доступна

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
            # Преобразуем строку ISO обратно в datetime
            if last_updated_val:
                 try:
                     if 'Z' in last_updated_val: # Обработка 'Z'
                          last_updated_val = last_updated_val.replace('Z', '+00:00')
                     last_updated_dt = datetime.fromisoformat(last_updated_val)
                 except ValueError as e:
                     print(f"Error parsing last_updated '{last_updated_val}' for profile user {user_id}: {e}")
                     last_updated_dt = None

            # Безопасная загрузка JSON
            try:
                 mood_trend_list = json.loads(row["mood_trend"]) if row["mood_trend"] else []
            except json.JSONDecodeError:
                 mood_trend_list = []
            try:
                 themes_list = json.loads(row["themes"]) if row["themes"] else []
            except json.JSONDecodeError:
                 themes_list = []

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
                "last_updated": last_updated_dt # Возвращаем datetime или None
            }
        return None # Возвращаем None, если профиль не найден

    def update_user_profile(self, user_id, profile):
         # Убедимся, что last_updated это datetime объект перед форматированием
         last_updated_dt = profile.get("last_updated")
         if isinstance(last_updated_dt, datetime):
             last_updated_iso = last_updated_dt.isoformat()
         else:
             # Если объект не datetime, используем текущее время
             print(f"Warning: last_updated in profile for user {user_id} is not datetime. Using current time.")
             last_updated_iso = datetime.now(TIMEZONE).isoformat()

         with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO user_profiles (
                    user_id, mood, mood_trend, themes, response_count, request_count,
                    avg_response_length, days_active, interactions_per_day, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                profile.get("mood"),
                json.dumps(profile.get("mood_trend", [])), # Сериализуем в JSON
                json.dumps(profile.get("themes", [])),     # Сериализуем в JSON
                profile.get("response_count"),
                profile.get("request_count"),
                profile.get("avg_response_length"),
                profile.get("days_active"),
                profile.get("interactions_per_day"),
                last_updated_iso # Сохраняем строку ISO
            ))
