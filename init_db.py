import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()   # lets `python init_db.py` read DATABASE_URL from .env

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def get_db_connection():
    return psycopg.connect(
        os.environ["DATABASE_URL"],
        row_factory=dict_row,      # rows behave like dicts: row["id"]
        prepare_threshold=None,
    )


def init_db():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        script = f.read()
    with get_db_connection() as conn:     # commits on success, then closes
        conn.execute(script)             
    print("Database initialized.")


if __name__ == "__main__":
    init_db()