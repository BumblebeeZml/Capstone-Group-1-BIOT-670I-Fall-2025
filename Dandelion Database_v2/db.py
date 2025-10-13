from contextlib import contextmanager
import sqlite3
import os
from pathlib import Path

# Project directory
BASE_DIR = Path(__file__).resolve().parent

# DB and schema live alongside your code by default
DB_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "Tables.db"))
SCHEMA_PATH = os.environ.get("SCHEMA_PATH", str(BASE_DIR / "schema.sql"))

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_conn_cm():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db(schema_path: str = SCHEMA_PATH):
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with get_conn_cm() as conn:
        conn.executescript(schema_sql)

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    # initialize if tables missing
    with get_conn_cm() as conn:
        has_files = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='files';"
        ).fetchone() is not None
        has_users = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users';"
        ).fetchone() is not None
    if not (has_files and has_users):
        init_db()
