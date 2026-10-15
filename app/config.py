import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

SECRET_KEY = os.environ.get("QUIZMASTER_SECRET_KEY", "dev-secret-change-me")
DATABASE_PATH = os.environ.get(
    "QUIZMASTER_DATABASE_PATH", os.path.join(BASE_DIR, "instance", "quizmaster.db"))
DATA_DIR = os.path.join(os.path.dirname(__file__), "data_source")

SCORE_CORRECT = 10
SCORE_WRONG = -5
DAILY_QUESTIONS_PER_DAY = 50
MAX_HINTS_NORMAL = 5
MAX_HINTS_DAILY = 0
