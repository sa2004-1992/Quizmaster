import os
from flask import Flask, g, session

from . import config
from .db import init_db, init_questions, get_db


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["DATABASE_PATH"] = config.DATABASE_PATH
    app.config["DATABASE_URL"] = config.DATABASE_URL
    app.config["QUESTIONS_PATH"] = config.QUESTIONS_PATH
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    if config.SECRET_KEY == "dev-secret-change-me":
        print("WARNING: using the default SECRET_KEY. Set QUIZMASTER_SECRET_KEY in production.")

    init_db(app)
    init_questions(app)

    from .auth import bp as auth_bp
    from .routes import bp as main_bp
    from .api import bp as api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.before_request
    def load_user():
        g.user = None
        uid = session.get("user_id")
        if uid:
            g.user = get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
            if g.user is None:
                session.clear()

    @app.context_processor
    def inject():
        return {"current_user": g.get("user")}

    return app
