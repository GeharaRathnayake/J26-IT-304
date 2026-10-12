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
