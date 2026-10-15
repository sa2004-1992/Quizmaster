CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    gender TEXT,
    location TEXT DEFAULT 'India',
    dark_mode INTEGER DEFAULT 0,
    joined_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    icon TEXT,
    position INTEGER,
    total INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS questions_nq1 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    seq INTEGER NOT NULL,
    question TEXT, a TEXT, b TEXT, c TEXT, d TEXT,
    correct TEXT, explanation TEXT, subcategory TEXT
);
CREATE INDEX IF NOT EXISTS idx_nq1 ON questions_nq1(category_id, seq);
CREATE TABLE IF NOT EXISTS questions_nq2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seq INTEGER NOT NULL,
    question TEXT, a TEXT, b TEXT, c TEXT, d TEXT,
    correct TEXT, explanation TEXT, category TEXT, subcategory TEXT
);
CREATE INDEX IF NOT EXISTS idx_nq2 ON questions_nq2(seq);
CREATE TABLE IF NOT EXISTS questions_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seq INTEGER NOT NULL,
    question TEXT, a TEXT, b TEXT, c TEXT, d TEXT,
    correct TEXT, explanation TEXT, category TEXT, subcategory TEXT
);
CREATE INDEX IF NOT EXISTS idx_daily ON questions_daily(seq);
CREATE TABLE IF NOT EXISTS category_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    next_seq INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, category_id)
);
CREATE TABLE IF NOT EXISTS nq2_progress (
    user_id INTEGER PRIMARY KEY,
    next_seq INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS daily_progress (
    user_id INTEGER PRIMARY KEY,
    next_seq INTEGER NOT NULL DEFAULT 0,
    last_play_date TEXT,
    answered_today INTEGER NOT NULL DEFAULT 0,
    current_streak INTEGER NOT NULL DEFAULT 0,
    longest_streak INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS active_quiz (
    user_id INTEGER PRIMARY KEY,
    state_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS game_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    quiz_type TEXT NOT NULL,
    category_name TEXT,
    game_no INTEGER,
    played_at TEXT NOT NULL,
    questions_played INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    wrong INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    time_seconds INTEGER DEFAULT 0,
    hints_used INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_hist ON game_history(user_id, played_at);
