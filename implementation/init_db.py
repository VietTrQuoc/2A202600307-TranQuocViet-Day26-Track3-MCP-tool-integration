from __future__ import annotations

import sqlite3
from pathlib import Path

try:
    from .db import DEFAULT_DB_PATH
except ImportError:  # pragma: no cover - used when run as a script from this directory.
    from db import DEFAULT_DB_PATH


SCHEMA_SQL = """
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    cohort TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age >= 16),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0)
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'dropped')),
    enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE (student_id, course_id)
);
"""


SEED_SQL = """
INSERT INTO students (name, email, cohort, age) VALUES
    ('An Nguyen', 'an.nguyen@example.edu', 'A1', 20),
    ('Binh Tran', 'binh.tran@example.edu', 'A1', 21),
    ('Chi Pham', 'chi.pham@example.edu', 'B2', 19),
    ('Dung Le', 'dung.le@example.edu', 'B2', 22),
    ('Hoa Vo', 'hoa.vo@example.edu', 'C3', 20);

INSERT INTO courses (code, title, credits) VALUES
    ('MCP101', 'Model Context Protocol Fundamentals', 3),
    ('DB201', 'SQLite for Applications', 4),
    ('AI301', 'Applied AI Integration', 3);

INSERT INTO enrollments (student_id, course_id, score, status) VALUES
    (1, 1, 91.5, 'completed'),
    (1, 2, 86.0, 'active'),
    (2, 1, 78.0, 'completed'),
    (2, 3, 83.5, 'active'),
    (3, 1, 94.0, 'completed'),
    (3, 2, 88.0, 'completed'),
    (4, 2, 72.5, 'active'),
    (5, 3, 90.0, 'completed');
"""


def create_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    """Create a reproducible SQLite database and return its path."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()
    return path


if __name__ == "__main__":
    created_path = create_database()
    print(f"Created SQLite lab database at {created_path}")
