// Pure decisions behind `useEpisode.send`, kept out of the hook so they can be
// unit tested in the node test environment (no DOM, no React rendering).

import type { TurnInput, TutorTransport } from './api/adapter';
import type { HealthResponse, TopicOption } from './api/types';
import { inferTopic } from './inferTopic';
import type { EpisodeUI, Phase } from './reducer';

/** What one turn puts on the wire.
 *
 * A turn whose topic differs from the episode's current topic belongs to a NEW
 * episode (TOPIC_CHANGED resets history and server state), so it carries no
 * history and no state. So does a turn sent after the episode ENDED
 * (`closed`: resolved or end_unresolved): the contract's state has no "ended"
 * flag, so sending the post-resolution `updated_state` would make the service
 * reopen the finished episode under the same `episode_id`; the next message
 * starts a new one instead, with `state: null` and `history: []` (history is
 * episode-scoped). A turn on the same topic in a live episode carries the
 * accumulated history and the last `updated_state` verbatim (invariant I1).
 *
 * `state` must be the episode as it was BEFORE any dispatch from this send: the
 * hook's captured value is stale by design, which is exactly why this decision
 * is made here from the topic rather than read off the captured fields. */
export function turnInputFor(state: EpisodeUI, topic: string, message: string, thinking: boolean = false): TurnInput {
  const sameEpisode = topic === state.topic && state.phase !== 'closed';
  return {
    topic,
    message,
    history: sameEpisode ? state.history : [],
    state: sameEpisode ? state.serverState : null,
    profile: null,
    thinking,
  };
}

/** Whether a message may be sent in this phase: only while a reply is in flight. The conversation
 * never ends (an episode does), so `closed` does not block the composer. */
export function canSend(phase: Phase): boolean {
  return phase !== 'awaiting_tutor';
}

/** A synchronous in-flight latch. The `phase` check in `send` reads a value
 * captured at render time, so two calls from the same render both pass it; a
 * ref-backed latch is checked and set before the first dispatch, so they cannot. */
export interface SendLatch {
  tryAcquire(): boolean;
  release(): void;
}

export function createSendLatch(): SendLatch {
  let busy = false;
  return {
    tryAcquire() {
      if (busy) return false;
      busy = true;
      return true;
    },
    release() {
      busy = false;
    },
  };
}

/** Runs `task` unless another run holds the latch. Always releases, even if the
 * task throws. Resolves to `undefined` when it was skipped. */
export async function runExclusive<T>(latch: SendLatch, task: () => Promise<T>): Promise<T | undefined> {
  if (!latch.tryAcquire()) return undefined;
  try {
    return await task();
  } finally {
    latch.release();
  }
}

/** Whether the service could be asked at all. A rejected `/health` used to leave
 * `health` null, which the UI rendered the same as "no problem". */
export type HealthStatus = 'checking' | 'ok' | 'unreachable';

export async function probeHealth(transport: Pick<TutorTransport, 'health'>): Promise<{ status: Exclude<HealthStatus, 'checking'>; health: HealthResponse | null }> {
  try {
    return { status: 'ok', health: await transport.health() };
  } catch {
    return { status: 'unreachable', health: null };
  }
}

// Slug used when the student chats without choosing a topic. NOTE: the tutor
// service validates topic slugs (422 for unknown ones), so it must accept this
// value for no-topic chats to work against the real backend.
export const GENERAL_TOPIC = 'general';

/** The topic a turn is sent under: an explicit one, else the episode's, else one
 * named in the message, else a general chat.
 *
 * SYNCHRONOUS BY DESIGN. An earlier version awaited `GET /topics` here so it
 * would not infer from an empty list. That await sat inside the send latch and
 * before `SEND_STARTED`, which meant a slow or wedged `/topics` left the student
 * with no bubble and, if the fetch never settled, permanently wedged the latch.
 * `topics` is now seeded with `FALLBACK_TOPICS` and is never empty, so there is
 * nothing to wait for and the whole failure mode is gone. Keep this synchronous:
 * anything awaited here delays the student's first feedback. */
export function resolveTurnTopic(args: {
  explicit?: string | undefined;
  current: string | null;
  message: string;
  topics: TopicOption[];
}): string {
  if (args.explicit) return args.explicit;
  if (args.current) return args.current;
  return inferTopic(args.message, args.topics)?.id ?? GENERAL_TOPIC;
}

/** Tracks which episode is current, so a response that arrives after the episode
 * was replaced (topic change, or "New chat" clicked mid-reply) is dropped rather
 * than appended to the fresh one. Lives here, not in the reducer, because the
 * reducer must stay a pure function of the action it is given; the staleness
 * question is "is this response still wanted", which only the caller can answer. */
export interface GenerationGuard {
  /** Call when the episode is replaced. Invalidates every in-flight response. */
  bump(): void;
  /** Token for the send about to go out. Capture AFTER any episode reset. */
  current(): number;
  isStale(captured: number): boolean;
}

export function createGenerationGuard(): GenerationGuard {
  let generation = 0;
  return {
    bump() { generation += 1; },
    current() { return generation; },
    isStale(captured) { return generation !== captured; },
  };
}
