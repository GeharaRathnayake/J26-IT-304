import json
import secrets
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE = Path(__file__).resolve().parent
FRONTEND = BASE.parents[2] / "frontend" / "public"
sys.path.insert(0, str(BASE))

from adaptive_engine import choose_questions, normalize_answer
from learner_store import (
    initialize_database, create_learner, record_attempt,
    get_module_statistics, get_concept_statistics,
    get_weak_concepts, get_unassessed_concepts,
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

                if not learner:
                    send_json(self, {"error": "Please enter a learner ID."}, 400)
                    return

                module = get_module(module_no)
                if module is None:
                    send_json(self, {"error": "Invalid module number."}, 400)
                    return

                initialize_database()
                create_learner(learner)

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

                concepts = get_concepts(module_no)
                unassessed = get_unassessed_concepts(learner, module_no, concepts)
                weak = get_weak_concepts(learner, module_no)

                if unassessed:
                    focus = unassessed
                    try_qwen = False
                    mode = "Initial assessment"
                elif weak:
                    focus = weak
                    try_qwen = True
                    mode = "Targeted practice for weak concepts"
                else:
                    focus = concepts
                    try_qwen = False
                    mode = "Module practice"

                questions = choose_questions(
                    learner_id=learner,
                    module_no=module_no,
                    module_name=module["module_name"],
                    concepts=focus,
                    count=10,
                    try_qwen=try_qwen,
                    set_no=1 if unassessed else None,
                )

                if not questions:
                    send_json(self, {"error": "No valid questions were found for this module."}, 500)
                    return

                token = secrets.token_urlsafe(24)
                SESSIONS[token] = {
                    "learner": learner,
                    "module_no": module_no,
                    "module_name": module["module_name"],
                    "questions": questions,
                    "mode": mode,
                }

                send_json(self, {
                    "session_id": token,
                    "learner_id": learner,
                    "module_no": module_no,
                    "module_name": module["module_name"],
                    "mode": mode,
                    "total": len(questions),
                    "questions": [public_question(q, i) for i, q in enumerate(questions, 1)],
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
            correct_count = sum(1 for result in results if result["correct"])
            total = len(questions)
            score_percent = round(correct_count / total * 100, 1)
            passed = correct_count >= PASS_COUNT
            stats = get_module_statistics(learner, module_no)
            decision = evaluate_module(learner, module_no)
            weak = get_weak_concepts(learner, module_no)

            SESSIONS.pop(token, None)

            send_json(self, {
                "score": correct_count,
                "total": total,
                "percentage": score_percent,
                "passed": passed,
                "pass_rule": "9 out of 10 correct",
                "results": results,
                "weak_concepts": weak,
                "module_accuracy": stats["accuracy"],
                "module_mastered": stats["mastered"],
                "decision": decision["decision"],
                "recommendation": decision["reason"],
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
