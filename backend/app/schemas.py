"""Pydantic v2 mirrors of the request types in the frozen contract
(frontend/src/features/tutor/api/types.ts). The contract is the specification.

Rules:
- Unknown extra fields are IGNORED (contract rule 5: extra fields are dropped, not
  rejected), so an additive field from Express is not a 422.
- Missing, renamed or wrongly typed fields ARE rejected. `strict=True` stops Pydantic
  coercing "1" to 1 or true to 1.
- Only constraints the contract dictates are applied. `cycle`, `ts`, ids and counters
  are deliberately unconstrained beyond their types; `message` has no length limit.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.topics import is_accepted_topic

Strategy = Literal["theory", "example", "simplified", "analogy"]
Trigger = Literal["default", "confusion", "request", "personalised"]


class _Contract(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)


class HistoryTurn(_Contract):
    role: Literal["student", "tutor"]
    text: str
    strategy: Strategy | None = None  # optional in the contract (`strategy?`)
    ts: str  # ISO 8601 per the contract; format is not enforced


class StrategyUse(_Contract):
    strategy: Strategy
    trigger: Trigger


class TutorState(_Contract):
    episode_id: str
    cycle: int
    strategies_used: list[StrategyUse]
    awaiting_cycle_confirmation: bool
    prior_explanations: list[str]


class StrategyStat(_Contract):
    uses: int
    wins: int


class Profile(_Contract):
    # Partial<Record<Strategy, StrategyStat>>: any subset of the four strategies as keys.
    strategy_stats: dict[Strategy, StrategyStat]
    weak_topics: list[str]


class TutorRequest(_Contract):
    # Non-empty: it is echoed into a response field the contract requires to be non-empty, and an empty
    # id means a broken client (the frontend always sends a UUID).
    request_id: str = Field(min_length=1)
    student_id: str
    session_id: str
    topic: str
    message: str
    history: list[HistoryTurn]
    state: TutorState | None  # required: may be null, may not be absent
    profile: Profile | None = None  # PP2 only; always null in PP1

    @field_validator("topic")
    @classmethod
    def _topic_must_be_accepted(cls, v: str) -> str:
        if not is_accepted_topic(v):
            raise ValueError("unknown topic slug")
        return v

    @field_validator("message")
    @classmethod
    def _message_must_not_be_blank(cls, v: str) -> str:
        # Check the stripped text but return the ORIGINAL: the classifier must get
        # the raw message in a later stage, so validation never modifies it.
        if not v.strip():
            raise ValueError("message must not be empty or whitespace-only")
        return v

# --- response models (contract: EpisodeLog / Delivery in types.ts) --------------------------
# extra="forbid": the service must never emit a field the contract lacks.

Label = Literal["confused", "understood"]
Source = Literal["rule", "model"]
Outcome = Literal["resolved", "end_unresolved"]


class _Emitted(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class Delivery(_Emitted):
    seq: int = Field(ge=1)
    strategy: Strategy
    trigger: Trigger
    cycle: int = Field(ge=1)
    student_label: Label
    probability: float = Field(ge=0, le=1)
    source: Source


class EpisodeLog(_Emitted):
    schema_version: Literal["1.0"]
    episode_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    started_at: str
    ended_at: str
    outcome: Outcome
    cycles: int = Field(ge=1)
    deliveries: list[Delivery]
    counted_strategies: int = Field(ge=0)
    requested_strategies: int = Field(ge=0)
    winning_strategy: Strategy | None
    winning_combination: list[Strategy]
    is_weak: bool
    weak_rule: str
    model_version: str

# --- the tutor response (contract: TutorResponse in types.ts) ----------------------------------

Action = Literal["explain", "resolved", "offer_new_cycle", "end_unresolved", "clarify"]


class ConfusionResult(_Emitted):
    label: Label
    probability: float = Field(ge=0, le=1)
    source: Source


class LatencyBreakdown(_Emitted):
    classify: float = Field(ge=0)
    llm: float = Field(ge=0)
    total: float = Field(ge=0)


class ResponseMeta(_Emitted):
    model_version: str
    llm: str
    latency_ms: LatencyBreakdown
    fallback: bool | None = None  # always set by this service; optional in the contract


class TutorResponse(_Emitted):
    request_id: str = Field(min_length=1)
    confusion: ConfusionResult
    detected_request: Strategy | None
    action: Action
    strategy: Strategy | None
    trigger: Trigger | None
    response: str
    updated_state: TutorState  # COMPLETE on every turn: the client stores it and echoes it back
    episode_log: EpisodeLog | None
    meta: ResponseMeta

    @model_validator(mode="after")
    def _contract_invariants(self):
        # The frontend's own schema rejects these; failing here turns a demo dead-end into a loud
        # server-side error.
        ended = self.action in ("resolved", "end_unresolved")
        if ended != (self.episode_log is not None):
            raise ValueError("episode_log must be non-null if and only if the action is terminal")
        if self.action == "explain" and (self.strategy is None or self.trigger is None):
            raise ValueError("an explain reply needs a strategy and a trigger")
        if self.action != "explain" and (self.strategy is not None or self.trigger is not None):
            raise ValueError("strategy and trigger are set only for explain")
        if self.action == "offer_new_cycle" and not self.updated_state.awaiting_cycle_confirmation:
            raise ValueError("offer_new_cycle must set awaiting_cycle_confirmation")
        if self.action == "clarify" and not self.updated_state.awaiting_cycle_confirmation:
            raise ValueError("clarify must keep awaiting_cycle_confirmation true")
        return self
