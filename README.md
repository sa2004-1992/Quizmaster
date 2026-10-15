# 🧠 Quiz Master

A full-stack quiz website built with **Flask + SQLite + HTML/CSS/JavaScript**. It has session login with hashed passwords, a REST API, three separate quiz types, per-user progress, history, a leaderboard, a profile with a daily streak, and dark mode.

## Screenshots

| Quizzes | Quiz playing | Daily quiz |
|---|---|---|
| ![Quizzes](screenshots/quizzes.png) | ![Playing](screenshots/quiz-playing.png) | ![Daily](screenshots/daily-quiz.png) |

| History | Leaderboard | Profile | All Quiz |
|---|---|---|---|
| ![History](screenshots/history.png) | ![Leaderboard](screenshots/leaderboard.png) | ![Profile](screenshots/profile.png) | ![All Quiz](screenshots/all-quiz.png) |

## Quiz types (kept completely separate)

| Type | Where | Dataset | Length |
|---|---|---|---|
| Normal Quiz 1 | Quizzes page (56 categories) | `app/data_source/categories/*.csv.gz` | Unlimited |
| Normal Quiz 2 ("Play All Quiz") | Home page | `normal_quiz_2_part1.csv.gz` + `part2.csv.gz` | Unlimited |
| Daily Quiz | Home → Start Daily Challenge | `daily_quiz.csv.gz` | 50/day, once per day, no hints |

| Page | Shows data from |
|---|---|
| Profile | Normal Quiz 1 only, plus the Daily streak card (current / longest) |
| All Quiz | Normal Quiz 2 only |
| History | All 3 quiz types, for the logged-in user |
| Leaderboard | All 3 quiz types, all users (All Time / Month / Week / Today) |

## Game rules
- Nothing is revealed before you answer. Click an option and you instantly see right/wrong, the correct option and the explanation.
- Scoring: correct **+10**, wrong **−5** (the score never goes below 0). Hints (max 5 in Normal quizzes, none in Daily) reveal the answer and don't change the score.
- Questions are served in order from a per-user pointer, so you continue where you stopped (wrapping around at the end of the dataset).
- A game is saved only when you press **Finish & Save**. **Exit** discards it.
- Daily streak: playing on consecutive days increases it; missing a day resets it.
- **Profile → Clear All Data** wipes only your own history, progress, streaks and scores. Your account stays and other users are unaffected.

## Run locally
```bash
pip install -r requirements.txt
python run.py          # http://127.0.0.1:5000
```
On the first run the datasets (about 712,000 questions) are imported into SQLite, which takes roughly 10–20 seconds. The database file is created at `instance/quizmaster.db`. **The `.db` file is generated automatically and is never committed to GitHub** (see `.gitignore`).

## Deploy on Render
1. Push the project to GitHub (without `instance/` or any `.db`).
2. New → Web Service → connect the repo. Build command: `pip install -r requirements.txt`. Start command: `gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120` (also in `Procfile`).
3. Environment variables: `QUIZMASTER_SECRET_KEY` = a long random string; `QUIZMASTER_DATABASE_PATH` = `/var/data/quizmaster.db`.
4. Add a **Disk** mounted at `/var/data`. Without a persistent disk, Render's free tier wipes accounts and history on every restart.

## Project structure
```
run.py  Procfile  requirements.txt  README.md  .gitignore
screenshots/            README images
app/
  __init__.py           app factory, auto-import on first run
  config.py             settings (env vars, scoring constants)
  db.py  schema.sql     SQLite connection + tables
  import_data.py        gzip CSV importer (supports _partN files)
  categories_meta.py    the 56 categories in order
  quiz_engine.py        start / answer / hint / finish logic
  stats.py              profile, streak and leaderboard queries
  auth.py  routes.py  api.py
  data_source/          gzip datasets (GitHub-safe)
  templates/  static/
```

## Notes
- Passwords are hashed with Werkzeug. Sessions use a signed cookie. Set `QUIZMASTER_SECRET_KEY` in production.
- The data layer uses Python's built-in `sqlite3` with raw SQL. To use MySQL, replace `db.py` / `schema.sql` with a MySQL driver and equivalent tables.
- Files are read with explicit UTF-8, so it also runs on Windows.
