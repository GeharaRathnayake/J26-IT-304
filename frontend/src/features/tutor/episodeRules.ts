// Pure decisions behind `useEpisode.send`, kept out of the hook so they can be
// unit tested in the node test environment (no DOM, no React rendering).

import type { TurnInput } from './api/adapter';
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
