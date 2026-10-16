import { env } from '../config/env';
import { FALLBACK_TOPICS } from '../config/topics';
import { TutorError, mapStatusToKind } from './errors';
import { parseHealth, parseModelInfo, parseTopics, parseTutorResponse } from './schemas';
import type { HealthResponse, ModelInfo, TopicOption, TutorResponse, TutorState, HistoryTurn } from './types';
import { createMockTransport, type MockFault } from './mockTransport';

export interface TurnInput {
  topic: string;
  message: string;
  history: HistoryTurn[];
  state: TutorState | null;
  profile?: null;
  /** Thinking mode (backend T1 field; a backend without it ignores it). */
  thinking?: boolean;
}

export interface TutorTransport {
  sendTurn(input: TurnInput): Promise<TutorResponse>;
  health(): Promise<HealthResponse>;
  modelInfo(): Promise<ModelInfo>;
  topics(): Promise<TopicOption[]>;
}

export type { MockFault };

/** Client-side request budgets. Without these a socket that accepts and never
 * answers leaves the promise pending forever: `loadTopics` only catches
 * *rejections*, so a hang used to wedge the send latch permanently.
 *
 * These are NOT the 3s NFR latency budget. That figure is what we measure a turn
 * against and report; enforcing it as a cutoff would fail legitimate turns and
 * corrupt the latency evidence. */
export const METADATA_TIMEOUT_MS = 5_000;   // /topics, /health, /model-info — all have fallbacks, so fail fast
export const TURN_TIMEOUT_MS = 30_000;      // /tutor/message — classify + LLM generation
// Thinking turns take 1–3 minutes. Server LLM_THINKING_TIMEOUT_S is 180 s; the
// extra 20 s is margin so the server's own answer (or 504) arrives before we give up.
export const THINKING_TURN_TIMEOUT_MS = 200_000;

/** The client budget for one turn: long only on the thinking path. */
export function turnTimeoutFor(input: TurnInput): number {
  return input.thinking ? THINKING_TURN_TIMEOUT_MS : TURN_TIMEOUT_MS;
}

function isTimeout(cause: unknown): boolean {
  return cause instanceof DOMException && cause.name === 'TimeoutError';
}

async function request<T>(url: string, init: RequestInit, parse: (value: unknown) => T, timeoutMs: number = METADATA_TIMEOUT_MS, onTimeout: 'network' | 'llm_timeout' = 'network'): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { ...init, signal: AbortSignal.timeout(timeoutMs) });
  } catch (cause) {
    // A client-side abort is recorded distinctly in `detail`: it shares a kind
    // with a server 504, but a developer reading the research panel must be able
    // to tell "we gave up" from "the service said it timed out".
    if (isTimeout(cause)) throw new TutorError(onTimeout, `Tutor service did not answer within ${timeoutMs}ms`, { detail: { client_timeout: true, timeout_ms: timeoutMs, url }, cause });
    throw new TutorError('network', 'Tutor service could not be reached', { cause });
  }
  const text = await response.text();
  let body: unknown = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!response.ok) {
    const kind = mapStatusToKind(response.status);
    throw new TutorError(kind, `Tutor service returned ${response.status}`, { status: response.status, detail: body });
  }
  return parse(body);
}

function liveTransport(mode: 'direct' | 'express'): TutorTransport {
  const base = mode === 'direct' ? env.tutorUrl : env.expressBase;
  return {
    sendTurn: async (input) => {
      const requestId = crypto.randomUUID();
      const body = mode === 'direct'
        ? { request_id: requestId, student_id: getStudentId(), session_id: getSessionId(), ...input, profile: null }
        : { topic: input.topic, message: input.message };
      return request(`${base}/tutor/message`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, (data) => parseTutorResponse(data, mode === 'direct' ? requestId : undefined), turnTimeoutFor(input), 'llm_timeout');
    },
    health: () => request(`${base}/health`, {}, parseHealth),
    modelInfo: () => request(`${base}/model-info`, {}, parseModelInfo),
    topics: () => request(`${base}/topics`, {}, parseTopics),
  };
}

let sessionId: string | undefined;
function getSessionId() { sessionId ??= `sess_${crypto.randomUUID().slice(0, 8)}`; return sessionId; }
function getStudentId() {
  const key = 'java-tutor.student-id';
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const value = `stu_${crypto.randomUUID().slice(0, 8)}`;
  localStorage.setItem(key, value);
  return value;
}

export function createTransport(mode: typeof env.mode = env.mode): TutorTransport {
  if (mode === 'mock') {
    const mock = createMockTransport();
    return { ...mock, sendTurn: async (input) => parseTutorResponse(await mock.sendTurn(input)) };
  }
  return liveTransport(mode);
}

export async function loadTopics(transport: TutorTransport): Promise<TopicOption[]> {
  try { return await transport.topics(); } catch { return [...FALLBACK_TOPICS]; }
}
