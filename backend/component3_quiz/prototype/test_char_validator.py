
from question_validator import _char_literal_intent_errors

question = {
    "stem": "Which statement declares a char variable named flag and initializes it to 'true'?",
    "options": {
        "A": "char flag = 'true';",
        "B": "char flag = true;",
        "C": "boolean flag = 'T';",
        "D": "char flag = 'T';"
    },
    "answer": "D"
}

errors = _char_literal_intent_errors(question)

print("Validator test result:")

if errors:
    print("PASS: The invalid question was detected.")
    for error in errors:
        print("-", error)
else:
    print("FAIL: The invalid question was not detected.")
