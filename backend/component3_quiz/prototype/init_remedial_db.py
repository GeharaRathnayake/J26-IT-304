import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "learner_data.db"

with sqlite3.connect(DB_FILE) as conn:
    # Create a table to track each remedial round.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS remedial_rounds (
            round_id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            module_no INTEGER NOT NULL,
            set_no INTEGER NOT NULL,
            round_no INTEGER NOT NULL,
            weak_concepts_json TEXT NOT NULL,
            questions_json TEXT,
            correct_count INTEGER,
            total_questions INTEGER NOT NULL DEFAULT 30,
            score REAL,
            status TEXT NOT NULL DEFAULT 'generated',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            UNIQUE (learner_id, module_no, set_no, round_no)
        )
    """)

    # Add a round reference to attempts without changing old records.
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(attempts)")
    }

    if "round_id" not in columns:
        conn.execute(
            "ALTER TABLE attempts ADD COLUMN round_id INTEGER"
        )
        print("Added round_id column to attempts.")
    else:
        print("attempts already has round_id.")

    # Improve lookup speed for remedial rounds.
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_remedial_round_lookup
        ON remedial_rounds (learner_id, module_no, set_no)
    """)

    conn.commit()

# Verify the new structure.
with sqlite3.connect(DB_FILE) as conn:
    print("\nDatabase setup completed.")
    print("\nRemedial-round columns:")

    for column in conn.execute(
        "PRAGMA table_info(remedial_rounds)"
    ):
        print(f"{column[1]} | {column[2]}")

    print("\nAttempts columns:")
    for column in conn.execute("PRAGMA table_info(attempts)"):
        print(f"{column[1]} | {column[2]}")
