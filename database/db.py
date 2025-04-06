import sqlite3
from datetime import datetime
from config import TIMEZONE

class Database:
    def __init__(self, path=f"{DATA_DIR}/bot.db"):
        self.conn = sqlite3.connect(path)
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

    def get_user(self, user_id):
        cursor = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return {"user_id": row[0], "name": row[1], "last_request": datetime.fromisoformat(row[3]) if row[3] else None} if row else {}

    def update_last_request(self, user_id, timestamp):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO users (user_id, last_request) VALUES (?, ?)", (user_id, timestamp.isoformat()))

    def save_action(self, user_id, username, name, action, details, timestamp):
        with self.conn:
            self.conn.execute("INSERT INTO actions (user_id, username, name, action, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                              (user_id, username, name, action, str(details), timestamp))
