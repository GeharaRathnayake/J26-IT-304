# Frontend Review — 2026-10-13

**Reviewer:** supervisor (frontend).
**Target:** `dev/frontend` @ commit `dc2c9f8`, branch `dev1`.
**Companion document:** `frontend-and-api-guide.md` (the guide). This review also
corrects two places where the guide describes behaviour the code does not have.

## Method and confidence

- `npx tsc --noEmit` — **clean**.
- `npx vitest run` — **19/19 pass** (2 files: `schemas.test.ts`, `reducer.test.ts`).
- The rest is a code read of `useEpisode.ts`, `reducer.ts`, `api/adapter.ts`,
  `api/schemas.ts`, `inferTopic.ts`, `SearchComposer.tsx`, `TutorFeatureApp.tsx`.
- **The app was not run in a browser for this review**, and no live backend
  exists yet. So findings are labelled:
  - **[verified]** — provable from the code alone, no runtime needed.
  - **[needs runtime]** — a code-read conclusion still to be confirmed in the browser.

The guide's own §10.4 already says `direct` and `express` are untested. Several
findings below are exactly the kind of thing that only bites once a real service
is on the other end, which is why they matter **now**, before the backend lands.

## Verdict

The architecture is sound and the composer work landed well. The defects cluster
in one place: **`useEpisode.send` and the reducer's handling of a mid-episode
topic change**. F1 is a data-correctness bug that would corrupt tutoring state
against a real service, and it is invisible in `mock` mode because the mock
accepts any state it is handed.

---

# Part 1 — Code defects

## F1 — [verified] A mid-episode topic change sends the new topic with the *old* episode's history and state

`src/features/tutor/useEpisode.ts:25-30`

```ts
const topic = options?.topic ?? state.topic ?? GENERAL_TOPIC;
if (topic !== state.topic) dispatch({ type: 'TOPIC_CHANGED', topic });   // clears history + serverState
const id = crypto.randomUUID();
dispatch({ type: 'SEND_STARTED', message, id, voice: options?.voice });
try {
  const response = await transport.sendTurn({
    topic,                       // the NEW topic
    message,
    history: state.history,      // the OLD episode's history
    state: state.serverState,    // the OLD episode's server state
    profile: null,
  });
```

`state` is the value captured in this `useCallback` closure. `dispatch` does not
mutate it. So when the topic changes, `TOPIC_CHANGED` correctly resets the
reducer — and the request that goes out on the wire still carries the previous
episode's `history` and `updated_state`.

**Why it matters.** The guide §4.1 states the invariant: `state` is the previous
`updated_state` echoed back unmodified, and §5 says `TOPIC_CHANGED` "starts a
brand-new episode (clears messages, history and server state)". The payload
contradicts both. Against the real tutor service, a topic switch would hand it a
state object belonging to a *different episode and topic* — carrying that
episode's `cycle`, `strategies_used` and `prior_explanations`. The service would
continue an old escalation cycle under a new topic, and `episode_log`
(`counted_strategies`, `winning_strategy`, `is_weak`) would be computed from a
mixture of two episodes. That is corrupted research data, not just a UI glitch.

**Why `mock` mode hides it.** `mockTransport` accepts any slug and any state it
is given (guide §9), so nothing ever complains.

**How to trigger.** Start a chat on one topic, send a message, then pick a
different topic from the in-bar picker (or let `inferTopic` name a different one
in the next message) and send again.

**Fix.** Derive the payload from the episode the message actually belongs to. A
topic change means a fresh episode, so that request must carry `history: []` and
`state: null`.

Extract the decision into a pure, exported function and unit-test it — do not
just patch the inline expression. `vite.config.ts` sets
`test.environment: 'node'`, so a pure function is testable today whereas a hook
test would need a jsdom dependency:

```ts
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
```

## F2 — [verified] Two sends can be in flight at once

`src/features/tutor/useEpisode.ts:24`

```ts
if (!message.trim() || state.phase === 'awaiting_tutor' || state.phase === 'closed') return;
```

The guard reads the captured `state`. Two calls raised from the same render — a
held Enter key, a `CycleOffer` button double-clicked, or a speech utterance
landing in the same tick as a typed submit — both see a pre-`awaiting_tutor`
phase and both proceed.

Consequences: two student bubbles, two requests, two `SEND_SUCCEEDED`
dispatches, and the **second response's `updated_state` overwrites the first**,
so one delivery vanishes from the tutoring state while remaining visible on
screen.

**Fix.** A `useRef` in-flight latch, checked and set synchronously before the
first `dispatch`, cleared in `finally`. The phase check stays as the
user-visible rule; the ref is the correctness guarantee.

## F3 — [verified] An identical repeated failure loses the student's message

`src/features/tutor/TutorFeatureApp.tsx:60` → `SearchComposer.tsx:130-132`

```tsx
draftOnFailure={episode.state.error ? [...episode.state.messages].reverse()
  .find((m) => m.role === 'student' && m.failed)?.text ?? '' : ''}
```

```tsx
useEffect(() => { if (draftOnFailure) setDraft(draftOnFailure); }, [draftOnFailure]);
```

`submit()` clears the draft before sending. On failure the text is pushed back
through this prop. But the effect is keyed on the **value** of `draftOnFailure`:
if the student resends the same text and it fails again, the prop is unchanged,
the effect does not re-run, and the composer stays empty. The message is gone.

This is the most likely path in practice — a 503 or an offline laptop fails the
same text twice in a row.

The guide §4.6 claims the message "is marked `failed`, put back into the composer,
and can be resent", and the UI prints "Your message is still available in the
composer" (`TutorFeatureApp.tsx:137`). Both are false on the second identical
failure.

**Fix.** Key the restore on the failed **message id**, not its text, so each
distinct failure event restores once. Also note `pendingText` in the reducer is
set on `SEND_STARTED` and nulled on `SEND_FAILED` (`reducer.ts:26,33`), so it
holds nothing by the time anything could read it — it is dead state. Either make
it the single mechanism for this restore or delete it.

## F4 — [verified] A draft of only topic labels cannot be sent, with no feedback

`src/features/tutor/SearchComposer.tsx:90,230,271`

```tsx
const hasContent = labels.reduce((text, label) => text.split(label).join(''), draft).trim().length > 0;
```

`hasContent` strips **every** topic label from the draft before deciding whether
there is anything to send. So a draft of exactly `Loops` — which is what picking
"Loops" from the in-bar picker produces — counts as empty. The send button is
disabled and Enter does nothing, silently.

The natural first interaction (open the picker, choose a topic, press Enter) is a
dead end with no explanation. "Loops" is also a perfectly reasonable message.

**Fix.** Decide the rule and make the UI state it. Simplest defensible version:
treat a label-only draft as valid and send it. If it really must be blocked, the
send button needs a title/`aria-describedby` saying why, because a disabled
control with no reason is worse than a rejected submit.

## F5 — [verified] Failed student bubble is unreadable

`src/features/tutor/TutorFeatureApp.tsx:193`

```tsx
className={`... ${message.failed ? 'border-red-300 bg-red-700' : 'border-[#f6d6df] bg-[#fdf4f7] text-ink'}`}
```

`text-ink` sits in the **else** branch, so a failed message gets a dark red
background (`bg-red-700`) with inherited dark `--ink` text. Near-zero contrast on
the one message the student most needs to read and re-send.

Every other error surface in this file uses the light treatment
(`bg-red-50 text-red-900`). This looks like `bg-red-50` mistyped as `bg-red-700`.

**Fix.** Light error background, dark red text, and assert the contrast ratio
against WCAG AA (4.5:1) in both themes.

## F6 — [verified] `/health` failure shows no banner at all

`src/features/tutor/useEpisode.ts:19`

```ts
void transport.health().then(setHealth).catch(() => undefined);
```

A rejected `/health` leaves `health` as `null`. The banner at
`TutorFeatureApp.tsx:58` renders only when `episode.health && !llm_reachable`, so
a service that is **completely down** produces a calmer UI than one that is
merely degraded: no banner, no hint, until the student types a message and the
send fails.

**Fix.** Track the health *check* as a third state (unknown / ok / unreachable)
and surface unreachable with the same prominence as `llm_reachable: false`.

## F7 — [needs runtime] The word-by-word voice reveal spams assistive tech

`src/features/tutor/TutorFeatureApp.tsx:180` with the reveal at `:156-167`

The scroller carries `aria-live="polite"` while its text grows every 250ms
(`REVEAL_WORDS_PER_SECOND = 6`). A polite region re-announces on mutation, so a
screen-reader user plausibly hears the reply restart every quarter second for its
whole duration.

The normal transcript (`:137`) has the same `aria-live="polite"` but mutates once
per message, which is correct and should stay.

**Fix.** Render the revealing text inside `aria-hidden`, and announce the
complete reply once in a separate live region when the reveal finishes. Verify
with a real screen reader (NVDA or Narrator) — this is the one finding here that
cannot be settled by reading code.

## F8 — [verified] Low-severity, confirm then fix

| | Finding | Location |
|---|---|---|
| F8.1 | `SEND_FAILED` sets `phase: 'idle'` when `serverState` is null, even though a topic is selected and `newEpisode(topic)` would say `awaiting_student`. Cosmetic today (the composer is gated on `awaiting_tutor`/`closed`), but it is an inconsistent state machine. | `reducer.ts:33` |
| F8.2 | `clearError` / `RETRY_CLEARED` is exported and never called. Errors clear only via the next `SEND_STARTED`. Dead or unwired — decide which. | `useEpisode.ts:40`, `reducer.ts:34` |
| F8.3 | `inferTopic` matches substrings, not words, so a 5+ letter label word hits inside a longer word. Pre-existing and low-impact; add word boundaries while the file is open. | `inferTopic.ts:16` |
| F8.4 | `topics` is `[]` until `GET /topics` resolves. A message sent before then cannot infer a topic and silently becomes `general`. Instant in mock; real against a slow service. | `useEpisode.ts:16,19` |
| F8.5 | End-of-episode button says "Start a new topic" while the sidebar says "New chat". Guide §10.7. | `TutorFeatureApp.tsx:137` |

## F9 — Dead code to remove (guide §10.7, confirmed present)

- `src/features/tutor/TutorFeature.tsx` — 305 lines, imported nowhere.
- `TutorTabBar` in `TutorFeatureApp.tsx:201`, kept alive only by
  `void TutorTabBar;` at `:21`. That statement exists to silence an unused
  warning; delete both.
- `.tutor-header`, `.tutor-new-topic` in `index.css`.
- `pendingText` (see F3) if F3 is fixed the other way.

Removing these is ~370 lines and makes the next review cheaper. Do it in its own
commit so it never obscures a behavioural diff.

---

# Part 2 — Corrections to `frontend-and-api-guide.md`

The guide is accurate and genuinely useful — these are the exceptions, and they
matter because the backend team will build against it.

## G1 — `session_id` does not change per episode, and the guide says both things

§5 says `TOPIC_CHANGED` gives a "New `session_id`". §4.1 says `session_id` is
"per page load". **§4.1 matches the code; §5 does not.**

`reducer.ts:21` mints `sessionId` in `newEpisode()`, but `api/adapter.ts:58-59`
keeps its own module-level `getSessionId()` memoised for the page lifetime, and
**that** is what the request carries. The reducer's `sessionId` is never read by
anything.

Pick one and make code and guide agree:

- **Recommended:** keep per-page-load semantics, delete `EpisodeUI.sessionId`,
  and strike the claim from §5.
- Or make a new episode a new session, wire `state.sessionId` into the request,
  and tell the backend — it affects how they group turns.

This needs a decision because the backend may key storage on `session_id`.

## G2 — §4.6's "put back into the composer" is conditionally false

See F3. Correct the guide once F3 is fixed, and keep the UI string at
`TutorFeatureApp.tsx:137` honest with it.

## G3 — Worth adding to §10

- `vite.config.ts` sets `test.environment: 'node'`, so **no DOM or component
  tests are possible** as configured. The `include` glob lists `*.test.tsx`,
  which is misleading — such a file would fail on first render. This is why F1
  and F2 need pure functions to be testable, and it is a gap the next agent
  should know about before promising a test.
- `GET /health` failing is silent (F6), which belongs next to the existing
  item 1 about `general`.

---

# Part 3 — Suggested order of work

1. **F1** — data correctness, and it blocks trustworthy backend integration.
2. **F2** — same class of bug, same file, same fix session.
3. **F3, F4, F5** — student-facing and cheap.
4. **F6, G1** — needed before anyone tests `direct` mode.
5. **F7** — needs a screen reader; do not mark done without one.
6. **F8, F9** — cleanup, separate commits.
7. **G1–G3** — update the guide last, so it describes what the code now does.

Each of 1–6 should carry a regression test where the test environment allows one
(F1, F2, F8.1, F8.3 all can). Do not report an item fixed without either a test
or a stated manual reproduction that now passes.
