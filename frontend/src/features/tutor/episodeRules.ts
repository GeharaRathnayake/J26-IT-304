// Pure decisions behind `useEpisode.send`, kept out of the hook so they can be
// unit tested in the node test environment (no DOM, no React rendering).

import type { TurnInput, TutorTransport } from './api/adapter';
import type { HealthResponse, TopicOption } from './api/types';
import { inferTopic } from './inferTopic';
import type { EpisodeUI } from './reducer';

/** What one turn puts on the wire.
 *
 * A turn whose topic differs from the episode's current topic belongs to a NEW
 * episode (TOPIC_CHANGED resets history and server state), so it carries no
 * history and no state. A turn on the same topic carries the accumulated
 * history and the last `updated_state` verbatim (invariant I1).
 *
 * `state` must be the episode as it was BEFORE any dispatch from this send: the
 * hook's captured value is stale by design, which is exactly why this decision
 * is made here from the topic rather than read off the captured fields. */
export function turnInputFor(state: EpisodeUI, topic: string, message: string): TurnInput {
  const sameEpisode = topic === state.topic;
  return {
    topic,
    message,
    history: sameEpisode ? state.history : [],
    state: sameEpisode ? state.serverState : null,
    profile: null,
  };
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
 * named in the message, else a general chat. `topics` is null until `GET /topics`
 * has answered; in that window the choice waits for it rather than inferring
 * from an empty list and silently falling back to general (review F8.4). */
export async function resolveTurnTopic(args: {
  explicit?: string | undefined;
  current: string | null;
  message: string;
  topics: TopicOption[] | null;
  topicsReady: Promise<TopicOption[]>;
}): Promise<string> {
  if (args.explicit) return args.explicit;
  if (args.current) return args.current;
  const list = args.topics ?? (await args.topicsReady);
  return inferTopic(args.message, list)?.id ?? GENERAL_TOPIC;
}
