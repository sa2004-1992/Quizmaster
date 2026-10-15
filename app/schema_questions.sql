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
