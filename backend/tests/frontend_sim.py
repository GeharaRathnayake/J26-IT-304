"""Test helper: drives POST /tutor/message the way the frontend does (reducer.ts / episodeRules.ts).

- the request carries `history` and `state` as they were BEFORE the current message;
- the current message is NOT in `history`;
- a tutor reply is appended to history with its `strategy` only when it delivered one;
- `state` is replaced by the reply's `updated_state`, verbatim;
- a FAILED send leaves the student's message in history with no tutor reply after it.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from app.schemas import TutorResponse

FIXTURES = Path(__file__).resolve().parent / "contract_fixtures"
TS = "2026-10-14T10:00:00Z"
STATE_KEYS = {"episode_id", "cycle", "strategies_used", "awaiting_cycle_confirmation", "prior_explanations"}


class Episode:
    def __init__(self, client, topic="inheritance", student_id="stu_1", session_id="sess_1", prefix="req"):
        self.client, self.topic = client, topic
        self.student_id, self.session_id, self.prefix = student_id, session_id, prefix
        self.history: list[dict] = []
        self.state = None
        self.n = 0
        self.responses: list[dict] = []
        self.bodies: list[dict] = []

    def body(self, message: str) -> dict:
        self.n += 1
        return {
            "request_id": f"{self.prefix}-{self.n}",
            "student_id": self.student_id,
            "session_id": self.session_id,
            "topic": self.topic,
            "message": message,
            "history": copy.deepcopy(self.history),  # excludes the current message
            "state": copy.deepcopy(self.state),
        }

    def send(self, message: str, *, fail: bool = False):
        body = self.body(message)
        self.history.append({"role": "student", "text": message, "ts": TS})  # SEND_STARTED
        if fail:  # SEND_FAILED: the student turn stays, nothing else changes
            return None
        r = self.client.post("/tutor/message", json=body)
        self.bodies.append(body)
        if r.status_code == 200:  # SEND_SUCCEEDED
            res = r.json()
            turn = {"role": "tutor", "text": res["response"], "ts": TS}
            if res["strategy"]:
                turn["strategy"] = res["strategy"]
            self.history.append(turn)
            self.state = res["updated_state"]
            self.responses.append(res)
        return r

    def play(self, *messages: str) -> list[dict]:
        out = []
        for m in messages:
            r = self.send(m)
            assert r.status_code == 200, (m, r.status_code, r.text)
            out.append(r.json())
        return out


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_bytes())


def contract_violations(res: dict, request_id: str) -> list[str]:
    """Every contract item the demo depends on; an empty list means the response is fine."""
    bad: list[str] = []
    try:
        TutorResponse.model_validate(res)
    except Exception as exc:  # noqa: BLE001
        bad.append(f"does not validate against TutorResponse: {exc}")
    if res.get("request_id") != request_id:
        bad.append("request_id was not echoed exactly")
    state = res.get("updated_state") or {}
    if set(state) != STATE_KEYS:
        bad.append(f"updated_state is incomplete or has extra keys: {sorted(state)}")
    action = res.get("action")
    if action == "offer_new_cycle" and state.get("awaiting_cycle_confirmation") is not True:
        bad.append("offer_new_cycle without awaiting_cycle_confirmation=true")
    if action == "clarify" and state.get("awaiting_cycle_confirmation") is not True:
        bad.append("clarify dropped awaiting_cycle_confirmation")
    ended = action in ("resolved", "end_unresolved")
    if ended != (res.get("episode_log") is not None):
        bad.append("episode_log is non-null iff the action is terminal: violated")
    if action == "explain":
        if not res.get("strategy"):
            bad.append("explain without a strategy")
        lines = [ln for ln in res.get("response", "").splitlines() if ln.strip()]
        if not lines or not lines[-1].startswith("**Check:**"):
            bad.append("explain reply does not end with a **Check:** line")
        if res.get("response", "").count("**Check:**") != 1:
            bad.append("explain reply does not have exactly one **Check:**")
    meta = res.get("meta") or {}
    if "fallback" not in meta:
        bad.append("meta.fallback missing")
    p = (res.get("confusion") or {}).get("probability")
    if not isinstance(p, (int, float)) or not 0 <= p <= 1:
        bad.append("confusion.probability is not a number in [0, 1]")
    lat = meta.get("latency_ms") or {}
    if set(lat) != {"classify", "llm", "total"} or any(v < 0 for v in lat.values()):
        bad.append("latency_ms malformed")
    return bad
