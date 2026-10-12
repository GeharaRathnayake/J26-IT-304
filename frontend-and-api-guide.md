# Java AI Tutor: Frontend and API Guide

**Audience:** another frontend agent picking up `dev/frontend`, and the backend team (tutor service and Express server) who need to know exactly what the frontend sends, expects and assumes.
**Last updated:** 2026-10-13 (revised after the frontend review; see `frontend-review-2026-10-13.md`)
**Scope of verification:** everything below was checked against the code in `dev/frontend` and exercised in the browser in **`mock` mode only**. `direct` and `express` modes are implemented but have **not** been run against a real server. Anything in §10 is a known gap or an open question, not a settled decision.

Related documents in this folder:

- `frontend/README.md` – run instructions and build-order status (written earlier; the "Status" table there is older than this file).
- `git.md` – Git strategy for the repo.
- `searchbar-animation-refinement-guide.md` – the earlier spec for the composer's sizing and animation behaviour. The composer has grown since (topic tokens, voice pill, Enter-to-send); §6 here is current.
- The planning documents the code comments refer to (`frontendPlan/…`, `ARCHITECTURE.md`, `10_DECISIONS.md`) are **not** in this folder. Treat `api/types.ts` and `api/schemas.ts` as the executable contract.

---

## 1. What this is

A React single-page app: the student-facing chat for the **Adaptive AI Voice Tutor for Java Programming** (J26-IT-304, PP1). The student asks questions about Java; the tutor service answers with one of four teaching strategies (theory, example, simplified, analogy), watches for confusion, escalates strategy when the student is still confused, and ends an episode as `resolved` or `end_unresolved`.

The frontend is deliberately thin. **All pedagogy lives in the tutor service.** The frontend renders what the service decides, holds the conversation state the service hands back, and never invents any of it.

Stack: React 19, Vite 6, TypeScript (strict), Tailwind CSS v4, Zod for runtime validation, Vitest. Fonts: Nunito via `@fontsource`.

## 2. Running it

```bash
cd dev/frontend
npm install
npm run dev          # http://localhost:5173 (port set in vite.config.ts)
npm run typecheck
npm test             # 37 tests (contract schemas, reducer, episode rules, topic inference)
npm run build        # typecheck, then production build
```

No backend is needed: the default transport is `mock`.

### Configuration (`.env`, copy from `.env.example`)

| Variable | Default | Meaning |
|---|---|---|
| `VITE_TUTOR_MODE` | `mock` | `mock` \| `direct` \| `express` |
| `VITE_TUTOR_URL` | `http://localhost:8001` | FastAPI tutor service base URL, used by `direct` |
| `VITE_EXPRESS_BASE` | `/api` | Base path of the team Express server, used by `express` |

Read in `src/features/tutor/config/env.ts`. Unknown or missing mode falls back to `mock`.

## 3. Architecture at a glance

```
 student ──> TutorFeatureApp (UI) ──> useEpisode (hook) ──> transport adapter ──> backend
                  │                        │                       │
                  │                  episodeReducer          Zod validation
                  │                  (pure state)            (schemas.ts)
                  └─ SearchComposer, Transcript, VoicePanel, ResearchPanel
```

- **Everything is under `src/features/tutor/`.** `main.tsx` and `index.html` are the only standalone-specific files; the feature mounts into a larger app by importing `TutorFeature` from `features/tutor` (see `index.ts`).
- **No component calls `fetch`.** All backend access goes through `api/adapter.ts`.
- **Every response is validated at the boundary** (`api/schemas.ts`). A shape mismatch throws a `TutorError` of kind `contract`; it never renders as a blank badge.

### File map

| Path | Role |
|---|---|
| `src/main.tsx` | Standalone entry. Safe to delete when embedding. |
| `src/index.css` | Tailwind v4 theme tokens and all component CSS (`.tutor-*` classes). |
| `features/tutor/index.ts` | Public surface: `TutorFeature` + contract types. |
| `features/tutor/TutorFeatureApp.tsx` | The whole screen: sidebar, voice panel, transcript, research panel, voice-mode wiring. |
| `features/tutor/SearchComposer.tsx` | The message composer (see §6). |
| `features/tutor/useEpisode.ts` | The hook the UI talks to: `send`, `chooseTopic`, `reset`, health, topics, mock fault switch. |
| `features/tutor/episodeRules.ts` | **Pure decisions behind `send`** (what a turn puts on the wire, the in-flight latch, topic resolution, health probe). Exists so they are unit-testable (see §10, item 4). |
| `features/tutor/reducer.ts` | Pure episode state machine (see §5). Unit tested. |
| `features/tutor/api/types.ts` | **Contract types. Shared with the Express teammate.** |
| `features/tutor/api/schemas.ts` | Zod schemas for every response. |
| `features/tutor/api/adapter.ts` | The three transports (`mock`, `direct`, `express`) behind one interface. |
| `features/tutor/api/mockTransport.ts` | In-memory re-implementation of the tutor state machine, with fault injection. |
| `features/tutor/api/errors.ts` | `TutorError` taxonomy. |
| `features/tutor/api/fixtures/` | Sample payloads (`tutor-response.*.json`, `episode-log.json`, `topics.json`). Safe to share with backend for contract tests. |
| `features/tutor/config/topics.ts` | Fallback topic list (the service owns the real one). |
| `features/tutor/inferTopic.ts` | Guesses a topic from free text (see §7). |
| `features/tutor/useMicrophone.ts`, `useSpeechInput.ts`, `voiceState.ts`, `VoiceAura.tsx`, `VoiceWave.tsx` | Voice mode (see §8). |
| `src/components/agents-ui/*`, `src/hooks/agents-ui/*`, `src/lib/utils.ts` | Third-party visualizer code (LiveKit registry) plus a `cn` helper. Do not edit casually. |

**Rule for any agent editing here:** files under `api/` (`types.ts`, `schemas.ts`, `fixtures/`) are a shared contract. Do not change them without agreement from the backend side.

## 4. The API contract

The frontend talks to one logical service with four endpoints. Paths below are relative to the transport base (`VITE_TUTOR_URL` for `direct`, `VITE_EXPRESS_BASE` for `express`).

| Method and path | Purpose | Response |
|---|---|---|
| `POST /tutor/message` | Send one student turn | `TutorResponse` |
| `GET /health` | Service status; drives a "template responses" banner, and an "unreachable" alert if the call itself fails | `HealthResponse` |
| `GET /model-info` | Model metadata for the research panel | `ModelInfo` |
| `GET /topics` | The authoritative topic list | `TopicOption[]` (non-empty) |

`GET /topics` failing is tolerated: the frontend falls back to the static list in `config/topics.ts`. A topic slug the service does not know produces a **422**, so the two lists must not drift.

### 4.1 Two transport modes, two request shapes

**`direct`** (PP1 demo): the browser talks to the FastAPI service and **holds the tutoring state itself**.

```jsonc
POST {VITE_TUTOR_URL}/tutor/message
{
  "request_id": "uuid",          // generated per call; the response must echo it
  "student_id": "stu_ab12cd34",  // pseudonymous; stored in localStorage
  "session_id": "sess_ab12cd34", // per page load
  "topic": "loops",              // snake_case slug
  "message": "…",                // the student's text
  "history": [ { "role": "student"|"tutor", "text": "…", "strategy"?: "theory", "ts": "ISO-8601" } ],
  "state": null,                 // null on the first message of a topic; else the last updated_state, verbatim
  "profile": null                // always null in PP1
}
```

**`express`** (target architecture): the browser sends only what the student decided; **Express owns state, history, ids and profile**.

```jsonc
POST {VITE_EXPRESS_BASE}/tutor/message
{ "topic": "loops", "message": "…" }
```

In `express` mode the frontend does not send a `request_id`, so the request-id echo check is skipped. Express is expected to return the same `TutorResponse` shape the tutor service does.

Notes on the `direct` body:

- `history` contains all earlier turns and **does not include the message being sent** (that is in `message`).
- `state` is the previous `updated_state` echoed back **unmodified** (invariant I1: the frontend never constructs or edits it).
- `student_id` is never a name or email (NFR-05).

### 4.2 `TutorResponse`

```jsonc
{
  "request_id": "echo",
  "confusion": { "label": "confused"|"understood", "probability": 0..1, "source": "rule"|"model" },
  "detected_request": "theory"|"example"|"simplified"|"analogy"|null,  // strategy the student explicitly asked for
  "action": "explain"|"resolved"|"offer_new_cycle"|"end_unresolved"|"clarify",
  "strategy": "theory"|"example"|"simplified"|"analogy"|null,
  "trigger": "default"|"confusion"|"request"|"personalised"|null,
  "response": "markdown text shown to the student",
  "updated_state": { "episode_id", "cycle", "strategies_used":[{strategy,trigger}], "awaiting_cycle_confirmation", "prior_explanations":[…] },
  "episode_log": null | { …EpisodeLog… },
  "meta": { "model_version", "llm", "latency_ms": {classify,llm,total}, "fallback"?: boolean }
}
```

Cross-field rules **enforced by the frontend** (a violation is a `contract` error):

1. `action` is `resolved` or `end_unresolved` **if and only if** `episode_log` is non-null.
2. `action === "explain"` requires a non-null `strategy`.
3. In `direct` mode, `request_id` must equal the one sent.
4. All fields in `api/schemas.ts` are required with the listed types. The schemas are not strict: extra, unknown fields are silently dropped, not rejected.

`response` is rendered as **Markdown** (code fences get syntax highlighting). A `**Check:** <question>` segment, preceded by a newline, is pulled out and shown as a separate "check" line; keep that convention for the end-of-turn comprehension question.

### 4.3 What each `action` does in the UI

| `action` | UI result | Phase after |
|---|---|---|
| `explain` | Tutor reply shown; student can answer | `awaiting_student` |
| `clarify` | Tutor reply shown (asks for a clearer answer) | `awaiting_student`, **or `awaiting_cycle_decision` if `updated_state.awaiting_cycle_confirmation` is still true** (the mock's `clarify` after an unclear yes/no keeps it true) |
| `offer_new_cycle` | Reply shown **plus** Yes/No buttons that send the literal messages `"yes"` / `"no"` | `awaiting_cycle_decision` (when `updated_state.awaiting_cycle_confirmation` is true) |
| `resolved` | Reply shown, "Episode complete" card, composer disabled | `closed` |
| `end_unresolved` | Same as `resolved` | `closed` |

The phase is derived by `phaseFromResponse` in `reducer.ts`: `resolved` / `end_unresolved` give `closed`; otherwise **`updated_state.awaiting_cycle_confirmation` decides** between `awaiting_cycle_decision` and `awaiting_student`, whatever the `action` is. So a backend that wants the Yes/No buttons must set that flag, not only return `offer_new_cycle`.

All five must be handled by any alternative implementation. `meta.fallback === true` shows a "template response" tag so a fallback is never passed off as LLM output.

### 4.4 `EpisodeLog` (non-null only when the episode ends)

`schema_version: "1.0"`, `episode_id`, `student_id`, `topic`, `started_at`, `ended_at`, `outcome` (`resolved`|`end_unresolved`), `cycles`, `deliveries[]` (`seq, strategy, trigger, cycle, student_label, probability, source`), `counted_strategies`, `requested_strategies`, `winning_strategy`, `winning_combination[]`, `is_weak`, `weak_rule`, `model_version`. `counted_strategies` excludes `trigger: "request"` deliveries (this is what makes requested vs confusion-driven strategies measurable). The frontend stores it as received and shows it in the research panel; Express persists it unchanged.

### 4.5 `HealthResponse` and `ModelInfo`

```jsonc
GET /health      -> { "status": "ok"|"degraded", "model_loaded": bool, "llm_reachable": bool, "model_version": string|null }
GET /model-info  -> { "version", "trained_at", "dataset", "threshold": number, "metrics": { "<name>": number } }
```

`llm_reachable: false` shows an amber "Running with template responses." banner. If the `/health` request itself fails (service down, CORS, offline), the UI shows a red "Can't reach the tutor service." alert with a Retry button; the check is tracked as `checking` / `ok` / `unreachable` in `useEpisode`.

### 4.6 Errors

| Condition | Frontend `TutorError.kind` | Student sees | Retryable |
|---|---|---|---|
| fetch throws (offline, CORS, DNS) | `network` | "Connection lost. Your message is still here, try again." | yes |
| HTTP 503 | `model_unavailable` | "The tutor is not available right now." + red banner with Retry | no |
| HTTP 504 | `llm_timeout` | "That took too long to answer. Try sending it again." | yes |
| HTTP 422 | `validation` | generic "Something went wrong." | no. Developer detail in the research panel. Means contract drift or an **unknown topic slug**. |
| any other non-2xx | `unknown` | generic | no |
| 2xx but body fails Zod / request-id mismatch | `contract` | generic | no. Loud (`console.error`) in dev. |

On a failed send the student's message is marked `failed` (shown in a light red bubble) and **put back into the composer on every failure, including repeated failures of the same text** (verified against a fake `direct` server returning 503 three times in a row), with focus returned to the composer so Enter resends. The error body (JSON or text) is kept as `detail` for developers only.

### 4.7 Other contract facts the backend should know

- **CORS.** In `direct` mode the browser calls the tutor service from another origin (dev: `http://localhost:5173` to `:8001`), so the service must send CORS headers for the dev and deploy origins.
- **Express base path.** `express` mode uses the relative base `/api`. `vite.config.ts` has **no dev proxy** configured, so for local `express` testing either add a proxy or set `VITE_EXPRESS_BASE` to an absolute URL with CORS enabled.
- **Topic slugs** are snake_case, regex `^[a-z][a-z0-9_]*$`. The frontend sends exactly the `id` from `GET /topics`.
- **The message text may contain the topic's display label** (for example `Loops why do we need these`), because topic selection inserts the label into the sentence (§6). The `topic` field is still sent separately and is the authority.
- **Voice turns arrive as ordinary text.** There is no audio upload and no voice field in the contract (§8).

## 5. Episode state machine (frontend side)

`reducer.ts` holds the state; `useEpisode` wraps it.

Phases: `idle` → `awaiting_student` → `awaiting_tutor` → (`awaiting_student` | `awaiting_cycle_decision` | `closed`).

| Action | Effect |
|---|---|
| `TOPIC_CHANGED(topic)` | **Starts a brand-new episode** (clears messages, history and server state). `session_id` does **not** change: it is minted once per page load by `api/adapter.ts` and shared by every episode (see §10, item 11). |
| `SEND_STARTED` | Appends the student message, phase `awaiting_tutor`. May carry `voice: true`. |
| `SEND_SUCCEEDED` | Appends the tutor message, stores `updated_state` and `episode_log`, derives the next phase from `action` (see §4.3). |
| `SEND_FAILED` | Marks the last student message `failed`, keeps the previous server state, stores the error. |
| `RESET` | Back to an empty, topic-less episode. |

`useEpisode.send(message, options?)`:

- Ignored when the message is blank or the phase is `awaiting_tutor` / `closed` (the user-visible rule), **and** while another send holds an in-flight latch (a `useRef` latch set synchronously before the first dispatch, released in `finally`). The latch is the correctness guarantee: two calls from the same render both read the same captured `phase`, so the phase check alone cannot stop them.
- Topic chosen by `resolveTurnTopic`: `options.topic` → the current topic → a topic named in the message (`inferTopic`) → **`GENERAL_TOPIC` (`'general'`)**. While `GET /topics` has not answered yet, inference **waits** for it instead of inferring from an empty list. If the result differs from the current topic it dispatches `TOPIC_CHANGED`, which restarts the episode.
- The wire payload comes from `turnInputFor(state, topic, message)`: a turn on the **same topic** carries the accumulated `history` and the last `updated_state` verbatim; a turn whose topic differs from the episode's belongs to a **new episode** and carries `history: []` and `state: null`. (Today's UI callers always change topic via `TOPIC_CHANGED` before calling `send`, so this guard is hardening, not a live bug.)
- Sends through the transport, then dispatches success or failure.

## 6. The composer (`SearchComposer.tsx`)

It looks like a search bar but is a **multiline message composer**: a `<textarea>` with a mirror layer on top.

Behaviour a maintainer must not break:

- **Enter sends; Shift+Enter inserts a newline.** (An earlier spec said the opposite; this was changed on request.) Enter during IME composition is ignored.
- **Sizing.** Idle: a 40px single-line pill. When the text would wrap, it flips to a growing multiline box (22px lines, +8px breathing room, cap 146px / 6 lines, then internal scroll with the scrollbar hidden). Font steps 16 to 15px at 4 estimated lines. All measurement is in one `useLayoutEffect`; the geometry constants (reserved space for the topic, voice and send buttons) are named at the top of the file and drive both the CSS padding and the measurement probe. See `searchbar-animation-refinement-guide.md` for the reasoning.
- **Docking.** The composer rests 230px above its docked position while the conversation is empty and voice mode is off; it slides down (240ms) on the first message or when voice mode starts.
- **Topic tokens.** Picking a topic from the in-bar picker **inserts its label into the text at the caret** (several topics can be in one sentence). The label is drawn in bold accent blue by the mirror layer. The topic stays "active" while its exact label appears anywhere in the text; editing the label (for example deleting a letter) turns it back into plain text and, **before the first message is sent**, clears the topic or falls back to another label still present. After the first message the topic is left alone, because changing topic restarts the episode. A topic chosen elsewhere (the sidebar's recent-chat items) is inserted into the draft the same way.
- **No topic is required to send, and a label-only draft is sendable.** Picking "Loops" and pressing Enter sends the message `Loops` under topic `loops`. If no topic is picked, a topic named in the text is used (§7); otherwise the message is sent as a general chat (§10, item 1).
- **Focus.** The textarea is disabled while the tutor replies; the composer gives focus back when it re-enables (unless the student focused something else), so a student can keep typing and pressing Enter without clicking.
- **Voice button.** Always available, even with text typed (the typed draft is kept untouched while voice mode is on and returns when it ends), except while the tutor is replying or the episode is closed. See §8.
- The topic picker keeps `role="listbox"` and closes on outside pointer. Buttons use `onMouseDown` preventDefault so clicking them never steals focus from the textarea.
- Clicking empty space in the main area focuses the composer (not buttons, links, or when text is selected).

## 7. Topic inference (`inferTopic.ts`)

Case-insensitive, **whole-word** match of a topic's full label, or one of its longer label words (5+ letters, excluding generic words such as "types", "statements"), against the message (so "functions" does not match inside "dysfunctions"). The topic mentioned **earliest** wins. It only runs when no topic is currently selected. It is a convenience, not a classifier; the backend should still validate the slug.

## 8. Voice mode

Pressing the mic button starts a voice session. It **never records or uploads audio**.

| Piece | What it does |
|---|---|
| `useMicrophone` | Opens the mic via `livekit-client`'s `createLocalAudioTrack()` (lazy-loaded). On failure shows an amber alert and leaves voice mode. Released when voice mode closes. |
| `voiceState.ts` | Mic level to `'speaking'` (above 0.03) or `'idle'`. Only the student's own voice drives the visuals; tutor output or "thinking" states are never shown. |
| `VoiceAura.tsx` | Aura animation at the top of the page (slides down 240ms, back up on close). |
| `VoiceWave.tsx` | Wave inside the composer, which shrinks to a pill (320px) holding only the wave and the stop (X) button. |
| `useSpeechInput.ts` | Browser **Web Speech API** (`SpeechRecognition`/`webkitSpeechRecognition`). Final utterances are sent as messages via `send(text, { voice: true })`. Ignored while the tutor is replying. Shows a notice when the browser has no support. |
| `VoiceResponse` (in `TutorFeatureApp.tsx`) | While voice mode is on, the main area shows only the tutor's replies for this session, stacked with a divider line between each, scrollable (it follows new text unless scrolled up). The newest reply is revealed word by word (about 6 words/s) to feel spoken. |

Facts that matter to the backend and to privacy review:

1. **No LiveKit server is involved.** `livekit-client` / `@livekit/components-react` are used only for the mic track and audio level; there is no room, token, or agent.
2. **Speech-to-text runs in the browser's own service.** In Chrome and Edge the audio is sent to the browser vendor's cloud for recognition. The tutor service receives only the resulting text. Firefox and Safari lack the API, so spoken messages cannot be sent there. Confirm this is acceptable for the study's ethics approval before real students use it.
3. **`voice: true` is a UI-only flag** on the message. It makes the chat show a generic "Voice message" pill instead of the recognised text. It is **not** in the request contract and the backend never sees it. Do not rely on it server-side.
4. **No streaming.** The service returns the full reply; the word-by-word reveal is purely client-side. There is no audio output (no TTS) yet.
5. `UIMessage` has reserved `transcript` / `audioUrl` fields for PP2; nothing populates them today.
6. The aura and wave components come from the LiveKit UI registry under the **Polyform Non-Resale License** (see the file headers in `src/components/agents-ui/`). Check this fits the project's intended use.

### Voice mode and assistive technology (review F7: implemented, **not verified with a screen reader**)

The reply is revealed word by word every 250ms, which a live region would re-announce on every tick. So the voice response scroller is **not** a live region; the reply currently being revealed is `aria-hidden`; and a separate visually-hidden `role="status"` region says "The tutor is thinking." while waiting and then reads the **finished** reply once. The DOM states were checked in a browser; the spoken behaviour has **not** been tested with NVDA or Narrator. Treat as open until it has.

### Chat rendering after voice

On leaving voice mode the normal transcript returns: tutor replies are plain text on the page (not bubbles), student typed messages are right-aligned bubbles with a "YOU" label, and student voice messages are a "Voice message" pill without the label. A failed message uses a light red bubble (`#7f1d1d` on `#fef2f2`, 9.16:1 contrast). The tutor-reply and voice-response scrollers have bottom padding so the last lines are never under the absolutely-positioned composer.

## 9. Mock transport (use it for frontend work and for backend contract tests)

`api/mockTransport.ts` re-implements the service's behaviour in memory so the whole UI can be built and tested without a backend:

- Strategy escalation order: theory → example → simplified → analogy; a student-requested strategy (keywords like "example", "simpler", "analogy") is delivered with `trigger: "request"` and does not consume a slot in the escalation cycle.
- A message that classifies as "understood" after at least one delivery returns `resolved` with an `episode_log`.
- After all four strategies, if cycle < 2 it returns `offer_new_cycle`; "yes"/"no" are interpreted; otherwise `end_unresolved`. Max cycles is 2 (`DISPLAY_MAX_CYCLES`, display-only; the service is the authority).
- Accepts **any** topic slug (including `general`). The real service does not necessarily do so.
- **Fault injection:** a dropdown in the research panel (`MockFault`: `none`, `503`, `504`, `fallback`, `slow`, `malformed`) exercises every error path above.

The `fixtures/*.json` files plus `schemas.test.ts` are a ready-made contract test: a backend response that passes these schemas will render.

## 10. Known gaps, open questions and things that will bite you

1. **General (no-topic) chat vs the real service.** Messages sent with no topic use the slug `general` (`GENERAL_TOPIC` in `episodeRules.ts`, re-exported from `useEpisode.ts`). The service returns 422 for unknown slugs, so **it must accept `general` (or tell the frontend which existing slug to use)** before no-topic chats work outside mock mode. Backend decision needed.
2. **Express mode proxy.** No dev proxy for `/api` (see §4.7).
3. **Topic switch restarts the conversation.** Choosing or inferring a different topic mid-chat discards the episode. This is existing reducer behaviour, not a bug, but a product owner may want a different rule.
4. **`direct` and `express` against a real service: untested.** `mock` has been exercised end to end, and `direct` mode has been exercised against a throwaway fake server that implements the four endpoints. That proved the request/response plumbing, error paths and health banner, but **not** the real tutor service. Run the contract fixtures against the real service first. **No DOM tests are possible as configured:** `vite.config.ts` sets `test.environment: 'node'`, so a component or hook test cannot render. That is why the decisions behind `send` live in pure functions in `episodeRules.ts`; to test components, add `jsdom` + `@testing-library/react` and widen the `include` glob.
5. **Voice privacy and licensing**: items 2 and 6 in §8.
6. **Voice latency feel**: the reveal pace is a constant (`REVEAL_WORDS_PER_SECOND`), not synced to any audio.
7. **Dead code: removed.** The unmounted `TutorFeature.tsx`, `TutorTabBar`, the unused header and tab-bar CSS and the unread `pendingText` / `RETRY_CLEARED` / `EpisodeUI.sessionId` have been deleted, and the end-of-episode button now says "Start a new chat".
8. **Bundle size.** The voice visualizers add about 700 kB and are loaded lazily on first use; the main chunk is also over 500 kB. No code-splitting beyond that has been done.
9. **README status table** in `frontend/README.md` predates the work described here.
10. **Theme.** Colour tokens are CSS variables in `index.css`. The `prefers-color-scheme: dark` block deliberately reuses the **same light values**, so the UI is visually identical in both OS themes (only the voice aura switches its own light/dark mode). A real dark theme does not exist yet.
11. **`session_id` semantics (needs a supervisor decision).** The request's `session_id` is per **page load**, not per episode, even though a topic change starts a new episode. The reducer used to mint an unused per-episode `sessionId`; it has been removed. If the backend groups or stores turns by `session_id`, tell the frontend: switching to per-episode sessions is a small change (wire a per-episode id into the request) but affects how turns are grouped.

## 11. Quick checklist for the backend team

- [ ] `POST /tutor/message` returns exactly the `TutorResponse` shape in §4.2 (run `api/fixtures/*.json` through `schemas.ts` or compare field by field).
- [ ] `episode_log` is non-null **iff** `action` is `resolved` or `end_unresolved`.
- [ ] `request_id` is echoed (direct mode).
- [ ] `updated_state` is complete: the frontend echoes it back verbatim next turn.
- [ ] `GET /topics` returns the full list; slugs match `config/topics.ts` or the frontend list is replaced at runtime (it is, on a successful call).
- [ ] 503 / 504 / 422 are used as in §4.6.
- [ ] CORS configured for the frontend origin (direct mode).
- [ ] Decide how to handle slug `general` (§10, item 1).
- [ ] Express: accept `{ topic, message }` only; own `state`, `history`, ids; return the same response shape.

## 12. Quick checklist for a new frontend agent

- Start with `api/types.ts` and `api/schemas.ts`, then `reducer.ts`, `useEpisode.ts`, then `TutorFeatureApp.tsx`.
- Run `npm run typecheck` and `npm test` before and after any change. Both must pass.
- Do not touch `api/` casually; it is a shared contract.
- Composer changes: re-read `searchbar-animation-refinement-guide.md` and the named constants at the top of `SearchComposer.tsx`. Keep the textarea's vertical padding at 0 and all measurement in the single `useLayoutEffect`.
- Voice changes: remember the browser speech service sends audio to a third party (§8).
- If you need a real microphone or speech recognition in automated tests, fake `navigator.mediaDevices.getUserMedia` and `window.SpeechRecognition` (this is how voice mode was verified).
