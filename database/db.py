import sqlite3
import json
from datetime import datetime
import os
from config import TIMEZONE

class Database:
    def __init__(self, path="/data/bot.db"):
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        sqlite3.register_adapter(datetime, lambda val: val.isoformat())
        sqlite3.register_converter("timestamp", lambda val: datetime.fromisoformat(val.decode()))
        self.conn.row_factory = sqlite3.Row
        self.bot = None
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    last_request TEXT,
                    reminder_time TEXT,
                    bonus_available BOOLEAN DEFAULT FALSE
                )""")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_cards (
                    user_id INTEGER,
                    card_number INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    name TEXT,
                    action TEXT,
                    details TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_id) REFERENCES users(user_id)
                )""")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS card_feedback (
                    user_id INTEGER,
                    card_number INTEGER,
                    answer TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    user_id INTEGER,
                    name TEXT,
                    feedback TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_requests (
                    user_id INTEGER,
                    request TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    mood TEXT,
                    mood_trend TEXT,
                    themes TEXT,
                    response_count INTEGER,
                    request_count INTEGER,
                    avg_response_length REAL,
                    days_active INTEGER,
                    interactions_per_day REAL,
                    last_updated TEXT
                )""")
            # Новая таблица для хранения ресурсного состояния
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS resource_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id INTEGER,
                    initial_state TEXT,  -- 😊, 😐, 😔
                    final_state TEXT,   -- 😊, 😐, 😔
                    recovery_method TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")

    def get_user(self, user_id):
        cursor = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            last_request_val = row["last_request"]
            last_request_dt = None
            if last_request_val:
                try:
                    if 'Z' in last_request_val:
                        last_request_val = last_request_val.replace('Z', '+00:00')
                    elif '+' not in last_request_val and '-' not in last_request_val[10:]:
                        pass
                    last_request_dt = datetime.fromisoformat(last_request_val)
                except ValueError as e:
                    print(f"Error parsing last_request '{last_request_val}' for user {user_id}: {e}")
                    last_request_dt = None
            return {
                "user_id": row["user_id"],
                "name": row["name"],
                "username": row["username"],
                "last_request": last_request_dt,
                "reminder_time": row["reminder_time"],
                "bonus_available": bool(row["bonus_available"])
            }
        return {"user_id": user_id, "name": "", "username": "", "last_request": None, "reminder_time": None, "bonus_available": False}

    def update_user(self, user_id, data):
        current_user_data = self.get_user(user_id)
        last_request_to_save = None
        if "last_request" in data:
            last_request_to_save = data["last_request"]
            if not isinstance(last_request_to_save, str):
                print(f"Warning: last_request passed to update_user is not a string for user {user_id}. Type: {type(last_request_to_save)}. Trying to convert.")
                try:
                    last_request_to_save = last_request_to_save.isoformat()
                except AttributeError:
                    print(f"Error: Could not convert last_request to string for user {user_id}. Using None.")
                    last_request_to_save = None
        else:
            current_last_request_dt = current_user_data["last_request"]
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
                data.get("name", current_user_data["name"]),
                data.get("username", current_user_data["username"]),
                last_request_to_save,
                data.get("reminder_time", current_user_data["reminder_time"]),
                data.get("bonus_available", current_user_data["bonus_available"])
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
        with self.conn:
            self.conn.execute(
                "INSERT INTO actions (user_id, username, name, action, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, name, action, json.dumps(details), timestamp_str)
            )

    def get_actions(self, user_id=None):
        if user_id:
            cursor = self.conn.execute("SELECT * FROM actions WHERE user_id = ? ORDER BY timestamp ASC", (user_id,))
        else:
            cursor = self.conn.execute("SELECT * FROM actions ORDER BY timestamp ASC")
        actions = []
        for row in cursor.fetchall():
            try:
                details_dict = json.loads(row["details"])
            except json.JSONDecodeError:
                details_dict = {"error": "invalid_json"}
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
        last_request_dt = self.get_user(user_id)["last_request"]
        if last_request_dt:
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
                    print(f"Error parsing last_updated '{last_updated_val}' for profile user {user_id}: {e}")
                    last_updated_dt = None
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
                "last_updated": last_updated_dt
            }
        return None

    def update_user_profile(self, user_id, profile):
        last_updated_dt = profile.get("last_updated")
        if isinstance(last_updated_dt, datetime):
            last_updated_iso = last_updated_dt.isoformat()
        else:
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
                json.dumps(profile.get("mood_trend", [])),
                json.dumps(profile.get("themes", [])),
                profile.get("response_count"),
                profile.get("request_count"),
                profile.get("avg_response_length"),
                profile.get("days_active"),
                drob.get("interactions_per_day"),
                last_updated_iso
            ))

    # Новые методы для работы с ресурсным состоянием
    def save_resource_state(self, user_id, session_id, initial_state, final_state=None, recovery_method=None):
        timestamp = datetime.now(TIMEZONE).isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO resource_states (user_id, session_id, initial_state, final_state, recovery_method, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, session_id, initial_state, final_state, recovery_method, timestamp))

    def update_resource_final_state(self, user_id, session_id, final_state, recovery_method=None):
        timestamp = datetime.now(TIMEZONE).isoformat()
        with self.conn:
            self.conn.execute("""
                UPDATE resource_states
                SET final_state = ?, recovery_method = ?, timestamp = ?
                WHERE user_id = ? AND session_id = ?
            """, (final_state, recovery_method, timestamp, user_id, session_id))
