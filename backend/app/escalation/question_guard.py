"""R6, the question guard: a question never RESOLVES an episode.

The engine resolves an episode on the first `understood` label after a delivery. The proxy
classifier (trained on synthetic answers, macro F1 0.663, not a validated confusion detector)
labels some questions `understood`: "where does the actual value come from?" scores
P(confused)=0.115 and "can we move on?" 0.208 (backendPlan/03 section 1.1). A tester's episode
resolved on "I understand that Dog inherits the name field, but where does the actual value
'Buddy' come from?", a question, and the episode log recorded a resolution that did not happen.

R6 (lead ruling 2026-10-16, backendPlan/04 section 3.5): when the current student message is a
question, the engine refuses to resolve and escalates instead. It lives in the ENGINE, not the
classifier or rules.yaml, and fires whether the `understood` label came from the model or the rule
layer ("that makes sense, but why does it work?" matches the rule phrase `that makes sense`). A
message that carries a strategy request follows the request branch and is never touched.

Accepted direction of error (app/classifier/rules.py NOTE 1): a trailing "?" will sometimes
escalate someone who meant to stop ("got it, thanks?", "can we move on?"). A false confused costs
one explanation; a false understood abandons a lost student. Since SF1 an escalation never blocks
the conversation.

R6 does NOT generalise to R1 (short-message uncertainty) or R3 (negation guard), which stay held:
one finding justifies one rule.

One definition: the engine and the episode-log builder both IMPORT `r6_applies`; there is no copy.
"""

from __future__ import annotations

# Closing punctuation and quotes that may follow the question mark: "why does it work?!",
# "(why?)", 'is it "Buddy"?', "what?...".
_TRAILING = frozenset("!.)]}\"'”’»…")
_QUESTION_MARKS = ("?", "？")


def is_question(message: str) -> bool:
    """True iff the message, ignoring trailing whitespace, closing punctuation and quotes, ends with
    a question mark (ASCII or full-width)."""
    end = message.rstrip()
    while end and (end[-1] in _TRAILING or end[-1].isspace()):
        end = end[:-1]
    return end.endswith(_QUESTION_MARKS)


def r6_applies(label: str, message: str, request: str | None) -> bool:
    """True iff R6 must refuse to resolve: an `understood` label, no detected strategy request, and a
    message that is a question."""
    return label == "understood" and request is None and is_question(message)
