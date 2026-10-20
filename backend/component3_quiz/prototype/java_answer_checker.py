"""
java_answer_checker.py

Additional validation for generated Java multiple-choice questions.

Checks:
1. The marked answer satisfies explicit variable-name, type and value
   requirements in the question (only when the answers are Java
   declarations, and not for "which one is invalid" questions).
2. For supported single-declaration questions, the Java compiler checks
   which options compile.
3. For "valid" questions, exactly one option must compile and it must
   be the marked answer.
4. For "compile-time error" / "NOT valid" questions, exactly one option
   must fail to compile and it must be the marked answer.

Important:
- An empty error list does not prove every question is correct.
- Unsupported question types are not compiler-verified.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


JAVA_TYPES = (
    "byte|short|int|long|float|double|boolean|char|String"
)

CODE_OPTION = re.compile(
    rf"^\s*(?:final\s+)?(?:{JAVA_TYPES})(?:\[\])?\s+"
    r"[A-Za-z_$][A-Za-z0-9_$]*\s*=.*;\s*$"
)

# Looser test: "does this answer look like a Java declaration at all?"
DECLARATION_LIKE = re.compile(
    rf"^\s*(?:final\s+)?(?:{JAVA_TYPES})(?:\[\])?\s+"
    r"[A-Za-z_$][A-Za-z0-9_$]*\s*[=;,]"
)

VALID_PHRASES = (
    "valid declaration",
    "valid variable declaration",
    "valid statement",
    "valid java",
    "valid way to declare",
    "valid way to initialize",
    "valid way to initialise",
    "correct declaration",
    "correct statement",
    "correctly declares",
    "legal declaration",
    "legal statement",
    "compiles successfully",
    "will compile",
    "does compile",
)

ERROR_PHRASES = (
    "compile-time error",
    "compile time error",
    "compilation error",
    "does not compile",
    "will not compile",
    "causes an error",
    "cause an error",
    "fails to compile",
    "will fail to compile",
    "is invalid",
    "is illegal",
    "invalid declaration",
    "invalid statement",
    "invalid way",
    "is an invalid",
    "is not valid",
    "is not a valid",
)

# "Which of these is NOT a valid declaration?" asks for the failing option.
NEGATION = re.compile(
    r"\b(?:not|isn't|except|invalid|illegal|incorrect)\b"
    r"|n't\b"
)

# Stems that ask for the invalid option: the marked answer is SUPPOSED
# to break a rule, so name/type/value requirements must not be enforced.
INVALID_STEM = re.compile(
    r"compile[- ]?time error|compilation error|\berrors?\b|"
    r"\b(?:does|do)(?:n't| not) compile|"
    r"\b(?:will|would|can|could)(?:n't| not) compile|"
    r"fails? to compile|\binvalid\b|\billegal\b|\bincorrect\b|"
    r"\bnot (?:a )?(?:valid|legal|allowed)\b",
    re.IGNORECASE,
)


def compact(text):
    """Remove whitespace while preserving case."""
    return re.sub(r"\s+", "", str(text))


def _compiler_command():
    """Find javac; return None if unavailable."""
    compiler = shutil.which("javac")
    if compiler:
        return [compiler]

    # Fallback for machines whose Java runtime bundles the compiler module.
    if shutil.which("java"):
        return ["java", "-m", "jdk.compiler/com.sun.tools.javac.Main"]

    return None


def compiles(code, as_field=False):
    """
    Compile a single declaration in a temporary Java class.

    Returns:
        True  - compilation succeeded
        False - compilation failed
        None  - javac is unavailable
    """
    command = _compiler_command()

    if command is None:
        return None

    if as_field:
        source = (
            "public class T {\n"
            f"    {code}\n"
            "}\n"
        )
    else:
        source = (
            "public class T {\n"
            "    void m() {\n"
            f"        {code}\n"
            "    }\n"
            "}\n"
        )

    with tempfile.TemporaryDirectory() as folder:
        source_path = Path(folder) / "T.java"
        source_path.write_text(source, encoding="utf-8")

        try:
            result = subprocess.run(
                command + [
                    "-proc:none",
                    "-d", folder,
                    str(source_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None

    return result.returncode == 0


def _extract_requested_name(stem):
    """Extract a simple variable name from wording such as 'named count'."""
    match = re.search(
        r"\bnamed\s+[`'\"]?([A-Za-z_$][A-Za-z0-9_$]*)[`'\"]?",
        stem,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else None


def _extract_requested_type(stem):
    """Extract an explicitly requested Java variable type."""
    match = re.search(
        rf"\b(?:a|an|the)\s+({JAVA_TYPES})\s+"
        r"(?:variable|field|value)\b",
        stem,
    )
    return match.group(1) if match else None


def _extract_requested_value(stem):
    """
    Extract a simple explicit value after phrases such as
    'initialize it to', 'set it to', or 'equal to'.
    """
    pattern = (
        r"\b(?:initialize[sd]?\s+(?:it\s+)?to|"
        r"initiali[sz]e\s+(?:it\s+)?to|"
        r"set\s+(?:it\s+)?to|"
        r"equal\s+to|"
        r"value\s+of)\s*"
        r"('[^']*'|\"[^\"]*\"|"
        r"-?\d+(?:\.\d+)?[lLfFdD]?|"
        r"true|false|null)"
        r"(?![A-Za-z0-9_$])"
    )

    match = re.search(pattern, stem, flags=re.IGNORECASE)

    if not match:
        return None

    return match.group(1)


def _contains_exact_value(option, value):
    """
    Check a requested literal against the option's assignment value.
    Quoted values are compared as complete literals, not substrings.
    """
    option_compact = compact(option)
    value_compact = compact(value)

    if value.startswith("'") or value.startswith('"'):
        return value_compact in option_compact

    # Avoid matching 10 inside 100 or true inside a longer identifier.
    return re.search(
        rf"(?<![A-Za-z0-9_$.'\"]){re.escape(value_compact)}"
        rf"(?![A-Za-z0-9_$.'\"])",
        option_compact,
        flags=re.IGNORECASE,
    ) is not None


def check_stem_requirements(candidate):
    """Check explicit name, type and value requirements."""
    errors = []

    if not isinstance(candidate, dict):
        return ["The candidate must be a question object."]

    stem = candidate.get("stem")
    options = candidate.get("options")
    answer = candidate.get("answer")

    if not isinstance(stem, str) or not isinstance(options, dict):
        return ["Missing or invalid stem/options."]

    if answer not in options:
        return ["The marked answer is not present in the options."]

    correct = str(options[answer])

    # "Which line is invalid?" questions: the marked answer is meant to
    # break the stated name/type/value, so there is nothing to enforce.
    if INVALID_STEM.search(stem):
        return errors

    # Value-style or sentence answers ("null", "0", "x is not visible")
    # have no declaration to compare with the stem.
    if not DECLARATION_LIKE.match(correct):
        return errors

    requested_name = _extract_requested_name(stem)
    if requested_name:
        declaration_pattern = (
            rf"^\s*(?:final\s+)?(?:{JAVA_TYPES})(?:\[\])?\s+"
            rf"{re.escape(requested_name)}\s*[=;,]"
        )
        if not re.search(declaration_pattern, correct):
            errors.append(
                f"The stem asks for a variable named {requested_name}, "
                f"but the marked answer does not declare that variable."
            )

    requested_type = _extract_requested_type(stem)
    if requested_type:
        type_pattern = (
            rf"^\s*(?:final\s+)?{re.escape(requested_type)}"
            rf"(?:\[\])?\s+"
        )
        if not re.search(type_pattern, correct):
            errors.append(
                f"The stem asks for a {requested_type} variable, "
                f"but the marked answer does not declare that type."
            )

    requested_value = _extract_requested_value(stem)
    if requested_value and not _contains_exact_value(
        correct, requested_value
    ):
        errors.append(
            f"The stem requests the value {requested_value}, but the "
            "marked answer does not contain that exact value."
        )

    return errors


def _question_kind(stem):
    """
    Identify a narrow set of question types that can be checked by
    compiling every option. Return 'valid', 'error', or None.
    """
    text = re.sub(r"\s+", " ", stem.lower()).strip()

    error_question = any(
        phrase in text for phrase in ERROR_PHRASES
    )
    valid_question = any(
        phrase in text for phrase in VALID_PHRASES
    )

    # "Which of these is NOT a valid declaration?" asks for the option
    # that does NOT compile.
    if valid_question and NEGATION.search(text):
        error_question = True
        valid_question = False

    if error_question and valid_question:
        return None

    if error_question:
        return "error"

    if valid_question:
        return "valid"

    return None


def check_unique_answer(candidate):
    """
    Return a list of validation errors.

    An empty list means the checks passed or the compiler could not
    check the question type. Callers should not interpret this as
    universal proof of correctness.
    """
    if not isinstance(candidate, dict):
        return ["The candidate must be a question object."]

    errors = check_stem_requirements(candidate)

    stem = candidate.get("stem")
    options = candidate.get("options")
    answer = candidate.get("answer")

    if not isinstance(stem, str) or not isinstance(options, dict):
        return errors + ["Missing or invalid stem/options."]

    if set(options) != {"A", "B", "C", "D"}:
        return errors + [
            "Compiler validation requires options A, B, C and D."
        ]

    kind = _question_kind(stem)

    if kind is None:
        # This question type is not safely classifiable by these rules.
        return errors

    if not all(
        CODE_OPTION.fullmatch(str(options[label]))
        for label in "ABCD"
    ):
        # Do not pretend that unsupported options were compiler-checked.
        return errors

    stem_lower = stem.lower()
    as_field = any(
        phrase in stem_lower
        for phrase in ("field", "instance variable", "static field")
    )

    results = {}

    for label in "ABCD":
        result = compiles(
            str(options[label]).strip(),
            as_field=as_field,
        )

        if result is None:
            errors.append(
                "Java compiler validation was unavailable or timed out. "
                "This question has not been compiler-verified."
            )
            return errors

        results[label] = result

    # A "valid" question has one compiling answer.
    # An "error" question has one non-compiling answer.
    desired_result = kind == "valid"

    matching = [
        label
        for label, result in results.items()
        if result == desired_result
    ]

    if len(matching) != 1:
        expected = (
            "compiling" if kind == "valid" else "non-compiling"
        )
        errors.append(
            f"Compiler check: expected exactly one {expected} option, "
            f"but found {len(matching)} "
            f"({', '.join(matching) if matching else 'none'})."
        )
    elif matching[0] != answer:
        errors.append(
            f"Compiler check: the marked answer is {answer}, but "
            f"option {matching[0]} is the only option matching the "
            f"question's compiler criterion."
        )

    return errors


if __name__ == "__main__":
    def make(stem, opts, answer):
        return {
            "stem": stem,
            "options": dict(zip("ABCD", opts)),
            "answer": answer,
        }

    tests = [
        (
            "Incorrect requested char value (must be rejected)",
            make(
                "Which statement is a valid declaration of a char "
                "variable named flag and initializes it to 'true'?",
                [
                    "char flag = 'true';",
                    "char flag = true;",
                    "boolean flag = 'true';",
                    "char flag = 'T';",
                ],
                "A",
            ),
            False,
        ),
        (
            "Two compiling char options (must be rejected)",
            make(
                "Which statement is a valid declaration of a char "
                "variable named ch?",
                [
                    "char ch = '5';",
                    "char ch = 5;",
                    "char ch = '5.0';",
                    "char ch = 5.0;",
                ],
                "A",
            ),
            False,
        ),
        (
            "Multiple valid variable declarations (must be rejected)",
            make(
                "Which of the following is a valid variable declaration "
                "in Java?",
                [
                    "double rate = 5.0;",
                    "int count = 10;",
                    "float price = 19.99f;",
                    "String name = 'John';",
                ],
                "B",
            ),
            False,
        ),
        (
            "One valid int declaration (must pass)",
            make(
                "Which statement is a valid declaration of an int "
                "variable named score?",
                [
                    "int score = 100;",
                    "int score = 'ab';",
                    'int score = "100";',
                    "int score = 1.5;",
                ],
                "A",
            ),
            True,
        ),
        (
            "Default of a String field, answer 'null' (must pass)",
            make(
                "What is the default value of a String field in a "
                "Java class?",
                ["0", "null", "false", '""'],
                "B",
            ),
            True,
        ),
        (
            "NOT a valid declaration, answer is the one that fails "
            "(must pass)",
            make(
                "Which of the following is NOT a valid declaration of "
                "an int variable named n?",
                [
                    "int n = 5;",
                    "int n = 'a';",
                    "int n = 2;",
                    'int n = "5";',
                ],
                "D",
            ),
            True,
        ),
        (
            "Scope question with a variable name in the stem and "
            "sentence answers (must pass)",
            make(
                "Which statement about a variable named total declared "
                "inside a for loop is true?",
                [
                    "It can be used after the loop ends.",
                    "It can only be used inside the loop.",
                    "It is a field of the class.",
                    "It is always equal to 0.",
                ],
                "B",
            ),
            True,
        ),
    ]

    all_passed = True

    for title, question, should_pass in tests:
        problems = check_unique_answer(question)
        passed = not problems

        test_ok = passed == should_pass
        all_passed = all_passed and test_ok

        print(f"\n{title}:")
        print("  OK" if test_ok else "  TEST FAILED")

        for problem in problems:
            print(f"  - {problem}")

    print(
        "\nAll self-tests passed."
        if all_passed
        else "\nOne or more self-tests failed."
    )