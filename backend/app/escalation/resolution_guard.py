"""R7: only a RULE-matched `understood` resolves an episode; a model-only `understood` never does.

The engine resolves an episode on the first `understood` after a delivery. The model half of the
prototype proxy classifier (trained on synthetic answers, macro F1 0.663, not a validated confusion
detector) hands out `understood` inconsistently (backendPlan/04 section 3.6, lead ruling 2026-10-16):

    message                                     label       P(confused)  source
    "ask me questions related to the topic"     understood  0.051        model
    "quiz me on inheritance"                    understood  0.305        model
    "test me"                                   confused    0.609        model
    "give me some questions"                    confused    0.896        model

while it is close to inverted on real understanding: "that makes sense" 0.992 confused, "got it"
0.946 confused (backendPlan/03 section 1.1). A model-only `understood` is noise, not evidence of
understanding. So the engine resolves ONLY when the RULE layer matched an understanding phrase
(`classify(...).source == "rule"`); a model-sourced `understood` escalates instead, as R6 does. The
same principle already limits the request-confusion override (orchestrator.py: only rule-layer
confusion earns an override).

Precedence: R6 (question guard) is checked FIRST, then R7. A model-sourced `understood` that is also
a question is recorded as `question_guard`, exactly as before R6 and R7 coexisted; R7 covers the
model-sourced NON-questions. A rule-matched question ("that makes sense, but why does it work?") is
declined by R6 alone.

Direction of error (app/classifier/rules.py NOTE 1): a student who expresses understanding in
unlisted words gets one more explanation, and since SF1 that never blocks the conversation. Measured
side effect (30 natural "I understand" phrasings): 26 were already labelled `confused` by the model
("I understand" 0.810, "ok" 0.810, "thanks" 0.810, "makes sense" 0.999) and never resolved; R7 newly
blocks only "that helped a lot" (0.197, model). The rule phrases tested ("got it, thanks", "that
makes sense", "i get it now") still resolve. To resolve, a student uses a listed understanding
phrase (`rules.yaml` `understanding_phrases`).

NO PHRASE LIST, by ruling: do not add "quiz me" / "ask me" patterns anywhere. One condition covers
the quiz phrases, "can we move on?", the "actual" case and every future instance. R7 does not unlock
R1 (short-message uncertainty) or R3 (negation guard).

One definition: the engine and the episode-log builder both IMPORT `r7_applies`; there is no copy.
"""

from __future__ import annotations

from app.escalation.question_guard import r6_applies


def r7_applies(label: str, source: str, message: str, request: str | None) -> bool:
    """True iff R7 must refuse to resolve: an `understood` label that came from the MODEL, no detected
    strategy request, and R6 not already applying (R6 is checked first)."""
    return label == "understood" and source == "model" and request is None and not r6_applies(label, message, request)
