"""Quiz session logic. In-progress state lives in the active_quiz table (JSON)."""
import json
import time
from datetime import date, timedelta

from . import config
from .db import get_db, now_iso

TABLES = {"nq1": "questions_nq1", "nq2": "questions_nq2", "daily": "questions_daily"}


def _load(user_id):
    r = get_db().execute("SELECT state_json FROM active_quiz WHERE user_id=?", (user_id,)).fetchone()
    return json.loads(r["state_json"]) if r else None


def _save(user_id, st):
    db = get_db()
    db.execute("INSERT INTO active_quiz(user_id,state_json) VALUES(?,?) "
               "ON CONFLICT(user_id) DO UPDATE SET state_json=excluded.state_json",
               (user_id, json.dumps(st)))
    db.commit()


def _total(qtype, cat_id=None):
    db = get_db()
    if qtype == "nq1":
        return db.execute("SELECT total FROM categories WHERE id=?", (cat_id,)).fetchone()[0]
    return db.execute(f"SELECT COUNT(*) FROM {TABLES[qtype]}").fetchone()[0]


def daily_status(user_id):
    r = get_db().execute("SELECT * FROM daily_progress WHERE user_id=?", (user_id,)).fetchone()
    return r


def played_daily_today(user_id):
    r = daily_status(user_id)
    return bool(r and r["last_play_date"] == date.today().isoformat())


def start_quiz(user_id, qtype, key=None):
    db = get_db()
    cat_id, cat_name, start = None, "Play All Quiz", 0
    if qtype == "nq1":
        c = db.execute("SELECT * FROM categories WHERE key=?", (key,)).fetchone()
        if not c:
            return None, "Unknown category."
        cat_id, cat_name = c["id"], c["name"]
        p = db.execute("SELECT next_seq FROM category_progress WHERE user_id=? AND category_id=?",
                       (user_id, cat_id)).fetchone()
        start = p["next_seq"] if p else 0
    elif qtype == "nq2":
        p = db.execute("SELECT next_seq FROM nq2_progress WHERE user_id=?", (user_id,)).fetchone()
        start = p["next_seq"] if p else 0
    elif qtype == "daily":
        if played_daily_today(user_id):
            return None, "You have already played today's Daily Challenge. Come back tomorrow!"
        cat_name = "Daily Quiz"
        p = daily_status(user_id)
        start = p["next_seq"] if p else 0
    else:
        return None, "Unknown quiz type."
    total = _total(qtype, cat_id)
    if not total:
        return None, "No questions available."
    st = {"type": qtype, "key": key, "cat_id": cat_id, "cat_name": cat_name,
          "start": start % total, "total_ds": total, "started": time.time(),
          "hints_used": 0, "hints_max": config.MAX_HINTS_DAILY if qtype == "daily" else config.MAX_HINTS_NORMAL,
          "answers": {}, "hinted": [], "score": 0, "correct": 0, "wrong": 0,
          "max_index": config.DAILY_QUESTIONS_PER_DAY if qtype == "daily" else None}
    _save(user_id, st)
    return st, None


def get_state(user_id):
    return _load(user_id)


def public_state(st):
    return {"type": st["type"], "category": st["cat_name"], "hints_left": st["hints_max"] - st["hints_used"],
            "hints_max": st["hints_max"], "correct": st["correct"], "wrong": st["wrong"],
            "score": st["score"], "total": st["max_index"], "answered": len(st["answers"]),
            "elapsed": int(time.time() - st["started"])}


def _row(st, index):
    seq = (st["start"] + index) % st["total_ds"]
    db = get_db()
    t = TABLES[st["type"]]
    if st["type"] == "nq1":
        return db.execute(f"SELECT * FROM {t} WHERE category_id=? AND seq=?", (st["cat_id"], seq)).fetchone()
    return db.execute(f"SELECT * FROM {t} WHERE seq=?", (seq,)).fetchone()


def get_question(user_id, index):
    st = _load(user_id)
    if not st:
        return None, "No active quiz."
    if index < 0 or (st["max_index"] is not None and index >= st["max_index"]):
        return None, "Question out of range."
    r = _row(st, index)
    if not r:
        return None, "Question not found."
    k = str(index)
    out = {"index": index, "number": index + 1, "question": r["question"],
           "options": {"A": r["a"], "B": r["b"], "C": r["c"], "D": r["d"]},
           "answered": k in st["answers"], "choice": st["answers"].get(k, {}).get("choice"),
           "hinted": index in st["hinted"], "state": public_state(st)}
    if out["answered"] or out["hinted"]:
        out["correct_option"] = r["correct"]
        out["explanation"] = r["explanation"]
    return out, None


def submit_answer(user_id, index, choice):
    st = _load(user_id)
    if not st:
        return None, "No active quiz."
    choice = (choice or "").upper()
    if choice not in "ABCD" or len(choice) != 1:
        return None, "Invalid option."
    if st["max_index"] is not None and index >= st["max_index"]:
        return None, "Question out of range."
    k = str(index)
    r = _row(st, index)
    if k in st["answers"]:
        return None, "Already answered."
    ok = choice == r["correct"]
    if ok:
        st["correct"] += 1
        st["score"] += config.SCORE_CORRECT
    else:
        st["wrong"] += 1
        st["score"] = max(0, st["score"] + config.SCORE_WRONG)
    st["answers"][k] = {"choice": choice, "ok": ok}
    _save(user_id, st)
    return {"is_correct": ok, "correct_option": r["correct"], "explanation": r["explanation"],
            "state": public_state(st)}, None


def use_hint(user_id, index):
    st = _load(user_id)
    if not st:
        return None, "No active quiz."
    k = str(index)
    r = _row(st, index)
    if k in st["answers"] or index in st["hinted"]:
        return {"correct_option": r["correct"], "explanation": r["explanation"], "state": public_state(st)}, None
    if st["hints_used"] >= st["hints_max"]:
        return None, "No hints remaining." if st["hints_max"] else "Hints are not available in the Daily Quiz."
    st["hints_used"] += 1
    st["hinted"].append(index)
    _save(user_id, st)
    return {"correct_option": r["correct"], "explanation": r["explanation"], "state": public_state(st)}, None


def finish_and_save(user_id, client_time=None):
    st = _load(user_id)
    if not st:
        return None, "No active quiz."
    db = get_db()
    answered = len(st["answers"])
    elapsed = int(time.time() - st["started"])
    secs = elapsed
    if isinstance(client_time, (int, float)) and 0 <= client_time <= elapsed + 5:
        secs = int(client_time)
    if answered == 0:
        db.execute("DELETE FROM active_quiz WHERE user_id=?", (user_id,))
        db.commit()
        return {"saved": False, "message": "No questions answered, nothing saved."}, None
    qtype = st["type"]
    n = db.execute("SELECT COUNT(*) FROM game_history WHERE user_id=?", (user_id,)).fetchone()[0] + 1
    db.execute("INSERT INTO game_history(user_id,quiz_type,category_name,game_no,played_at,questions_played,"
               "correct,wrong,score,time_seconds,hints_used) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
               (user_id, qtype, st["cat_name"], n, now_iso(), answered, st["correct"], st["wrong"],
                st["score"], secs, st["hints_used"]))
    new_next = (st["start"] + answered) % st["total_ds"]
    if qtype == "nq1":
        db.execute("INSERT INTO category_progress(user_id,category_id,next_seq) VALUES(?,?,?) "
                   "ON CONFLICT(user_id,category_id) DO UPDATE SET next_seq=excluded.next_seq",
                   (user_id, st["cat_id"], new_next))
    elif qtype == "nq2":
        db.execute("INSERT INTO nq2_progress(user_id,next_seq) VALUES(?,?) "
                   "ON CONFLICT(user_id) DO UPDATE SET next_seq=excluded.next_seq", (user_id, new_next))
    else:
        today = date.today()
        p = daily_status(user_id)
        cur = p["current_streak"] if p else 0
        longest = p["longest_streak"] if p else 0
        last = p["last_play_date"] if p else None
        cur = cur + 1 if last == (today - timedelta(days=1)).isoformat() else 1
        longest = max(longest, cur)
        db.execute("INSERT INTO daily_progress(user_id,next_seq,last_play_date,answered_today,current_streak,longest_streak) "
                   "VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET next_seq=excluded.next_seq,"
                   "last_play_date=excluded.last_play_date,answered_today=excluded.answered_today,"
                   "current_streak=excluded.current_streak,longest_streak=excluded.longest_streak",
                   (user_id, new_next, today.isoformat(), answered, cur, longest))
    db.execute("DELETE FROM active_quiz WHERE user_id=?", (user_id,))
    db.commit()
    return {"saved": True, "questions": answered, "correct": st["correct"], "wrong": st["wrong"],
            "score": st["score"], "time": secs, "category": st["cat_name"]}, None


def exit_without_saving(user_id):
    db = get_db()
    db.execute("DELETE FROM active_quiz WHERE user_id=?", (user_id,))
    db.commit()
