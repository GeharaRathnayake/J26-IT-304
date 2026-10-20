import json
import random
import re
import urllib.request
import urllib.error
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from question_validator import validate_generated_questions
from java_answer_checker import check_unique_answer


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).parent
SERVER_URL = "http://127.0.0.1:8080/v1/chat/completions"

STATIC_BANK_PATH = BASE_DIR / "static_questions.json"
OUTPUT_DIR = BASE_DIR / "generated_questions"

BATCH_SIZE = 1
MAX_RETRIES = 5
MAX_TOKENS = 1800
REQUEST_TIMEOUT = 600

BASE_TEMPERATURE = 0.3
TEMPERATURE_STEP = 0.1
MAX_TEMPERATURE = 0.7

PROMPT_STEM_LIMIT = 20
OPENING_WORDS = 4
OPENING_CHECK_LAST = 5

NEAR_DUPLICATE_THRESHOLD = 0.92
MAX_STEM_SIMILARITY = 0.90

# Print the full JSON of every rejected question (useful while testing).
DEBUG_PRINT_REJECTED = True


# ============================================================
# CONCEPT GUIDE
# ============================================================

CONCEPT_GUIDE = {
    "declaration": (
        "Java variable declarations: type and name, optional initialization, "
        "valid syntax, semicolons, and invalid declaration forms."
    ),
    "initialization": (
        "Assigning an initial value, assigning a value later, reassignment, "
        "and reading a local variable before initialization."
    ),
    "naming": (
        "Java identifier rules: names cannot start with digits, contain "
        "spaces, or use reserved keywords. Names are case-sensitive."
    ),
    "default_values": (
        "Default values for Java fields and array elements. Primitive and "
        "reference fields have different defaults. Local variables do not "
        "receive automatic default values. Explicitly identify a field "
        "or array element."
    ),
    "variable_types": (
        "Java primitive types and String, literal syntax, assignment "
        "compatibility, and choosing appropriate types."
    ),
    "scope": (
        "Variable visibility within methods and blocks, loop-variable scope, "
        "and restrictions on redeclaring local variables."
    ),
}

GENERIC_CONCEPT_GUIDE = (
    "Test the requested Java concept with a clear, self-contained "
    "beginner-level question."
)

QUESTION_STYLES = [
    "Ask which statement is valid Java.",
    "Ask which line causes a compile-time error.",
    "Use a short Java example and ask what it prints, if suitable.",
    "Ask which statement about the requested concept is true.",
    "Show a broken line and ask which option fixes it.",
    "Ask which option is incorrect, with exactly one incorrect option.",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def normalize_text(value):
    return " ".join(str(value).lower().split())


def compact_code(value):
    return re.sub(r"\s+", "", str(value))


def normalized_option(value):
    return re.sub(r"\s+", " ", str(value).strip())


def opening(stem, words=OPENING_WORDS):
    return tuple(
        re.findall(r"[a-z0-9']+", str(stem).lower())[:words]
    )


def save_questions(questions, filename):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename

    with path.open("w", encoding="utf-8") as file:
        json.dump(questions, file, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(questions)} question(s) to:\n{path}")
    return path


def load_static_bank():
    if not STATIC_BANK_PATH.exists():
        raise FileNotFoundError(
            f"Question bank not found: {STATIC_BANK_PATH}"
        )

    with STATIC_BANK_PATH.open("r", encoding="utf-8") as file:
        bank = json.load(file)

    if not isinstance(bank, list):
        raise ValueError(
            "static_questions.json must contain a JSON list."
        )

    print(f"Loaded {len(bank)} static questions.")
    return bank


# Stems that ask for the INVALID / failing option. For these, the marked
# answer is SUPPOSED to be bad Java, so the "marked answer looks invalid"
# checks must not run.
INVALID_STEM_PATTERN = re.compile(
    r"compile[- ]?time error|compilation error|\berrors?\b|"
    r"\b(?:does|do)(?:n't| not) compile|"
    r"\b(?:will|would|can|could)(?:n't| not) compile|"
    r"fails? to compile|\binvalid\b|\billegal\b|\bincorrect\b|"
    r"\bnot (?:a )?(?:valid|legal|allowed)\b",
    re.IGNORECASE,
)


def asks_for_invalid_option(stem):
    return bool(INVALID_STEM_PATTERN.search(str(stem)))


# ============================================================
# SHUFFLED OPTIONS
#
# Qwen writes ONE correct answer and THREE wrong answers. The script
# shuffles them into A-D and sets the answer letter itself, so the
# answer key is always right and four identical options cannot happen.
# ============================================================

OPTION_LETTER = re.compile(r"\b[Oo]ptions?\s+[A-D]\b")
OPTION_LABELS = "ABCDEFGH"


def drop_option_letter_sentences(text):
    """The explanation is written before the shuffle, so it must not
    refer to option letters. Remove any sentence that does."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [s for s in sentences if not OPTION_LETTER.search(s)]
    return " ".join(kept).strip()


def convert_candidate(item, rng=random):
    """
    {stem, concept_tag, correct, wrong[3], explanation}
        -> {stem, concept_tag, options{A-D}, answer, explanation}

    Malformed input is passed on in a form that check_structure rejects.
    Items already in the old options/answer shape are returned unchanged.
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

    for label, index in zip(OPTION_LABELS, order):
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
        result["explanation"] = drop_option_letter_sentences(
            result["explanation"]
        )

    return result


# ============================================================
# STRUCTURAL CHECKS
# ============================================================

def check_structure(candidate, target_concept):
    errors = []

    if not isinstance(candidate, dict):
        return ["The generated question must be a JSON object."]

    required = {
        "stem", "concept_tag", "options", "answer", "explanation"
    }

    missing = required - set(candidate)
    extra = set(candidate) - required

    if missing:
        errors.append(f"Missing fields: {sorted(missing)}")

    if extra:
        errors.append(f"Unexpected fields: {sorted(extra)}")

    for field in ("stem", "explanation"):
        value = candidate.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be non-empty text.")

    if candidate.get("concept_tag") != target_concept:
        errors.append(
            f"concept_tag must be {target_concept!r}, "
            f"not {candidate.get('concept_tag')!r}."
        )

    options = candidate.get("options")

    if not isinstance(options, dict):
        errors.append("options must be an object.")
        return errors

    if set(options) != {"A", "B", "C", "D"}:
        errors.append(
            "There must be exactly one 'correct' answer and exactly "
            "three different 'wrong' answers (four different answers "
            "in total)."
        )
        return errors

    values = []
    folded = []

    for label in "ABCD":
        value = options[label]

        if not isinstance(value, str) or not value.strip():
            errors.append("Every answer must be non-empty text.")
        else:
            values.append(normalized_option(value))
            folded.append(normalized_option(value).casefold())

    if len(values) == 4 and len(set(values)) != 4:
        errors.append(
            "Two or more answers are identical after whitespace "
            "normalization. The correct answer and the three wrong "
            "answers must all be different."
        )
    elif len(folded) == 4 and len(set(folded)) != 4:
        errors.append(
            "Two or more answers differ only by capitalization. "
            "Ensure they are genuinely distinct answers."
        )

    if candidate.get("answer") not in {"A", "B", "C", "D"}:
        errors.append("The correct answer is missing or malformed.")

    return errors


# ============================================================
# REPETITION CHECKS
# ============================================================

def check_repetition(candidate, previous_stems, comparison_bank):
    stem = candidate.get("stem", "")

    if not isinstance(stem, str) or not stem.strip():
        return ["The stem is empty."]

    normalized = normalize_text(stem)

    for item in comparison_bank:
        if not isinstance(item, dict):
            continue

        old_stem = item.get("stem", "")

        if (
            isinstance(old_stem, str)
            and normalize_text(old_stem) == normalized
        ):
            return ["The question exactly duplicates an existing stem."]

    for item in comparison_bank:
        if not isinstance(item, dict):
            continue

        old_stem = item.get("stem", "")

        if not isinstance(old_stem, str) or not old_stem.strip():
            continue

        similarity = SequenceMatcher(
            None, normalized, normalize_text(old_stem)
        ).ratio()

        if similarity >= MAX_STEM_SIMILARITY:
            return ["The question is too similar to an existing question."]

    new_opening = opening(stem)

    for old_stem in previous_stems[-OPENING_CHECK_LAST:]:
        if new_opening and opening(old_stem) == new_opening:
            return [
                "The stem repeats the opening pattern of a recent question."
            ]

    return []


# ============================================================
# JAVA DEFAULT-VALUE CHECKS
# ============================================================

DEFAULT_VALUES = {
    "byte": {"0"},
    "short": {"0"},
    "int": {"0"},
    "long": {"0", "0l"},
    "float": {"0.0", "0.0f", "0f"},
    "double": {"0.0", "0.0d", "0d"},
    "boolean": {"false"},
    "char": {"'\\u0000'", "'\\0'"},
    "String": {"null"},
    "Integer": {"null"},
    "Long": {"null"},
    "Double": {"null"},
    "Float": {"null"},
    "Boolean": {"null"},
    "Character": {"null"},
    "Object": {"null"},
}

NEGATION = (
    r"\b(not|never|no|cannot|can't|doesn't|does not|isn't|aren't|"
    r"without|rather than|instead of)\b"
)


def extract_declared_type(stem):
    for type_name in sorted(DEFAULT_VALUES, key=len, reverse=True):
        if re.search(rf"\b{re.escape(type_name)}\b", stem):
            return type_name
    return None


def option_is_default_value(option, type_name):
    value = str(option).strip()

    if "=" in value:
        value = value.split("=", 1)[1].strip()

    value = compact_code(value.rstrip(";").strip())
    return value in DEFAULT_VALUES.get(type_name, set())


def check_java_facts(candidate):
    errors = []

    stem = candidate["stem"]
    explanation = candidate["explanation"]
    options = candidate["options"]
    answer = candidate["answer"]

    stem_lower = stem.lower()

    if "default" in stem_lower:
        field_context = any(
            phrase in stem_lower
            for phrase in (
                "field", "instance variable", "static variable",
                "static field", "array element", "array elements"
            )
        )

        if "local variable" in stem_lower:
            errors.append(
                "Local variables do not receive automatic default values."
            )
        elif not field_context:
            errors.append(
                "Default-value questions must explicitly identify a field "
                "or array element."
            )

        type_name = extract_declared_type(stem)

        if type_name:
            answer_text = str(options[answer])

            # Only judge short value-style answers (null, 0, false,
            # "String s = null;"), not full-sentence answers.
            if len(compact_code(answer_text)) <= 25:
                if not option_is_default_value(answer_text, type_name):
                    errors.append(
                        f"The marked answer does not match the Java "
                        f"default value for {type_name} fields."
                    )

                matches = [
                    label for label in "ABCD"
                    if option_is_default_value(options[label], type_name)
                ]

                if len(matches) > 1:
                    errors.append(
                        f"More than one option matches the default value "
                        f"for {type_name}."
                    )

    # Explanation checks run clause by clause, so a correct explanation
    # such as "defaults to null, not an empty string" is not rejected.
    clauses = [
        clause.lower()
        for clause in re.split(
            r"(?<=[.!?])\s+|[,;]\s*|\b(?:but|whereas|while)\b",
            explanation
        )
    ]

    for clause in clauses:
        if (
            "default" in clause
            and re.search(r"empty string|[\"']{2}", clause)
            and not re.search(NEGATION, clause)
        ):
            errors.append(
                "A String field defaults to null, not an empty string."
            )
            break

    for clause in clauses:
        if (
            "local variable" in clause
            and re.search(
                r"(automatically initiali[sz]ed|default value is|"
                r"defaults? to)",
                clause
            )
            and not re.search(NEGATION, clause)
        ):
            errors.append(
                "The explanation may incorrectly claim that local "
                "variables are automatically initialized."
            )
            break

    return errors


# ============================================================
# CHECK COMMON JAVA SYNTAX ERRORS IN THE MARKED ANSWER
# ============================================================

INVALID_CORRECT_OPTION_PATTERNS = [
    (
        r"\bstring\s+\w+",
        "Java uses String with a capital S."
    ),
    (
        r"\bchar\s+\w+\s*=\s*\"",
        "A char literal uses single quotes."
    ),
    (
        r"\bString\s+\w+\s*=\s*'",
        "A String literal uses double quotes."
    ),
    (
        r"\bint\s+\w+\s*=\s*\"",
        "An int cannot be assigned a String literal."
    ),
    (
        r"\bint\s+\w+\s*=\s*\d+\.\d+\s*;",
        "An int cannot be assigned a decimal literal directly."
    ),
    (
        r"\bboolean\s+\w+\s*=\s*(?:\d|\"|'|null)",
        "A boolean variable must be assigned true or false."
    ),
    (
        r"\bfloat\s+\w+\s*=\s*\d+\.\d+\s*;",
        "A decimal float literal normally requires an f or F suffix."
    ),
    (
        r"\b(?:int|double|long|float|short|byte|char|boolean|String)\s+"
        r"(?:class|int|double|long|float|short|byte|char|boolean|new|for|"
        r"if|while|static|void|public|private|return)\s*[=;]",
        "A reserved Java keyword cannot be used as a variable name."
    ),
    (
        r"\b(?:int|double|long|float|short|byte|char|boolean|String)\s+"
        r"\d\w*\s*[=;]",
        "A Java variable name cannot start with a digit."
    ),
]


def check_correct_option_syntax(candidate):
    # If the stem asks for the line that causes an error (or the invalid
    # option), the marked answer is SUPPOSED to be bad Java.
    if asks_for_invalid_option(candidate["stem"]):
        return []

    errors = []
    correct = candidate["options"][candidate["answer"]]

    for pattern, explanation in INVALID_CORRECT_OPTION_PATTERNS:
        if re.search(pattern, correct):
            errors.append(
                f"The marked correct option {correct!r} may be invalid: "
                f"{explanation}"
            )

    if re.match(
        r"^\s*(?:int|double|long|float|short|byte|char|boolean|String)"
        r"\s+\w+\s*=\s*[^;]+$",
        correct
    ):
        errors.append(
            "The marked correct declaration appears to be missing "
            "a semicolon."
        )

    return errors


# ============================================================
# CONCEPT ALIGNMENT
# ============================================================

def check_concept_alignment(candidate, target_concept):
    errors = []
    text = candidate.get("stem", "").lower()

    if target_concept == "default_values":
        mentions_default = any(term in text for term in (
            "default value", "default values", "defaults to",
            "default for", "automatically initialized",
            "automatically initialised", "initialized by default",
            "initialised by default"
        ))
        field_context = any(term in text for term in (
            "field", "instance variable", "static variable",
            "static field", "array element", "array elements"
        ))

        if not mentions_default:
            errors.append(
                "Concept mismatch: the stem does not ask about a default value."
            )

        if not field_context:
            errors.append(
                "A Java default-value question must identify a field, "
                "static/instance variable, or array element."
            )

        if "local variable" in text:
            errors.append(
                "Local variables do not receive automatic default values."
            )

    elif target_concept == "naming":
        if not any(term in text for term in (
            "identifier", "variable name", "name of", "named", "naming",
            "keyword", "start with a digit", "valid name"
        )):
            errors.append(
                "The stem does not clearly test Java naming rules."
            )

    elif target_concept == "scope":
        if not any(term in text for term in (
            "scope", "visible", "visibility", "inside the method",
            "outside the method", "block", "loop", "access the variable",
            "accessible"
        )):
            errors.append(
                "The stem does not clearly test variable scope or visibility."
            )

    elif target_concept == "initialization":
        if not any(term in text for term in (
            "initializ", "assign", "reassign", "before it is read",
            "before reading", "uninitialized", "uninitialised", "value to",
            "compile-time error", "compile time error",
            "result of the following code", "fixes the error",
            "causes a compile-time error"
        )):
            errors.append(
                "The stem does not clearly test variable initialization."
            )

    elif target_concept == "declaration":
        if not any(term in text for term in (
            "declar", "statement", "variable", "type and name",
            "semicolon", "line", "code", "compile"
        )):
            errors.append(
                "The stem does not clearly test variable declaration."
            )

    elif target_concept == "variable_types":
        if not any(term in text for term in (
            "type", "string", "char", "boolean", "int", "double",
            "float", "compatible", "literal", "assign"
        )):
            errors.append(
                "The stem does not clearly test Java types or compatibility."
            )

    return errors


# ============================================================
# ANSWER AND EXPLANATION CONSISTENCY
# ============================================================

def check_answer_explanation_consistency(candidate):
    errors = []
    options = candidate.get("options", {})
    answer = candidate.get("answer")
    explanation = candidate.get("explanation", "")

    if not isinstance(options, dict) or answer not in options:
        return errors

    correct = options[answer]
    explanation_lower = explanation.lower()

    # These two checks assume the marked answer should be VALID Java,
    # so they are skipped for "which line causes an error" questions.
    if not asks_for_invalid_option(candidate.get("stem", "")):
        if re.search(r"\bString\s+\w+\s*=\s*'[^']*'", correct):
            errors.append(
                "The marked answer assigns a single-quoted literal to String."
            )

        if re.search(r'\bchar\s+\w+\s*=\s*"[^"]*"', correct):
            errors.append(
                "The marked answer assigns a double-quoted literal to char."
            )

    if (
        re.search(r'\bString\s+\w+\s*=\s*"[^"]*"', correct)
        and any(phrase in explanation_lower for phrase in (
            "string literals use single quotes",
            "string uses single quotes",
            "string literal uses single quotes"
        ))
    ):
        errors.append(
            "The explanation contradicts Java String literal syntax."
        )

    other_option_claims = re.findall(
        r"\boption\s+([ABCD])\s+(?:is|would be)\s+"
        r"(?:the\s+)?correct\b",
        explanation,
        flags=re.IGNORECASE
    )

    if any(label.upper() != answer for label in other_option_claims):
        errors.append(
            "The explanation appears to identify a different correct option."
        )

    return errors


def check_initialization_ambiguity(candidate, target_concept):
    """Reject known ambiguous wording in initialization questions."""
    if target_concept != "initialization":
        return []

    stem = candidate.get("stem", "").lower()
    options = candidate.get("options", {})

    # Broad true/false questions about local-variable initialization
    # can accidentally allow multiple correct answers.
    normalized_stem = " ".join(stem.split())

    broad_patterns = (
        "which statement about local variable initialization is true",
        "which statement about initialization of local variables is correct",
        "which statement about variable initialization is true",
        "which statement about initialization is correct",
    )

    if any(pattern in normalized_stem for pattern in broad_patterns):
        return [
            "Potentially ambiguous initialization question: use a "
            "specific code example or ask about one clearly defined rule."
        ]

    # Reject a known incorrect claim if it is used as the explanation.
    explanation = candidate.get("explanation", "").lower()

    if (
        "local variable" in explanation
        and "default value" in explanation
        and (
            "receives a default value" in explanation
            or "automatically receives" in explanation
        )
        and "not" not in explanation
    ):
        return [
            "Potentially incorrect explanation: local variables do not "
            "receive automatic default values."
        ]

    return []



def run_local_checks(
    candidate, target_concept, previous_stems, comparison_bank
):
    errors = check_structure(candidate, target_concept)

    if errors:
        return errors

    errors.extend(
        check_repetition(candidate, previous_stems, comparison_bank)
    )
    errors.extend(check_concept_alignment(candidate, target_concept))
    errors.extend(
        check_initialization_ambiguity(candidate, target_concept)
    )
    errors.extend(check_java_facts(candidate))
    errors.extend(check_correct_option_syntax(candidate))
    errors.extend(check_answer_explanation_consistency(candidate))

    return errors


# ============================================================
# LOCAL QWEN REQUEST
# ============================================================

def extract_json_array(message):
    message = message.strip()

    if message.startswith("```"):
        lines = message.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        message = "\n".join(lines).strip()

    start = message.find("[")
    end = message.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found in the model response.")

    return message[start:end + 1]


def ask_qwen(prompt, temperature=BASE_TEMPERATURE):
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }

    request = urllib.request.Request(
        SERVER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request, timeout=REQUEST_TIMEOUT
        ) as response:
            result = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Qwen HTTP {exc.code}: {details}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Cannot reach Qwen. Ensure llama-server.exe is running "
            "at http://127.0.0.1:8080."
        ) from exc

    except TimeoutError as exc:
        raise RuntimeError("The Qwen request timed out.") from exc

    try:
        message = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            "Unexpected response structure from Qwen."
        ) from exc

    try:
        questions = json.loads(extract_json_array(message))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Qwen returned invalid JSON: {exc}") from exc

    if not isinstance(questions, list):
        raise ValueError("Qwen must return a JSON array.")

    # Build options A-D (shuffled) from "correct" and "wrong".
    return [convert_candidate(question) for question in questions]


# ============================================================
# PROMPT BUILDER
# ============================================================

def build_prompt(
    module_name,
    target_concept,
    previous_stems,
    previous_errors,
    question_number,
    module_no,
    style,
):
    concept_guide = CONCEPT_GUIDE.get(
        target_concept, GENERIC_CONCEPT_GUIDE
    )

    recent_stems = previous_stems[-PROMPT_STEM_LIMIT:]

    errors_text = (
        "\n".join(f"- {error}" for error in previous_errors)
        if previous_errors
        else "No previous validation errors."
    )


    if target_concept == "default_values":
        concept_rule = (
            "Ask ONLY about automatic default values for an explicitly "
            "identified Java field or array element. State that context "
            "in the stem. Do not substitute a normal declaration question."
        )

    elif target_concept == "initialization":
        concept_rule = (
            "Test exactly one specific Java initialization rule: "
            "declaring a local variable without assigning a value; "
            "assigning a value after declaration but before first use; "
            "reassigning an already initialized variable; or reading a "
            "local variable before assigning a value. Prefer a short, "
            "self-contained Java code example when suitable. Do not ask "
            "broad questions such as 'Which statement about variable "
            "initialization is true?' Do not ask merely which declaration "
            "is valid Java. Local variables do not receive automatic "
            "default values and must be assigned before they are read. "
            "Instance and static fields receive default values. All four "
            "answer options must be distinct, and exactly one must satisfy "
            "the complete question. Ensure the explanation accurately "
            "explains the correct answer and Java rule."
        )


    elif target_concept == "declaration":
        if question_number % 2 == 1:
            concept_rule = (
                "Use question form A: ask which declaration compiles successfully in Java. "
                "The correct answer must be one valid declaration. All three wrong answers must have definite compile-time errors. "
                "Possible errors include assigning a String literal to int, using single quotes for a String literal, or assigning a double-quoted String to char. "
                "Use different variable names and values in each question. "
                "Check every option independently. Exactly one option must compile."
            )
        else:
            concept_rule = (
                "Use question form B: ask which declaration causes a compile-time error. "
                "The correct answer must be one invalid declaration, and all three wrong answers must compile successfully. "
                "For example, a String declaration using single quotes is invalid. Valid alternatives can include int count = 10;, double price = 9.99;, and char grade = 'A';. "
                "Do not use int x = 'a'; as an invalid declaration because it is valid Java. "
                "Check every option independently. Exactly one option must fail compilation. "
                "Do not use the generic stem 'Which declaration is valid Java?' for this question form."
            )

    else:
        concept_rule = (
            "Stay tightly focused on the requested concept. Do not substitute "
            "a nearby Java topic."
        )


    return f"""
/no_think

Create exactly ONE new beginner-level Java multiple-choice question.

MODULE: {module_name}
MODULE NUMBER: {module_no}
QUESTION NUMBER: {question_number}
TARGET CONCEPT TAG: {target_concept}

CONCEPT GUIDE:
{concept_guide}

CONCEPT RULE:
{concept_rule}

QUESTION STYLE:
{style}

RECENT QUESTION STEMS — DO NOT REPEAT:
{json.dumps(recent_stems, ensure_ascii=False)}

PREVIOUS VALIDATION ERRORS — FIX THEM:
{errors_text}


REQUIREMENTS:
1. Return exactly one question object inside a JSON array.
2. Include exactly these fields:
   stem, concept_tag, correct, wrong, explanation.
   Do NOT write options A-D or an answer letter. The program builds
   the options from "correct" and "wrong".
3. Use the exact concept tag: {target_concept}
4. "correct" must be the ONLY answer that satisfies the complete stem.
5. "wrong" must contain exactly three distinct answers. Each wrong answer
   must be demonstrably incorrect for the specific question asked.
6. CRITICAL: Before returning the question, mentally test ALL FOUR answers
   against the exact wording of the stem. There must be exactly ONE answer
   that satisfies the stem. If two or more answers satisfy it, rewrite the
   question or its answers before responding.
7. For "Which declaration is valid Java?" questions, do NOT provide several
   ordinary valid declarations. Make exactly one declaration compile and
   make the other three contain clear, genuine Java errors.
8. For "Which line causes a compile-time error?" questions, provide enough
   code context to establish the error. Make exactly one option cause the
   stated error and ensure the other three options do not cause that error.
   Do not ask which line is wrong if all options are valid in isolation.
9. Avoid ambiguous questions. Include the necessary code, type, variable
   name, and context so a beginner can determine one answer.
10. For Java naming questions, ensure exactly one option satisfies or
    violates the stated identifier rule, as requested. Remember that names
    such as userName and userName2 can both be valid identifiers.
11. For default-value questions, identify the field type and whether it is
    an instance field, static field, or array element. Do not confuse field
    defaults with local-variable initialization.
12. "correct" and all three "wrong" answers must differ in meaning, not just
    whitespace or formatting. Never repeat an option.
13. If the stem names a variable, type, literal, or code fragment, use
    those details consistently throughout the answers and explanation.
14. The explanation must contain one or two accurate sentences explaining
    why the correct answer satisfies the stem. Do not mention option letters
    or positions.
15. Do not copy or lightly modify recent questions. Avoid repeating their
    opening words.
16. Check all answers against Java rules. Do not invent a Java rule.
17. Return valid JSON only, without Markdown or commentary.
18. For String literals use double quotes; for char literals use single
    quotes.
19. If you cannot construct one unambiguous correct answer and three
    demonstrably incorrect answers, create a simpler question on the same
    concept instead.

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
  {{
    "stem": "Write a new question here",
    "concept_tag": "{target_concept}",
    "correct": "The one answer that satisfies the stem",
    "wrong": [
      "First incorrect answer",
      "Second incorrect answer",
      "Third incorrect answer"
    ],
    "explanation": "Explain why the correct answer satisfies the stem."
  }}
]

The text above is a schema illustration, not a question to copy.
Create new content focused on the requested concept.
Return exactly one question inside a JSON array.
"""


# ============================================================
# GENERATE ONE BATCH

def build_declaration_fallback(question_number):
    """Build varied declaration questions using explicit Java rules."""
    types = [
        ("int", "quizInt", 'int {v} = 42;',
         ['int {v} = "forty-two";', 'int {v} = true;', 'int {v} = 4.5;'],
         "An int accepts an integer-compatible value, not a String, boolean, or double."),

        ("String", "quizString", 'String {v} = "Ada";',
         ["String {v} = 'Ada';", "String {v} = 42;", "String {v} = false;"],
         "A String literal uses double quotes; an integer, boolean, or multi-character single-quoted literal is not a String."),

        ("char", "quizChar", "char {v} = 'K';",
         ['char {v} = "K";', "char {v} = 'KL';", "char {v} = false;"],
         "A char holds one character in single quotes; a String, multi-character literal, or boolean is incompatible."),

        ("boolean", "quizFlag", "boolean {v} = true;",
         ['boolean {v} = "true";', "boolean {v} = 1;", "boolean {v} = null;"],
         "A primitive boolean accepts true or false, not a String, integer, or null."),

        ("float", "quizRate", "float {v} = 2.5f;",
         ["float {v} = 2.5;", 'float {v} = "2.5";', "float {v} = true;"],
         "A decimal literal assigned directly to float needs an f or F suffix; String and boolean values are incompatible."),

        ("long", "quizTotal", "long {v} = 42L;",
         ['long {v} = "42";', "long {v} = false;", "long {v} = 3.5;"],
         "A long accepts an integer-compatible value; a String, boolean, or double literal cannot be assigned directly."),

        ("double", "quizPrice", "double {v} = 19.75;",
         ['double {v} = "19.75";', "double {v} = false;", "double {v} = null;"],
         "A double accepts a numeric decimal literal, not a String, boolean, or null.")
    ]

    kind, prefix, correct_template, wrong_templates, explanation = (
        types[(question_number - 1) % len(types)]
    )
    variable = f"{prefix}{random.randint(10000, 99999)}"
    correct = correct_template.format(v=variable)
    wrong = [item.format(v=variable) for item in wrong_templates]

    stems = [
        "Which Java declaration correctly initializes the {kind} variable {v}?",
        "A Java program needs {v} to have type {kind}. Which declaration compiles?",
        "Select the declaration with a compatible initializer for {v}, whose type is {kind}.",
        "Identify the legal initializer for {v} by selecting the declaration using Java type {kind}.",
        "Choose the Java declaration accepted by the compiler for {v} of type {kind}.",
        "Given a variable named {v} with type {kind}, choose a declaration that compiles.",
        "To initialize {v} as a {kind}, which Java statement is valid?",
    ]

    stem = stems[(question_number - 1) % len(stems)].format(
        kind=kind, v=variable
    )

    choices = [(correct, True)] + [(item, False) for item in wrong]
    random.shuffle(choices)

    options = {}
    answer = None
    for label, (text, is_correct) in zip("ABCD", choices):
        options[label] = text
        if is_correct:
            answer = label

    return {
        "stem": stem,
        "concept_tag": "declaration",
        "explanation": explanation,
        "options": options,
        "answer": answer,
    }



# ============================================================

def show_rejected(candidate):
    if DEBUG_PRINT_REJECTED:
        print(json.dumps(candidate, indent=2, ensure_ascii=False))


def generate_batch(
    module_name,
    weak_concepts,
    batch_count,
    previous_stems,
    batch_number,
    static_bank,
    accepted_questions,
    module_no,
):
    accepted_batch = []

    for item_number in range(1, batch_count + 1):
        accepted_question = None
        last_errors = []

        question_number = (
            len(accepted_questions) + len(accepted_batch) + 1
        )

        target_concept = weak_concepts[
            (question_number - 1) % len(weak_concepts)
        ]

        for attempt in range(1, MAX_RETRIES + 1):
            temperature = min(
                BASE_TEMPERATURE + TEMPERATURE_STEP * (attempt - 1),
                MAX_TEMPERATURE,
            )

            style = QUESTION_STYLES[
                (question_number + attempt - 2) % len(QUESTION_STYLES)
            ]

            print(
                f"\nQuestion {question_number} [{target_concept}] "
                f"— attempt {attempt}/{MAX_RETRIES}, "
                f"temperature={temperature:.1f}"
            )

            prompt = build_prompt(
                module_name=module_name,
                target_concept=target_concept,
                previous_stems=previous_stems,
                previous_errors=last_errors,
                question_number=question_number,
                module_no=module_no,
                style=style,
            )

            try:
                questions = ask_qwen(prompt, temperature=temperature)

                if len(questions) != 1:
                    raise ValueError(
                        f"Expected one question; received {len(questions)}."
                    )

                candidate = questions[0]

                if not isinstance(candidate, dict):
                    raise ValueError(
                        "The generated question is not a JSON object."
                    )

                print("\nGenerated stem:")
                print(candidate.get("stem", "<missing>"))

                print("\nGenerated options:")
                options = candidate.get("options", {})

                if isinstance(options, dict):
                    for label in "ABCD":
                        print(
                            f"  {label}: "
                            f"{options.get(label, '<missing>')!r}"
                        )

                print(f"Marked answer: {candidate.get('answer')}")

                comparison_bank = (
                    static_bank + accepted_questions + accepted_batch
                )

                # Check 1: existing local rules.
                local_errors = run_local_checks(
                    candidate,
                    target_concept,
                    previous_stems,
                    comparison_bank,
                )

                if local_errors:
                    last_errors = local_errors
                    print("\nRejected by local checks:")

                    for error in local_errors:
                        print(f"  - {error}")

                    show_rejected(candidate)
                    continue

                # Check 2: actual Java compiler for supported questions,
                # plus explicit stem requirements such as name/type/value.
                java_errors = check_unique_answer(candidate)

                if java_errors:
                    last_errors = java_errors
                    print("\nRejected by java_answer_checker.py:")

                    for error in java_errors:
                        print(f"  - {error}")

                    show_rejected(candidate)
                    continue

                # Check 3: existing project validator.
                validated, validator_errors = validate_generated_questions(
                    questions=[candidate],
                    module_no=module_no,
                    allowed_concepts=weak_concepts,
                    existing_questions=comparison_bank,
                    required_count=1,
                    near_duplicate_threshold=NEAR_DUPLICATE_THRESHOLD,
                )

                if validator_errors:
                    last_errors = validator_errors
                    print("\nRejected by question_validator.py:")

                    for error in validator_errors:
                        print(f"  - {error}")

                    show_rejected(candidate)
                    continue

                if not validated:
                    last_errors = [
                        "The project validator returned no accepted question."
                    ]
                    print("\nRejected: validator returned no accepted question.")
                    continue

                accepted_question = validated[0]

                print(
                    "\nPassed local checks, Java answer checks, "
                    "and question_validator.py."
                )
                break

            except (ValueError, RuntimeError) as exc:
                last_errors = [str(exc)]
                print(f"\nAttempt failed: {exc}")

        if accepted_question is None and target_concept == "declaration":
            fallback = build_declaration_fallback(question_number)
            comparison_bank = static_bank + accepted_questions + accepted_batch

            fallback_errors = run_local_checks(
                fallback, target_concept, previous_stems, comparison_bank
            )

            if not fallback_errors:
                fallback_errors = check_unique_answer(fallback)

            if not fallback_errors:
                validated, fallback_errors = validate_generated_questions(
                    questions=[fallback],
                    module_no=module_no,
                    allowed_concepts=weak_concepts,
                    existing_questions=comparison_bank,
                    required_count=1,
                    near_duplicate_threshold=NEAR_DUPLICATE_THRESHOLD,
                )

                if validated and not fallback_errors:
                    accepted_question = validated[0]
                    print(
                        "\\nQwen retries failed; a rule-based declaration "
                        "question passed all validators."
                    )

            if accepted_question is None:
                print("Declaration fallback was also rejected:")
                for error in fallback_errors:
                    print("  -", error)

        if accepted_question is None:
            raise RuntimeError(
                f"Unable to generate a valid question after {MAX_RETRIES} "
                f"attempts. Batch {batch_number}, item {item_number}. "
                f"Last errors: {'; '.join(last_errors)}"
            )

        accepted_batch.append(accepted_question)
        previous_stems.append(accepted_question["stem"])

    return accepted_batch


# ============================================================
# MAIN GENERATION FUNCTION
# ============================================================

def generate_questions(
    module_name,
    weak_concepts,
    count=30,
    module_no=1,
):
    if (
        not isinstance(count, int)
        or isinstance(count, bool)
        or count < 1
    ):
        raise ValueError("count must be a positive integer.")

    if not isinstance(module_name, str) or not module_name.strip():
        raise ValueError("module_name must be non-empty text.")

    if not isinstance(weak_concepts, list) or not weak_concepts:
        raise ValueError("weak_concepts must be a non-empty list.")

    if any(
        not isinstance(concept, str) or not concept.strip()
        for concept in weak_concepts
    ):
        raise ValueError("Every concept tag must be non-empty text.")

    if len(set(weak_concepts)) != len(weak_concepts):
        raise ValueError("Duplicate concept tags were supplied.")

    if (
        not isinstance(module_no, int)
        or isinstance(module_no, bool)
        or module_no < 1
    ):
        raise ValueError("module_no must be a positive integer.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    static_bank = load_static_bank()

    module_bank = [
        item for item in static_bank
        if isinstance(item, dict)
        and item.get("module_no") == module_no
    ]

    print(
        f"Static questions belonging to module {module_no}: "
        f"{len(module_bank)}"
    )

    if not module_bank:
        print(
            "WARNING: no static question has module_no == "
            f"{module_no}, so new questions are not compared with "
            "the static bank. Check the 'module_no' field in "
            "static_questions.json."
        )

    all_questions = []
    previous_stems = []
    run_stamp = timestamp()

    print(f"\nModule: {module_name}")
    print(f"Module number: {module_no}")
    print(f"Requested questions: {count}")

    try:
        while len(all_questions) < count:
            remaining = count - len(all_questions)
            batch_count = min(BATCH_SIZE, remaining)

            batch = generate_batch(
                module_name=module_name,
                weak_concepts=weak_concepts,
                batch_count=batch_count,
                previous_stems=previous_stems,
                batch_number=len(all_questions) + 1,
                static_bank=module_bank,
                accepted_questions=all_questions,
                module_no=module_no,
            )

            all_questions.extend(batch)
            print(f"\nProgress: {len(all_questions)}/{count}")


    except RuntimeError:
        if all_questions:
            partial_name = (
                f"partial_{module_name.lower().replace(' ', '_')}_"
                f"{run_stamp}.json"
            )
            save_questions(all_questions, partial_name)
            print("Partial results have been preserved.")
            print(
                "Returning valid questions generated before the failure."
            )
            return all_questions

        raise


    output_name = (
        f"{module_name.lower().replace(' ', '_')}_"
        f"validated_{run_stamp}.json"
    )

    save_questions(all_questions, output_name)

    print("\nGeneration completed.")
    print(
        "Reminder: automated validation reduces errors but does not prove "
        "that every question and explanation is semantically correct. "
        "Review questions before using them in the learning system."
    )

    return all_questions


# ============================================================
# TEST RUN
# ============================================================

if __name__ == "__main__":
    concepts = [
        "declaration",
        "initialization",
        "naming",
        "default_values",
        "variable_types",
        "scope",
    ]

    generated = generate_questions(
        module_name="Variables",
        weak_concepts=concepts,
        count=5,
        module_no=1,
    )

    print(f"\nReturned questions: {len(generated)}")
