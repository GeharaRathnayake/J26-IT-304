
"""mastery_controller.py
Decision logic for mastery-based Java learning.
"""

from learner_store import (
    initialize_database,
    get_module_statistics,
    get_concept_statistics,
    get_weak_concepts,
    get_unassessed_concepts,
)
from knowledge_graph import (
    get_module,
    get_concepts,
    get_prerequisite_modules,
)

MASTERY_THRESHOLD = 0.80
MIN_ATTEMPTS_FOR_MASTERY = 5


def evaluate_module(learner_id, module_no):
    """Decide whether to practise, assess, or progress."""

    module = get_module(module_no)

    if module is None:
        raise ValueError(f"Module {module_no} does not exist.")

    stats = get_module_statistics(learner_id, module_no)
    weak = get_weak_concepts(learner_id, module_no)
    unassessed = get_unassessed_concepts(
        learner_id, module_no, get_concepts(module_no)
    )

    # Check the prerequisite modules before progression.
    blocked_by = []

    for prerequisite_no in get_prerequisite_modules(module_no):
        prerequisite = get_module_statistics(
            learner_id, prerequisite_no
        )

        if not prerequisite["mastered"]:
            prerequisite_module = get_module(prerequisite_no)
            blocked_by.append(prerequisite_module["module_name"])

    if blocked_by:
        decision = "PREREQUISITES_REQUIRED"
        reason = "Complete the prerequisite modules first."

    elif unassessed:
        decision = "ASSESS_UNASSESSED_CONCEPTS"
        reason = "Some concepts have not been assessed yet."

    elif stats["attempts"] < MIN_ATTEMPTS_FOR_MASTERY:
        decision = "CONTINUE_PRACTICE"
        reason = (
            f"Complete at least {MIN_ATTEMPTS_FOR_MASTERY} "
            "recorded attempts before mastery is confirmed."
        )

    elif stats["accuracy"] < MASTERY_THRESHOLD:
        decision = "TARGETED_REVISION"
        reason = "The module score is below the mastery threshold."

    elif weak:
        decision = "TARGETED_REVISION"
        reason = "One or more concepts still need practice."

    else:
        decision = "MODULE_MASTERED"
        reason = "The learner has met the mastery requirements."

    return {
        "learner_id": learner_id,
        "module_no": module_no,
        "module_name": module["module_name"],
        "attempts": stats["attempts"],
        "accuracy": stats["accuracy"],
        "mastered": decision == "MODULE_MASTERED",
        "decision": decision,
        "reason": reason,
        "weak_concepts": weak,
        "unassessed_concepts": unassessed,
        "blocked_by": blocked_by,
    }


def recommend_next_action(learner_id, module_no):
    """Produce a learner-specific practice recommendation."""

    result = evaluate_module(learner_id, module_no)

    if result["decision"] == "PREREQUISITES_REQUIRED":
        result["recommendation"] = (
            "Study prerequisite modules: "
            + ", ".join(result["blocked_by"])
        )

    elif result["decision"] == "ASSESS_UNASSESSED_CONCEPTS":
        result["recommendation"] = (
            "Assess these concepts: "
            + ", ".join(result["unassessed_concepts"])
        )

    elif result["decision"] == "TARGETED_REVISION":
        result["recommendation"] = (
            "Generate fresh questions for weak concepts: "
            + ", ".join(result["weak_concepts"])
            if result["weak_concepts"]
            else "Provide another module practice quiz."
        )

    elif result["decision"] == "MODULE_MASTERED":
        result["recommendation"] = (
            "Allow progression to the next module."
        )

    else:
        result["recommendation"] = (
            "Continue practice and record more answers."
        )

    return result


if __name__ == "__main__":
    initialize_database()

    learner_id = input("Enter learner ID: ").strip()
    if not learner_id:
        learner_id = "test_learner"

    module_text = input(
        "Enter module number (1-10), or press Enter for 1: "
    ).strip()
    module_no = int(module_text) if module_text else 1

    result = recommend_next_action(learner_id, module_no)

    print("\n--- Mastery Controller Result ---")
    for key, value in result.items():
        print(f"{key}: {value}")
