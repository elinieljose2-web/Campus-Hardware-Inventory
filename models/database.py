import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


class Database:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")

        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL is not configured. "
                "Please add your Supabase PostgreSQL connection string to .env."
            )

    def get_connection(self):
        return psycopg.connect(self.database_url)

    def fetch_all(self, query, params=()):
        conn = self.get_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                columns = [desc.name for desc in cursor.description]
                rows = cursor.fetchall()

                return [
                    dict(zip(columns, row))
                    for row in rows
                ]
        finally:
            conn.close()

    def execute(self, query, params=()):
        conn = self.get_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
