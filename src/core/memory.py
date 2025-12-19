import sqlite3
import json
import os
from datetime import datetime
from src.core.config import Config

class MemoryManager:
    def __init__(self):
        self.config = Config()
        os.makedirs(os.path.dirname(self.config.DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(self.config.DB_PATH, check_same_thread=False)
        self._init_db()
        self._seed_saas_data()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS history
                          (id INTEGER PRIMARY KEY, role TEXT, content TEXT, timestamp TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS users
                          (id INTEGER PRIMARY KEY, name TEXT, email TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS stores
                          (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, 
                           industry TEXT, location TEXT, platform_version TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS sales
                          (id INTEGER PRIMARY KEY, store_id INTEGER, date TEXT, amount REAL, category TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS profile
                          (key TEXT PRIMARY KEY, value TEXT)''')
                          
        # --- NEW: INTERNAL WORKFLOW STORAGE ---
        # This simulates your Platform's Backend Database
        cursor.execute('''CREATE TABLE IF NOT EXISTS workflows
                          (id INTEGER PRIMARY KEY, 
                           store_id INTEGER, 
                           name TEXT, 
                           status TEXT, 
                           json_structure TEXT, 
                           created_at TEXT)''')
        self.conn.commit()

    def _seed_saas_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT count(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (id, name, email) VALUES (1, 'Nguyen Van A', 'user@example.com')")
            cursor.execute('''INSERT INTO stores (user_id, name, industry, location, platform_version) 
                              VALUES (1, 'BabyWorld Cầu Giấy', 'Mom & Baby', 'Hanoi - Cau Giay', 'Pro_v2')''')
            cursor.execute('''INSERT INTO stores (user_id, name, industry, location, platform_version) 
                              VALUES (1, 'Cafe Sáng', 'F&B', 'Da Nang', 'Lite_v1')''')
            # Seed Sales
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("INSERT INTO sales (store_id, date, amount, category) VALUES (1, ?, 2500000, 'Diapers')", (today,))
            self.conn.commit()

    def save_workflow(self, store_id, name, json_data):
        """Saves the AI-generated design to your platform's DB."""
        cursor = self.conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO workflows (store_id, name, status, json_structure, created_at) VALUES (?, ?, ?, ?, ?)",
                       (store_id, name, 'draft', json.dumps(json_data), now))
        self.conn.commit()
        return cursor.lastrowid

    def get_user_stores(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, industry, location FROM stores WHERE user_id = ?", (user_id,))
        return [{"id": r[0], "name": r[1], "industry": r[2], "location": r[3]} for r in cursor.fetchall()]

    def get_sales_data(self, store_id, metric="revenue_today"):
        cursor = self.conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        if metric == "revenue_today":
            cursor.execute("SELECT SUM(amount) FROM sales WHERE store_id = ? AND date = ?", (store_id, today))
            res = cursor.fetchone()[0]
            return f"{res:,.0f} VND" if res else "0 VND"
        return "No Data"

    def update_profile(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO profile (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

    def get_profile(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM profile")
        return {row[0]: row[1] for row in cursor.fetchall()}

    def add_message(self, role, content):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO history (role, content, timestamp) VALUES (?, ?, ?)",
                       (role, str(content), datetime.now().isoformat()))
        self.conn.commit()

    def get_context_string(self, limit=6):
        cursor = self.conn.cursor()
        cursor.execute("SELECT role, content FROM history ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        history = reversed(rows)
        formatted = []
        for role, content in history:
            role_name = "User" if role == "user" else "Assistant"
            formatted.append(f"{role_name}: {content}")
        return "\n".join(formatted)