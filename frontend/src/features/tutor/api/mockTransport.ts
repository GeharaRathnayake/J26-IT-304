import { TutorError } from './errors';
import type { HealthResponse, ModelInfo, Strategy, TopicOption, TutorResponse, TutorState } from './types';
import type { TurnInput, TutorTransport } from './adapter';
import { FALLBACK_TOPICS } from '../config/topics';

export type MockFault = 'none' | '503' | '504' | 'fallback' | 'slow' | 'malformed';
let fault: MockFault = 'none';
export function setMockFault(next: MockFault) { fault = next; }
export function getMockFault() { return fault; }

const ORDER: Strategy[] = ['theory', 'example', 'simplified', 'analogy'];
const labels: Record<Strategy, string> = {
  theory: 'Here is the core idea in plain language.',
  example: 'Let’s work through a small Java example step by step.',
  simplified: 'Let’s strip it back to the simplest version.',
  analogy: 'Think of it like a familiar real-world process.',
};
const checks: Record<Strategy, string> = {
  theory: 'Can you explain the main idea in your own words?',
  example: 'What would this example do if you changed the highlighted line?',
  simplified: 'Which part feels clearer after simplifying it?',
  analogy: 'How does this analogy map to the Java concept?',
};
const code = '```java\nclass Dog extends Animal {\n    Dog(String name) {\n        super(name);\n    }\n}\n```';

function classify(message: string) {
  const lower = message.toLowerCase();
  const understood = /\b(yes|yeah|got it|i understand|makes sense|exactly|correct|okay|ok)\b/.test(lower) && !/not|don't|confus|still/.test(lower);
  const confused = /don'?t|get it|confus|still|not sure|no idea|explain|what does|how does|help/.test(lower);
  return { label: understood && !confused ? 'understood' as const : 'confused' as const, probability: understood && !confused ? 0.22 : 0.81, source: /don'?t|get it|confus|still/.test(lower) ? 'rule' as const : 'model' as const };
}
function requested(message: string): Strategy | null {
  const lower = message.toLowerCase();
  if (/example|show me/.test(lower)) return 'example';
  if (/simpl|easier|plain/.test(lower)) return 'simplified';
  if (/analog|real world/.test(lower)) return 'analogy';
  if (/theory|explain the concept/.test(lower)) return 'theory';
  return null;
}
function cycleIntent(message: string): 'accept' | 'decline' | 'unclear' {
  const lower = message.toLowerCase();
  if (/\b(yes|sure|okay|ok|again|explain it another way)\b/.test(lower)) return 'accept';
  if (/\b(no|move on|skip|later)\b/.test(lower)) return 'decline';
  return 'unclear';
}
function delay(ms: number) { return new Promise((resolve) => setTimeout(resolve, ms)); }

function logFor(input: TurnInput, state: TutorState, outcome: 'resolved' | 'end_unresolved', winner: Strategy | null, confusion: ReturnType<typeof classify>) {
  const deliveries = state.strategies_used.map((use, index) => ({ seq: index + 1, strategy: use.strategy, trigger: use.trigger, cycle: Math.floor(index / ORDER.length) + 1, student_label: confusion.label, probability: confusion.probability, source: confusion.source }));
  return { schema_version: '1.0' as const, episode_id: state.episode_id, student_id: 'stu_mock', topic: input.topic, started_at: new Date(Date.now() - 60000).toISOString(), ended_at: new Date().toISOString(), outcome, cycles: state.cycle, deliveries, counted_strategies: state.strategies_used.filter((x) => x.trigger !== 'request').length, requested_strategies: state.strategies_used.filter((x) => x.trigger === 'request').length, winning_strategy: winner, winning_combination: state.strategies_used.map((x) => x.strategy), is_weak: outcome === 'end_unresolved' || state.strategies_used.filter((x) => x.trigger !== 'request').length >= 3, weak_rule: 'counted_strategies >= 3 OR outcome == end_unresolved', model_version: 'mock-clf-v1.0.0' };
}

export function createMockTransport(): TutorTransport {
  return {
    async sendTurn(input) {
      if (fault === '503') throw new TutorError('model_unavailable', 'Tutor service unavailable', { status: 503 });
      if (fault === '504') throw new TutorError('llm_timeout', 'LLM timed out', { status: 504 });
      if (fault === 'slow') await delay(1800);
      if (fault === 'malformed') return { broken: true } as unknown as TutorResponse;
      const confusion = classify(input.message);
      let state = input.state;
      if (!state) state = { episode_id: `ep_${crypto.randomUUID().slice(0, 8)}`, cycle: 1, strategies_used: [], awaiting_cycle_confirmation: false, prior_explanations: [] };
      if (state.awaiting_cycle_confirmation) {
        const intent = cycleIntent(input.message);
        if (intent === 'unclear') return response(input, state, confusion, 'clarify', null, null, 'Would you like me to explain it another way? **Check:** Please answer yes or no.');
        if (intent === 'decline') return response(input, { ...state, awaiting_cycle_confirmation: false }, confusion, 'end_unresolved', null, logFor(input, state, 'end_unresolved', null, confusion), 'Let’s pause here. I’ve noted this topic so we can come back to it — it may also help to go over it with your lecturer.');
        state = { ...state, cycle: state.cycle + 1, awaiting_cycle_confirmation: false };
      }
      const req = requested(input.message);
      if (confusion.label === 'understood' && state.strategies_used.length > 0 && !req) {
        return response(input, state, confusion, 'resolved', null, logFor(input, state, 'resolved', state.strategies_used.at(-1)?.strategy ?? null, confusion), 'Exactly right — that shows you have the idea.');
      }
      // A student-requested delivery is evidence for the log, but it does not
      // consume a slot in the confusion-driven escalation cycle (FR-17/C6).
      const used = new Set(state.strategies_used.filter((x) => x.trigger !== 'request').map((x) => x.strategy));
      const strategy = req ?? ORDER.find((item) => !used.has(item));
      if (!strategy) {
        if (state.cycle < 2) return response(input, { ...state, awaiting_cycle_confirmation: true }, confusion, 'offer_new_cycle', null, null, 'This one is tricky, and that’s completely normal. Would you like me to explain it another way?');
        return response(input, state, confusion, 'end_unresolved', null, logFor(input, state, 'end_unresolved', null, confusion), 'Let’s pause here. I’ve noted this topic so we can come back to it — it may also help to go over it with your lecturer.');
      }
      const trigger = req ? 'request' as const : state.strategies_used.length === 0 ? 'default' as const : 'confusion' as const;
      const nextState = { ...state, strategies_used: [...state.strategies_used, { strategy, trigger }], prior_explanations: [...state.prior_explanations, labels[strategy]], awaiting_cycle_confirmation: false };
      const body = `${labels[strategy]}\n\n${strategy === 'example' ? code + '\n\n' : ''}${checks[strategy]}\n\n**Check:** ${checks[strategy]}`;
      return response(input, nextState, confusion, 'explain', strategy, null, body);
    },
    async health(): Promise<HealthResponse> { return { status: fault === '503' ? 'degraded' : 'ok', model_loaded: fault !== '503', llm_reachable: fault !== '504', model_version: 'mock-clf-v1.0.0' }; },
    async modelInfo(): Promise<ModelInfo> { return { version: 'mock-clf-v1.0.0', trained_at: '2026-10-08', dataset: 'mock', threshold: 0.5, metrics: { accuracy: 1 } }; },
    async topics(): Promise<TopicOption[]> { return FALLBACK_TOPICS.slice(); },
  };
}

function response(input: TurnInput, state: TutorState, confusion: ReturnType<typeof classify>, action: TutorResponse['action'], strategy: Strategy | null, episode_log: TutorResponse['episode_log'], text: string): TutorResponse {
  return { request_id: `mock_${crypto.randomUUID()}`, confusion, detected_request: requested(input.message), action, strategy, trigger: strategy ? state.strategies_used.at(-1)?.trigger ?? null : null, response: text, updated_state: state, episode_log, meta: { model_version: 'mock-clf-v1.0.0', llm: 'mock-template', latency_ms: { classify: 6, llm: fault === 'slow' ? 1800 : 24, total: fault === 'slow' ? 1830 : 36 }, fallback: fault === 'fallback' } };
}
