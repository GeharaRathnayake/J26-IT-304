"""
test_gate.py - evaluate the curriculum gate on a labelled question set (no LLM needed).

Run from C:\\4y1s\\rag-project:
    python tests\\test_gate.py

Each question lists the lectures that can answer it ("answerable_in"; [] = off-topic).
It is run with several "completed lectures" settings, with the gate ON and OFF.

Definitions (reported separately, for gate ON and gate OFF)
  expected answer    : at least one lecture in answerable_in is completed
  DECISION LEAK      : the question is only answerable from a locked lecture, but the
                       system decides to answer it
  RETRIEVAL LEAK     : the same kind of question, but chunks from a locked lecture were
                       retrieved into the context (what the LLM would be shown)
  WRONG BLOCK        : expected answer, but the system declines
  OFF-TOPIC ANSWERED : off-topic question that the system tries to answer
Gate OFF is the unrestricted baseline: same retrieval and distance cut-off, no lecture filter
and no locked-lecture decline, so it "answers" whenever something is close enough.
Results are also written to tests\\results.csv.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ask import decide  # noqa: E402

L1, L2 = "lec1", "lec2"

QUESTIONS = [
    # --- only lecture 1 can answer ---
    ("What is bytecode?", [L1]),
    ("What does the JVM do?", [L1]),
    ("Who created Java?", [L1]),
    ("How do I compile a Java program?", [L1]),
    ("What is the difference between print and println?", [L1]),
    ("How do I read input from the keyboard in Java?", [L1]),
    ("How does a for loop work in Java?", [L1]),
    ("What is a switch statement?", [L1]),
    ("What is the difference between JDK and JRE?", [L1]),
    ("How do I write comments in Java?", [L1]),
    ("What is the main method?", [L1]),
    ("What does write once run anywhere mean?", [L1]),
    ("What file extension do compiled Java programs have?", [L1]),
    ("What is a do while loop?", [L1]),
    # --- only lecture 2 can answer ---
    ("What is a constructor in Java?", [L2]),
    ("What is the difference between a default and a parameterized constructor?", [L2]),
    ("What is encapsulation?", [L2]),
    ("What is abstraction in object oriented programming?", [L2]),
    ("What is inheritance in Java?", [L2]),
    ("What is polymorphism?", [L2]),
    ("What does the this keyword do?", [L2]),
    ("What are getters and setters?", [L2]),
    ("What does the super keyword do?", [L2]),
    ("What is information hiding?", [L2]),
    ("How do I create an object in Java?", [L2]),
    ("What is the Object class in Java?", [L2]),
    ("What is the difference between private and public?", [L2]),
    ("How do I extend a class in Java?", [L2]),
    # --- overlapping topics: either lecture can answer ---
    ("What is a class in Java?", [L1, L2]),
    ("What is a method in Java?", [L1, L2]),
    ("What are the differences between C++ and Java?", [L1, L2]),
    # --- off-topic ---
    ("What is the capital of France?", []),
    ("How do I cook rice?", []),
    ("Who won the football world cup?", []),
    ("How do I sort a list in Python?", []),
    ("What is machine learning?", []),
]

SETTINGS = [
    ("completed = lec1", [L1]),
    ("completed = lec1,lec2", [L1, L2]),
]


def expected_answer(answerable_in, completed):
    return any(l in completed for l in answerable_in)


def run():
    rows = []
    for setting_name, completed in SETTINGS:
        for gate in (True, False):
            for q, ans_in in QUESTIONS:
                exp = expected_answer(ans_in, completed)
                d = decide(q, completed, gate=gate)
                chunks = d["result"]["chunks"]
                locked_chunks = [c for c in chunks if c["lecture_id"] not in completed]
                decision = d["decision"]
                if gate:
                    answered = decision == "answer"
                else:
                    answered = d["result"]["status"] == "ok"  # baseline never declines on lock
                locked_only = bool(ans_in) and not exp
                rows.append({
                    "setting": setting_name,
                    "gate": "ON" if gate else "OFF",
                    "question": q,
                    "answerable_in": ",".join(ans_in) or "off-topic",
                    "expected": "answer" if exp else "decline",
                    "decision": decision if gate else ("answer" if answered else "not_covered"),
                    "best_distance": "" if d["best"] is None else f"{d['best']:.3f}",
                    "locked_chunks_retrieved": len(locked_chunks),
                    "decision_leak": locked_only and answered,
                    "retrieval_leak": locked_only and bool(locked_chunks),
                    "wrong_block": exp and not answered,
                    "offtopic_answered": (not ans_in) and answered,
                })
    return rows


def summarize(rows):
    print()
    for setting_name, _ in SETTINGS:
        for gate in ("ON", "OFF"):
            sub = [r for r in rows if r["setting"] == setting_name and r["gate"] == gate]
            n_locked = sum(1 for r in sub if r["answerable_in"] != "off-topic" and r["expected"] == "decline")
            n_exp = sum(1 for r in sub if r["expected"] == "answer")
            n_off = sum(1 for r in sub if r["answerable_in"] == "off-topic")
            dleaks = [r for r in sub if r["decision_leak"]]
            rleaks = [r for r in sub if r["retrieval_leak"]]
            wb = [r for r in sub if r["wrong_block"]]
            off = [r for r in sub if r["offtopic_answered"]]
            print(f"=== {setting_name} | gate {gate}")
            print(f"  decision leaks      : {len(dleaks)}/{n_locked}  ({100*len(dleaks)/max(n_locked,1):.0f}%)")
            print(f"  retrieval leaks     : {len(rleaks)}/{n_locked}  ({100*len(rleaks)/max(n_locked,1):.0f}%)")
            print(f"  wrong blocks        : {len(wb)}/{n_exp}  ({100*len(wb)/max(n_exp,1):.0f}%)")
            print(f"  off-topic answered  : {len(off)}/{n_off}")
            if gate == "ON":
                for r in dleaks:
                    print(f"    DECISION LEAK : {r['question']}  (best {r['best_distance']})")
                for r in rleaks:
                    print(f"    RETRIEVAL LEAK: {r['question']}")
                for r in wb:
                    print(f"    WRONG BLOCK   : {r['question']}  -> {r['decision']} (best {r['best_distance']})")
                for r in off:
                    print(f"    OFF-TOPIC     : {r['question']}  (best {r['best_distance']})")
            print()


if __name__ == "__main__":
    rows = run()
    out = ROOT / "tests" / "results.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summarize(rows)
    print(f"Per-question results saved to {out}")
