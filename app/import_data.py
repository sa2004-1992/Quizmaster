"""Imports the gzip'd CSV datasets into SQLite on first run."""
import csv
import glob
import gzip
import os
import re
import sqlite3
import sys

from .config import DATA_DIR
from .categories_meta import CATEGORIES

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
_LETTER = re.compile(r"^\s*([ABCD])\s*[\).:\-]")


def _find_dataset_parts(base_path):
    """base_path without extension, e.g. .../daily_quiz or .../normal_quiz_2.
    Accepts a single file or numbered _partN files (.csv.gz or .csv)."""
    for ext in (".csv.gz", ".csv"):
        if os.path.exists(base_path + ext):
            return [base_path + ext]
    parts = glob.glob(base_path + "_part*.csv.gz") + glob.glob(base_path + "_part*.csv")
    def num(p):
        m = re.search(r"_part(\d+)", p)
        return int(m.group(1)) if m else 0
    return sorted(parts, key=num)


def _open(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", newline="", encoding="utf-8-sig")
    return open(path, "r", newline="", encoding="utf-8-sig")


def _rows(paths):
    for p in paths:
        with _open(p) as f:
            for r in csv.DictReader(f):
                yield r


def _letter(raw, row):
    raw = (raw or "").strip()
    m = _LETTER.match(raw)
    if m:
        return m.group(1)
    if raw[:1].upper() in "ABCD" and len(raw) == 1:
        return raw.upper()
    for L in "ABCD":  # fall back to text match
        if raw and raw == (row.get("Option " + L) or "").strip():
            return L
    return "A"


def _vals(r):
    return (r.get("Question", ""), r.get("Option A", ""), r.get("Option B", ""),
            r.get("Option C", ""), r.get("Option D", ""), _letter(r.get("Correct Answer"), r),
            r.get("Solution/Explanation", ""))


def _flush(conn, sql, batch):
    if batch:
        conn.executemany(sql, batch)
        batch.clear()


def import_nq1(conn):
    cdir = os.path.join(DATA_DIR, "categories")
    sql = ("INSERT INTO questions_nq1(category_id,seq,question,a,b,c,d,correct,explanation,subcategory)"
           " VALUES(?,?,?,?,?,?,?,?,?,?)")
    for pos, (key, name, icon) in enumerate(CATEGORIES, 1):
        paths = _find_dataset_parts(os.path.join(cdir, key))
        if not paths:
            continue
        cur = conn.execute("INSERT INTO categories(key,name,icon,position,total) VALUES(?,?,?,?,0)",
                           (key, name, icon, pos))
        cid, n, batch = cur.lastrowid, 0, []
        for r in _rows(paths):
            batch.append((cid, n) + _vals(r) + (r.get("Subcategory", ""),))
            n += 1
            if len(batch) >= 5000:
                _flush(conn, sql, batch)
        _flush(conn, sql, batch)
        conn.execute("UPDATE categories SET total=? WHERE id=?", (n, cid))


def _import_flat(conn, table, base):
    paths = _find_dataset_parts(os.path.join(DATA_DIR, base))
    sql = (f"INSERT INTO {table}(seq,question,a,b,c,d,correct,explanation,category,subcategory)"
           " VALUES(?,?,?,?,?,?,?,?,?,?)")
    n, batch = 0, []
    for r in _rows(paths):
        batch.append((n,) + _vals(r) + (r.get("Category", ""), r.get("Subcategory", "")))
        n += 1
        if len(batch) >= 5000:
            _flush(conn, sql, batch)
    _flush(conn, sql, batch)
    return n


def run_import(db_path, only=None):
    """Import datasets. `only` = subset of {"nq1","nq2","daily"}; default all.
    Only the listed datasets are (re)imported, user data is never touched."""
    only = set(only or ("nq1", "nq2", "daily"))
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    if "nq1" in only:
        for t in ("questions_nq1", "categories"):
            conn.execute(f"DELETE FROM {t}")
        import_nq1(conn)
    if "nq2" in only:
        conn.execute("DELETE FROM questions_nq2")
        if not _find_dataset_parts(os.path.join(DATA_DIR, "normal_quiz_2")):
            print("WARNING: Normal Quiz 2 files not found in app/data_source/ "
                  "(normal_quiz_2_part1.csv.gz and normal_quiz_2_part2.csv.gz).")
        else:
            _import_flat(conn, "questions_nq2", "normal_quiz_2")
    if "daily" in only:
        conn.execute("DELETE FROM questions_daily")
        _import_flat(conn, "questions_daily", "daily_quiz")
    conn.commit()
    conn.close()
