"""
shuffled_options.py

Changes how Qwen writes multiple-choice questions.

Before: Qwen writes four options A-D and picks the answer letter.
        (It often repeats one option four times or marks the wrong key.)

Now:    Qwen writes ONE correct answer and THREE wrong answers.
        This module shuffles them into A-D and sets the answer letter
        itself, so the answer key is always right by construction.

Usage in qwen_generator.py (three small edits, see the chat message):

    from shuffled_options import with_shuffled_options, with_shuffled_prompt
    ...
    ask_qwen = with_shuffled_options(ask_qwen)       # after ask_qwen
    build_prompt = with_shuffled_prompt(build_prompt)  # after build_prompt
"""

import functools
import random
import re

LABELS = "ABCD"

OPTION_LETTER = re.compile(r"\b[Oo]ptions?\s+[A-D]\b")


# --------------------------------------------------
# Answer shuffling
# --------------------------------------------------

def _drop_letter_sentences(text):
    """
    The explanation is written before shuffling, so it must not refer to
    option letters. Remove any sentence that does.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [s for s in sentences if not OPTION_LETTER.search(s)]
    return " ".join(kept).strip()


def convert_candidate(item, rng=random):
    """
    Turn {stem, concept_tag, correct, wrong[3], explanation} into the
    {stem, concept_tag, options{A-D}, answer, explanation} shape that the
    rest of the generator expects.

    Anything malformed is passed on in a form that the generator's
    existing structure checks will reject (wrong number of options,
    duplicate options, missing fields).
    """
    if not isinstance(item, dict) or "correct" not in item:
        return item

    wrong = item.get("wrong")
    if not isinstance(wrong, list):
        wrong = []

    texts = [item["correct"]] + list(wrong)

    order = list(range(len(texts)))
    rng.shuffle(order)

    options = {}
    answer = None

    for label, index in zip(LABELS, order):
        options[label] = texts[index]

        if index == 0:
            answer = label

    result = {
        key: value
        for key, value in item.items()
        if key not in ("correct", "wrong")
    }
    result["options"] = options
    result["answer"] = answer

    if isinstance(result.get("explanation"), str):
        result["explanation"] = _drop_letter_sentences(result["explanation"])

    return result


def with_shuffled_options(ask_function):
    """Wrap ask_qwen so its questions come back with shuffled options."""

    @functools.wraps(ask_function)
    def wrapper(*args, **kwargs):
        questions = ask_function(*args, **kwargs)

        if isinstance(questions, list):
            return [convert_candidate(question) for question in questions]

        return questions

    return wrapper


# --------------------------------------------------
# Prompt replacement
# --------------------------------------------------

PROMPT_TAIL = """REQUIREMENTS:
Ignore any earlier instruction to write options A, B, C and D or an answer
letter. Use the format described here instead.

1. Return exactly one question object inside a JSON array.
2. Include exactly these fields:
   stem, concept_tag, correct, wrong, explanation.
   Do NOT write options A-D and do NOT write an answer letter. The program
   builds the options from "correct" and "wrong".
3. Use the exact concept tag: {concept}
4. "correct" is the ONE answer that satisfies the complete stem.
5. "wrong" is a list of exactly three different answers. Each one must be
   definitely incorrect because it breaks at least one condition of the
   stem. It must not be another valid answer.
6. "correct" and the three "wrong" answers must all be different in wording
   and meaning. Never repeat the same code with different spacing.
7. If the stem names a variable, a type or a literal value, "correct" must
   use exactly that name, type and value.
8. The explanation is one or two sentences about why "correct" is right.
   It must NOT mention option letters or positions (no "Option A", no
   "the first option").
9. Do not copy or lightly modify the recent questions. Avoid repeating
   their opening words.
10. Check the answers against the Java rules. Do not invent a Java rule.
11. Return valid JSON only, without Markdown or commentary.

IMPORTANT JAVA FACTS:
- String literals use double quotation marks.
- Character literals use single quotation marks and represent one character
  or a valid Java escape sequence.
- A String field defaults to null, not an empty string.
- Instance and static int fields default to 0.
- Local variables do not receive automatic default values.
- A local variable must be assigned before it is read.
- A decimal literal such as 5.0 is a double by default.
- A float decimal literal normally requires an f or F suffix.
- An answer must satisfy every detail of the stem.

OUTPUT JSON SHAPE:
[
  {
    "stem": "Write a new question here",
    "concept_tag": "{concept}",
    "correct": "The one answer that satisfies the stem",
    "wrong": [
      "First incorrect answer",
      "Second incorrect answer",
      "Third incorrect answer"
    ],
    "explanation": "Explain why the correct answer satisfies the stem."
  }
]

The text above is a schema illustration, not a question to copy.
Create new content focused on the requested concept.
Return exactly one question inside a JSON array.
"""


def with_shuffled_prompt(build_function):
    """
    Wrap build_prompt: keep everything before "REQUIREMENTS:" and replace
    the rest with the correct/wrong format instructions.
    """

    @functools.wraps(build_function)
    def wrapper(*args, **kwargs):
        prompt = build_function(*args, **kwargs)

        start = prompt.find("REQUIREMENTS:")

        if start == -1:
            return prompt

        match = re.search(r"exact concept tag:\s*(\S+)", prompt)
        concept = match.group(1) if match else ""

        return prompt[:start] + PROMPT_TAIL.replace("{concept}", concept)

    return wrapper


# --------------------------------------------------
# Self-test:  py -3.12 shuffled_options.py
# --------------------------------------------------

if __name__ == "__main__":
    raw = {
        "stem": "Which statement declares an int variable named score "
                "and sets it to 100?",
        "concept_tag": "declaration",
        "correct": "int score = 100;",
        "wrong": ["int score = 10;", "double score = 100;",
                  "int total = 100;"],
        "explanation": "It declares an int named score. Option A is right.",
    }

    positions = set()
    for _ in range(40):
        converted = convert_candidate(raw)
        assert sorted(converted["options"]) == list("ABCD")
        assert converted["options"][converted["answer"]] == "int score = 100;"
        assert "Option" not in converted["explanation"]
        positions.add(converted["answer"])

    print("Answer key always matches the correct text: OK")
    print("Letters used for the correct answer:", sorted(positions))
    print("Explanation after cleanup:", converted["explanation"])

    broken = convert_candidate({"stem": "x", "concept_tag": "y",
                                "correct": "a", "wrong": ["a", "b"],
                                "explanation": "z"})
    print("Broken input becomes:", broken["options"])

    fake_prompt = (
        "HEAD\nUse the exact concept tag: scope\nREQUIREMENTS:\nold text"
    )
    new_prompt = with_shuffled_prompt(lambda: fake_prompt)()
    assert new_prompt.startswith("HEAD")
    assert "old text" not in new_prompt
    assert '"concept_tag": "scope"' in new_prompt
    print("Prompt replacement: OK")