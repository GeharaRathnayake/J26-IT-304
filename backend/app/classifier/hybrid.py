"""Hybrid classification: explicit-phrase rules first, proxy classifier otherwise.

Prototype hybrid. The model is a TF-IDF + LogisticRegression proxy trained on SYNTHETIC
answers (labelled by correctness); it has never seen a real student message and is not a
validated confusion detector. See rules.py for why the rule layer decides first.

    P = model.predict_confused(text)        always computed, on the RAW text
    rules: confusion list, then understanding list      first match decides (source="rule")
    no match: confused if P >= threshold else understood (source="model")

The classifier sees the current student message only, never history or the previous
tutor turn: it was trained on single answers. `classify` therefore takes one `str` and
nothing else; there is deliberately no parameter through which history could enter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.classifier.model import LoadedModel

Label = Literal["confused", "understood"]
Source = Literal["rule", "model"]


@dataclass(frozen=True)
class ClassificationResult:
    # label / probability / source mirror ConfusionResult in the frontend contract.
    label: Label
    probability: float  # the model's own P(confused), even when a rule decided
    source: Source
    # Internal diagnostics, never part of the API contract:
    matched_phrase: str | None  # the rule phrase that fired, if any
    model_label: Label  # the label P alone would give


def classify(model: LoadedModel, text: str) -> ClassificationResult:
    probability = model.predict_confused(text)  # raw text, unmodified
    model_label: Label = "confused" if probability >= model.threshold else "understood"
    rule_label, phrase = model.rules.match(text)  # normalisation happens inside, rules only
    if rule_label is not None:
        return ClassificationResult(rule_label, probability, "rule", phrase, model_label)
    return ClassificationResult(model_label, probability, "model", None, model_label)
