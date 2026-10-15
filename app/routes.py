from datetime import datetime, date
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, g, flash, abort

from .db import get_db, get_qdb
from . import quiz_engine as qe
from . import stats

bp = Blueprint("main", __name__)


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not g.user:
            return redirect(url_for("auth.login"))
        return f(*a, **k)
    return w


def _fmt_date(s):
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        return s


@bp.route("/")
@login_required
def home():
    uid = g.user["id"]
    return render_template("home.html", active="home", streak=stats.get_streak(uid),
                           played_today=qe.played_daily_today(uid))


@bp.route("/quizzes")
@login_required
def quizzes():
    q = (request.args.get("q") or "").strip().lower()
    cats = get_qdb().execute("SELECT * FROM categories ORDER BY position").fetchall()
    if q:
        cats = [c for c in cats if q in c["name"].lower() or q in c["key"].lower()]
    return render_template("quizzes.html", active="quizzes", cats=cats, q=q)


@bp.route("/play/nq1/<key>")
@login_required
def play_nq1(key):
    c = get_qdb().execute("SELECT * FROM categories WHERE key=?", (key,)).fetchone()
    if not c:
        abort(404)
    return render_template("play.html", qtype="nq1", key=key, title=c["name"], icon=c["icon"],
                           today=date.today().strftime("%d %b %Y"))


@bp.route("/play/nq2")
@login_required
def play_nq2():
    return render_template("play.html", qtype="nq2", key="", title="Play All Quiz", icon="🌐",
                           today=date.today().strftime("%d %b %Y"))


@bp.route("/play/daily")
@login_required
def play_daily():
    if qe.played_daily_today(g.user["id"]):
        flash("You have already played today's Daily Challenge. Come back tomorrow!", "info")
        return redirect(url_for("main.home"))
    return render_template("play.html", qtype="daily", key="", title="Daily Quiz", icon="📅",
                           today=date.today().strftime("%d %b %Y"))


@bp.route("/history")
@login_required
def history():
    uid = g.user["id"]
    q = (request.args.get("q") or "").strip()
    cat = (request.args.get("category") or "").strip()
    d1 = (request.args.get("from_date") or "").strip()
    d2 = (request.args.get("to_date") or "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    where, args = ["user_id=?"], [uid]
    if q:
        where.append("(lower(category_name) LIKE lower(?) OR lower('Game #' || CAST(game_no AS TEXT)) LIKE lower(?))")
        args += [f"%{q}%", f"%{q}%"]
    if cat:
        where.append("category_name=?")
        args.append(cat)
    if d1:
        where.append("substr(played_at,1,10)>=?")
        args.append(d1)
    if d2:
        where.append("substr(played_at,1,10)<=?")
        args.append(d2)
    w = " AND ".join(where)
    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM game_history WHERE {w}", args).fetchone()[0]
    per = 15
    pages = max(1, (total + per - 1) // per)
    page = min(page, pages)
    rows = db.execute(f"SELECT * FROM game_history WHERE {w} ORDER BY played_at DESC, id DESC LIMIT ? OFFSET ?",
                      args + [per, (page - 1) * per]).fetchall()
    icons = {c["name"]: c["icon"] for c in get_qdb().execute("SELECT name, icon FROM categories")}
    icons["Play All Quiz"], icons["Daily Quiz"] = "🌐", "📅"
    names = [r[0] for r in db.execute("SELECT DISTINCT category_name FROM game_history WHERE user_id=? "
                                      "ORDER BY category_name", (uid,))]
    items = [{"date": _fmt_date(r["played_at"]), "no": r["game_no"], "cat": r["category_name"],
              "icon": icons.get(r["category_name"], "🎯"), "type": r["quiz_type"],
              "time": stats.fmt_clock(r["time_seconds"]), "score": r["score"], "q": r["questions_played"],
              "c": r["correct"], "w": r["wrong"]} for r in rows]
    return render_template("history.html", active="history", items=items, total=total, page=page, pages=pages,
                           per=per, q=q, cat=cat, d1=d1, d2=d2, names=names,
                           first=(page - 1) * per + 1 if total else 0, last=min(total, page * per))


@bp.route("/leaderboard")
@login_required
def leaderboard():
    period = request.args.get("period", "all")
    if period not in ("all", "month", "week", "today"):
        period = "all"
    page = max(1, request.args.get("page", 1, type=int))
    rows = stats.leaderboard_rows(period)
    total = len(rows)
    per = 15
    pages = max(1, (total + per - 1) // per)
    page = min(page, pages)
    start = (page - 1) * per
    items = [{"rank": start + i + 1, "name": r["username"], "score": r["score"], "q": r["q"],
              "games": r["games"], "time": stats.fmt_dur(r["secs"])} for i, r in enumerate(rows[start:start + per])]
    return render_template("leaderboard.html", active="leaderboard", items=items, period=period, page=page,
                           pages=pages, total=total, first=start + 1 if total else 0, last=min(total, start + per),
                           me=g.user["username"])


@bp.route("/profile")
@login_required
def profile():
    uid = g.user["id"]
    return render_template("profile.html", active="profile", s=stats.user_summary(uid, ["nq1"]),
                           cats=stats.category_performance(uid), streak=stats.get_streak(uid),
                           joined=_fmt_date(g.user["joined_at"]))


@bp.route("/all-quiz")
@login_required
def all_quiz():
    return render_template("all_quiz.html", active="all_quiz", s=stats.user_summary(g.user["id"], ["nq2"]))


@bp.post("/profile/clear-data")
@login_required
def clear_data():
    uid = g.user["id"]
    db = get_db()
    for t in ("game_history", "category_progress", "nq2_progress", "daily_progress", "active_quiz"):
        db.execute(f"DELETE FROM {t} WHERE user_id=?", (uid,))
    db.commit()
    flash("All your quiz data has been cleared.", "success")
    return redirect(url_for("main.profile"))


@bp.post("/toggle-dark-mode")
@login_required
def toggle_dark():
    db = get_db()
    db.execute("UPDATE users SET dark_mode = 1 - COALESCE(dark_mode,0) WHERE id=?", (g.user["id"],))
    db.commit()
    return ("", 204)
