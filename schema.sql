DROP TABLE IF EXISTS tasks;

CREATE TABLE tasks (
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