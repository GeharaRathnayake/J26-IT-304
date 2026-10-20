
import re
from difflib import SequenceMatcher

VALID_OPTIONS = {"A", "B", "C", "D"}

JAVA_PRIMITIVE_DEFAULTS = {
    "byte": {"0"},
    "short": {"0"},
    "int": {"0"},
    "long": {"0", "0l"},
    "float": {"0.0", "0.0f", "0f"},
    "double": {"0.0", "0.0d", "0d"},
    "boolean": {"false"},
    "char": {"'\\u0000'", "'\\0'"},
}

JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private",
    "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "true", "false",
    "null", "var", "record", "sealed", "permits", "yield"
}


def normalize_text(value):
    """Normalize prose for comparisons."""
    return " ".join(str(value).lower().split())


def normalize_code(value):
    """Normalize formatting differences without changing letter case."""
    return re.sub(r"\s+", "", str(value).strip())


def similarity(first, second):
    """Return a text similarity score between 0 and 1."""
    return SequenceMatcher(
        None,
        normalize_text(first),
        normalize_text(second)
    ).ratio()


def is_field_default_question(stem):
    """Recognize questions that explicitly ask about default values."""
    text = normalize_text(stem)
    return "default value" in text or "default values" in text


def _options_are_valid(options):
    return (
        isinstance(options, dict)
        and set(options.keys()) == VALID_OPTIONS
        and all(
            isinstance(options[k], str) and options[k].strip()
            for k in "ABCD"
        )
    )


def _simple_declaration_validity(option):
    """
    Check a deliberately small subset of simple Java declarations.

    Returns:
        True  - the declaration is valid within the supported subset
        False - the declaration is invalid within the supported subset
        None  - the option is outside the supported subset

    This is not a Java compiler or a complete Java semantic checker.
    """
    code = str(option).strip().strip("`").strip()

    match = re.fullmatch(
        r"(byte|short|int|long|float|double|boolean|char|String)\s+"
        r"([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(.*?)\s*;",
        code
    )

    if not match:
        return None

    type_name, name, value = match.groups()

    if name in JAVA_KEYWORDS:
        return False

    value = value.strip()

    # Character declarations
    if type_name == "char":
        char_literal_pattern = (
            r"'(?:[^'\\]|\\[btnfr\"'\\]|"
            r"\\u[0-9a-fA-F]{4}|\\[0-7]{1,3})'"
        )

        if re.fullmatch(char_literal_pattern, value):
            inner = value[1:-1]

            if inner.startswith("\\"):
                return True

            return len(inner) == 1

        # Java permits constant integer values in the char range
        # to be narrowed to char in an assignment context.
        if re.fullmatch(r"-?\d+", value):
            return 0 <= int(value) <= 65535

        return False

    # String declarations
    if type_name == "String":
        return bool(
            re.fullmatch(r'"(?:[^"\\]|\\.)*"', value)
            or value == "null"
        )

    # Boolean declarations
    if type_name == "boolean":
        return value in {"true", "false"}

    # Integer declarations
    if type_name in {"byte", "short", "int", "long"}:
        if not re.fullmatch(r"-?\d+[lL]?", value):
            return False

        number = int(value.rstrip("lL"))

        ranges = {
            "byte": (-128, 127),
            "short": (-32768, 32767),
            "int": (-2147483648, 2147483647),
            "long": (
                -9223372036854775808,
                9223372036854775807
            ),
        }

        low, high = ranges[type_name]

        if type_name == "long":
            return low <= number <= high

        # An unsuffixed integer constant can be narrowed to byte,
        # short, or int when its value is in range.
        if not value.lower().endswith("l"):
            return low <= number <= high

        return False

    # Floating-point declarations
    if type_name in {"float", "double"}:
        if not re.fullmatch(
            r"-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?[fFdD]?",
            value
        ):
            return False

        suffix = value[-1:] if value[-1:] in "fFdD" else ""

        if type_name == "float":
            return suffix.lower() == "f"

        return suffix.lower() in {"", "d"}

    return None


def _concept_alignment_errors(stem, concept):
    """Catch obvious mismatches between common concepts and question stems."""
    text = normalize_text(stem)
    errors = []

    cues = {
        "declaration": (
            "declaration", "declare", "declares", "declaring",
            "variable named", "variable called"
        ),
        "initialization": (
            "initialize", "initialise", "initialization", "initialisation",
            "initializes", "initialises", "assigned", "assign a value",
            "before it is read", "before reading"
        ),
        "naming": (
            "identifier", "variable name", "valid name", "naming rules",
            "name is valid", "name is invalid", "camelcase"
        ),
        "default_values": (
            "default value", "default values", "automatically initialized",
            "automatically initialised"
        ),
        "variable_types": (
            "data type", "variable type", "type of", "type can store",
            "literal", "string literal", "character literal", "char literal"
        ),
        "scope": (
            "scope", "visible", "visibility", "accessible", "block",
            "outside the loop", "outside the method"
        ),
    }

    if concept in cues and not any(
        cue in text for cue in cues[concept]
    ):
        if concept in {"default_values", "scope", "naming"}:
            errors.append(
                f"Concept mismatch: target is {concept!r}, but the stem "
                "does not contain a clear cue for that concept."
            )

    if concept == "default_values" and "default" in text:
        has_field_context = any(
            phrase in text
            for phrase in (
                "field", "instance variable", "static variable",
                "static field", "array element"
            )
        )

        if "local variable" in text:
            errors.append(
                "Java local variables do not receive automatic default values."
            )
        elif not has_field_context:
            errors.append(
                "A default-value question must explicitly identify a field "
                "or array element."
            )

    return errors


def _answer_explanation_consistency_errors(question):
    """Catch selected obvious contradictions between the answer and explanation."""
    # Error-identification questions may intentionally mark invalid
    # Java code as the correct answer.
    stem = normalize_text(question.get("stem", ""))

    if re.search(
        r"compile[- ]?time error|compilation error|\berrors?\b|"
        r"\b(?:does|do)(?:n't| not) compile|"
        r"\b(?:will|would|can|could)(?:n't| not) compile|"
        r"fails? to compile|\binvalid\b|\billegal\b|\bincorrect\b|"
        r"\bnot (?:a )?(?:valid|legal|allowed)\b",
        stem,
        flags=re.IGNORECASE,
    ):
        return []
    options = question.get("options", {})
    answer = question.get("answer")
    explanation = normalize_text(question.get("explanation", ""))

    if not _options_are_valid(options) or answer not in VALID_OPTIONS:
        return []

    correct_option = options[answer]
    errors = []

    if re.search(
        r"\bString\s+[A-Za-z_$]\w*\s*=\s*'",
        correct_option
    ):
        errors.append(
            "The marked answer assigns a single-quoted literal to String; "
            "Java String literals use double quotes."
        )

    if re.search(
        r'\bchar\s+[A-Za-z_$]\w*\s*=\s*"',
        correct_option
    ):
        errors.append(
            "The marked answer assigns a double-quoted literal to char; "
            "a char literal uses single quotes."
        )

    if (
        "double quote" in explanation
        and re.search(
            r"\bString\s+[A-Za-z_$]\w*\s*=\s*'",
            correct_option
        )
    ):
        errors.append(
            "The explanation says String requires double quotes, but the "
            "marked option uses single quotes."
        )

    return errors


def _char_literal_intent_errors(question):
    """
    Check whether a char question's requested character matches its answer.

    This handles explicit questions such as:
    "Which statement declares a char variable and initializes it to 'T'?"

    It also rejects an impossible request such as initializing a char
    variable to the multi-character value 'true'.
    """
    stem = question.get("stem", "")
    options = question.get("options", {})
    answer = question.get("answer")

    if not isinstance(stem, str):
        return []

    if not re.search(r"\bchar\b", stem, re.IGNORECASE):
        return []

    if not _options_are_valid(options) or answer not in VALID_OPTIONS:
        return []

    # Find an explicitly requested character, for example:
    # "initializes it to 'T'"
    match = re.search(
        r"\bchar\b.*?\bto\s*'([^']*)'",
        stem,
        re.IGNORECASE
    )

    if not match:
        return []

    expected = match.group(1)

    valid_escape = bool(
        re.fullmatch(
            r"\\(?:[btnfr\"'\\]|u[0-9a-fA-F]{4}|[0-7]{1,3})",
            expected
        )
    )

    if len(expected) != 1 and not valid_escape:
        return [
            f"The stem requests {expected!r} as a char value, but a Java "
            "char literal must represent one character or a valid escape."
        ]

    correct_option = options[answer]

    option_match = re.fullmatch(
        r"\s*char\s+[A-Za-z_$][A-Za-z0-9_$]*\s*=\s*"
        r"'([^']*)'\s*;\s*",
        correct_option
    )

    if option_match:
        actual = option_match.group(1)

        if actual != expected:
            return [
                f"The stem requests the character {expected!r}, but the "
                f"marked answer initializes the variable with {actual!r}."
            ]

    return []


def _single_correct_answer_errors(question):
    """
    Check simple declaration questions when all four options are understood
    by the limited declaration checker.
    """
    stem = normalize_text(question.get("stem", ""))
    options = question.get("options", {})
    answer = question.get("answer")

    if not _options_are_valid(options) or answer not in VALID_OPTIONS:
        return []

    asks_for_valid = any(
        phrase in stem
        for phrase in (
            "which statement is valid",
            "which of the following is valid",
            "which statement correctly",
            "which declaration is valid",
            "valid declaration",
            "valid initialization",
            "valid initialisation",
        )
    )

    if not asks_for_valid:
        return []

    recognized = {
        label: _simple_declaration_validity(options[label])
        for label in "ABCD"
    }

    # Only enforce uniqueness if every option belongs to the subset
    # that this helper can evaluate.
    if all(value is not None for value in recognized.values()):
        valid_labels = [
            label
            for label, is_valid in recognized.items()
            if is_valid
        ]

        if len(valid_labels) != 1:
            return [
                "The simple-declaration check found "
                f"{len(valid_labels)} valid options "
                f"({', '.join(valid_labels) or 'none'}); "
                "a single-answer MCQ must have exactly one correct option."
            ]

        if valid_labels[0] != answer:
            return [
                f"The simple-declaration check identifies option "
                f"{valid_labels[0]} as valid, but the answer key marks {answer}."
            ]

    return []


def validate_generated_questions(
    questions,
    module_no,
    allowed_concepts,
    existing_questions,
    required_count=30,
    near_duplicate_threshold=0.90
):
    """
    Validate MCQ structure, repetition, concepts and selected Java rules.

    This function does not compile Java and cannot prove the correctness
    of arbitrary questions. Human review and compiler-based tests may
    still be needed.
    """
    errors = []
    validated = []

    if not isinstance(questions, list):
        return [], ["Generated questions must be a list."]

    if len(questions) != required_count:
        errors.append(
            f"Expected {required_count} questions, received {len(questions)}."
        )

    allowed_concepts = set(allowed_concepts)

    existing_stems = []

    for item in existing_questions:
        if not isinstance(item, dict):
            continue

        stem = item.get("stem", "")

        if isinstance(stem, str) and stem.strip():
            existing_stems.append(stem)

    batch_stems = []

    for index, question in enumerate(questions, start=1):
        prefix = f"Question {index}:"
        question_errors = []

        if not isinstance(question, dict):
            errors.append(f"{prefix} must be a JSON object.")
            continue

        stem = question.get("stem")
        concept = question.get("concept_tag")
        options = question.get("options")
        answer = question.get("answer")
        explanation = question.get("explanation")

        # 1. Stem and repetition checks.
        if not isinstance(stem, str) or not stem.strip():
            question_errors.append("missing or empty stem")
            stem = ""
        else:
            normalized_stem = normalize_text(stem)

            if any(
                normalized_stem == normalize_text(old)
                for old in existing_stems
            ):
                question_errors.append(
                    "stem exactly duplicates a question in the comparison bank"
                )

            if any(
                normalized_stem == normalize_text(old)
                for old in batch_stems
            ):
                question_errors.append(
                    "stem exactly duplicates another generated question"
                )

            for old in existing_stems + batch_stems:
                if (
                    normalized_stem != normalize_text(old)
                    and similarity(stem, old) >= near_duplicate_threshold
                ):
                    question_errors.append(
                        "stem is very similar to an existing question; "
                        "review repetition"
                    )
                    break

            batch_stems.append(stem)

        # 2. Concept tag and alignment checks.
        if not isinstance(concept, str) or concept not in allowed_concepts:
            question_errors.append(
                f"concept_tag {concept!r} is not allowed"
            )
        elif isinstance(stem, str) and stem.strip():
            question_errors.extend(
                _concept_alignment_errors(stem, concept)
            )

        # 3. Option structure and duplicate checks.
        if not isinstance(options, dict):
            question_errors.append("options must be an object")
            options = {}
        elif set(options.keys()) != VALID_OPTIONS:
            question_errors.append(
                "options must contain exactly A, B, C and D"
            )
        else:
            option_values = []

            for label in "ABCD":
                value = options[label]

                if not isinstance(value, str) or not value.strip():
                    question_errors.append(
                        f"option {label} is empty or not text"
                    )
                else:
                    option_values.append(normalize_code(value))

            if (
                len(option_values) == 4
                and len(set(option_values)) != 4
            ):
                question_errors.append(
                    "answer options contain duplicate content"
                )

        # 4. Answer and explanation checks.
        if not isinstance(answer, str) or answer not in VALID_OPTIONS:
            question_errors.append("answer must be A, B, C or D")

        if not isinstance(explanation, str) or not explanation.strip():
            question_errors.append("missing or empty explanation")

        if (
            isinstance(stem, str)
            and isinstance(explanation, str)
            and isinstance(answer, str)
        ):
            question_errors.extend(
                _answer_explanation_consistency_errors(question)
            )
            question_errors.extend(
                _single_correct_answer_errors(question)
            )
            question_errors.extend(
                _char_literal_intent_errors(question)
            )

        # 5. Basic field-default checks.
        if stem and is_field_default_question(stem):
            stem_lower = normalize_text(stem)

            field_context = any(
                phrase in stem_lower
                for phrase in (
                    "field", "instance variable", "static variable",
                    "static field", "array element"
                )
            )

            if "local variable" in stem_lower:
                question_errors.append(
                    "Local variables do not receive automatic default values."
                )

            elif not field_context:
                question_errors.append(
                    "Default-value question must clearly specify a field "
                    "or array element."
                )

        # Record the errors or accept the question.
        if question_errors:
            for issue in dict.fromkeys(question_errors):
                errors.append(f"{prefix} {issue}")
        else:
            validated.append(question)

    if errors:
        return [], errors

    return validated, []


def assign_question_ids(questions, module_no, set_no, round_no):
    """Add IDs and metadata after a batch passes validation."""
    identified = []

    for index, question in enumerate(questions, start=1):
        item = dict(question)

        item["id"] = (
            f"R-M{module_no:02d}-S{set_no:02d}-"
            f"RD{round_no:02d}-Q{index:02d}"
        )

        item["module_no"] = module_no
        item["set_no"] = set_no
        item["q_no"] = index
        item.setdefault("set_title", f"Remedial Round {round_no}")

        identified.append(item)

    return identified
