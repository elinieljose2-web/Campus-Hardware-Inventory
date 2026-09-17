import sqlite3
import os

class Database:
    def __init__(self, db_name="hardware_inventory.db"):
        # Points directly to hardware_inventory.db in the root project folder
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_name)
        
        # Fallback to current working directory if root resolution differs
        if not os.path.exists(self.db_path):
            self.db_path = db_name

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def fetch_all(self, query, params=()):
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def execute(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()