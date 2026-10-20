import json

from qwen_generator import generate_questions
from question_validator import validate_generated_questions

# Load your existing 1,000-question bank
with open("static_questions.json", "r", encoding="utf-8") as file:
    existing_questions = json.load(file)

# Ask Qwen for one new question
questions = generate_questions(
    module_name="Variables",
    weak_concepts=["declaration"],
    count=1
)

# Check the generated question
valid_questions, errors = validate_generated_questions(
    questions,
    1,
    ["declaration"],
    existing_questions,
    required_count=1
)

if errors:
    print("VALIDATION FAILED")
    for error in errors:
        print("-", error)
else:
    print("VALIDATION PASSED")
    print(json.dumps(valid_questions, indent=2, ensure_ascii=False))