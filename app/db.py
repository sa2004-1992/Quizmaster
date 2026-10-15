import os
import sqlite3
from datetime import datetime
from flask import g, current_app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"], timeout=30)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _migrate(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)")]
    if "full_name" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
    if "gender" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN gender TEXT")


def init_db(app):
    path = app.config["DATABASE_PATH"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    _migrate(conn)
    conn.commit()
    conn.close()
    app.teardown_appcontext(close_db)
