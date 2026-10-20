import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from ask import decide

COMPLETED = ["lec1"]

# (question, expected) expected: answer | locked | offtopic
QUESTIONS = [
    # allowed (lec1) - FILL IN 6+ from lec1 slides you have NOT used
    ("In Java, what does a class describe?", "answer"),
    ("What is the purpose of the JVM?", "answer"),
    # ("...", "answer"),

    # locked (lec2) - FILL IN 6+ on lec2 slides you have NOT used
    ("How does a constructor initialize an instance?", "locked"),
    ("Explain polymorphism in object-oriented programming.", "locked"),
    # ("...", "locked"),

    # off-topic - include hard ones that mention programming
    ("How can I sort a list in Python?", "offtopic"),
    ("How do I install Python?", "offtopic"),
    ("What is a REST API?", "offtopic"),
    # ("...", "offtopic"),
]

leaks = wrong_blocks = offtopic_answered = 0
n_locked = n_allowed = n_off = 0

print("HELD-OUT TESTS (completed = lec1)")
print("-" * 90)
for q, expected in QUESTIONS:
    d = decide(q, COMPLETED, gate=True)
    actual = d["decision"]
    best = d["best"]
    if expected == "locked":
        n_locked += 1
        ok = actual != "answer"
        leaks += not ok
    elif expected == "answer":
        n_allowed += 1
        ok = actual == "answer"
        wrong_blocks += not ok
    else:
        n_off += 1
        ok = actual != "answer"
        offtopic_answered += not ok
    b = f"{best:.3f}" if best is not None else "  -  "
    print(f"{'PASS ' if ok else 'CHECK'} | exp={expected:8} got={actual:11} best={b} | {q}")

print("-" * 90)
print(f"decision leaks     : {leaks}/{n_locked}")
print(f"wrong blocks       : {wrong_blocks}/{n_allowed}")
print(f"off-topic answered : {offtopic_answered}/{n_off}")