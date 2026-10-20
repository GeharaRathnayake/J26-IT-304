
"""learner_store.py
SQLite persistence for the mastery-based adaptive Java quiz system.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "learner_profiles.db"

MASTERY_THRESHOLD = 0.80
MIN_ATTEMPTS_FOR_MASTERY = 5


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create the learner profile and attempt-history tables."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS learners (
                learner_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                learner_id TEXT NOT NULL,
                module_no INTEGER NOT NULL,
                module_name TEXT NOT NULL,
                concept TEXT NOT NULL,
                question_id TEXT,
                is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
                attempted_at TEXT NOT NULL,
                FOREIGN KEY (learner_id)
                    REFERENCES learners(learner_id)
            );

            CREATE INDEX IF NOT EXISTS idx_attempts_learner_module
            ON attempts (learner_id, module_no);

            CREATE INDEX IF NOT EXISTS idx_attempts_learner_concept
            ON attempts (learner_id, concept);
        """)


def create_learner(learner_id):
    """Create a learner profile without overwriting an existing profile."""
    learner_id = str(learner_id).strip()

    if not learner_id:
        raise ValueError("Learner ID cannot be empty.")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO learners (learner_id, created_at)
            VALUES (?, ?)
            """,
            (learner_id, datetime.now(timezone.utc).isoformat()),
        )

    return get_learner(learner_id)


def get_learner(learner_id):
    """Return a learner profile, or None if it does not exist."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM learners WHERE learner_id = ?",
            (str(learner_id).strip(),),
        ).fetchone()

    return dict(row) if row else None


def record_attempt(
    learner_id,
    module_no,
    module_name,
    concept,
    is_correct,
    question_id=None,
):
    """Save one answered question to the learner's permanent history."""
    learner_id = str(learner_id).strip()
    concept = str(concept).strip()
    module_name = str(module_name).strip()

    if not learner_id or not concept or not module_name:
        raise ValueError("Learner ID, module name, and concept are required.")

    if int(module_no) < 1:
        raise ValueError("Module number must be at least 1.")

    create_learner(learner_id)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO attempts (
                learner_id, module_no, module_name, concept,
                question_id, is_correct, attempted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                learner_id,
                int(module_no),
                module_name,
                concept,
                str(question_id) if question_id is not None else None,
                int(bool(is_correct)),
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_concept_statistics(learner_id, module_no=None):
    """Return attempt counts and accuracy for each concept."""
    sql = """
        SELECT
            concept,
            COUNT(*) AS attempts,
            SUM(is_correct) AS correct,
            ROUND(AVG(is_correct), 4) AS accuracy
        FROM attempts
        WHERE learner_id = ?
    """
    params = [str(learner_id).strip()]

    if module_no is not None:
        sql += " AND module_no = ?"
        params.append(int(module_no))

    sql += " GROUP BY concept ORDER BY concept"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


def get_module_statistics(learner_id, module_no):
    """Calculate a learner's overall score for one module."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS attempts,
                COALESCE(SUM(is_correct), 0) AS correct,
                ROUND(AVG(is_correct), 4) AS accuracy
            FROM attempts
            WHERE learner_id = ? AND module_no = ?
            """,
            (str(learner_id).strip(), int(module_no)),
        ).fetchone()

    result = dict(row)
    result["accuracy"] = result["accuracy"] or 0.0
    result["mastered"] = (
        result["attempts"] >= MIN_ATTEMPTS_FOR_MASTERY
        and result["accuracy"] >= MASTERY_THRESHOLD
    )
    return result


def get_weak_concepts(learner_id, module_no):
    """Return concepts that need more practice.

    A concept is weak if its observed accuracy is below the mastery
    threshold. Concepts with no recorded attempts are not included;
    those should be treated as unassessed.
    """
    statistics = get_concept_statistics(learner_id, module_no)

    return [
        item["concept"]
        for item in statistics
        if item["accuracy"] < MASTERY_THRESHOLD
    ]


def get_unassessed_concepts(learner_id, module_no, module_concepts):
    """Find module concepts for which the learner has no recorded attempts."""
    assessed = {
        item["concept"]
        for item in get_concept_statistics(learner_id, module_no)
    }

    return [
        concept for concept in module_concepts
        if concept not in assessed
    ]


def get_attempt_history(learner_id, limit=100):
    """Return the most recent attempts for a learner."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT module_no, module_name, concept, question_id,
                   is_correct, attempted_at
            FROM attempts
            WHERE learner_id = ?
            ORDER BY attempt_id DESC
            LIMIT ?
            """,
            (str(learner_id).strip(), max(1, int(limit))),
        ).fetchall()

    return [dict(row) for row in rows]


if __name__ == "__main__":
    initialize_database()
    print(f"Database ready: {DB_PATH}")

    learner = create_learner("test_learner")
    print("Learner profile:", learner)

    # Small persistence test using a separate test learner.
    record_attempt(
        learner_id="test_learner",
        module_no=1,
        module_name="Variables",
        concept="declaration",
        is_correct=True,
        question_id="test_q1",
    )

    print("Saved test attempt.")
    print("Concept statistics:", get_concept_statistics("test_learner"))
    print("Module statistics:", get_module_statistics("test_learner", 1))
