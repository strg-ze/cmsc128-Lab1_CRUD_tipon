DROP TABLE IF EXISTS tasks;

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    priority TEXT,
    due_date TEXT,
    time TEXT,
    tags TEXT,
    category TEXT,
    completed INTEGER DEFAULT 0,
    is_visible INTEGER DEFAULT 1
)

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,    
    password_hash TEXT NOT NULL
);