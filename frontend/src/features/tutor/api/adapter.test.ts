/**
 * Regression tests for the send-latch wedge.
 *
 * The defect: `request()` called `fetch` with no AbortSignal, so a socket that
 * accepts and never answers never settled. `loadTopics` catches *rejections*, so
 * it did not help; `topicsReady` never resolved, `runExclusive` never reached its
 * `finally`, and every later send was dropped silently by the held latch.
 *
 * Node has no DOM, so these drive the transport directly rather than the hook.
 * `AbortSignal.timeout` is stubbed to abort in milliseconds instead of seconds so
 * the suite stays fast; the budget actually requested is asserted separately, and
 * everything else on the path (signal plumbing, abort -> TutorError mapping,
 * latch release) is the real code.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { METADATA_TIMEOUT_MS, THINKING_TURN_TIMEOUT_MS, TURN_TIMEOUT_MS, createTransport, loadTopics, turnTimeoutFor } from './adapter';
import { TutorError } from './errors';
import { createSendLatch, runExclusive } from '../episodeRules';
import explainFixture from './fixtures/tutor-response.explain.json';

const realTimeout = AbortSignal.timeout.bind(AbortSignal);
import type { TurnInput } from './adapter';

const turn = (): TurnInput => ({ topic: 'loops', message: 'hi', history: [], state: null, profile: null });

/** A fetch that accepts the connection and never answers — the wedged-server case.
 *  It settles only if something aborts the signal it was handed. */
function neverAnswers() {
  return vi.fn((_url: string, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
    init?.signal?.addEventListener('abort', () => reject((init.signal as AbortSignal).reason));
  }));
}

let requestedBudgets: number[] = [];

beforeEach(() => {
  requestedBudgets = [];
  // Record the real budget, then abort fast so the suite does not wait 30s.
  vi.spyOn(AbortSignal, 'timeout').mockImplementation((ms: number) => {
    requestedBudgets.push(ms);
    return realTimeout(10);
  });
  vi.stubGlobal('localStorage', { getItem: () => null, setItem: () => undefined });
});

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('budgets', () => {
  it('uses the long budget for a turn and the short one for metadata', async () => {
    vi.stubGlobal('fetch', neverAnswers());
    const transport = createTransport('direct');
    await expect(transport.sendTurn(turn())).rejects.toThrow(TutorError);
    expect(requestedBudgets).toEqual([TURN_TIMEOUT_MS]);

    requestedBudgets = [];
    await expect(transport.health()).rejects.toThrow(TutorError);
    expect(requestedBudgets).toEqual([METADATA_TIMEOUT_MS]);
  });

  it('keeps the turn budget well clear of the 3s NFR measurement budget', () => {
    // Enforcing the NFR figure as a cutoff would fail legitimate turns and
    // corrupt the latency evidence it exists to collect.
    expect(TURN_TIMEOUT_MS).toBeGreaterThan(3_000);
    expect(METADATA_TIMEOUT_MS).toBeLessThan(TURN_TIMEOUT_MS);
  });
});

describe('thinking turns', () => {
  it('turnTimeoutFor: 30 s normally, 200 s when thinking', () => {
    expect(turnTimeoutFor(turn())).toBe(30_000);
    expect(turnTimeoutFor({ ...turn(), thinking: false })).toBe(30_000);
    expect(turnTimeoutFor({ ...turn(), thinking: true })).toBe(200_000);
    expect(THINKING_TURN_TIMEOUT_MS).toBe(200_000);
  });

  it('requests the long budget only for a thinking turn', async () => {
    vi.stubGlobal('fetch', neverAnswers());
    await createTransport('direct').sendTurn({ ...turn(), thinking: true }).catch(() => undefined);
    expect(requestedBudgets).toEqual([THINKING_TURN_TIMEOUT_MS]);
  });

  it('the direct body carries thinking', async () => {
    const fetchStub = vi.fn(async (_url: string, _init?: RequestInit) => new Response(JSON.stringify(explainFixture), { status: 200 }));
    vi.stubGlobal('fetch', fetchStub);
    await createTransport('direct').sendTurn({ ...turn(), thinking: true }).catch(() => undefined);
    expect(JSON.parse(String(fetchStub.mock.calls[0]?.[1]?.body))).toMatchObject({ thinking: true });
  });
});

describe('a wedged server cannot hang a request', () => {
  it('aborts a never-answering turn as llm_timeout, not unknown or network', async () => {
    vi.stubGlobal('fetch', neverAnswers());
    const error = await createTransport('direct').sendTurn(turn()).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(TutorError);
    expect((error as TutorError).kind).toBe('llm_timeout');
    // Student-facing text is the retryable one already in the taxonomy.
    expect((error as TutorError).isRetryable).toBe(true);
  });

  it('marks a client-side give-up distinctly from a server 504', async () => {
    vi.stubGlobal('fetch', neverAnswers());
    const error = await createTransport('direct').sendTurn(turn()).catch((e: unknown) => e) as TutorError;
    // Same kind as a 504, different provenance: whoever reads the research panel
    // must be able to tell "we gave up" from "the service said it timed out".
    expect(error.detail).toMatchObject({ client_timeout: true, timeout_ms: TURN_TIMEOUT_MS });
    expect(error.status).toBeUndefined();
  });

  it('falls back to the static topic list instead of failing the student', async () => {
    vi.stubGlobal('fetch', neverAnswers());
    const list = await loadTopics(createTransport('direct'));
    expect(list.length).toBeGreaterThan(0);
    expect(list.some((t) => t.id === 'loops')).toBe(true);
  });
});

describe('the latch cannot wedge (the original defect)', () => {
  it('releases after a hung request, so the next send still goes out', async () => {
    const latch = createSendLatch();
    const transport = createTransport('direct');

    vi.stubGlobal('fetch', neverAnswers());
    const first = await runExclusive(latch, () => transport.sendTurn(turn())).catch((e: unknown) => e);
    expect((first as TutorError).kind).toBe('llm_timeout');

    // The server recovers. Before the fix this never ran: the latch was still held.
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(explainFixture), { status: 200 })));
    const second = await runExclusive(latch, async () => 'sent');
    expect(second).toBe('sent');
  });

  it('still blocks a duplicate send while a request is in flight', async () => {
    vi.stubGlobal('fetch', neverAnswers());
    const latch = createSendLatch();
    const transport = createTransport('direct');
    let calls = 0;
    const task = () => { calls += 1; return transport.sendTurn(turn()); };

    const first = runExclusive(latch, task).catch(() => 'failed');
    const second = await runExclusive(latch, task);   // same tick: latch is held
    expect(second).toBeUndefined();
    expect(calls).toBe(1);
    await first;
  });
});
