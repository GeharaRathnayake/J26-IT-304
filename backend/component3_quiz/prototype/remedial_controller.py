
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from graph_helper import expand_weak_concepts
from knowledge_graph import get_module
from qwen_generator import generate_questions


BASE_DIR = Path(__file__).parent
REMEDIAL_PASS_COUNT = 28
REMEDIAL_QUESTION_COUNT = 30
SETS_PER_MODULE = 10
MODULE_COUNT = 10


def run_remedial_round(conn, learner_id, module_no, set_no, weak_tags):
    """
    Generate and run 30-question remedial rounds until the learner
    scores at least 28/30, or question generation fails.

    Uses the existing learner_data.db connection.
    """

    module = get_module(module_no)
    if not module:
        print(f"Module {module_no} was not found.")
        return False

    valid_concepts = set(module.get("concepts", []))
    current_weak = list(dict.fromkeys(
        tag for tag in weak_tags
        if isinstance(tag, str)
        and tag in valid_concepts
    ))

    if not current_weak:
        print("No valid weak concept tags were supplied.")
        print("Remedial round cannot start.")
        return False

    while True:
        related_concepts = expand_weak_concepts(
            module_no=module_no,
            weak_tags=current_weak,
            max_related=2,
        )

        next_round = conn.execute(
            """
            SELECT COALESCE(MAX(round_no), 0) + 1
            FROM remedial_rounds
            WHERE learner_id = ? AND module_no = ? AND set_no = ?
            """,
            (learner_id, module_no, set_no),
        ).fetchone()[0]

        cursor = conn.execute(
            """
            INSERT INTO remedial_rounds
                (learner_id, module_no, set_no, round_no,
                 weak_concepts_json, total_questions, status)
            VALUES (?, ?, ?, ?, ?, ?, 'generating')
            """,
            (
                learner_id,
                module_no,
                set_no,
                next_round,
                json.dumps(related_concepts),
                REMEDIAL_QUESTION_COUNT,
            ),
        )
        round_id = cursor.lastrowid
        conn.commit()

        print(f"\n=== Remedial Round {next_round} ===")
        print("Target concepts:", ", ".join(related_concepts))
        print("Generating 30 new Java questions using local Qwen...")

        try:
            questions = generate_questions(
                module_name=module["module_name"],
                weak_concepts=related_concepts,
                count=REMEDIAL_QUESTION_COUNT,
                module_no=module_no,
            )
        except Exception as exc:
            conn.execute(
                """
                UPDATE remedial_rounds
                SET status = 'generation_failed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE round_id = ?
                """,
                (round_id,),
            )
            conn.commit()
            print("Question generation failed:", exc)
            print("No incomplete round will be scored.")
            return False

        # Never start a round with fewer than the required 30 questions.
        if len(questions) != REMEDIAL_QUESTION_COUNT:
            conn.execute(
                """
                UPDATE remedial_rounds
                SET questions_json = ?, status = 'generation_failed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE round_id = ?
                """,
                (json.dumps(questions), round_id),
            )
            conn.commit()
            print(
                f"Only {len(questions)} of "
                f"{REMEDIAL_QUESTION_COUNT} questions were generated."
            )
            print("This incomplete round will not be scored.")
            return False

        # Validate the complete batch before asking the learner anything.
        valid_batch = True
        prepared = []

        for number, question in enumerate(questions, start=1):
            options = question.get("options", {})
            answer = str(question.get("answer", "")).upper()

            if (
                not isinstance(question, dict)
                or not isinstance(question.get("stem"), str)
                or not question["stem"].strip()
                or not isinstance(options, dict)
                or set(options.keys()) != {"A", "B", "C", "D"}
                or answer not in {"A", "B", "C", "D"}
                or not isinstance(question.get("explanation"), str)
                or not question["explanation"].strip()
                or question.get("concept_tag") not in related_concepts
            ):
                valid_batch = False
                break

            item = dict(question)
            item["module_no"] = module_no
            item["set_no"] = set_no
            item["question_id"] = f"remedial_{round_id}_q{number}"
            prepared.append(item)

        if not valid_batch:
            conn.execute(
                """
                UPDATE remedial_rounds
                SET questions_json = ?, status = 'generation_failed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE round_id = ?
                """,
                (json.dumps(questions), round_id),
            )
            conn.commit()
            print("The generated batch failed structural validation.")
            print("No questions from this batch were scored.")
            return False

        conn.execute(
            """
            UPDATE remedial_rounds
            SET questions_json = ?, status = 'in_progress'
            WHERE round_id = ?
            """,
            (json.dumps(prepared), round_id),
        )
        conn.commit()

        score = 0
        wrong_tags = []

        for number, question in enumerate(prepared, start=1):
            print(f"\nQuestion {number}/{REMEDIAL_QUESTION_COUNT}")
            print(question["stem"])

            for letter in "ABCD":
                print(f"{letter}. {question['options'][letter]}")

            while True:
                answer = input("Your answer (A/B/C/D): ").strip().upper()
                if answer in {"A", "B", "C", "D"}:
                    break
                print("Please enter A, B, C, or D.")

            correct = answer == question["answer"].upper()
            if correct:
                print("Correct!")
                score += 1
            else:
                print(
                    "Incorrect. Correct answer:",
                    question["answer"],
                )
                wrong_tags.append(question["concept_tag"])

            print("Explanation:", question["explanation"])

            conn.execute(
                """
                INSERT INTO attempts
                    (learner_id, question_id, concept_tag,
                     selected_answer, is_correct, set_type,
                     module_no, set_no, round_id)
                VALUES (?, ?, ?, ?, ?, 'remedial', ?, ?, ?)
                """,
                (
                    learner_id,
                    question["question_id"],
                    question["concept_tag"],
                    answer,
                    int(correct),
                    module_no,
                    set_no,
                    round_id,
                ),
            )

            conn.execute(
                """
                INSERT OR IGNORE INTO question_history
                    (learner_id, question_id)
                VALUES (?, ?)
                """,
                (learner_id, question["question_id"]),
            )
            conn.commit()

        percentage = score / REMEDIAL_QUESTION_COUNT
        passed = score >= REMEDIAL_PASS_COUNT

        conn.execute(
            """
            UPDATE remedial_rounds
            SET correct_count = ?, score = ?,
                status = ?, completed_at = CURRENT_TIMESTAMP
            WHERE round_id = ?
            """,
            (
                score,
                percentage,
                "passed" if passed else "failed",
                round_id,
            ),
        )
        conn.commit()

        print(
            f"\nRemedial score: {score}/"
            f"{REMEDIAL_QUESTION_COUNT} ({percentage:.1%})"
        )

        # Passing requires at least 28 correct answers out of 30.
        if passed:
            conn.execute(
                """
                UPDATE set_progress
                SET status = 'passed'
                WHERE learner_id = ? AND module_no = ? AND set_no = ?
                """,
                (learner_id, module_no, set_no),
            )

            # Unlock the next fixed set, or the next module.
            if set_no < SETS_PER_MODULE:
                next_module, next_set = module_no, set_no + 1
            elif module_no < MODULE_COUNT:
                next_module, next_set = module_no + 1, 1
            else:
                next_module, next_set = None, None

            if next_module is not None:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO set_progress
                        (learner_id, module_no, set_no, status, best_score)
                    VALUES (?, ?, ?, 'open', NULL)
                    """,
                    (learner_id, next_module, next_set),
                )
                print(
                    f"Unlocked Module {next_module}, Set {next_set}."
                )
            else:
                print("You completed every module!")

            conn.commit()
            print("Mastery requirement achieved!")
            return True

        print("Mastery requirement not achieved.")
        print("Preparing another remedial round using missed concepts.")

        # Target the concepts missed in this round.
        current_weak = list(dict.fromkeys(
            tag for tag in wrong_tags
            if tag in valid_concepts
        ))

        if not current_weak:
            current_weak = related_concepts
