"""gpu_fraction: unknown is None, never 0.0 (0.0 means fully on CPU). Plus the Deps timeout default."""

import pytest

from app.config import Settings
from app.generation.placement import gpu_fraction
from app.orchestrator import Deps

M = "llama3.2:3b"


def body(**entry):
    return {"models": [{"name": M, **entry}]}


def test_fully_on_gpu():
    assert gpu_fraction(body(size=100, size_vram=100), M) == 1.0


def test_fully_on_cpu_is_zero_not_none():
    assert gpu_fraction(body(size=100, size_vram=0), M) == 0.0


def test_partial_is_rounded_to_three_places():
    assert gpu_fraction(body(size=3, size_vram=2), M) == 0.667


def test_unknown_is_none_never_zero():
    assert gpu_fraction({"models": []}, M) is None  # not listed
    assert gpu_fraction({"models": [{"name": "other", "size": 1, "size_vram": 1}]}, M) is None
    assert gpu_fraction(body(size_vram=5), M) is None  # size missing
    assert gpu_fraction(body(size=0, size_vram=0), M) is None  # size 0
    assert gpu_fraction(body(size=10), M) is None  # size_vram missing


@pytest.mark.parametrize("bad", [{}, {"models": None}, {"models": "x"}, {"models": [None]}, {"models": [1]},
                                 None, [], "oops"])
def test_malformed_body_is_none(bad):
    assert gpu_fraction(bad, M) is None


def test_malformed_numbers_are_none():
    assert gpu_fraction(body(size="big", size_vram=1), M) is None
    assert gpu_fraction(body(size=10, size_vram=True), M) is None


def test_deps_timeout_default_is_the_settings_default():
    """S8b left a literal 14.0 here after LLM_TIMEOUT_S became 18.0: one number, not two."""
    assert Deps.__dataclass_fields__["llm_timeout_s"].default == Settings.model_fields["LLM_TIMEOUT_S"].default
