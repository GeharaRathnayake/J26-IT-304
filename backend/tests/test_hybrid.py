"""Hybrid classifier tests (real model and real rules unless a stub is stated).

Prototype hybrid over a proxy classifier trained on synthetic answers; not a validated
confusion detector. `test_documented_wrong_*` pin current behaviour without endorsing it.
Every string is hand-written (no experiment1 data or probe).
"""

import dataclasses
import inspect

import numpy as np
import pytest

from app.classifier.hybrid import classify
from app.classifier.model import load_model
from app.config import DEFAULT_MODELS_DIR


@pytest.fixture(scope="module")
def model():
    return load_model(DEFAULT_MODELS_DIR / "clf-v1.0.0")


class StubPipeline:
    """Stands in for the sklearn pipeline: records inputs, returns a fixed P(confused)."""

    def __init__(self, p):
        self.p = p
        self.seen = []

    def predict_proba(self, texts):
        self.seen.extend(texts)
        return np.array([[1.0 - self.p, self.p]])


def stubbed(model, p):
    stub = StubPipeline(p)
    return dataclasses.replace(model, pipeline=stub), stub


# --- headline ---------------------------------------------------------------------------


def test_that_makes_sense_is_understood_by_rule_despite_high_model_p(model):
    r = classify(model, "that makes sense")
    print(f"\nP(confused) for 'that makes sense' = {r.probability:.4f} (model alone says {r.model_label})")
    assert (r.label, r.source, r.matched_phrase) == ("understood", "rule", "that makes sense")
    assert r.probability > 0.9
    assert r.model_label == "confused"


# --- known false triggers and limits (documented wrong behaviour, pinned) --------------


def test_documented_wrong_got_it_from_the_docs(model):
    r = classify(model, "I got it from the docs")
    assert (r.label, r.source, r.matched_phrase) == ("understood", "rule", "got it")


def test_documented_wrong_makes_sense_in_theory(model):
    r = classify(model, "that makes sense in theory but how do I code it")
    assert (r.label, r.source) == ("understood", "rule")


def test_documented_limit_i_am_so_lost_falls_to_model(model):
    r = classify(model, "I am so lost")
    assert r.source == "model" and r.matched_phrase is None


def test_documented_choice_challenge_to_tutor_is_confusion(model):
    r = classify(model, "That doesn't make sense, 2 + 2 is 4")
    assert (r.label, r.source) == ("confused", "rule")


def test_fixed_got_it_wrong_again(model):
    r = classify(model, "I got it wrong again")
    assert (r.label, r.source, r.matched_phrase) == ("confused", "rule", "got it wrong")


@pytest.mark.parametrize("text", ["got it, but now I'm lost", "got it, but now I'm lost again"])
def test_confusion_beats_understanding(model, text):
    r = classify(model, text)
    assert (r.label, r.source) == ("confused", "rule")


def test_none_of_that_makes_sense_is_confused(model):
    r = classify(model, "none of that makes sense")
    assert (r.label, r.source) == ("confused", "rule")


def test_no_ideal_has_no_rule_match(model):
    assert classify(model, "no ideal").matched_phrase is None


# --- raw text reaches the model; P is the model's own P ----------------------------------


def test_raw_text_reaches_the_model_unchanged_while_rules_still_match(model):
    raw = "  I DON’T   Understand\t"
    spoofed, spy = stubbed(model, 0.3)
    r = classify(spoofed, raw)
    assert spy.seen == [raw]  # byte for byte: no lowercasing, stripping or rewriting
    assert (r.label, r.source, r.matched_phrase) == ("confused", "rule", "i don't understand")


def test_probability_is_the_models_own_p_when_a_rule_decides(model):
    text = "that makes sense"
    r = classify(model, text)
    assert r.source == "rule"
    assert r.probability == model.predict_confused(text)


def test_model_is_always_consulted_even_when_a_rule_decides(model):
    spoofed, spy = stubbed(model, 0.123)
    r = classify(spoofed, "got it")
    assert spy.seen == ["got it"]
    assert r.probability == pytest.approx(0.123)
    assert r.model_label == "understood"


# --- threshold ---------------------------------------------------------------------------


def test_threshold_comes_from_metadata(model):
    assert model.threshold == 0.5 == model.metadata["threshold"]


def test_unmatched_message_at_exactly_the_threshold_is_confused(model):
    stub_model, _ = stubbed(model, model.threshold)
    r = classify(stub_model, "purple elephants")
    assert (r.label, r.source) == ("confused", "model")


def test_unmatched_message_just_below_the_threshold_is_understood(model):
    stub_model, _ = stubbed(model, np.nextafter(model.threshold, 0))
    r = classify(stub_model, "purple elephants")
    assert (r.label, r.source) == ("understood", "model")


# --- single input -------------------------------------------------------------------------


def test_classify_takes_one_student_text_and_no_history():
    params = list(inspect.signature(classify).parameters)
    assert params == ["model", "text"]
    assert not {"history", "context", "previous"} & set(params)
