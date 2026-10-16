"""POST /tutor/message end to end, on template replies (no LLM) and on the mock provider.

The classifier behind the labels is a prototype proxy trained on synthetic answers (not a
validated confusion detector). Messages are hand-written. The contract items that make or break
the demo are tested one by one, and again on every response of a full episode.
"""

import asyncio
import importlib.util
import itertools
import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.generation.adapters as adapters_mod
import app.orchestrator as orchestrator
from app.config import DEFAULT_MODELS_DIR, Settings
from app.generation.adapters import STRATEGIES, MockAdapter, TemplateError, TemplateFallback
from app.generation.fixed_copy import CLARIFY, END_UNRESOLVED, OFFER_NEW_CYCLE
from app.generation.prompts import NO_REPEAT_INSTRUCTION
from app.main import create_app
from app.schemas import TutorResponse
from app.topics import GENERAL, public_topics
from frontend_sim import FIXTURES, STATE_KEYS, Episode, contract_violations, fixture

TOPIC_IDS = [t["id"] for t in public_topics()] + [GENERAL]
CONFUSED = "I don't understand"
TO_OFFER = [CONFUSED] * 5
FIXED_NOW = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
FRONTEND_FIXTURES = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "features" / "tutor" / "api" / "fixtures"
)
TEMPLATES = TemplateFallback()


def make_app(models_dir=None, adapter=None, **settings):
    ids = itertools.count(1)
    return create_app(
        models_dir,
        settings=Settings(_env_file=None, **settings),
        adapter=adapter,
        now=lambda: FIXED_NOW,
        new_episode_id=lambda: f"ep_{next(ids)}",
    )


@pytest.fixture(scope="module")
def client():
    with TestClient(make_app()) as c:
        yield c


@pytest.fixture
def warnings_and_errors(caplog):
    """Capture records from the 'app' logger tree (it sets propagate=False, so attach directly)."""
    app_logger = logging.getLogger("app")
    app_logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger="app")
    yield caplog
    app_logger.removeHandler(caplog.handler)


def projection(res: dict) -> tuple:
    """What a turn decided, without ids, timings or timestamps."""
    s = res["updated_state"]
    return (
        res["action"], res["strategy"], res["trigger"], s["cycle"], s["awaiting_cycle_confirmation"],
        res["response"], res["confusion"], res["detected_request"], len(s["strategies_used"]),
        len(s["prior_explanations"]), res["episode_log"] is not None,
    )


# --- the full episode over HTTP -------------------------------------------------------------------------


def test_full_episode_over_http_on_inheritance(client):
    ep = Episode(client)
    res = ep.play(*TO_OFFER, "wait, what do you mean?", "yes", "got it")

    # the exact decision sequence
    assert [(r["action"], r["strategy"], r["trigger"]) for r in res] == [
        ("explain", "theory", "default"),
        ("explain", "example", "confusion"),
        ("explain", "simplified", "confusion"),
        ("explain", "analogy", "confusion"),
        ("offer_new_cycle", None, None),
        ("clarify", None, None),
        ("explain", "theory", "confusion"),
        ("resolved", None, None),
    ]
    flags = [r["updated_state"]["awaiting_cycle_confirmation"] for r in res]
    assert flags == [False, False, False, False, True, True, False, False]  # true on offer + clarify, false after accept
    assert [r["updated_state"]["cycle"] for r in res] == [1, 1, 1, 1, 1, 1, 2, 2]

    # claim C3: the cycle 2 theory text differs from the cycle 1 text (the second variant)
    assert res[6]["response"] != res[0]["response"]
    assert res[0]["response"] == TEMPLATES.get("inheritance", "theory", 1)
    assert res[6]["response"] == TEMPLATES.get("inheritance", "theory", 2)

    # every response: contract items 1-5 and the extra rules, validated against the model
    for i, r in enumerate(res, start=1):
        assert contract_violations(r, f"req-{i}") == [], (i, r["action"])
        TutorResponse.model_validate(r)

    # exactly the key set of the copied fixtures
    explain_fx, resolved_fx = fixture("tutor-response.explain.json"), fixture("tutor-response.resolved.json")
    for r in res:
        assert set(r) == set(explain_fx) == set(resolved_fx)
        assert set(r["meta"]) - {"fallback", "resolution_declined"} == set(explain_fx["meta"])  # fallback (optional) and R6's additive field
        assert set(r["meta"]["latency_ms"]) == set(explain_fx["meta"]["latency_ms"])
        assert set(r["updated_state"]) == set(explain_fx["updated_state"]) == STATE_KEYS
        assert set(r["confusion"]) == set(explain_fx["confusion"])
    assert set(res[-1]["episode_log"]) == set(resolved_fx["episode_log"])
    assert set(res[-1]["episode_log"]["deliveries"][0]) - {"reaction_override"} == set(resolved_fx["episode_log"]["deliveries"][0])  # R6's additive field

    # the closing log
    log = res[-1]["episode_log"]
    assert (log["outcome"], log["cycles"], log["winning_strategy"]) == ("resolved", 2, "theory")
    assert [d["cycle"] for d in log["deliveries"]] == [1, 1, 1, 1, 2]
    assert (log["counted_strategies"], log["requested_strategies"], log["is_weak"]) == (5, 0, True)
    assert log["model_version"] == "clf-v1.0.0" and log["topic"] == "inheritance" and log["student_id"] == "stu_1"
    assert res[-1]["response"] == "Nice work! The **Theory** explanation did the trick."


def test_decline_ends_unresolved_with_a_log_and_is_weak(client):
    res = Episode(client).play(*TO_OFFER, "no")
    last = res[-1]
    assert (last["action"], last["strategy"], last["trigger"]) == ("end_unresolved", None, None)
    assert last["response"] == END_UNRESOLVED
    assert last["updated_state"]["awaiting_cycle_confirmation"] is False
    log = last["episode_log"]
    assert (log["outcome"], log["is_weak"], log["winning_strategy"]) == ("end_unresolved", True, None)
    assert len(log["deliveries"]) == 4 and log["cycles"] == 1
    assert contract_violations(last, "req-6") == []


def test_exhausting_cycle_two_ends_unresolved(client):
    res = Episode(client).play(*TO_OFFER, "yes", *[CONFUSED] * 4)
    assert [r["action"] for r in res][-1] == "end_unresolved"
    assert res[-1]["episode_log"]["cycles"] == 2 and len(res[-1]["episode_log"]["deliveries"]) == 8
    assert all(contract_violations(r, f"req-{i}") == [] for i, r in enumerate(res, start=1))


def test_general_topic_full_episode_uses_the_general_templates(client):
    ep = Episode(client, topic="general")
    res = ep.play(*TO_OFFER, "yes", "got it")
    explains = [r for r in res if r["action"] == "explain"]
    assert len(explains) == 5
    for r in explains:
        cycle = r["updated_state"]["cycle"]
        assert r["response"] == TEMPLATES.get(GENERAL, r["strategy"], cycle)
    assert res[-1]["action"] == "resolved" and res[-1]["episode_log"]["topic"] == "general"
    assert all(contract_violations(r, f"req-{i}") == [] for i, r in enumerate(res, start=1))


# --- contract items 1-5, each on its own ------------------------------------------------------------------


def test_item1_offer_new_cycle_sets_the_flag_and_clarify_keeps_it(client):
    ep = Episode(client)
    res = ep.play(*TO_OFFER)
    assert res[-1]["action"] == "offer_new_cycle" and res[-1]["response"] == OFFER_NEW_CYCLE
    assert res[-1]["updated_state"]["awaiting_cycle_confirmation"] is True
    clarify = ep.play("hmm, maybe")[0]
    assert clarify["action"] == "clarify" and clarify["response"] == CLARIFY
    assert clarify["updated_state"]["awaiting_cycle_confirmation"] is True
    accept = ep.play("yes")[0]
    assert accept["updated_state"]["awaiting_cycle_confirmation"] is False


def test_item1_a_request_during_a_pending_offer_still_clarifies_and_keeps_the_flag(client):
    ep = Episode(client)
    ep.play(*TO_OFFER)
    r = ep.play("show me an example")[0]
    assert r["action"] == "clarify" and r["updated_state"]["awaiting_cycle_confirmation"] is True


def test_item2_episode_log_is_non_null_if_and_only_if_terminal(client):
    for script in ([*TO_OFFER, "wait, what do you mean?", "yes", "got it"], [*TO_OFFER, "no"]):
        for r in Episode(client).play(*script):
            terminal = r["action"] in ("resolved", "end_unresolved")
            assert (r["episode_log"] is not None) == terminal, r["action"]


@pytest.mark.parametrize("topic", TOPIC_IDS)
def test_item3_every_explain_ends_with_exactly_one_check_line(client, topic):
    for message in ("define it", "show me", "simplify", "analogy"):  # one request per strategy
        r = Episode(client, topic=topic).play(message)[0]
        assert r["action"] == "explain"
        lines = [ln for ln in r["response"].splitlines() if ln.strip()]
        assert lines[-1].startswith("**Check:**")
        assert r["response"].count("**Check:**") == 1


def test_item4_meta_fallback_is_true_on_every_template_turn(client):
    for r in Episode(client).play(*TO_OFFER, "yes", "got it"):
        assert r["meta"]["fallback"] is True
        assert r["meta"]["llm"] == "template"


def test_item5_updated_state_is_complete_and_request_id_echoed_exactly(client):
    ep = Episode(client)
    odd_ids = ["  Req-ID/ü 1  ", "a" * 200, "0"]
    for message, rid in zip(["define it", CONFUSED, "got it"], odd_ids):
        body = ep.body(message)
        body["request_id"] = rid
        r = client.post("/tutor/message", json=body)
        assert r.status_code == 200
        res = r.json()
        assert res["request_id"] == rid  # exactly: no trim, no case change, no regeneration
        assert set(res["updated_state"]) == STATE_KEYS
        ep.state = res["updated_state"]
        ep.history += [
            {"role": "student", "text": message, "ts": "t"},
            {"role": "tutor", "text": res["response"], "ts": "t", **({"strategy": res["strategy"]} if res["strategy"] else {})},
        ]


def test_explain_always_has_a_strategy_and_probability_is_a_number_even_when_a_rule_decided(client):
    res = Episode(client).play(CONFUSED, "got it")
    assert res[0]["confusion"]["source"] == "rule"
    for r in res:
        assert isinstance(r["confusion"]["probability"], float) and 0 <= r["confusion"]["probability"] <= 1
        assert r["action"] != "explain" or r["strategy"] is not None
    # the rule said understood while the model's own P stays high: the returned P is the model's
    assert res[1]["confusion"]["label"] == "understood" and res[1]["confusion"]["probability"] > 0.5


def test_detected_request_is_reported(client):
    r = Episode(client).play("show me")[0]
    assert (r["detected_request"], r["strategy"], r["trigger"]) == ("example", "example", "request")
    assert Episode(client).play(CONFUSED)[0]["detected_request"] is None


def test_latency_keys_are_present_and_non_negative_with_classify_positive(client):
    for r in Episode(client).play(CONFUSED, CONFUSED):
        lat = r["meta"]["latency_ms"]
        assert set(lat) == {"classify", "llm", "total"}
        assert lat["classify"] > 0 and lat["llm"] >= 0 and lat["total"] >= lat["classify"]
    non_explain = Episode(client).play(*TO_OFFER)[-1]
    assert non_explain["meta"]["latency_ms"]["llm"] == 0  # fixed copy: no generation step


@pytest.mark.parametrize("topic", TOPIC_IDS)
def test_every_topic_strategy_reply_is_the_template(client, topic):
    for message, strategy in (("define it", "theory"), ("show me", "example"), ("simplify", "simplified"), ("analogy", "analogy")):
        r = Episode(client, topic=topic).play(message)[0]
        assert r["strategy"] == strategy and r["response"] == TEMPLATES.get(topic, strategy, 1)


# --- C2: the classifier sees the current message only ---------------------------------------------------------


def test_c2_same_message_with_long_history_and_empty_history_gives_the_same_confusion_block(client):
    long = Episode(client)
    long.play(*TO_OFFER[:3])
    with_history = long.play(CONFUSED)[0]["confusion"]
    alone = Episode(client).play(CONFUSED)[0]["confusion"]
    assert with_history == alone


def test_c2_classify_receives_exactly_the_raw_message(client, monkeypatch):
    seen = []
    real = orchestrator.classify

    def spy(model, text):
        seen.append(text)
        return real(model, text)

    monkeypatch.setattr(orchestrator, "classify", spy)
    ep = Episode(client)
    ep.play(CONFUSED, CONFUSED)  # build up history
    seen.clear()
    raw = "  I DON’T   Understand\t\n"
    r = ep.send(raw)
    assert r.status_code == 200 and r.json()["action"] == "explain"
    assert seen == [raw]  # raw, unmodified, and nothing else (no history, no previous tutor turn)


# --- C5: stateless ------------------------------------------------------------------------------------------------


def test_c5_two_interleaved_episodes_each_match_their_solo_run(client):
    script_a = ("inheritance", [*TO_OFFER, "yes", "got it"])
    script_b = ("loops", ["define it", CONFUSED, CONFUSED, "no idea", "still confused", "no"])

    def solo(topic, msgs, sid):
        return [projection(r) for r in Episode(client, topic=topic, student_id=sid).play(*msgs)]

    solo_a, solo_b = solo(*script_a, "sa"), solo(*script_b, "sb")
    a, b = Episode(client, topic=script_a[0], student_id="sa"), Episode(client, topic=script_b[0], student_id="sb")
    out_a, out_b = [], []
    for i in range(max(len(script_a[1]), len(script_b[1]))):
        if i < len(script_a[1]):
            out_a.append(projection(a.play(script_a[1][i])[0]))
        if i < len(script_b[1]):
            out_b.append(projection(b.play(script_b[1][i])[0]))
    assert out_a == solo_a and out_b == solo_b


def test_c5_a_new_app_instance_in_the_middle_of_an_episode_continues_it():
    msgs = [*TO_OFFER, "wait, what do you mean?", "yes", "got it"]
    with TestClient(make_app()) as one:
        uninterrupted = [projection(r) for r in Episode(one).play(*msgs)]
    with TestClient(make_app()) as first:
        ep = Episode(first)
        part1 = [projection(r) for r in ep.play(*msgs[:5])]  # up to the offer
    with TestClient(make_app()) as second:  # a restart: nothing remembered server-side
        ep.client = second
        part2 = [projection(r) for r in ep.play(*msgs[5:])]
    assert part1 + part2 == uninterrupted


def test_c5_replaying_an_old_request_gives_the_same_decision_as_the_first_time(client):
    ep = Episode(client)
    ep.play(*TO_OFFER[:3])
    old_body = ep.bodies[2]  # the third turn's request, sent before later turns advanced the episode
    first = projection(ep.responses[2])
    ep.play(CONFUSED, CONFUSED)  # the episode moves on
    replay = client.post("/tutor/message", json=old_body).json()
    assert projection(replay) == first  # only the echoed state counts, not anything the server remembers


def test_c5_the_server_keeps_no_per_episode_state_in_the_orchestrator_module():
    leftovers = {k: v for k, v in vars(orchestrator).items() if isinstance(v, (dict, list, set)) and not k.startswith("__")}
    assert leftovers == {}


# --- the confusion override (lead ruling) ------------------------------------------------------------------------------


def test_override_first_message_rule_confusion_plus_request_is_a_counted_confusion_delivery(client):
    res = Episode(client).play("I don't understand, explain the theory again")[0]
    assert res["confusion"]["source"] == "rule" and res["confusion"]["label"] == "confused"
    assert (res["detected_request"], res["strategy"], res["trigger"]) == ("theory", "theory", "confusion")
    assert res["updated_state"]["strategies_used"] == [{"strategy": "theory", "trigger": "confusion"}]


def test_a_request_with_model_sourced_confusion_and_no_rule_phrase_stays_a_request(client):
    res = Episode(client).play("give me an example please")[0]
    # precondition that makes this test meaningful: the MODEL said confused, no rule decided
    assert res["confusion"]["source"] == "model" and res["confusion"]["label"] == "confused"
    assert (res["strategy"], res["trigger"]) == ("example", "request")


def test_documented_limitation_requesting_a_strategy_already_counted_in_the_cycle_stays_a_request(client):
    """Plan `04` §3.1a: the confusion override cannot apply to a strategy already delivered as a counted
    delivery in the current cycle (counting a repeat would put five counted deliveries in a cycle and
    break the cycle derivation of §3.1), so the repeat stays `trigger: request`.

    The limitation is in the AGGREGATE (`counted_strategies`), not the RECORD: the repeat is still in
    `episode_log.deliveries` with `trigger: "request"`, which this test pins. The PP2 fix is a
    per-delivery `counted` flag, which is a contract change (frozen frontend types), so not in PP1."""
    ep = Episode(client)
    first = ep.play(CONFUSED)[0]
    assert first["strategy"] == "theory"
    again = ep.play("I don't understand, explain the theory again")[0]
    assert again["confusion"]["source"] == "rule"
    assert (again["strategy"], again["trigger"]) == ("theory", "request")  # not counted again
    terminal = ep.play("got it")[0]
    assert terminal["action"] == "resolved"
    log = terminal["episode_log"]
    # the first theory is the episode opener (trigger "default"); the confused repeat IS recorded
    assert [(d["strategy"], d["trigger"]) for d in log["deliveries"]] == [("theory", "default"), ("theory", "request")]
    assert log["counted_strategies"] == 1  # but the aggregate counts only the opener


def test_a_plain_request_with_no_confusion_stays_a_request(client):
    res = Episode(client).play("show me")[0]
    assert res["trigger"] == "request"
    assert res["updated_state"]["strategies_used"] == [{"strategy": "example", "trigger": "request"}]


# --- consecutive student turns (a failed send then a retry) --------------------------------------------------------


def test_consecutive_student_turns_are_accepted_warned_without_text_and_paired_correctly(client, warnings_and_errors):
    ep = Episode(client)
    ep.play(CONFUSED)  # delivery 1
    assert ep.send("got it", fail=True) is None  # this message failed to send: the service never saw it
    ep.play(CONFUSED, CONFUSED, CONFUSED)  # the retry flow continues: deliveries 2-4
    ep.play(CONFUSED)  # the offer
    ep.play("yes", "got it")  # accept into cycle 2, then resolve
    terminal = ep.responses[-1]
    assert terminal["action"] == "resolved"
    log = terminal["episode_log"]
    # delivery 1's reaction is the LAST student turn before the next tutor turn ("I don't understand",
    # confused by rule), NOT the failed "got it" that sat in front of it (understood by rule)
    assert (log["deliveries"][0]["student_label"], log["deliveries"][0]["source"]) == ("confused", "rule")
    text = warnings_and_errors.text
    assert "consecutive student turn" in text and ep.state["episode_id"] in text
    assert "got it" not in text and "I don't understand" not in text  # never the student text


def test_the_warning_counts_each_adjacent_pair(client, warnings_and_errors):
    ep = Episode(client)
    ep.play(CONFUSED)
    for failed in ("x", "y", "z"):
        ep.send(failed, fail=True)  # three failed sends in a row: three adjacent student turns, two pairs
    ep.play(CONFUSED)
    assert "2 consecutive student turn" in warnings_and_errors.text


def test_no_warning_when_there_are_no_adjacent_student_turns(client, warnings_and_errors):
    Episode(client).play(CONFUSED, CONFUSED)
    assert "consecutive" not in warnings_and_errors.text


# --- errors ---------------------------------------------------------------------------------------------------------------


def test_an_impossible_echoed_state_is_422(client):
    ep = Episode(client)
    ep.play(CONFUSED)
    body = ep.body(CONFUSED)
    body["state"]["cycle"] = 5
    r = client.post("/tutor/message", json=body)
    assert r.status_code == 422 and "cycle" in r.json()["detail"]


def test_a_non_request_count_the_engine_could_never_produce_is_422(client):
    ep = Episode(client)
    ep.play(CONFUSED)
    body = ep.body(CONFUSED)
    body["state"]["strategies_used"] = [{"strategy": "theory", "trigger": "default"}] * 3
    assert client.post("/tutor/message", json=body).status_code == 422


def test_a_terminal_turn_whose_history_contradicts_the_state_is_422(client):
    ep = Episode(client)
    ep.play(CONFUSED, CONFUSED)
    body = ep.body("got it")
    body["history"] = [h for h in body["history"] if h["role"] == "student"]  # the tutor turns vanished
    r = client.post("/tutor/message", json=body)
    assert r.status_code == 422 and "episode log" in r.json()["detail"]


def test_a_terminal_turn_with_an_empty_student_id_is_422_not_500(client):
    ep = Episode(client, student_id="")
    ep.play(CONFUSED)
    r = ep.send("got it")
    assert r.status_code == 422 and "episode log" in r.json()["detail"]


def test_an_empty_request_id_is_422_not_a_500(client):
    body = Episode(client).body("hi")
    body["request_id"] = ""
    assert client.post("/tutor/message", json=body).status_code == 422


def test_invalid_body_is_422(client):
    assert client.post("/tutor/message", json={"message": "hi"}).status_code == 422
    body = Episode(client).body("hi")
    body["topic"] = "nonsense"
    assert client.post("/tutor/message", json=body).status_code == 422


def test_degraded_app_is_503_and_still_serves_topics(tmp_path):
    models = tmp_path / "models"
    shutil.copytree(DEFAULT_MODELS_DIR, models)
    path = models / "clf-v1.0.0" / "pipeline.joblib"
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 1
    path.write_bytes(bytes(data))
    with TestClient(make_app(models)) as c:
        assert c.get("/health").json()["status"] == "degraded"
        r = Episode(c).send(CONFUSED)
        assert r.status_code == 503 and "model not loaded" in r.json()["detail"]
        bad = Episode(c).body("hi")
        bad["topic"] = "nonsense"
        assert c.post("/tutor/message", json=bad).status_code == 422
        assert len(c.get("/topics").json()) == 14


# --- LLM_PROVIDER=mock ---------------------------------------------------------------------------------------------------------


def test_mock_provider_reports_fallback_false_and_llm_mock():
    adapter = MockAdapter()
    with TestClient(make_app(adapter=adapter, LLM_PROVIDER="mock")) as c:
        res = Episode(c).play(CONFUSED, CONFUSED)
    for r in res:
        assert r["meta"]["llm"] == "mock" and r["meta"]["fallback"] is False
        assert "mock" in r["response"].lower()  # theory gets the plain mock text, example the java one
        assert contract_violations(r, f"req-{res.index(r) + 1}") == []
    assert len(adapter.prompts) == 2


def test_mock_provider_non_explain_turns_are_not_marked_as_fallback():
    with TestClient(make_app(LLM_PROVIDER="mock")) as c:
        res = Episode(c).play(*TO_OFFER)
    assert res[-1]["action"] == "offer_new_cycle" and res[-1]["meta"]["fallback"] is False
    assert res[-1]["meta"]["latency_ms"]["llm"] == 0


def test_mock_reply_with_no_check_line_still_gets_exactly_one():
    with TestClient(make_app(adapter=MockAdapter(raw="A loop repeats code."), LLM_PROVIDER="mock")) as c:
        r = Episode(c).play(CONFUSED)[0]
    assert r["response"].count("**Check:**") == 1
    assert r["response"].splitlines()[-1].startswith("**Check:**")
    assert r["meta"]["fallback"] is False


def test_mock_reply_with_thinking_and_two_checks_is_cleaned():
    raw = "<think>plan</think>Loops repeat code.\n\n**Check:** A?\n**Check:** B?"
    with TestClient(make_app(adapter=MockAdapter(raw=raw), LLM_PROVIDER="mock")) as c:
        r = Episode(c).play(CONFUSED)[0]
    assert "think" not in r["response"] and r["response"].count("**Check:**") == 1
    assert r["response"].endswith("**Check:** B?")


class Boom:
    async def complete(self, prompt, timeout_s):
        raise RuntimeError("model crashed")


class Hangs:
    async def complete(self, prompt, timeout_s):
        await asyncio.sleep(30)


@pytest.mark.parametrize("adapter, settings", [(Boom(), {}), (Hangs(), {"LLM_TIMEOUT_S": 0.05})], ids=["raises", "times-out"])
def test_a_failing_llm_serves_the_template_with_fallback_true_and_a_warning(adapter, settings, warnings_and_errors):
    secret = "zebra-unique-student-phrase"
    started = time.perf_counter()
    with TestClient(make_app(adapter=adapter, LLM_PROVIDER="mock", **settings)) as c:
        ep = Episode(c)
        r = ep.send(f"{secret} I don't understand")
    assert r.status_code == 200
    res = r.json()
    assert res["meta"]["fallback"] is True and res["meta"]["llm"] == "mock"
    assert res["response"] == TEMPLATES.get("inheritance", "theory", 1)
    assert time.perf_counter() - started < 10  # the 30 s hang was cut off by the timeout
    warnings = [rec for rec in warnings_and_errors.records if rec.levelno == logging.WARNING]
    reason = "(RuntimeError)" if isinstance(adapter, Boom) else "(timeout)"
    assert [rec.getMessage() for rec in warnings if "LLM reply not served" in rec.getMessage() and reason in rec.getMessage()]
    assert secret not in warnings_and_errors.text  # never the student text
    assert "model crashed" not in warnings_and_errors.text  # nor the exception message


def test_cycle_two_prompt_carries_prior_explanations_and_cycle_one_does_not():
    adapter = MockAdapter()
    with TestClient(make_app(adapter=adapter, LLM_PROVIDER="mock")) as c:
        ep = Episode(c)
        res = ep.play(*TO_OFFER, "yes")
    prompts = adapter.prompts
    assert len(prompts) == 5  # four cycle-1 explains, then the cycle-2 theory
    assert all("Do not repeat these explanations" not in p for p in prompts[:4])
    assert "Do not repeat these explanations; use a different angle." in prompts[4]
    assert "This is a mock explanation" in prompts[4]  # an earlier explanation, echoed back
    assert "Explanation cycle: 2" in prompts[4]
    assert len(res[-1]["updated_state"]["prior_explanations"]) == 5


def test_prompt_contains_the_raw_student_message_inside_its_block():
    adapter = MockAdapter()
    msg = "  I DON'T understand\tthis  "
    with TestClient(make_app(adapter=adapter, LLM_PROVIDER="mock")) as c:
        Episode(c).play(msg)
    assert f"<student_message>\n{msg}\n</student_message>" in adapter.prompts[0]


def _raw_body(message: str, state: dict) -> dict:
    return {
        "request_id": "req-1", "student_id": "stu_1", "session_id": "sess_1", "topic": "inheritance",
        "message": message, "history": [], "state": state,
    }


def _cycle1_complete_state(prior_explanations: list[str]) -> dict:
    return {
        "episode_id": "ep_s8b_test",
        "cycle": 1,
        "strategies_used": [
            {"strategy": "theory", "trigger": "default"},
            {"strategy": "example", "trigger": "confusion"},
            {"strategy": "simplified", "trigger": "confusion"},
            {"strategy": "analogy", "trigger": "confusion"},
        ],
        "awaiting_cycle_confirmation": True,
        "prior_explanations": prior_explanations,
    }


def test_cycle_two_theory_prompt_carries_only_the_cycle_one_theory_text():
    state = _cycle1_complete_state(["THEORY_MARKER_1", "EXAMPLE_MARKER_1", "SIMPLIFIED_MARKER_1", "ANALOGY_MARKER_1"])
    adapter = MockAdapter()
    with TestClient(make_app(adapter=adapter, LLM_PROVIDER="mock")) as c:
        r = c.post("/tutor/message", json=_raw_body("yes", state))
    assert r.status_code == 200
    res = r.json()
    assert (res["action"], res["strategy"], res["updated_state"]["cycle"]) == ("explain", "theory", 2)
    prompt = adapter.prompts[-1]
    assert "Explanation cycle: 2" in prompt and NO_REPEAT_INSTRUCTION in prompt
    assert "THEORY_MARKER_1" in prompt
    for marker in ("EXAMPLE_MARKER_1", "SIMPLIFIED_MARKER_1", "ANALOGY_MARKER_1"):
        assert marker not in prompt


def test_a_mismatched_echoed_state_falls_back_to_every_prior_with_exactly_one_warning(warnings_and_errors):
    # prior_explanations has 1 entry but strategies_used has 4: the pairing is unknowable.
    state = _cycle1_complete_state(["ONLY_ONE_MARKER_zebra"])
    adapter = MockAdapter()
    with TestClient(make_app(adapter=adapter, LLM_PROVIDER="mock")) as c:
        r = c.post("/tutor/message", json=_raw_body("yes", state))
    assert r.status_code == 200
    prompt = adapter.prompts[-1]
    assert "ONLY_ONE_MARKER_zebra" in prompt  # the mismatch falls back to passing everything
    warnings = [rec.getMessage() for rec in warnings_and_errors.records if rec.levelno == logging.WARNING]
    mismatches = [w for w in warnings if "cannot pair prior_explanations" in w]
    assert len(mismatches) == 1
    assert "ep_s8b_test" in mismatches[0]
    assert "yes" not in mismatches[0] and "ONLY_ONE_MARKER_zebra" not in mismatches[0]


def test_prior_explanations_grow_by_the_reply_each_explain_turn(client):
    res = Episode(client).play(CONFUSED, CONFUSED, CONFUSED)
    for i, r in enumerate(res, start=1):
        prior = r["updated_state"]["prior_explanations"]
        assert len(prior) == i and prior[-1] == r["response"]
    non_explain = Episode(client).play(*TO_OFFER)[-1]
    assert len(non_explain["updated_state"]["prior_explanations"]) == 4  # not appended on an offer


# --- startup and settings ----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["openai", "Ollama", "", "llama3.2:3b"])
def test_unknown_llm_provider_fails_at_startup_with_a_clear_message(value):
    with pytest.raises(ValueError, match="not supported; use 'ollama', 'template' or 'mock'"):
        Settings(_env_file=None, LLM_PROVIDER=value)


def test_unknown_llm_provider_from_the_environment_fails_too(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "bogus")
    with pytest.raises(ValueError, match="not supported"):
        Settings(_env_file=None)


def test_settings_defaults(monkeypatch):
    # The project owner's decision (D2): the LLM is the default provider, the template the safety net.
    for var in ("LLM_PROVIDER", "LLM_MODEL", "OLLAMA_URL", "LLM_MAX_TOKENS", "LLM_TIMEOUT_S", "TURN_LOG_PATH"):
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert (s.LLM_PROVIDER, s.LLM_MODEL, s.LLM_MAX_TOKENS, s.LLM_TIMEOUT_S, s.TURN_LOG_PATH) == (
        "ollama", "llama3.2:3b", 110, 18.0, None
    )
    assert s.OLLAMA_URL == "http://127.0.0.1:11434"  # 127.0.0.1, not localhost (IPv6 lookup delay on Windows)


def test_a_broken_template_file_fails_startup_loudly(tmp_path, monkeypatch):
    bad = tmp_path / "fallbacks.yaml"
    bad.write_text("templates: {}\n", encoding="utf-8")
    monkeypatch.setattr(adapters_mod, "DEFAULT_TEMPLATES", bad)
    with pytest.raises(TemplateError):
        with TestClient(make_app()):
            pass


# --- R4: the opt-in per-turn research log -----------------------------------------------------------------------------------------------

TURN_KEYS = {
    "ts", "episode_id", "student_id", "topic", "message", "preceding_tutor_turn", "label", "probability",
    "source", "matched_phrase", "model_label", "disagreement", "detected_request", "action", "strategy",
    "trigger", "cycle", "question_guard",
}


def test_r4_unset_writes_nothing_to_disk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(make_app()) as c:
        Episode(c).play(CONFUSED, "got it")
    assert list(tmp_path.iterdir()) == []


def test_r4_set_writes_one_valid_json_line_per_turn(tmp_path):
    path = tmp_path / "turns.jsonl"
    with TestClient(make_app(TURN_LOG_PATH=path)) as c:
        ep = Episode(c)
        res = ep.play(CONFUSED, "show me", "got it")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    rows = [json.loads(line) for line in lines]
    assert all(set(r) == TURN_KEYS for r in rows)
    assert rows[0]["message"] == CONFUSED and rows[0]["preceding_tutor_turn"] is None
    assert rows[1]["preceding_tutor_turn"] == res[0]["response"]  # the last tutor turn in history
    assert rows[2]["preceding_tutor_turn"] == res[1]["response"]
    assert rows[1]["detected_request"] == "example" and rows[1]["trigger"] == "request"
    assert rows[0]["episode_id"] == res[0]["updated_state"]["episode_id"] and rows[0]["student_id"] == "stu_1"
    assert rows[2]["action"] == "resolved" and rows[2]["cycle"] == 1
    # "got it": the rule said understood while the model alone said confused -> a disagreement
    assert rows[2]["label"] == "understood" and rows[2]["model_label"] == "confused" and rows[2]["disagreement"] is True
    assert rows[0]["disagreement"] is False and rows[0]["matched_phrase"] == "i don't understand"
    assert rows[0]["probability"] == res[0]["confusion"]["probability"]


def test_r4_an_unwritable_path_never_fails_the_turn(tmp_path, warnings_and_errors):
    path = tmp_path / "no_such_dir" / "turns.jsonl"
    with TestClient(make_app(TURN_LOG_PATH=path)) as c:
        r = Episode(c).send(CONFUSED)
    assert r.status_code == 200 and r.json()["action"] == "explain"
    errors = [rec for rec in warnings_and_errors.records if rec.levelno == logging.ERROR]
    assert any("turn log write failed" in rec.getMessage() for rec in errors)
    assert not path.exists()


# --- fixtures: drift guards -----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["tutor-response.explain.json", "tutor-response.resolved.json"])
def test_response_fixture_copy_matches_frontend_source(name):
    source = FRONTEND_FIXTURES / name
    if not source.exists():
        pytest.skip(f"frontend fixture not present in this environment: {source}")
    assert (FIXTURES / name).read_bytes() == source.read_bytes()


@pytest.mark.parametrize("name", ["tutor-response.explain.json", "tutor-response.resolved.json"])
def test_the_frozen_response_fixtures_validate_against_our_response_model(name):
    TutorResponse.model_validate(fixture(name))


def test_the_response_model_rejects_what_the_frontend_schema_rejects():
    ok = fixture("tutor-response.resolved.json")
    for mutate in (
        lambda r: r.update(episode_log=None),  # terminal without a log
        lambda r: r.update(action="explain", strategy=None, trigger=None),  # log on a non-terminal action
        lambda r: r.update(surprise=1),  # a field the contract lacks
        lambda r: r["updated_state"].pop("cycle"),  # incomplete state
    ):
        bad = json.loads(json.dumps(ok))
        mutate(bad)
        with pytest.raises(Exception):
            TutorResponse.model_validate(bad)
    for mutate in (
        lambda r: r.update(strategy="theory"),  # strategy on a non-explain reply
        lambda r: r.update(action="clarify", episode_log=None, strategy=None, trigger=None),  # clarify without the flag
    ):
        bad = json.loads(json.dumps(ok))
        mutate(bad)
        with pytest.raises(Exception):
            TutorResponse.model_validate(bad)
    explain = fixture("tutor-response.explain.json")
    for mutate in (
        lambda r: r.update(strategy=None),
        lambda r: r["updated_state"].update(awaiting_cycle_confirmation=False) or r.update(action="offer_new_cycle", strategy=None, trigger=None),
    ):
        bad = json.loads(json.dumps(explain))
        mutate(bad)
        with pytest.raises(Exception):
            TutorResponse.model_validate(bad)


# --- the smoke script ------------------------------------------------------------------------------------------------------------------------


def load_smoke():
    path = Path(__file__).resolve().parents[1] / "scripts" / "smoke_episode.py"
    spec = importlib.util.spec_from_file_location("smoke_episode", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_script_passes_against_the_app(client):
    smoke = load_smoke()
    rows, violations, log = smoke.run_episode(client, expect_fallback=True)
    assert violations == [] and len(rows) == 8 and log["outcome"] == "resolved"


def test_smoke_script_can_fail_when_a_contract_item_is_violated(client):
    smoke = load_smoke()

    class DropsTheFlag:
        def post(self, url, json):
            r = client.post(url, json=json)
            body = r.json()
            if body.get("action") == "offer_new_cycle":
                body["updated_state"]["awaiting_cycle_confirmation"] = False  # the dead-end bug
            return type("R", (), {"status_code": r.status_code, "json": lambda self: body, "text": ""})()

    _, violations, _ = smoke.run_episode(DropsTheFlag(), expect_fallback=True)
    assert any("awaiting_cycle_confirmation" in v for v in violations)


def test_smoke_script_flags_a_wrong_fallback_expectation(client):
    smoke = load_smoke()
    _, violations, _ = smoke.run_episode(client, expect_fallback=False)
    assert any("meta.fallback" in v for v in violations)


def test_smoke_script_main_returns_2_when_the_server_is_unreachable():
    assert load_smoke().main(["--url", "http://127.0.0.1:9"]) == 2
