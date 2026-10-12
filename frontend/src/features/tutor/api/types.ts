/**
 * Contract types for the tutor service.
 *
 * SOURCE OF TRUTH: `ARCHITECTURE.md` §7 (plandocs), as amended by
 * `frontendPlan/10_DECISIONS.md`. This file is its TypeScript expression and is
 * the SHARED ARTEFACT with the Express teammate — any change here is a contract
 * change and must be agreed on both sides.
 *
 * Amendments applied:
 *   - Q6: `EpisodeLog.schema_version`
 *   - Q1: `TopicOption` + `GET /topics`
 */

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

/** The four pedagogical strategies, in default escalation order (FR-06). */
export type Strategy = 'theory' | 'example' | 'simplified' | 'analogy';

/** Why a strategy was delivered (FR-16). `request` is excluded from the
 *  weakness count — see `EpisodeLog.counted_strategies`. */
export type Trigger = 'default' | 'confusion' | 'request' | 'personalised';

/** What the tutor did this turn. All five must be rendered. */
export type Action =
  | 'explain'
  | 'resolved'
  | 'offer_new_cycle'
  | 'end_unresolved'
  | 'clarify';

export type Label = 'confused' | 'understood';

/** Whether the rule layer or the ML model decided (ADR-04). Surfaced in the
 *  Research Panel as honest disclosure of the hybrid decision. */
export type Source = 'rule' | 'model';

export type Outcome = 'resolved' | 'end_unresolved';

export const DEFAULT_STRATEGY_ORDER: readonly Strategy[] = [
  'theory',
  'example',
  'simplified',
  'analogy',
] as const;

// ---------------------------------------------------------------------------
// Topics (10_DECISIONS.md Q1)
// ---------------------------------------------------------------------------

/** Owned by the tutor service (`app/topics.py`), exposed via `GET /topics`.
 *  The frontend's static copy in `config/topics.ts` is a fallback only. */
export interface TopicOption {
  /** snake_case slug sent in `TutorRequest.topic`, e.g. 'exception_handling'. */
  id: string;
  /** Display label, e.g. 'Exception Handling'. */
  label: string;
}

// ---------------------------------------------------------------------------
// Request
// ---------------------------------------------------------------------------

export interface HistoryTurn {
  role: 'student' | 'tutor';
  text: string;
  strategy?: Strategy;
  /** ISO 8601. */
  ts: string;
}

export interface StrategyUse {
  strategy: Strategy;
  trigger: Trigger;
}

/**
 * Tutoring state. Produced by the service, echoed back by the client verbatim.
 *
 * INVARIANT I1: the frontend stores and resends this unmodified. It never
 * constructs or mutates a field inside it. Reading it for display is fine.
 */
export interface TutorState {
  episode_id: string;
  cycle: number;
  strategies_used: StrategyUse[];
  awaiting_cycle_confirmation: boolean;
  prior_explanations: string[];
}

export interface StrategyStat {
  uses: number;
  wins: number;
}

/** PP2 only. Always `null` in PP1. */
export interface Profile {
  strategy_stats: Partial<Record<Strategy, StrategyStat>>;
  weak_topics: string[];
}

/** Full wire payload for `direct` mode. In `express` mode the frontend sends
 *  only `{ topic, message }` and Express supplies the rest server-side. */
export interface TutorRequest {
  request_id: string;
  /** Pseudonymous. Never a name or email (NFR-05). */
  student_id: string;
  session_id: string;
  topic: string;
  message: string;
  history: HistoryTurn[];
  /** `null` on the first message of a topic. */
  state: TutorState | null;
  profile?: Profile | null;
}

/** The subset Express accepts; it adds ids, history, state and profile. */
export interface ExpressTutorRequest {
  topic: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Response
// ---------------------------------------------------------------------------

export interface ConfusionResult {
  label: Label;
  /** [0, 1]. */
  probability: number;
  source: Source;
}

export interface LatencyBreakdown {
  classify: number;
  llm: number;
  total: number;
}

export interface ResponseMeta {
  model_version: string;
  llm: string;
  latency_ms: LatencyBreakdown;
  /** True when the template fallback was used instead of the LLM. Must be
   *  shown in the UI so a fallback is never passed off as generation. */
  fallback?: boolean;
}

export interface TutorResponse {
  request_id: string;
  confusion: ConfusionResult;
  detected_request: Strategy | null;
  action: Action;
  strategy: Strategy | null;
  trigger: Trigger | null;
  response: string;
  updated_state: TutorState;
  /** Non-null ONLY when the episode ends. The client uses non-null as the
   *  signal to close the episode. */
  episode_log: EpisodeLog | null;
  meta: ResponseMeta;
}

// ---------------------------------------------------------------------------
// Episode log (ARCHITECTURE.md §7.3)
// ---------------------------------------------------------------------------

export interface Delivery {
  seq: number;
  strategy: Strategy;
  trigger: Trigger;
  cycle: number;
  student_label: Label;
  probability: number;
  source: Source;
}

/**
 * The weakness-logging contribution, and the export the analytics component
 * consumes. Stored by Express as received, without renaming (10_DECISIONS Q6).
 */
export interface EpisodeLog {
  /** Added per 10_DECISIONS.md Q6 so later changes are versioned. */
  schema_version: '1.0';
  episode_id: string;
  student_id: string;
  topic: string;
  started_at: string;
  ended_at: string;
  outcome: Outcome;
  cycles: number;
  deliveries: Delivery[];
  /** Excludes `trigger: 'request'` deliveries — this is what makes claim C6
   *  (requested vs confusion-driven) measurable. */
  counted_strategies: number;
  requested_strategies: number;
  winning_strategy: Strategy | null;
  winning_combination: Strategy[];
  is_weak: boolean;
  /** Human-readable rule that produced `is_weak`, for auditability. */
  weak_rule: string;
  model_version: string;
}

// ---------------------------------------------------------------------------
// Auxiliary endpoints
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: 'ok' | 'degraded';
  model_loaded: boolean;
  llm_reachable: boolean;
  model_version: string | null;
}

export interface ModelInfo {
  version: string;
  trained_at: string;
  dataset: string;
  threshold: number;
  metrics: Record<string, number>;
}
