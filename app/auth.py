import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from .db import get_db, now_iso

bp = Blueprint("auth", __name__)
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("main.home"))
    form = {}
    if request.method == "POST":
        form = {k: (request.form.get(k) or "").strip() for k in
                ("full_name", "email", "username", "gender")}
        pw, pw2 = request.form.get("password") or "", request.form.get("confirm_password") or ""
        err = None
        if not all(form.values()) or not pw or not pw2:
            err = "Please fill in all required fields."
        elif form["gender"] not in GENDER_OPTIONS:
            err = "Please select a valid gender option."
        elif not EMAIL_RE.match(form["email"]):
            err = "Please enter a valid email address."
        elif len(pw) < 6:
            err = "Password must be at least 6 characters."
        elif pw != pw2:
            err = "Passwords do not match."
        else:
            db = get_db()
            if db.execute("SELECT 1 FROM users WHERE lower(username)=lower(?)", (form["username"],)).fetchone():
                err = "That username is already taken."
            elif db.execute("SELECT 1 FROM users WHERE lower(email)=lower(?)", (form["email"],)).fetchone():
                err = "That email is already registered."
        if err:
            flash(err, "error")
        else:
            cur = db.execute("INSERT INTO users(username,email,password_hash,full_name,gender,joined_at) "
                             "VALUES(?,?,?,?,?,?) RETURNING id",
                             (form["username"], form["email"].lower(), generate_password_hash(pw),
                              form["full_name"], form["gender"], now_iso()))
            new_id = cur.fetchone()["id"]  # read before commit (RETURNING)
            db.commit()
            session.clear()
            session["user_id"] = new_id
            return redirect(url_for("main.home"))
    return render_template("register.html", form=form, genders=GENDER_OPTIONS)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("main.home"))
    if request.method == "POST":
        ident = (request.form.get("identifier") or "").strip()
        pw = request.form.get("password") or ""
        u = get_db().execute("SELECT * FROM users WHERE lower(username)=lower(?) OR lower(email)=lower(?)",
                             (ident, ident)).fetchone()
        if u and check_password_hash(u["password_hash"], pw):
            session.clear()
            session["user_id"] = u["id"]
            return redirect(url_for("main.home"))
        flash("Invalid username/email or password.", "error")
    return render_template("login.html")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
