import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "learner_data.db"

with sqlite3.connect(db_path) as conn:
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS learners (
            learner_id TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            concept_tag TEXT,
            selected_answer TEXT,
            is_correct INTEGER NOT NULL,
            set_type TEXT NOT NULL,
            module_no INTEGER,
            set_no INTEGER,
            attempted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (learner_id) REFERENCES learners(learner_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS concept_mastery (
            learner_id TEXT NOT NULL,
            concept_tag TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            mastery_score REAL DEFAULT 0,
            PRIMARY KEY (learner_id, concept_tag),
            FOREIGN KEY (learner_id) REFERENCES learners(learner_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS question_history (
            learner_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (learner_id, question_id),
            FOREIGN KEY (learner_id) REFERENCES learners(learner_id)
        )
    """)

    print("Database initialized successfully.")
    print("Tables:", [
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ])

print("Database file:", db_path)
