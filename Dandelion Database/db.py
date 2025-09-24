from contextlib import contextmanager
import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "Tables.db"))
SCHEMA_PATH = os.environ.get("SCHEMA_PATH", os.path.join(BASE_DIR, "schema.sql"))

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_conn_cm():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()

def _table_exists(conn, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,),
    )
    return cur.fetchone() is not None

def init_db(schema_path: str = SCHEMA_PATH):
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with get_conn() as conn:
        conn.executescript(schema_sql)

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with get_conn_cm() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files';")
        if not cur.fetchone():
            init_db()