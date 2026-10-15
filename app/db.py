"""Two databases:
  * user database   - accounts, progress, history. Supabase PostgreSQL when DATABASE_URL
                      is set, otherwise a local SQLite file.
  * question bank   - local read-only SQLite file, rebuilt from app/data_source on start.
"""
import os
import sqlite3
from datetime import datetime
from decimal import Decimal
from flask import g, current_app

HERE = os.path.dirname(__file__)


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- PostgreSQL wrapper
class Row(dict):
    """dict-like row that also supports row[0] (same as sqlite3.Row)."""

    def __init__(self, cols, vals):
        vals = [self._num(v) for v in vals]
        super().__init__(zip(cols, vals))
        self._vals = vals

    @staticmethod
    def _num(v):
        if isinstance(v, Decimal):
            return int(v) if v == v.to_integral_value() else float(v)
        return v

    def __getitem__(self, k):
        if isinstance(k, int):
            return self._vals[k]
        return dict.__getitem__(self, k)


class _Cursor:
    def __init__(self, cur):
        self._c = cur

    def _row(self, r):
        return Row([d.name for d in self._c.description], r)

    def fetchone(self):
        r = self._c.fetchone()
        return None if r is None else self._row(r)

    def fetchall(self):
        return [self._row(r) for r in self._c.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


class PGConn:
    """Gives a psycopg connection the small sqlite3-style API the app uses."""

    def __init__(self, url):
        import psycopg
        # prepare_threshold=None: required for Supabase's transaction pooler.
        self._conn = psycopg.connect(url, prepare_threshold=None, connect_timeout=15)

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql.replace("?", "%s"), tuple(params))
        return _Cursor(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.rollback()
        finally:
            self._conn.close()


def _sqlite(path):
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def connect_user_db(app):
    url = app.config["DATABASE_URL"]
    return PGConn(url) if url else _sqlite(app.config["DATABASE_PATH"])


# ---------------------------------------------------------------- request-scoped getters
def get_db():
    if "db" not in g:
        g.db = connect_user_db(current_app)
    return g.db


def get_qdb():
    if "qdb" not in g:
        g.qdb = _sqlite(current_app.config["QUESTIONS_PATH"])
    return g.qdb


def close_db(e=None):
    for k in ("db", "qdb"):
        c = g.pop(k, None)
        if c is not None:
            c.close()


# ---------------------------------------------------------------- initialisation
def _read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def _migrate_sqlite(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)")]
    if "full_name" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
    if "gender" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN gender TEXT")


def init_db(app):
    """Create the user tables (idempotent)."""
    if app.config["DATABASE_URL"]:
        conn = PGConn(app.config["DATABASE_URL"])
        for stmt in _read("schema_user_postgres.sql").split(";"):
            if stmt.strip():
                conn.execute(stmt)
        conn.commit()
        conn.close()
        print("User database: Supabase / PostgreSQL")
    else:
        path = app.config["DATABASE_PATH"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
        conn.executescript(_read("schema_user_sqlite.sql"))
        _migrate_sqlite(conn)
        conn.commit()
        conn.close()
        print("User database: local SQLite (" + path + ")")
    app.teardown_appcontext(close_db)


def init_questions(app):
    """Make sure the local question bank exists and is complete."""
    from .import_data import run_import
    path = app.config["QUESTIONS_PATH"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        tmp = path + ".tmp"
        if os.path.exists(tmp):
            os.remove(tmp)
        c = sqlite3.connect(tmp)
        c.executescript(_read("schema_questions.sql"))
        c.close()
        print("Building the question bank (about 10-20 seconds)...")
        run_import(tmp)
        os.replace(tmp, path)
        print("Question bank ready.")
        return
    conn = sqlite3.connect(path)
    conn.executescript(_read("schema_questions.sql"))
    todo = [n for n, t in (("nq1", "questions_nq1"), ("nq2", "questions_nq2"), ("daily", "questions_daily"))
            if conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0]
    conn.commit()
    conn.close()
    if todo:
        print("Importing quiz datasets:", ", ".join(todo))
        run_import(path, only=todo)
        print("Import finished.")
