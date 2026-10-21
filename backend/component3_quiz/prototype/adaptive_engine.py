
"""adaptive_engine.py

Integrated command-line application for the mastery-based adaptive
Java quiz system.

Connects:
- Existing static Java question bank
- Optional local Qwen question generation
- SQLite learner profiles and attempt history
- Java knowledge graph and prerequisites
- Mastery controller
"""

import random
import re
from collections import defaultdict

from qwen_generator import load_static_bank, generate_questions

from learner_store import (
    initialize_database,
    create_learner,
    record_attempt,
    get_attempt_history,
    get_concept_statistics,
    get_module_statistics,
    get_weak_concepts,
    get_unassessed_concepts,
)

from knowledge_graph import (
    get_module,
    get_concepts,
    get_prerequisite_modules,
)

from mastery_controller import recommend_next_action, evaluate_module

QUIZ_SIZE = 10
MASTERY_THRESHOLD = 0.80


def normalize_answer(value):
    """Normalize an answer such as A or option A."""
    if isinstance(value, list):
        return [normalize_answer(item) for item in value]

    text = str(value).strip()

    match = re.fullmatch(
        r"(?:option\s*)?([A-D])[\s.):]*",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(1).upper()

    return text


def normalize_question(raw, fallback_id):
    """Convert supported question formats into one internal format."""
    if not isinstance(raw, dict):
        return None

    stem = raw.get("stem") or raw.get("question")
    options_raw = raw.get("options")

    if not isinstance(stem, str) or not stem.strip():
        return None

    if isinstance(options_raw, dict):
        options = {
            str(key).strip().upper(): str(value).strip()
            for key, value in options_raw.items()
        }

    elif isinstance(options_raw, list):
        options = {}

        for index, option in enumerate(options_raw):
            if isinstance(option, dict):
                key = (
                    option.get("value")
                    or option.get("key")
                    or chr(65 + index)
                )

                label = (
                    option.get("label")
                    or option.get("text")
                    or option.get("option")
                )

                if label is not None:
                    options[str(key).strip().upper()] = str(label).strip()

            elif isinstance(option, str):
                options[chr(65 + index)] = option.strip()

    else:
        return None

    answer = (
        raw.get("answer")
        or raw.get("correct_answer")
        or raw.get("correctAnswer")
        or raw.get("correctValues")
        or raw.get("correct_values")
    )

    if isinstance(answer, list):
        if len(answer) != 1:
            return None
        answer = answer[0]

    if answer is None:
        return None

    answer = normalize_answer(answer)

    if (
        len(options) != 4
        or set(options) != {"A", "B", "C", "D"}
        or answer not in options
        or any(not text for text in options.values())
    ):
        return None

    concept = (
        raw.get("concept_tag")
        or raw.get("concept")
        or raw.get("weak_concept")
        or raw.get("topic")
    )

    if not isinstance(concept, str) or not concept.strip():
        return None

    return {
        "id": str(raw.get("id") or fallback_id),
        "module_no": raw.get("module_no"),
        "set_no": raw.get("set_no"),
        "module": raw.get("module") or raw.get("module_name") or "",
        "stem": stem.strip(),
        "concept_tag": concept.strip(),
        "options": options,
        "answer": answer,
        "explanation": str(
            raw.get("explanation")
            or raw.get("feedback")
            or "Review the Java concept associated with this question."
        ),
        "source": (
            "Qwen"
            if raw.get("source") == "Qwen"
            else "Question bank"
        ),
    }


def load_normalized_bank():
    """Load and normalize the existing static question bank."""
    bank = load_static_bank()
    normalized = []

    for index, raw in enumerate(bank):
        question = normalize_question(raw, f"static_{index + 1}")

        if question is not None:
            question["source"] = "Question bank"
            normalized.append(question)

    if not normalized:
        raise RuntimeError(
            "No valid questions were found in the static question bank."
        )

    return normalized


def choose_questions(
    learner_id,
    module_no,
    module_name,
    concepts,
    count=QUIZ_SIZE,
    try_qwen=False,
    set_no=None,
):
    """Select questions, preferring fresh questions and using static fallback."""
    bank = load_normalized_bank()
    history = get_attempt_history(learner_id, limit=10000)

    attempted_ids = {
        str(item["question_id"])
        for item in history
        if item["question_id"] is not None
    }

    # Find unused questions belonging to the selected module and concepts.
    available = [
        question
        for question in bank
        if question["module_no"] == module_no
        and (set_no is None or question["set_no"] == set_no)
        and question["concept_tag"] in concepts
        and question["id"] not in attempted_ids
    ]

    # If all matching questions have been attempted, allow repeats.
    if not available:
        available = [
            question
            for question in bank
            if question["module_no"] == module_no
            and (set_no is None or question["set_no"] == set_no)
            and question["concept_tag"] in concepts
        ]

    # Try local Qwen generation when requested.
    if try_qwen:
        try:
            generated = generate_questions(
                module_name=module_name,
                weak_concepts=concepts,
                count=min(count, 5),
                module_no=module_no,
            )

            accepted = []
            accepted_ids = set()

            for index, raw in enumerate(generated):
                question = normalize_question(
                    raw,
                    f"generated_{module_no}_{index + 1}",
                )

                if question is None:
                    continue

                # Only accept questions targeting the requested concepts.
                if question["concept_tag"] not in concepts:
                    continue

                # Do not reuse questions already attempted by this learner.
                if question["id"] in attempted_ids:
                    continue

                # Avoid duplicate IDs within the generated batch.
                if question["id"] in accepted_ids:
                    continue

                question["module_no"] = module_no
                question["module"] = module_name
                question["source"] = "Qwen"

                accepted.append(question)
                accepted_ids.add(question["id"])

            # Start with accepted Qwen questions.
            questions = accepted[:count]
            seen_ids = {question["id"] for question in questions}

            # Fill any remaining places using static questions.
            random.shuffle(available)

            for question in available:
                if len(questions) >= count:
                    break

                if question["id"] not in seen_ids:
                    questions.append(question)
                    seen_ids.add(question["id"])

            if questions:
                print(
                    f"\nQuestion selection: "
                    f"{sum(q['source'] == 'Qwen' for q in questions)} "
                    f"Qwen-generated, "
                    f"{sum(q['source'] == 'Question bank' for q in questions)} "
                    f"static."
                )
                return questions

            print(
                "\nQwen returned no usable questions. "
                "Trying the static question bank."
            )

        except Exception as exc:
            print("\nQwen generation was unavailable or failed.")
            print(f"Reason: {exc}")
            print("Continuing with the static question bank.\n")

    # Static-bank selection: prioritize one question per concept if possible.
    grouped = defaultdict(list)

    for question in available:
        grouped[question["concept_tag"]].append(question)

    for items in grouped.values():
        random.shuffle(items)

    selected = []
    seen_ids = set()

    for concept in concepts:
        items = grouped.get(concept, [])

        if items and len(selected) < count:
            question = items.pop()
            selected.append(question)
            seen_ids.add(question["id"])

    remaining = [
        question
        for items in grouped.values()
        for question in items
        if question["id"] not in seen_ids
    ]

    random.shuffle(remaining)

    for question in remaining:
        if len(selected) >= count:
            break

        selected.append(question)
        seen_ids.add(question["id"])

    # If unused questions are exhausted, the earlier fallback permits repeats.
    if not selected:
        selected = available[:count]

    return selected


def ask_question(question, question_number, total):
    """Display a question and return True, False, or None if the learner quits."""
    print("\n" + "=" * 65)
    print(f"Question {question_number} of {total}")
    print(f"Concept: {question['concept_tag']}")
    print(f"Source: {question['source']}")
    print("-" * 65)
    print(question["stem"])

    for key in ("A", "B", "C", "D"):
        print(f"  {key}. {question['options'][key]}")

    while True:
        answer = input(
            "\nYour answer (A/B/C/D, or Q to quit): "
        ).strip().upper()

        if answer == "Q":
            return None

        answer = normalize_answer(answer)

        if answer in ("A", "B", "C", "D"):
            break

        print("Please enter A, B, C, D, or Q.")

    correct = answer == question["answer"]

    if correct:
        print("\nCorrect!")
    else:
        print(f"\nNot quite. Correct answer: {question['answer']}")

    print("Explanation:", question["explanation"])
    return correct


def show_progress(learner_id, module_no):
    """Display saved module and concept performance."""
    module = get_module(module_no)

    if module is None:
        print("That module does not exist.")
        return

    stats = get_module_statistics(learner_id, module_no)

    print("\n" + "=" * 65)
    print("LEARNER PROGRESS")
    print("=" * 65)
    print(f"Learner: {learner_id}")
    print(f"Module: {module['module_name']}")
    print(f"Recorded attempts: {stats['attempts']}")
    print(f"Accuracy: {stats['accuracy'] * 100:.1f}%")
    print(f"Mastered: {'Yes' if stats['mastered'] else 'No'}")

    print("\nConcept performance:")

    concept_stats = get_concept_statistics(learner_id, module_no)
    by_name = {item["concept"]: item for item in concept_stats}

    for concept in get_concepts(module_no):
        item = by_name.get(concept)

        if item is None:
            print(f"  {concept}: Not assessed")
        else:
            print(
                f"  {concept}: {item['correct']}/{item['attempts']} correct "
                f"({item['accuracy'] * 100:.1f}%)"
            )

    decision = recommend_next_action(learner_id, module_no)

    print("\nAdaptive decision:", decision["decision"])
    print("Reason:", decision["reason"])
    print("Recommendation:", decision["recommendation"])


def run_application():
    """Run the interactive adaptive Java quiz application."""
    initialize_database()

    print("=" * 65)
    print("MASTERY-BASED ADAPTIVE JAVA QUIZ SYSTEM")
    print("=" * 65)

    learner_id = input("Enter your learner ID: ").strip()

    if not learner_id:
        print("Learner ID cannot be empty.")
        return

    create_learner(learner_id)

    while True:
        print("\nAvailable modules:")

        from knowledge_graph import MODULES

        for module in MODULES:
            print(
                f"  {module['module_no']:2}. "
                f"{module['module_name']}"
            )

        print("  P. View progress")
        print("  X. Exit")

        choice = input("\nChoose a module or action: ").strip()

        if choice.upper() == "X":
            print("Your progress is saved in the SQLite database.")
            break

        if choice.upper() == "P":
            module_text = input("Module number: ").strip()

            try:
                show_progress(learner_id, int(module_text))
            except (ValueError, TypeError):
                print("Please enter a valid module number from 1 to 10.")

            continue

        try:
            module_no = int(choice)
        except ValueError:
            print("Enter a module number from 1 to 10, P, or X.")
            continue

        module = get_module(module_no)

        if module is None:
            print("That module does not exist.")
            continue

        # Enforce prerequisite modules defined in the knowledge graph.
        blocked_by = []

        for prerequisite_no in get_prerequisite_modules(module_no):
            prerequisite_result = evaluate_module(
                learner_id,
                prerequisite_no,
            )

            if not prerequisite_result["mastered"]:
                prerequisite_module = get_module(prerequisite_no)

                if prerequisite_module is not None:
                    blocked_by.append(
                        prerequisite_module["module_name"]
                    )

        if blocked_by:
            print("\nThis module has unmet prerequisites:")
            for name in blocked_by:
                print(" -", name)
            print("Complete the prerequisite modules first.")
            continue

        unassessed = get_unassessed_concepts(
            learner_id,
            module_no,
            get_concepts(module_no),
        )
        weak = get_weak_concepts(learner_id, module_no)

        if unassessed:
            concepts_to_practice = unassessed
            print("\nInitial assessment for unassessed concepts.")
            use_qwen = False

        elif weak:
            concepts_to_practice = weak
            print("\nTargeted practice for weak concepts:")
            print(", ".join(weak))

            use_qwen = (
                input("Try generating fresh Qwen questions? (y/N): ")
                .strip()
                .lower()
                == "y"
            )

        else:
            stats = get_module_statistics(learner_id, module_no)

            if (
                stats["attempts"] >= 5
                and stats["accuracy"] >= MASTERY_THRESHOLD
            ):
                print("\nThis module currently meets the score threshold.")
                print(
                    "Review the concept performance before progressing."
                )
            else:
                print("\nContinue module practice.")

            concepts_to_practice = get_concepts(module_no)
            use_qwen = False

        questions = choose_questions(
            learner_id=learner_id,
            module_no=module_no,
            module_name=module["module_name"],
            concepts=concepts_to_practice,
            count=QUIZ_SIZE,
            try_qwen=use_qwen,
        )

        if not questions:
            print(
                "No usable questions were found for this module. "
                "Check the question-bank concept tags and module numbers."
            )
            continue

        print(f"\nStarting quiz: {module['module_name']}")
        print(f"Questions available in this quiz: {len(questions)}")

        correct_count = 0
        answered_count = 0

        for index, question in enumerate(questions, start=1):
            result = ask_question(question, index, len(questions))

            if result is None:
                print("Quiz stopped. Completed answers remain saved.")
                break

            answered_count += 1
            correct_count += int(result)

            record_attempt(
                learner_id=learner_id,
                module_no=module_no,
                module_name=module["module_name"],
                concept=question["concept_tag"],
                is_correct=result,
                question_id=question["id"],
            )

        if answered_count:
            print("\n" + "=" * 65)
            print("QUIZ SUMMARY")
            print("=" * 65)
            print(f"Answered: {answered_count}")
            print(f"Correct: {correct_count}")
            print(
                f"Quiz score: "
                f"{correct_count / answered_count * 100:.1f}%"
            )

            show_progress(learner_id, module_no)


if __name__ == "__main__":
    run_application()
