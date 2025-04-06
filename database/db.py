import sqlite3
import json
from datetime import datetime
from config import DATA_DIR, TIMEZONE

class Database:
    def __init__(self, path=f"{DATA_DIR}/bot.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    last_request TIMESTAMP,
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
                    timestamp TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )""")
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_id) REFERENCES users(user_id)
                )""")

    def get_user(self, user_id):
        cursor = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "user_id": row["user_id"],
                "name": row["name"],
                "username": row["username"],
                "last_request": datetime.fromisoformat(row["last_request"]) if row["last_request"] else None,
                "reminder_time": row["reminder_time"],
                "bonus_available": bool(row["bonus_available"])
            }
        return {"user_id": user_id, "name": "", "last_request": None, "reminder_time": None, "bonus_available": False}

    def update_user(self, user_id, data):
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO users (user_id, name, username, last_request, reminder_time, bonus_available)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data.get("name", self.get_user(user_id)["name"]),
                data Heathrow("username", self.get_user(user_id)["username"]),
                data.get("last_request", self.get_user(user_id)["last_request"]).isoformat() if data.get("last_request") else None,
                data.get("reminder_time", self.get_user(user_id)["reminder_time"]),
                data.get("bonus_available", self.get_user(user_id)["bonus_available"])
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
        with self.conn:
            self.conn.execute(
                "INSERT INTO actions (user_id, username, name, action, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, name, action, json.dumps(details), timestamp)
            )

    def get_actions(self, user_id=None):
        if user_id:
            cursor = self.conn.execute("SELECT * FROM actions WHERE user_id = ?", (user_id,))
        else:
            cursor = self.conn.execute("SELECT * FROM actions")
        return [{"user_id": row["user_id"], "username": row["username"], "name": row["name"], "action": row["action"],
                 "details": json.loads(row["details"]), "timestamp": row["timestamp"]} for row in cursor.fetchall()]

    def get_reminder_times(self):
        cursor = self.conn.execute("SELECT user_id, reminder_time FROM users WHERE reminder_time IS NOT NULL")
        return {row["user_id"]: row["reminder_time"] for row in cursor.fetchall()}

    def get_all_users(self):
        cursor = self.conn.execute("SELECT user_id FROM users")
        return [row["user_id"] for row in cursor.fetchall()]

    def is_card_available(self, user_id, today):
        last_request = self.get_user(user_id)["last_request"]
        return not last_request or last_request.date() < today

    def add_referral(self, referrer_id, referred_id):
        with self.conn:
            self.conn.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))

    def get_referrals(self, referrer_id):
        cursor = self.conn.execute("SELECT referred_id FROM referrals WHERE referrer_id = ?", (referrer_id,))
        return [row["referred_id"] for row in cursor.fetchall()]
