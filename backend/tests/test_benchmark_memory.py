"""M1's measurement script, against a fake Ollama (httpx.MockTransport). No real Ollama, nothing rated."""

import json
import sys
from pathlib import Path

import httpx

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import benchmark_llm as bench  # noqa: E402
import benchmark_memory as bm  # noqa: E402
from test_llm_scoring import FakeOllama  # noqa: E402


def run(tmp_path, fake, *extra):
    out = tmp_path / "memory"
    code = bm.main(["--model", "qwen3:4b", "--runs", "1", "--out", str(out), *extra], transport=httpx.MockTransport(fake))
    return code, out


def test_variant_a_is_byte_identical_to_the_r3_benchmark_prompts():
    """A must be exactly what benchmark_llm measures, so A vs B differ only by the conversation block."""
    assert [i["prompt"] for i in bm.memory_prompt_set(False)] == [i["prompt"] for i in bench.prompt_set(1)]


def test_variant_b_adds_exactly_the_scripted_four_turn_conversation():
    for a, b in zip(bm.memory_prompt_set(False), bm.memory_prompt_set(True)):
        assert len(b["prompt"]) > len(a["prompt"])
        assert b["prompt"].count("Student:") == 2 and b["prompt"].count("Tutor:") == 2
        assert "<conversation>" in b["prompt"] and "<conversation>" not in a["prompt"]
        assert "Student: I don't understand" in b["prompt"] and "Student: can you explain differently?" in b["prompt"]
    turns = bm.scripted_conversation("loops", "theory")
    assert [t.role for t in turns] == ["student", "tutor", "student", "tutor"]
    assert [t.strategy for t in turns if t.role == "tutor"] == ["example", "simplified"]  # the first two NOT theory
    assert [t.strategy for t in bm.scripted_conversation("loops", "example") if t.role == "tutor"] == ["theory", "simplified"]


def test_the_script_runs_both_variants_and_writes_new_files_only(tmp_path):
    fake = FakeOllama()
    code, out = run(tmp_path, fake)
    assert code == 0
    files = sorted(p.name for p in out.iterdir())
    assert any("_memory_A.json" in f for f in files) and any("_memory_B.json" in f for f in files)
    assert any(f.startswith("memory_comparison_") for f in files)
    a = json.loads(next(out.glob("*_memory_A.json")).read_text(encoding="utf-8"))
    b = json.loads(next(out.glob("*_memory_B.json")).read_text(encoding="utf-8"))
    assert (a["memory_variant"], b["memory_variant"]) == ("A", "B")
    assert a["conversation"] is None and b["conversation"]["max_turns"] == 6
    assert a["prompt_revision"] == b["prompt_revision"] and a["num_predict"] == b["num_predict"] == 220
    sa, sb = bm.summarise(a), bm.summarise(b)
    assert sb["prompt_chars_median"] > sa["prompt_chars_median"]
    assert bench.prompt_set is not None and bench.prompt_set(1)[0]["prompt"] == bm.memory_prompt_set(False)[0]["prompt"]  # patch undone


def test_a_missing_model_exits_non_zero_and_pulls_nothing(tmp_path):
    fake = FakeOllama(installed=["something-else:1b"])
    code, out = run(tmp_path, fake)
    assert code == bench.EXIT_NO_MODEL != 0
    assert not any(c[1] in ("/api/pull", "/api/delete", "/api/create") for c in fake.calls)


def test_shipped_words_counts_prose_outside_code_without_the_check_line():
    text = "One two three.\n\n```java\nint x = 1;\n```\n\nFour five.\n\n**Check:** Six seven eight?"
    assert bm.shipped_words(text) == 5
