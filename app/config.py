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

# Supabase / PostgreSQL. When DATABASE_URL is set, accounts, progress and history
# are stored there. When it is not set, the app uses a local SQLite file instead.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
# The read-only question bank is rebuilt from the gzip CSVs and stays local.
QUESTIONS_PATH = os.environ.get(
    "QUIZMASTER_QUESTIONS_PATH", os.path.join(BASE_DIR, "instance", "questions.db"))
