"""LLM benchmark: scoring functions, aggregation, SUMMARY regeneration and the script's exit codes.

No Ollama and no network: Ollama is faked with httpx.MockTransport. All texts are hand-written
except the two reasoning-leak strings, which are the exact text the lead observed from qwen3:4b.
The format checks here are mechanical; they say nothing about explanation quality.
"""

import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest

from app.generation.adapters import STRATEGIES, TemplateFallback
from app.generation.postprocess import finalise
from app.generation.prompts import build_prompt
from app.topics import GENERAL, public_topics

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sc = load("llm_scoring")
bench = load("benchmark_llm")

GOOD_THEORY = "Inheritance lets a subclass reuse a superclass. It uses the extends keyword.\n\n**Check:** Which class is the superclass?"
GOOD_EXAMPLE = (
    "Here is a small example:\n\n```java\nclass A {}\nclass B extends A {}\n```\n\n"
    "B reuses everything in A.\n\n**Check:** What does B extend?"
)

# --- Check line -----------------------------------------------------------------------------------------


def test_check_ok_exactly_one_and_last():
    assert sc.check_ok(GOOD_THEORY)
    assert sc.check_ok("Text.\n\n**Check:** Why?\n\n")  # trailing blank lines are fine


@pytest.mark.parametrize(
    "text",
    [
        "No check here.",
        "A.\n\n**Check:** One?\n**Check:** Two?",
        "A.\n\n**Check:** One?\n\nMore text after it.",
        "A. **Check:** inline, not on its own line",
        "",
    ],
    ids=["none", "two", "not-last", "mid-line", "empty"],
)
def test_check_not_ok(text):
    assert not sc.check_ok(text)


# --- sentences ----------------------------------------------------------------------------------------------


def test_sentence_count_basic_and_range():
    assert sc.sentence_count(GOOD_THEORY) == 2 and sc.sentences_ok(GOOD_THEORY)
    assert sc.sentence_count("One. Two. Three. Four. Five.\n\n**Check:** Q?") == 5
    assert not sc.sentences_ok("Only one.\n\n**Check:** Q?")
    assert not sc.sentences_ok("One. Two. Three. Four. Five.\n\n**Check:** Q?")


def test_sentence_count_excludes_code_blocks():
    text = "Intro here.\n\n```java\nint x = 1; // a. b. c. d. e. f.\nSystem.out.println(x);\n```\n\nDone now.\n\n**Check:** Q?"
    assert sc.sentence_count(text) == 2  # the periods inside the code do not count


def test_sentence_count_excludes_an_unclosed_trailing_fence_and_the_check_line():
    cut_off = "Look at this. It is short.\n\n```java\nint x = 1;\nint y = 2. . . ."
    assert sc.sentence_count(cut_off) == 2
    assert sc.sentence_count("One. Two.\n\n**Check:** A question? Another? More?") == 2


def test_sentence_count_ignores_full_stops_inside_inline_code_and_counts_a_lead_in():
    assert sc.sentence_count("Call `list.add(x)` to grow it. Then check `size()`.") == 2
    assert sc.sentence_count("Here is an example:\n\n```java\nint x;\n```\n\nIt declares x.") == 2  # lead-in + 1


# --- java fence ------------------------------------------------------------------------------------------------


def test_example_needs_a_closed_java_block():
    assert sc.java_ok(GOOD_EXAMPLE, "example")
    assert not sc.java_ok("Just words.\n\n**Check:** Q?", "example")
    assert not sc.java_ok("Look:\n\n```java\nint x = 1;\n\n**Check:** Q?", "example")  # never closed
    assert not sc.java_ok("Look:\n\n```\nint x = 1;\n```\n\n**Check:** Q?", "example")  # plain fence, not java


@pytest.mark.parametrize("strategy", ["theory", "simplified", "analogy"])
def test_other_strategies_must_not_have_unfenced_code(strategy):
    assert sc.java_ok("A loop repeats code. Use `for` to count.\n\n**Check:** Q?", strategy)
    assert sc.java_ok("A loop:\n\n```java\nfor (int i = 0; i < 3; i++) {}\n```\n\n**Check:** Q?", strategy)  # fenced is fine
    assert not sc.java_ok("A loop is this:\nint x = 5;\n\n**Check:** Q?", strategy)
    assert not sc.java_ok("Like so:\nfor (int i = 0; i < 3; i++) {\n    x++;\n}\n\n**Check:** Q?", strategy)
    assert not sc.java_ok("The call\nSystem.out.println(x);\nprints it.\n\n**Check:** Q?", strategy)


def test_prose_is_not_mistaken_for_code():
    for prose in (
        "A variable is declared with a type, a name and a value.",
        "Use an if statement when you need a decision.",
        "Think of a class as a blueprint: it describes the fields.",
    ):
        assert sc.unfenced_code_lines(prose) == [], prose


# --- <think> tags --------------------------------------------------------------------------------------------------


def test_think_tag_detection():
    assert sc.has_think_tag("<think>plan</think>Answer.")
    assert sc.has_think_tag("Answer. <THINK>")
    assert sc.has_think_tag("stray </think> tag")
    assert not sc.has_think_tag(GOOD_THEORY)


def test_finalise_removes_every_think_tag_so_the_final_score_is_zero():
    raw = "<think>hmm</think>A loop repeats code. It stops when its condition is false.\n\n**Check:** Why?"
    assert sc.score_raw(raw, "theory", "stop")["think_tag"] is True
    assert sc.score_final(finalise(raw, "theory"))["think_tag"] is False
    unclosed = "<think>never closed and the model ran out of tokens"
    assert sc.score_final(finalise(unclosed, "theory"))["think_tag"] is False


# --- untagged reasoning leak (heuristic) ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "We are explaining what a Java constructor is in 2-4 sentences.",  # exact text the lead observed
        "Let me write in 2-4 sentences:",  # exact text the lead observed
        "We are given the topic: Inheritance. We are to provide: theory.",  # observed on the production prompt at 80 tokens
        "Okay, so the student does not understand loops.",
        "The user wants an explanation of polymorphism.",
        "First, I should define the term.",
        "We need to keep it short.",
        "A loop repeats code.\nLet me think about the example.",  # not only the first line
        "  we are going to explain this",  # leading space, lower case
    ],
)
def test_reasoning_leak_is_flagged(text):
    assert sc.reasoning_leak(text)


@pytest.mark.parametrize("text", [GOOD_THEORY, GOOD_EXAMPLE, "A constructor sets up a new object.\n\n**Check:** What does it return?", ""])
def test_a_clean_tutor_reply_is_not_flagged(text):
    assert not sc.reasoning_leak(text)


def test_documented_limit_reasoning_in_the_middle_of_a_line_is_not_caught():
    assert not sc.reasoning_leak("A loop repeats code and let me explain how.")  # false negative, by design


def test_documented_limit_a_legitimate_reply_starting_with_we_are_is_flagged():
    assert sc.reasoning_leak("We are going to look at a loop now. It repeats code.")  # false positive, by design


def test_the_phrase_list_is_the_single_source():
    assert set(sc.LEAK_PHRASES) >= {"We are", "We need to", "Let me", "Okay, so", "First, I", "The user"}


def test_none_of_our_known_good_templates_is_flagged_as_a_leak_or_a_format_failure():
    fb = TemplateFallback()
    for topic in [t["id"] for t in public_topics()] + [GENERAL]:
        for strategy in STRATEGIES:
            for text in fb.variants(topic, strategy):
                assert not sc.reasoning_leak(text), (topic, strategy)
                assert sc.check_ok(text) and sc.java_ok(text, strategy) and sc.sentences_ok(text), (topic, strategy)


# --- truncation ---------------------------------------------------------------------------------------------------------


def test_truncation_comes_from_done_reason():
    assert sc.truncated("length") is True
    assert sc.truncated("stop") is False
    assert sc.truncated(None) is False
    assert sc.score_raw("text", "theory", "length")["truncated"] is True


def test_score_raw_marks_an_empty_output():
    s = sc.score_raw("   \n", "theory", "length")
    assert s["empty"] is True and s["check_ok"] is False


def test_raw_and_final_are_scored_separately_check_is_judged_on_the_raw_text_too():
    raw = "A loop repeats code. It stops when false."  # the model forgot the check line
    final = finalise(raw, "theory")
    s = sc.score_generation(raw, final, "theory", "stop")
    assert s["score_raw"]["check_ok"] is False
    assert s["score_final"]["check_ok"] is True


# --- aggregation and the summary ------------------------------------------------------------------------------------------


def gen(topic="loops", strategy="theory", run=1, wall=10.0, ttft=1.0, tok=10.0, trunc=False, leak=False, check=True, java=True, error=None):
    if error:
        return {"id": "x", "topic": topic, "strategy": strategy, "run": run, "error": error}
    return {
        "id": "x", "topic": topic, "strategy": strategy, "run": run, "wall_s": wall, "ttft_s": ttft, "tok_s": tok,
        "score_raw": {"empty": False, "check_ok": check, "sentences_ok": True, "java_ok": java, "think_tag": False,
                      "reasoning_leak": leak, "truncated": trunc},
        "score_final": {"check_ok": True, "sentences_ok": True, "think_tag": False, "reasoning_leak": leak},
    }


def test_aggregate_numbers():
    gens = [gen(wall=w, tok=t, trunc=(i % 2 == 0)) for i, (w, t) in enumerate([(10, 8), (20, 10), (30, 12), (40, 14)])]
    a = sc.aggregate(gens, cold_start_s=42.0)
    assert a["cold_start_s"] == 42.0
    assert a["wall_median_s"] == 25.0 and a["tok_s_median"] == 11.0
    assert a["wall_p95_s"] == 40.0  # nearest-rank: the top value of four
    assert a["pct_truncated"] == 50.0 and a["generations"] == 4 and a["errors"] == 0


def test_percentile_is_nearest_rank_and_handles_empty():
    assert sc.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10
    assert sc.percentile([5], 95) == 5
    assert sc.percentile([], 95) is None


def test_aggregate_splits_example_java_from_other_unfenced_code_and_counts_errors():
    gens = [
        gen(strategy="example", java=True), gen(strategy="example", java=False),
        gen(strategy="theory", java=True), gen(strategy="analogy", java=False),
        gen(error="timeout"),
    ]
    a = sc.aggregate(gens, None)
    assert a["pct_java_example"] == 50.0 and a["pct_no_unfenced_code_other"] == 50.0
    assert a["errors"] == 1 and a["generations"] == 5 and a["cold_start_s"] is None


def test_aggregate_spread_is_max_minus_min_per_prompt():
    gens = [gen(wall=10, run=1), gen(wall=16, run=2), gen(strategy="example", wall=5, run=1), gen(strategy="example", wall=6, run=2)]
    assert sc.aggregate(gens, None)["wall_spread_median_s"] == 3.5  # median of 6 and 1


def fake_result(model, date, num_predict=80, revision="r2", **kw):
    r = {"schema": 1, "model": model, "date": date, "num_predict": num_predict, "prompt_revision": revision,
         "cold_start": {"wall_s": kw.pop("cold", 30.0)}, "generations": [gen(**kw), gen(strategy="example", **kw)]}
    return r


def test_summary_regenerates_from_two_result_files_and_grows_with_a_third(tmp_path):
    for name, r in (("a.json", fake_result("qwen3:4b", "2026-10-14", wall=16.0, tok=9.5, trunc=True, leak=True)),
                    ("b.json", fake_result("llama3.2:3b", "2026-10-15", wall=4.0, tok=40.0, cold=8.0))):
        (tmp_path / name).write_text(json.dumps(r), encoding="utf-8")
    (tmp_path / "junk.json").write_text("not json", encoding="utf-8")  # ignored
    (tmp_path / "other.json").write_text(json.dumps({"hello": 1}), encoding="utf-8")  # ignored
    path = bench.regenerate_summary(tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "| qwen3:4b @80 r2 (2026-10-14) | 30.0 s | 16.0 s |" in text
    assert "| llama3.2:3b @80 r2 (2026-10-15) | 8.0 s | 4.0 s |" in text
    assert "9.5" in text and "40.0" in text
    assert "over 12 s" in text and "human rating (mean)" in text and text.count("\n| ") == 3  # header + two rows (sep starts with '|-')
    assert "100%" in text  # the leak / truncated percentages for the first model

    (tmp_path / "c.json").write_text(json.dumps(fake_result("qwen3:4b-instruct", "2026-10-16", wall=6.0)), encoding="utf-8")
    text = bench.regenerate_summary(tmp_path).read_text(encoding="utf-8")
    assert "qwen3:4b-instruct @80 r2 (2026-10-16)" in text and text.count("\n| ") == 4


def test_summary_recomputes_from_the_generations_not_from_a_stale_stored_aggregate(tmp_path):
    r = fake_result("m", "2026-10-14", wall=10.0)
    r["aggregates"] = {"wall_median_s": 999.0}
    (tmp_path / "m.json").write_text(json.dumps(r), encoding="utf-8")
    assert "999" not in bench.regenerate_summary(tmp_path).read_text(encoding="utf-8")


# --- the script, against a fake Ollama ---------------------------------------------------------------------------------------


class FakeOllama:
    def __init__(self, installed=("qwen3:4b",), resident=False, chat_status=200, reply=None, done_reason="stop"):
        self.installed, self.resident, self.chat_status = list(installed), resident, chat_status
        self.reply, self.done_reason = reply, done_reason
        self.chat_payloads, self.calls = [], []

    def reply_for(self, prompt):
        if self.reply is not None:
            return self.reply
        if "Strategy: example" in prompt:
            return GOOD_EXAMPLE
        return GOOD_THEORY

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append((request.method, path))
        if path == "/api/version":
            return httpx.Response(200, json={"version": "9.9.9"})
        if path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": n} for n in self.installed]})
        if path == "/api/ps":
            return httpx.Response(200, json={"models": [{"name": n} for n in self.installed] if self.resident else []})
        if path == "/api/generate":
            self.resident = False
            return httpx.Response(200, json={"done": True})
        if path == "/api/chat":
            body = json.loads(request.content)
            self.chat_payloads.append(body)
            if self.chat_status != 200:
                return httpx.Response(self.chat_status, text="boom")
            text = self.reply_for(body["messages"][0]["content"])
            half = len(text) // 2
            lines = [
                {"message": {"role": "assistant", "content": text[:half]}, "done": False},
                {"message": {"role": "assistant", "content": text[half:]}, "done": False},
                {"message": {"role": "assistant", "content": ""}, "done": True, "done_reason": self.done_reason,
                 "eval_count": 100, "eval_duration": 10_000_000_000, "prompt_eval_count": 300, "load_duration": 2_000_000_000},
            ]
            return httpx.Response(200, content="\n".join(json.dumps(x) for x in lines).encode())
        return httpx.Response(404)


def run_main(tmp_path, fake, *extra, models=("qwen3:4b",), runs="1"):
    args = ["--models", *models, "--runs", runs, "--out", str(tmp_path / "out"), *extra]
    code = bench.main(args, transport=httpx.MockTransport(fake))
    return code


def test_exits_non_zero_when_no_requested_model_is_installed(tmp_path, capsys):
    code = run_main(tmp_path, FakeOllama(installed=["something-else:1b"]))
    assert code == bench.EXIT_NO_MODEL != 0
    out = capsys.readouterr()
    assert "SKIPPED qwen3:4b: not installed" in out.out
    assert not (tmp_path / "out").exists()  # nothing written


def test_exits_non_zero_when_ollama_is_unreachable(tmp_path):
    def refuse(request):
        raise httpx.ConnectError("refused")

    assert run_main(tmp_path, refuse) == bench.EXIT_UNREACHABLE != 0


def test_skips_uninstalled_models_with_a_clear_line_and_benchmarks_the_installed_one(tmp_path, capsys):
    fake = FakeOllama(installed=["qwen3:4b"])
    code = run_main(tmp_path, fake, models=("qwen3:4b", "llama3.2:3b", "qwen3:4b-instruct"))
    out = capsys.readouterr().out
    assert code == 0
    assert "SKIPPED llama3.2:3b: not installed" in out and "SKIPPED qwen3:4b-instruct: not installed" in out
    files = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert any(f.startswith("qwen3_4b_") and f.endswith(".json") for f in files)
    assert any(f.endswith("_outputs.md") for f in files) and "SUMMARY.md" in files
    assert not any("llama" in f for f in files)


def test_a_model_name_without_a_tag_matches_latest(tmp_path):
    code = run_main(tmp_path, FakeOllama(installed=["mymodel:latest"]), models=("mymodel",))
    assert code == 0


def test_every_chat_call_uses_the_fixed_parameters_and_the_real_prompts(tmp_path):
    fake = FakeOllama()
    assert run_main(tmp_path, fake, runs="2") == 0
    expected_prompts = [
        build_prompt(topic=t, strategy=s, cycle=1, student_message="I don't understand", prior_explanations=[])
        for t in ("inheritance", "loops", "exception_handling", "polymorphism") for s in STRATEGIES
    ]
    assert len(fake.chat_payloads) == 1 + 16 * 2  # one warm-up + 16 prompts x 2 runs
    for payload in fake.chat_payloads:
        assert set(payload) == {"model", "messages", "think", "stream", "options"}
        assert payload["think"] is False and payload["stream"] is True
        assert payload["options"] == {"num_predict": 80}
        assert payload["model"] == "qwen3:4b" and len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user" and payload["messages"][0]["content"] in expected_prompts
    # identical prompts for every run: each prompt appears exactly 2 times (+1 warm-up for the first)
    sent = [p["messages"][0]["content"] for p in fake.chat_payloads[1:]]
    assert all(sent.count(p) == 2 for p in expected_prompts)
    assert fake.chat_payloads[0]["messages"][0]["content"] == expected_prompts[0]  # warm-up is a throwaway of prompt 1


def test_result_json_has_everything_the_lead_needs(tmp_path):
    fake = FakeOllama(resident=True)
    assert run_main(tmp_path, fake, runs="1") == 0
    path = next((tmp_path / "out").glob("qwen3_4b_*.json"))
    r = json.loads(path.read_text(encoding="utf-8"))
    assert r["model"] == "qwen3:4b" and r["ollama_version"] == "9.9.9" and r["runs_per_prompt"] == 1
    assert r["call_parameters"] == bench.CALL_PARAMETERS
    assert r["call_parameters"]["think"] is False and r["call_parameters"]["options"] == {"num_predict": 80}
    assert r["service_timeout_s_reference"] == 12.0 and "not a pass mark" in r["service_timeout_note"]
    assert r["call_parameters"]["client_timeout_s"] == 60.0
    assert len(r["prompt_set"]) == 16 and len({(p["topic"], p["strategy"]) for p in r["prompt_set"]}) == 16
    assert r["leak_phrases"] == list(sc.LEAK_PHRASES)
    assert r["cold_start"]["was_resident"] is True and r["cold_start"]["unloaded"] is True
    assert r["cold_start"]["wall_s"] is not None
    assert ("POST", "/api/generate") in fake.calls  # evicted before the warm-up, not pulled/deleted
    assert not any(c[1] in ("/api/pull", "/api/delete", "/api/create") for c in fake.calls)
    assert len(r["generations"]) == 16
    g = r["generations"][0]
    for key in ("id", "topic", "strategy", "run", "ttft_s", "wall_s", "eval_count", "tok_s", "done_reason",
                "raw_text", "final_text", "score_raw", "score_final"):
        assert key in g, key
    assert g["tok_s"] == pytest.approx(10.0) and g["eval_count"] == 100 and g["done_reason"] == "stop"
    assert g["ttft_s"] is not None and g["ttft_s"] <= g["wall_s"]
    assert set(g["score_raw"]) >= {"check_ok", "sentences_ok", "java_ok", "think_tag", "reasoning_leak", "truncated"}
    assert r["aggregates"]["generations"] == 16 and r["aggregates"]["errors"] == 0


def test_no_unload_flag_leaves_a_resident_model_alone(tmp_path):
    fake = FakeOllama(resident=True)
    assert run_main(tmp_path, fake, "--no-unload") == 0
    assert ("POST", "/api/generate") not in fake.calls


def test_the_rating_sheet_has_one_empty_rating_line_per_output_with_the_prompt_context(tmp_path):
    assert run_main(tmp_path, FakeOllama(), runs="1") == 0
    sheet = next((tmp_path / "out").glob("*_outputs.md")).read_text(encoding="utf-8")
    assert sheet.count("\nRating:\n") == 16
    assert "## qwen3_4b_p01_r1: inheritance / theory (run 1)" in sheet
    assert "Raw:" in sheet and "Shipped (post-processed" in sheet and GOOD_THEORY.splitlines()[0] in sheet


def test_a_truncated_and_leaking_model_is_measured_as_such(tmp_path):
    leak = "We are explaining what a Java constructor is in 2-4 sentences. Let me write it"
    fake = FakeOllama(reply=leak, done_reason="length")
    assert run_main(tmp_path, fake, runs="1") == 0
    r = json.loads(next((tmp_path / "out").glob("*.json")).read_text(encoding="utf-8"))
    a = r["aggregates"]
    assert a["pct_truncated"] == 100.0 and a["pct_leak_raw"] == 100.0 and a["pct_check_raw"] == 0.0
    assert a["pct_check_final"] == 100.0  # finalise appends a default check: read it with the raw column
    assert all(g["score_raw"]["truncated"] and g["score_raw"]["reasoning_leak"] for g in r["generations"])
    # the leak survives finalise (it is not tagged), which is exactly why it must be measured
    assert a["pct_leak_final"] == 100.0


def test_generation_errors_are_recorded_and_the_exit_code_is_non_zero(tmp_path):
    code = run_main(tmp_path, FakeOllama(chat_status=500), runs="1")
    assert code == bench.EXIT_ERRORS != 0
    r = json.loads(next((tmp_path / "out").glob("*.json")).read_text(encoding="utf-8"))
    assert r["aggregates"]["errors"] == 16 and all("HTTP 500" in g["error"] for g in r["generations"])


def test_a_timeout_is_recorded_not_raised(tmp_path):
    def slow(request):
        if request.url.path == "/api/chat":
            raise httpx.ReadTimeout("no data", request=request)
        return FakeOllama()(request)

    assert run_main(tmp_path, slow, runs="1") == bench.EXIT_ERRORS
    r = json.loads(next((tmp_path / "out").glob("*.json")).read_text(encoding="utf-8"))
    assert all("timeout" in g["error"] for g in r["generations"])


def test_the_summary_is_written_by_the_run(tmp_path):
    assert run_main(tmp_path, FakeOllama(), runs="1") == 0
    text = (tmp_path / "out" / "SUMMARY.md").read_text(encoding="utf-8")
    assert "qwen3:4b" in text and "cold start" in text and "human rating (mean)" in text


# --- the 12 s reference (the service's fallback timeout; not a pass mark) ----------------------------------------------------


def test_pct_over_the_service_timeout_counts_generations_above_12_seconds():
    gens = [gen(wall=w) for w in (5.0, 11.9, 12.0, 12.1, 30.0)]
    a = sc.aggregate(gens, None)
    assert sc.SERVICE_TIMEOUT_S == 12.0
    assert a["pct_over_service_timeout"] == 40.0  # 12.1 and 30.0; exactly 12.0 is not over


def test_a_client_side_timeout_with_a_measured_wall_time_counts_as_over():
    gens = [gen(wall=5.0), {"id": "x", "topic": "loops", "strategy": "theory", "run": 1, "error": "timeout", "wall_s": 60.0}]
    assert sc.aggregate(gens, None)["pct_over_service_timeout"] == 50.0


def test_generations_are_never_stopped_at_12_seconds(tmp_path):
    # the client timeout stays 60 s and the options carry no 12 s limit
    assert bench.TIMEOUT_S == 60.0 and bench.SERVICE_TIMEOUT_S == 12.0
    fake = FakeOllama()
    assert run_main(tmp_path, fake) == 0
    assert all(p["options"] == {"num_predict": 80} for p in fake.chat_payloads)  # no 12 s limit in the call


def test_the_summary_has_an_over_12s_column_filled_from_the_generations(tmp_path):
    r = fake_result("slow:1b", "2026-10-14", wall=20.0)
    (tmp_path / "s.json").write_text(json.dumps(r), encoding="utf-8")
    text = bench.regenerate_summary(tmp_path).read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| slow:1b"))
    assert "| 100% |" in row  # every generation took 20 s

# --- S7b: shipped scoring, the new columns, --num-predict, before/after rows -------------------------------------------------------------


LLAMA_STYLE = (
    "**Inheritance in Java**\n======================\n\nInheritance is a fundamental concept in object-oriented "
    "programming. The child class inherits from the parent class.\n\nThe key rules of inheritance are"
)


def test_score_raw_marks_a_heading():
    assert sc.score_raw(LLAMA_STYLE, "theory", "length")["heading"] is True
    assert sc.score_raw(GOOD_THEORY, "theory", "stop")["heading"] is False


def test_would_ship_uses_the_truncation_flag_and_rejects_a_leak():
    assert sc.would_ship(LLAMA_STYLE, "theory", True) is True  # heading stripped, trimmed to a full sentence
    assert sc.would_ship("A loop is a way to repeat", "theory", True) is False  # no complete sentence
    leak = "We are given the topic: Inheritance. We are to provide: theory. We must follow the instructions exactly."
    assert sc.would_ship(leak, "theory", True) is False  # format-wise it has sentences, but a leak never ships
    assert sc.would_ship("Look:\n\n```java\nint x = 1;\nint y", "example", True) is False  # unclosed code dropped
    assert sc.would_ship(GOOD_EXAMPLE, "example", False) is True


def test_the_benchmark_and_the_service_judge_by_the_same_functions():
    # S8: one definition of "would it ship?". The scoring module imports it and keeps no copy.
    from app.generation import postprocess

    assert sc.would_ship is postprocess.would_ship
    assert sc.reasoning_leak is postprocess.reasoning_leak
    assert sc.LEAK_PHRASES is postprocess.LEAK_PHRASES


def test_score_generation_derives_truncation_from_done_reason():
    # LLAMA_STYLE ends mid-sentence: shippable only when trimmed (done_reason "length").
    final = finalise(LLAMA_STYLE, "theory", truncated=True)
    assert sc.score_generation(LLAMA_STYLE, final, "theory", "length")["score_final"]["usable"] is True
    cut_example = "Look:\n\n```java\nint x = 1;\nint y"
    assert sc.score_generation(cut_example, finalise(cut_example, "example", True), "example", "length")["score_final"]["usable"] is False


def test_score_generation_records_the_shipped_flags():
    final = finalise(LLAMA_STYLE, "theory", truncated=True)
    s = sc.score_generation(LLAMA_STYLE, final, "theory", "length")
    assert s["score_final"]["usable"] is True and s["score_raw"]["heading"] is True and s["score_raw"]["truncated"] is True
    assert s["score_final"]["java_complete"] is False


def gen2(strategy="theory", usable=True, java=True, heading=False, **kw):
    g = gen(strategy=strategy, **kw)
    g["score_final"].update(usable=usable, java_complete=java)
    g["score_raw"]["heading"] = heading
    return g


def test_aggregate_new_columns():
    gens = [
        gen2(usable=True, heading=True), gen2(usable=False, heading=True), gen2(usable=True), gen2(usable=True),
        gen2(strategy="example", usable=True, java=True), gen2(strategy="example", usable=False, java=False),
    ]
    a = sc.aggregate(gens, None)
    assert a["pct_usable"] == pytest.approx(100 * 4 / 6)
    assert a["pct_example_java_complete"] == 50.0
    assert a["pct_headings_raw"] == pytest.approx(100 * 2 / 6)


def test_aggregate_recomputes_the_new_columns_for_r1_results_that_lack_them():
    old = {"id": "x", "topic": "loops", "strategy": "theory", "run": 1, "wall_s": 5.0, "ttft_s": 0.1, "tok_s": 10.0,
           "done_reason": "length", "raw_text": LLAMA_STYLE,
           "score_raw": {"empty": False, "check_ok": False, "sentences_ok": True, "java_ok": True, "think_tag": False,
                         "reasoning_leak": False, "truncated": True},
           "score_final": {"check_ok": True, "sentences_ok": True, "think_tag": False, "reasoning_leak": False}}
    a = sc.aggregate([old], None)
    assert a["pct_usable"] == 100.0 and a["pct_headings_raw"] == 100.0
    no_text = {k: v for k, v in old.items() if k != "raw_text"}
    assert sc.aggregate([no_text], None)["pct_usable"] is None  # nothing to recompute from: n/a, not a guess


def test_summary_has_the_new_columns_and_the_decisive_one_is_bold(tmp_path):
    r = fake_result("m", "2026-10-15", num_predict=110)
    for g in r["generations"]:
        g["score_final"].update(usable=True, java_complete=True)
        g["score_raw"]["heading"] = False
    (tmp_path / "m.json").write_text(json.dumps(r), encoding="utf-8")
    text = bench.regenerate_summary(tmp_path).read_text(encoding="utf-8")
    header = next(line for line in text.splitlines() if line.startswith("| model"))
    for column in ("usable (would ship)", "example complete java", "headings (raw)", "over 12 s", "human rating (mean)"):
        assert column in header
    assert header.count("|") == 21 and text.splitlines()[4].count("|") == 21  # 20 columns, header and separator
    row = next(line for line in text.splitlines() if line.startswith("| m @110"))
    assert "| m @110 r2 (2026-10-15) |" in row and "**100%**" in row


def test_summary_shows_before_and_after_rows_for_the_same_model(tmp_path):
    r1 = fake_result("llama3.2:3b", "2026-10-15", num_predict=80, revision="r1")
    del r1["prompt_revision"]  # an old result file predates the field: it is r1
    r1["generations"] = [dict(g, raw_text=LLAMA_STYLE, done_reason="length") for g in r1["generations"]]
    r2a = fake_result("llama3.2:3b", "2026-10-15", num_predict=80)
    r2b = fake_result("llama3.2:3b", "2026-10-15", num_predict=110)
    for name, r in (("a.json", r1), ("b.json", r2a), ("c.json", r2b)):
        (tmp_path / name).write_text(json.dumps(r), encoding="utf-8")
    text = bench.regenerate_summary(tmp_path).read_text(encoding="utf-8")
    labels = [line.split("|")[1].strip() for line in text.splitlines() if line.startswith("| llama")]
    assert labels == ["llama3.2:3b @80 r1 (2026-10-15)", "llama3.2:3b @80 r2 (2026-10-15)", "llama3.2:3b @110 r2 (2026-10-15)"]


def test_num_predict_default_is_80_and_is_sent_and_recorded(tmp_path):
    fake = FakeOllama()
    assert run_main(tmp_path, fake) == 0
    assert all(p["options"] == {"num_predict": 80} for p in fake.chat_payloads)
    r = json.loads(next((tmp_path / "out").glob("qwen3_4b_*_np80_r2.json")).read_text(encoding="utf-8"))
    assert r["num_predict"] == 80 and r["call_parameters"]["options"] == {"num_predict": 80}
    assert r["prompt_revision"] == "r2" and len(r["prompt_set_sha256"]) == 64


def test_num_predict_110_is_sent_recorded_and_named_in_the_file(tmp_path):
    fake = FakeOllama()
    assert run_main(tmp_path, fake, "--num-predict", "110") == 0
    assert len(fake.chat_payloads) == 17 and all(p["options"] == {"num_predict": 110} for p in fake.chat_payloads)
    path = next((tmp_path / "out").glob("qwen3_4b_*_np110_r2.json"))
    r = json.loads(path.read_text(encoding="utf-8"))
    assert r["num_predict"] == 110 and r["call_parameters"]["options"]["num_predict"] == 110
    assert "@110 r2" in (tmp_path / "out" / "SUMMARY.md").read_text(encoding="utf-8")


def test_a_second_run_with_another_cap_never_overwrites_the_first_or_an_earlier_file(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    earlier = out / "qwen3_4b_2026-10-15.json"  # the pre-S7b naming
    earlier.write_text(json.dumps(fake_result("qwen3:4b", "2026-10-15", num_predict=80, revision="r1")), encoding="utf-8")
    before = earlier.read_bytes()
    assert run_main(tmp_path, FakeOllama(), "--num-predict", "80") == 0
    assert run_main(tmp_path, FakeOllama(), "--num-predict", "110") == 0
    names = sorted(p.name for p in out.glob("qwen3_4b_*.json"))
    assert len(names) == 3 and earlier.name in names
    assert earlier.read_bytes() == before  # untouched
    summary = (out / "SUMMARY.md").read_text(encoding="utf-8")
    assert summary.count("\n| qwen3:4b @") == 3  # before and after, both caps


def test_the_shipped_text_in_the_result_is_post_processed_with_the_truncation_flag(tmp_path):
    fake = FakeOllama(reply=LLAMA_STYLE, done_reason="length")
    assert run_main(tmp_path, fake) == 0
    r = json.loads(next((tmp_path / "out").glob("*_np80_r2.json")).read_text(encoding="utf-8"))
    g = r["generations"][0]
    assert g["raw_text"] == LLAMA_STYLE
    assert g["final_text"].startswith("Inheritance is a fundamental concept") and "key rules" not in g["final_text"]
    assert g["score_final"]["usable"] is True and g["score_raw"]["heading"] is True
    assert r["aggregates"]["pct_usable"] == 75.0  # 12 of 16 ship; the 4 example prompts have no java block in this reply
    assert r["aggregates"]["pct_headings_raw"] == 100.0
    assert r["aggregates"]["pct_example_java_complete"] == 0.0


def test_the_benchmarks_readme_records_the_one_revision_rule():
    readme = (Path(__file__).resolve().parents[1] / "benchmarks" / "llm" / "README.md").read_text(encoding="utf-8")
    assert "one prompt revision" in readme and "one re-run" in readme and "stop" in readme
    assert "usable (would ship)" in readme
