from datetime import date, datetime, timedelta

from .db import get_db


def fmt_dur(sec):
    sec = int(sec or 0)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def fmt_clock(sec):
    sec = int(sec or 0)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _in(types):
    return ",".join("'%s'" % t for t in types if t in ("nq1", "nq2", "daily"))


def user_summary(user_id, quiz_types):
    db = get_db()
    ins = _in(quiz_types)
    rows = db.execute(f"SELECT * FROM game_history WHERE user_id=? AND quiz_type IN ({ins})", (user_id,)).fetchall()
    n = len(rows)
    corr = sum(r["correct"] for r in rows)
    wrong = sum(r["wrong"] for r in rows)
    qs = sum(r["questions_played"] for r in rows)
    score = sum(r["score"] for r in rows)
    secs = sum(r["time_seconds"] for r in rows)

    def best(field):
        if not rows:
            return 0, "-"
        r = max(rows, key=lambda x: x[field])
        return r[field], r["category_name"] or "-"

    bs, bsc = best("score")
    bq, bqc = best("questions_played")
    bc, bcc = best("correct")
    bw, bwc = best("wrong")
    bt, btc = best("time_seconds")
    return {
        "games": n, "correct": corr, "wrong": wrong, "score": score, "questions": qs,
        "time": fmt_dur(secs),
        "accuracy": round(100 * corr / qs, 2) if qs else 0.0,
        "avg_time": fmt_clock(secs / n) if n else "00:00",
        "avg_score": round(score / n, 2) if n else 0.0,
        "avg_questions": round(qs / n, 2) if n else 0.0,
        "correct_rate": round(100 * corr / qs, 2) if qs else 0.0,
        "wrong_rate": round(100 * wrong / qs, 2) if qs else 0.0,
        "best_score": bs, "best_score_cat": bsc,
        "max_q": bq, "max_q_cat": bqc, "max_correct": bc, "max_correct_cat": bcc,
        "max_wrong": bw, "max_wrong_cat": bwc, "max_time": fmt_dur(bt), "max_time_cat": btc,
        "avg_time_pct": min(100, (secs / n) / 6) if n else 0,
        "avg_score_pct": min(100, score / n / 10) if n else 0,
        "avg_q_pct": min(100, qs / n * 2) if n else 0,
    }


def category_performance(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT g.category_name name, SUM(questions_played) q, SUM(correct) c, SUM(wrong) w, MAX(score) best, "
        "c2.icon icon FROM game_history g LEFT JOIN categories c2 ON c2.name=g.category_name "
        "WHERE g.user_id=? AND g.quiz_type='nq1' GROUP BY g.category_name ORDER BY q DESC", (user_id,)).fetchall()
    return [{"name": r["name"], "icon": r["icon"] or "🎯", "q": r["q"], "c": r["c"], "w": r["w"],
             "acc": round(100 * r["c"] / r["q"]) if r["q"] else 0, "best": r["best"]} for r in rows]


def get_streak(user_id):
    r = get_db().execute("SELECT * FROM daily_progress WHERE user_id=?", (user_id,)).fetchone()
    if not r:
        return {"current": 0, "longest": 0, "played_today": False}
    cur = r["current_streak"]
    today = date.today()
    if r["last_play_date"] and r["last_play_date"] < (today - timedelta(days=1)).isoformat():
        cur = 0
    return {"current": cur, "longest": r["longest_streak"], "played_today": r["last_play_date"] == today.isoformat()}


def _period_start(period):
    now = datetime.now()
    if period == "today":
        return now.strftime("%Y-%m-%d 00:00:00")
    if period == "week":
        return (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d 00:00:00")
    if period == "month":
        return now.strftime("%Y-%m-01 00:00:00")
    return None


def leaderboard_rows(period):
    start = _period_start(period)
    where, args = "", []
    if start:
        where, args = "WHERE g.played_at >= ?", [start]
    return get_db().execute(
        "SELECT u.username, SUM(g.score) score, SUM(g.questions_played) q, COUNT(g.id) games, "
        f"SUM(g.time_seconds) secs FROM game_history g JOIN users u ON u.id=g.user_id {where} "
        "GROUP BY u.id ORDER BY score DESC, q DESC, u.username", args).fetchall()
