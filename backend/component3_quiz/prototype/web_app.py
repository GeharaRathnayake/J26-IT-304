import json
import secrets
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE = Path(__file__).resolve().parent
FRONTEND = BASE.parents[2] / "frontend" / "public"
sys.path.insert(0, str(BASE))

from adaptive_engine import (
    choose_questions, normalize_answer, load_normalized_bank,
)
from learner_store import (
    initialize_database, create_learner, record_attempt,
    get_module_statistics, get_concept_statistics,
    get_weak_concepts, get_unassessed_concepts,
    get_connection, get_set_progress, save_set_progress,
    start_remedial_round, finish_remedial_round,
)
from knowledge_graph import MODULES, get_module, get_concepts
from mastery_controller import evaluate_module

SESSIONS = {}
PASS_COUNT = 9


def public_question(q, index):
    options = q.get("options", {})
    if isinstance(options, list):
        options = {
            chr(65 + i): value
            for i, value in enumerate(options[:4])
        }
    return {
        "id": str(q.get("id", f"q{index}")),
        "stem": q.get("stem", q.get("question", "")),
        "options": {
            key: options.get(key, "")
            for key in ("A", "B", "C", "D")
        },
        "concept": q.get("concept_tag", "General"),
    }


def send_json(handler, data, status=200):
    payload = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(payload)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[web]", fmt % args)

    def do_OPTIONS(self):
        send_json(self, {"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            path = FRONTEND / "index.html"
            if not path.is_file():
                send_json(self, {"error": f"Frontend file not found: {path}"}, 404)
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        params = parse_qs(parsed.query)

        try:
            if parsed.path == "/api/modules":
                send_json(self, {"modules": MODULES})
                return

            if parsed.path == "/api/sets":
                learner = params.get("learner_id", [""])[0].strip()
                module_no = int(params.get("module_no", ["1"])[0])

                if not learner or get_module(module_no) is None:
                    send_json(self, {
                        "error": "Enter a learner ID and valid module."
                    }, 400)
                    return

                initialize_database()
                create_learner(learner)

                sets = []
                previous_passed = True

                for set_no in range(1, 11):
                    saved = get_set_progress(learner, module_no, set_no)
                    saved_status = saved["status"] if saved else None

                    if saved_status == "passed":
                        status = "passed"
                    elif saved_status == "remedial_required":
                        status = "remedial_required"
                    elif previous_passed:
                        status = "open"
                    else:
                        status = "locked"

                    sets.append({
                        "set_no": set_no,
                        "status": status,
                        "best_score": saved.get("best_score") if saved else None,
                    })

                    previous_passed = status == "passed"

                send_json(self, {
                    "learner_id": learner,
                    "module_no": module_no,
                    "sets": sets,
                })
                return

            if parsed.path == "/api/remedial":
                learner = params.get("learner_id", [""])[0].strip()
                module_no = int(params.get("module_no", ["1"])[0])
                set_no = int(params.get("set_no", ["1"])[0])

                if not learner:
                    send_json(self, {"error": "Please enter a learner ID."}, 400)
                    return

                module = get_module(module_no)
                if module is None or not 1 <= set_no <= 10:
                    send_json(self, {"error": "Invalid module or set number."}, 400)
                    return

                initialize_database()
                create_learner(learner)

                for previous_no in range(1, set_no):
                    previous = get_set_progress(learner, module_no, previous_no)
                    if not previous or previous.get("status") != "passed":
                        send_json(self, {
                            "error": f"Set {set_no} is locked. Pass Set {previous_no} first."
                        }, 409)
                        return

                current = get_set_progress(learner, module_no, set_no)
                if not current or current.get("status") != "remedial_required":
                    send_json(self, {
                        "error": "This set does not currently require remedial practice."
                    }, 409)
                    return

                # Identify weak concepts and question IDs already attempted
                # in the initial assessment and earlier remedial rounds.
                with get_connection() as conn:
                    rows = conn.execute(
                        """SELECT question_id, concept, is_correct
                           FROM attempts
                           WHERE learner_id = ? AND module_no = ?
                             AND set_no = ?""",
                        (learner, module_no, set_no),
                    ).fetchall()

                weak_concepts = list(dict.fromkeys(
                    str(row["concept"] or "General")
                    for row in rows
                    if row["is_correct"] in (0, False)
                ))
                excluded_ids = {str(row["question_id"]) for row in rows
                                if row["question_id"] is not None}

                bank = load_normalized_bank()
                module_questions = [
                    q for q in bank
                    if int(q.get("module_no", -1)) == module_no
                    and str(q.get("id")) not in excluded_ids
                ]

                # Prefer questions on weak concepts, then fill from other
                # unused questions in the same module if necessary.
                weak_pool = [
                    q for q in module_questions
                    if q.get("concept_tag", "General") in weak_concepts
                ]
                other_pool = [
                    q for q in module_questions
                    if q.get("concept_tag", "General") not in weak_concepts
                ]

                import random
                random.shuffle(weak_pool)
                random.shuffle(other_pool)
                questions = (weak_pool + other_pool)[:30]

                if len(questions) != 30:
                    send_json(self, {
                        "error": (
                            "Not enough unused questions for a 30-question remedial test. "
                            f"Found {len(questions)}."
                        )
                    }, 500)
                    return

                round_info = start_remedial_round(
                    learner_id=learner,
                    module_no=module_no,
                    set_no=set_no,
                    weak_concepts=weak_concepts,
                    questions=questions,
                )

                token = secrets.token_urlsafe(24)
                SESSIONS[token] = {
                    "learner": learner,
                    "module_no": module_no,
                    "module_name": module["module_name"],
                    "questions": questions,
                    "mode": "remedial",
                    "set_no": set_no,
                    "set_type": "remedial",
                    "round_id": round_info["round_id"],
                }

                send_json(self, {
                    "session_id": token,
                    "learner_id": learner,
                    "module_no": module_no,
                    "module_name": module["module_name"],
                    "set_no": set_no,
                    "mode": f"Remedial assessment - Set {set_no}",
                    "round_no": round_info["round_no"],
                    "total": 30,
                    "weak_concepts": weak_concepts,
                    "questions": [
                        public_question(q, i)
                        for i, q in enumerate(questions, 1)
                    ],
                })
                return

            if parsed.path == "/api/progress":
                learner = params.get("learner_id", [""])[0].strip()
                module_no = int(params.get("module_no", ["1"])[0])
                if not learner or get_module(module_no) is None:
                    send_json(self, {"error": "Enter a learner ID and valid module."}, 400)
                    return
                initialize_database()
                create_learner(learner)
                stats = get_module_statistics(learner, module_no)
                concepts = get_concept_statistics(learner, module_no)
                decision = evaluate_module(learner, module_no)
                send_json(self, {
                    "learner_id": learner,
                    "module_no": module_no,
                    "module_name": get_module(module_no)["module_name"],
                    "attempts": stats["attempts"],
                    "accuracy": stats["accuracy"],
                    "mastered": stats["mastered"],
                    "concepts": concepts,
                    "decision": decision["decision"],
                    "recommendation": decision["reason"],
                })
                return

            if parsed.path == "/api/quiz":
                learner = params.get("learner_id", [""])[0].strip()
                module_no = int(params.get("module_no", ["1"])[0])
                set_no = int(params.get("set_no", ["1"])[0])

                if not learner:
                    send_json(self, {"error": "Please enter a learner ID."}, 400)
                    return

                module = get_module(module_no)
                if module is None:
                    send_json(self, {"error": "Invalid module number."}, 400)
                    return

                if not 1 <= set_no <= 10:
                    send_json(self, {"error": "Set number must be between 1 and 10."}, 400)
                    return

                initialize_database()
                create_learner(learner)

                # Preserve the existing knowledge-graph prerequisite checks.
                for prerequisite_no in __import__(
                    "knowledge_graph"
                ).get_prerequisite_modules(module_no):
                    result = evaluate_module(learner, prerequisite_no)
                    if not result["mastered"]:
                        prerequisite = get_module(prerequisite_no)
                        name = prerequisite["module_name"] if prerequisite else str(prerequisite_no)
                        send_json(self, {
                            "error": f"Complete prerequisite module {name} before this module."
                        }, 409)
                        return

                # Every earlier set must be passed before this set can open.
                for previous_no in range(1, set_no):
                    previous = get_set_progress(learner, module_no, previous_no)
                    if not previous or previous.get("status") != "passed":
                        send_json(self, {
                            "error": f"Set {set_no} is locked. Pass Set {previous_no} first."
                        }, 409)
                        return

                current = get_set_progress(learner, module_no, set_no)
                current_status = current.get("status") if current else None

                if current_status == "passed":
                    send_json(self, {
                        "error": f"Set {set_no} has already been passed."
                    }, 409)
                    return

                if current_status == "remedial_required":
                    send_json(self, {
                        "error": f"Set {set_no} requires a remedial test before you can continue."
                    }, 409)
                    return

                # Read concepts from this exact set in the normalized question bank.
                bank = load_normalized_bank()
                set_questions = [
                    q for q in bank
                    if int(q.get("module_no", -1)) == module_no
                    and int(q.get("set_no", -1)) == set_no
                ]
                if len(set_questions) != 10:
                    send_json(self, {
                        "error": f"Set {set_no} must contain exactly 10 valid questions; found {len(set_questions)}."
                    }, 500)
                    return

                concepts = list(dict.fromkeys(
                    q.get("concept_tag", "General") for q in set_questions
                ))

                # Use the exact 10 prevalidated questions assigned to this set.
                # Remedial practice uses its own adaptive selection route.
                questions = list(set_questions)

                if len(questions) != 10:
                    send_json(self, {
                        "error": f"Could not load 10 questions for Set {set_no}."
                    }, 500)
                    return

                token = secrets.token_urlsafe(24)
                SESSIONS[token] = {
                    "learner": learner,
                    "module_no": module_no,
                    "module_name": module["module_name"],
                    "questions": questions,
                    "mode": "initial",
                    "set_no": set_no,
                    "set_type": "initial",
                    "round_id": None,
                }

                send_json(self, {
                    "session_id": token,
                    "learner_id": learner,
                    "module_no": module_no,
                    "module_name": module["module_name"],
                    "set_no": set_no,
                    "mode": f"Initial assessment - Set {set_no}",
                    "total": len(questions),
                    "questions": [
                        public_question(q, i)
                        for i, q in enumerate(questions, 1)
                    ],
                })
                return

            send_json(self, {"error": "Endpoint not found."}, 404)

        except Exception as exc:
            print("[API ERROR]", repr(exc))
            send_json(self, {"error": str(exc)}, 500)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/answer", "/api/submit"):
            send_json(self, {"error": "Endpoint not found."}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                send_json(self, {"error": "Request too large."}, 413)
                return

            data = json.loads(self.rfile.read(length).decode("utf-8"))
            token = data.get("session_id", "")
            session = SESSIONS.get(token)

            if not session:
                send_json(self, {"error": "Quiz session expired. Please start another quiz."}, 400)
                return

            questions = session["questions"]

            if path == "/api/answer":
                qid = str(data.get("question_id", ""))
                question = next(
                    (q for q in questions if str(q.get("id", "")) == qid),
                    None,
                )
                if question is None:
                    send_json(self, {"error": "Question not found in this quiz."}, 404)
                    return

                # A question can be answered only once in a quiz session.
                if qid in session.setdefault("answered", {}):
                    send_json(self, {"error": "This question has already been answered."}, 409)
                    return

                selected = normalize_answer(data.get("answer", ""))
                if selected not in ("A", "B", "C", "D"):
                    send_json(self, {"error": "Please select an answer first."}, 400)
                    return

                correct_answer = normalize_answer(question.get("answer", ""))
                is_correct = selected == correct_answer
                learner = session["learner"]
                module_no = session["module_no"]

                record_attempt(
                    learner_id=learner,
                    module_no=module_no,
                    module_name=session["module_name"],
                    concept=question.get("concept_tag", "General"),
                    is_correct=is_correct,
                    question_id=qid,
                    set_no=session.get("set_no"),
                    set_type=session.get("set_type", "initial"),
                    round_id=session.get("round_id"),
                )

                result = {
                    "question_id": qid,
                    "stem": question.get("stem", question.get("question", "")),
                    "concept": question.get("concept_tag", "General"),
                    "selected": selected,
                    "correct_answer": correct_answer,
                    "correct": is_correct,
                    "explanation": question.get(
                        "explanation",
                        "Review this concept before trying again.",
                    ),
                }
                session["answered"][qid] = result
                session.setdefault("results", []).append(result)

                send_json(self, {
                    "correct": is_correct,
                    "selected": selected,
                    "correct_answer": correct_answer,
                    "explanation": result["explanation"],
                    "answered": len(session["results"]),
                    "total": len(questions),
                })
                return

            # Finalize only after all questions have been answered.
            results = session.get("results", [])
            if len(results) != len(questions):
                send_json(self, {
                    "error": "Please answer every question before finishing the quiz."
                }, 400)
                return

            learner = session["learner"]
            module_no = session["module_no"]
            set_no = session.get("set_no", 1)
            set_type = session.get("set_type", "initial")
            round_id = session.get("round_id")
            correct_count = sum(1 for result in results if result["correct"])
            total = len(questions)
            score_percent = round(correct_count / total * 100, 1)

            if set_type == "remedial":
                passed = total == 30 and correct_count >= 28
                pass_rule = "At least 28 out of 30 correct"
                if round_id is None:
                    send_json(self, {"error": "Remedial round ID is missing."}, 500)
                    return

                finish_remedial_round(
                    round_id=round_id,
                    correct_count=correct_count,
                    total_questions=total,
                    passed=passed,
                )
                save_set_progress(
                    learner, module_no, set_no,
                    "passed" if passed else "remedial_required",
                    score_percent,
                )
            else:
                passed = total == 10 and correct_count >= 9
                pass_rule = "At least 9 out of 10 correct"
                save_set_progress(
                    learner, module_no, set_no,
                    "passed" if passed else "remedial_required",
                    score_percent,
                )

            stats = get_module_statistics(learner, module_no)
            decision = evaluate_module(learner, module_no)
            weak = list(dict.fromkeys(
                result.get("concept", "General")
                for result in results if not result["correct"]
            ))

            SESSIONS.pop(token, None)

            send_json(self, {
                "score": correct_count,
                "total": total,
                "percentage": score_percent,
                "passed": passed,
                "pass_rule": pass_rule,
                "set_no": set_no,
                "set_type": set_type,
                "remedial_required": set_type == "initial" and not passed
                    or set_type == "remedial" and not passed,
                "results": results,
                "weak_concepts": weak,
                "module_accuracy": stats["accuracy"],
                "module_mastered": stats["mastered"],
                "decision": decision["decision"],
                "recommendation": (
                    f"Set {set_no} passed. You may continue to the next set."
                    if passed else
                    f"Set {set_no} remains locked until you pass the required assessment."
                ),
            })

        except Exception as exc:
            print("[API ERROR]", repr(exc))
            send_json(self, {"error": str(exc)}, 500)


if __name__ == "__main__":
    initialize_database()
    print("=" * 54)
    print("ADAPTIVE JAVA QUIZ WEB SERVER")
    print("Open http://127.0.0.1:8000")
    print("Press Ctrl+C to stop.")
    print("=" * 54)
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
