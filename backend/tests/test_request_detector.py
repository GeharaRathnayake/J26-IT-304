"""Request detector (Tier 2) and cycle-intent tests. All strings are hand-written.

The detector is biased toward MISSING a request (claim C6): a false request is logged
trigger="request" and not counted, hiding real difficulty. Tests named `test_documented_wrong_*`
pin current behaviour that is known to be wrong; they do not endorse it.
"""

import pytest

from app.escalation.request_detector import detect_cycle_intent, detect_request

# --- every pattern, one positive test each ------------------------------------------------

POSITIVE = [
    ("show me", "example"),
    ("give me an example", "example"),
    ("can i see an example", "example"),
    ("can i have an example", "example"),
    ("example please", "example"),
    ("demonstrate", "example"),
    ("simplify", "simplified"),
    ("make it simpler", "simplified"),
    ("make it easier", "simplified"),
    ("make it easy", "simplified"),
    ("make it clearer", "simplified"),
    ("in simpler terms", "simplified"),
    ("explain it simpler", "simplified"),
    ("analogy", "analogy"),
    ("real world example", "analogy"),
    ("real life example", "analogy"),
    ("compare it to", "analogy"),
    ("like what", "analogy"),
    ("define", "theory"),
    ("explain the concept", "theory"),
    ("explain the theory", "theory"),
]


@pytest.mark.parametrize("pattern, strategy", POSITIVE)
def test_each_request_pattern_fires(pattern, strategy):
    assert detect_request(pattern) == strategy
    assert detect_request(f"Could you PLEASE {pattern.upper()} for me?") == strategy


def test_normalisation_is_shared_with_the_rule_layer():
    # whitespace runs and case are normalised exactly as in the rule layer
    assert detect_request("  Give   ME\tan\nexample ") == "example"


def test_pattern_table_has_21_patterns():
    assert len(POSITIVE) == 21


# --- priority: example -> simplified -> analogy -> theory ----------------------------------


def test_priority_example_beats_simplified():
    assert detect_request("show me a simpler version") == "example"


def test_priority_simplified_beats_analogy():
    assert detect_request("simplify it with an analogy") == "simplified"


def test_priority_analogy_beats_theory():
    assert detect_request("use an analogy to define it") == "analogy"


# --- deliberately NOT patterns (a request bias would corrupt the C6 data) --------------------


@pytest.mark.parametrize(
    "message",
    [
        "for example, a loop repeats while its condition is true",
        "there are many examples of inheritance",
        "oh it's clearer now",
        "what is a constructor?",
    ],
    ids=["for-example", "bare-examples-noun", "clearer-now-understanding", "what-is-question"],
)
def test_not_a_request(message):
    assert detect_request(message) is None


def test_ordinary_answers_and_questions_are_not_requests():
    for message in ["a loop repeats code", "what does static mean", "I got it", "ok", "", "   "]:
        assert detect_request(message) is None


def test_bare_word_example_is_not_a_pattern():
    assert detect_request("example") is None


def test_whole_word_matching():
    assert detect_request("this shows me nothing") is None  # 'shows me' is not 'show me'
    assert detect_request("undefined behaviour") is None  # 'define' inside a word


# --- documented residual false triggers (pinned, not endorsed) ------------------------------


def test_documented_wrong_like_what_in_an_answer_is_analogy():
    assert detect_request("it works like what we did with arrays") == "analogy"


def test_documented_wrong_define_in_an_answer_is_theory():
    assert detect_request("you could define a method for that") == "theory"


def test_documented_wrong_good_analogy_comment_is_analogy():
    assert detect_request("that's a good analogy") == "analogy"


def test_documented_wrong_demonstrate_in_an_answer_is_example():
    assert detect_request("to demonstrate polymorphism a subclass overrides the method") == "example"


def test_documented_wrong_real_world_example_in_an_answer_is_analogy():
    assert detect_request("a real world example of a class is a car") == "analogy"


def test_documented_wrong_confused_plus_theory_request_is_a_request():
    # A confused student asking for the theory is logged as a request and so not counted.
    assert detect_request("I don't understand, explain the theory again") == "theory"


# --- cycle intent ---------------------------------------------------------------------------


@pytest.mark.parametrize("message", ["yes", "sure", "okay", "ok", "again", "explain it another way", "yes please", "Okay!"])
def test_cycle_intent_accept(message):
    assert detect_cycle_intent(message) == "accept"


@pytest.mark.parametrize("message", ["no", "move on", "skip", "later", "no thanks", "No."])
def test_cycle_intent_decline(message):
    assert detect_cycle_intent(message) == "decline"


@pytest.mark.parametrize("message", ["not really", "wait, what do you mean?", "hmm", "", "maybe"])
def test_cycle_intent_unclear(message):
    assert detect_cycle_intent(message) == "unclear"


def test_cycle_intent_accept_is_checked_before_decline():
    assert detect_cycle_intent("no, explain it another way") == "accept"
    assert detect_cycle_intent("no, again") == "accept"


def test_cycle_intent_whole_word():
    assert detect_cycle_intent("nope") == "unclear"  # 'no' inside a word
    assert detect_cycle_intent("okayish") == "unclear"


def test_documented_wrong_not_sure_reads_as_accept():
    # 'sure' is an accept word, so "I'm not sure" accepts a new cycle. The cost is one more
    # explanation for an uncertain student, not a corrupted weakness record.
    assert detect_cycle_intent("I'm not sure") == "accept"