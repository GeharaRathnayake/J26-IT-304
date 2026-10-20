import json
import sqlite3
from collections import Counter
from pathlib import Path

BASE = Path(__file__).parent
QUESTION_FILE = BASE / "static_questions.json"
DB_FILE = BASE / "learner_data.db"

INITIAL_QUESTION_COUNT = 10
INITIAL_PASS_COUNT = 9
SETS_PER_MODULE = 10
MODULES = 10

def passed(score):
    return score >= INITIAL_PASS_COUNT

def init_progress(conn, learner):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS set_progress ("
        "learner_id TEXT NOT NULL, module_no INTEGER NOT NULL, set_no INTEGER NOT NULL, "
        "status TEXT NOT NULL, best_score REAL, "
        "PRIMARY KEY (learner_id, module_no, set_no))"
    )
    conn.execute("INSERT OR IGNORE INTO learners (learner_id) VALUES (?)", (learner,))
    has_rows = conn.execute(
        "SELECT COUNT(*) FROM set_progress WHERE learner_id=?", (learner,)
    ).fetchone()[0]
    if not has_rows:
        conn.execute(
            "INSERT INTO set_progress VALUES (?,?,?,?,NULL)", (learner, 1, 1, "open")
        )

def unlock(conn, learner, m, s):
    conn.execute(
        "INSERT OR IGNORE INTO set_progress VALUES (?,?,?,?,NULL)", (learner, m, s, "open")
    )

def record_score(conn, learner, m, s, pct, status):
    conn.execute(
        "UPDATE set_progress SET status=?, best_score=MAX(COALESCE(best_score,0), ?) "
        "WHERE learner_id=? AND module_no=? AND set_no=?",
        (status, pct, learner, m, s),
    )

def next_open(conn, learner):
    return conn.execute(
        "SELECT module_no, set_no FROM set_progress WHERE learner_id=? AND status='open' "
        "ORDER BY module_no, set_no LIMIT 1", (learner,)
    ).fetchone()

def show_status(conn, learner):
    print("\nQuiz page")
    for m in range(1, MODULES + 1):
        rows = conn.execute(
            "SELECT status, COUNT(*) FROM set_progress WHERE learner_id=? AND module_no=? "
            "GROUP BY status", (learner, m)
        ).fetchall()
        if not rows:
            print(f"  Module {m}: LOCKED")
        else:
            done = dict(rows).get("passed", 0)
            print(f"  Module {m}: open - {done}/{SETS_PER_MODULE} sets passed")

def save_answer(conn, learner, q, qid, answer, correct):
    tag = q.get("concept_tag", "unknown")
    conn.execute(
        "INSERT INTO attempts (learner_id, question_id, concept_tag, selected_answer, "
        "is_correct, set_type, module_no, set_no) VALUES (?,?,?,?,?,?,?,?)",
        (learner, qid, tag, answer, int(correct), "static", q["module_no"], q["set_no"]),
    )
    conn.execute(
        "INSERT OR IGNORE INTO question_history (learner_id, question_id) VALUES (?,?)",
        (learner, qid),
    )
    conn.execute(
        "INSERT INTO concept_mastery (learner_id, concept_tag, attempts, correct_count, mastery_score) "
        "VALUES (?,?,1,?,?) "
        "ON CONFLICT(learner_id, concept_tag) DO UPDATE SET "
        "mastery_score = (correct_count + ?) * 1.0 / (attempts + 1), "
        "attempts = attempts + 1, "
        "correct_count = correct_count + ?",
        (learner, tag, int(correct), float(correct), int(correct), int(correct)),
    )

def get_qid(q, index):
    return str(q.get("question_id") or q.get("id") or f"m{q['module_no']}s{q['set_no']}q{index}")

def main():
    with QUESTION_FILE.open("r", encoding="utf-8") as f:
        questions = json.load(f)

    learner = input("Learner ID (press Enter for 'learner1'): ").strip() or "learner1"
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    init_progress(conn, learner)
    conn.commit()

    show_status(conn, learner)
    current = next_open(conn, learner)
    if not current:
        print("\nAll modules completed. Well done!")
        return
    m, s = current
    selected = [q for q in questions if q["module_no"] == m and q["set_no"] == s]
    if len(selected) != INITIAL_QUESTION_COUNT:
        print(
            f"Expected {INITIAL_QUESTION_COUNT} questions for "
            f"Module {m}, Set {s}; found {len(selected)}. "
            "Cannot start an invalid quiz set."
        )
        conn.close()
        return

    print(f"\n=== Module {m}, Set {s} ===")
    score = 0
    wrong_tags = []

    for number, q in enumerate(selected, start=1):
        print(f"\nQuestion {number}/{len(selected)}")
        print(q["stem"])
        for letter, option in q["options"].items():
            print(f"{letter}. {option}")

        while True:
            answer = input("Your answer (A/B/C/D): ").strip().upper()
            if answer in q["options"]:
                break
            print("Please enter A, B, C, or D.")

        correct = answer == q["answer"].upper()
        if correct:
            print("Correct!")
            score += 1
        else:
            print(f"Incorrect. Correct answer: {q['answer']}")
            wrong_tags.append(q.get("concept_tag", "unknown"))
        print("Explanation:", q["explanation"])

        save_answer(conn, learner, q, get_qid(q, number), answer, correct)
        conn.commit()

    pct = score / len(selected)
    print(f"\nFinal score: {score}/{len(selected)} ({pct:.0%})")

    if passed(score):
        record_score(conn, learner, m, s, pct, "passed")
        print("PASS!")
        if s < SETS_PER_MODULE:
            unlock(conn, learner, m, s + 1)
            print(f"Module {m}, Set {s + 1} unlocked.")
        elif m < MODULES:
            unlock(conn, learner, m + 1, 1)
            print(f"Module {m} complete! Module {m + 1} unlocked.")
        else:
            print("You completed every module!")
    else:
        record_score(conn, learner, m, s, pct, "open")
        print("NOT YET: remedial round required.")
        print("Weak concepts from this set:")

        for tag, n in Counter(wrong_tags).most_common():
            print(f"  {tag}: {n} wrong")

        if wrong_tags:
            from remedial_controller import run_remedial_round

            weak_tags = [
                tag for tag, _ in Counter(wrong_tags).most_common()
            ]

            run_remedial_round(
                conn,
                learner_id=learner,
                module_no=m,
                set_no=s,
                weak_tags=weak_tags,
            )
        else:
            print("No weak concept tags were found.")

    conn.commit()
    show_status(conn, learner)
    conn.close()

if __name__ == "__main__":
    main()
