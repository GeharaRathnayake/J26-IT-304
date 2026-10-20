# Java AI Tutor — Frontend (Outdated, adjust according to what's currently in backend folder and rewrite this file as well.)

<!--
PP1 tutoring UI for the **Adaptive AI Voice Tutor for Java Programming** component of J26-IT-304 (SLIIT).

Plan and decisions live in [`../../frontendPlan/`](../../frontendPlan/). `10_DECISIONS.md` is the authority on open questions.

---

## Run it

```bash
npm install
npm run dev          # http://localhost:5173
```

No backend is required. The default transport is `mock`, which implements the
tutor service's state machine in memory (steps F1–F9 of the build order).

| Script | Does |
|---|---|
| `npm run dev` | Dev server with HMR |
| `npm run build` | Typecheck, then production build |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Contract + unit tests (Vitest) |
| `npm run test:watch` | Tests in watch mode |

## Configuration

Copy `.env.example` to `.env` to change anything. Defaults work with no file present.

| Variable | Default | Meaning |
|---|---|---|
| `VITE_TUTOR_MODE` | `mock` | `mock` \| `direct` \| `express` |
| `VITE_TUTOR_URL` | `http://localhost:8001` | FastAPI tutor service, for `direct` |
| `VITE_EXPRESS_BASE` | `/api` | Team Express server, for `express` |

**Transport modes** (`frontendPlan/04_API_CONTRACT.md`):

- **`mock`** — no network. Build and test the whole UI before the backend exists.
- **`direct`** — straight to the FastAPI tutor service. The PP1 demo mode; the frontend holds and resends `state`.
- **`express`** — through the team server, which owns `state`. The target architecture.

## Structure

```
src/
├── main.tsx                     # standalone entry — the ONLY file not portable
├── index.css                    # Tailwind v4 + semantic theme tokens
└── features/tutor/              # the entire module; mounts into the team app
    ├── index.ts                 # public surface: TutorFeature + contract types
    ├── TutorFeature.tsx         # F1 shell (three regions)
    ├── api/
    │   ├── types.ts             # ⭐ contract types — SHARED with Express teammate
    │   ├── schemas.ts           # Zod validation at the boundary
    │   ├── errors.ts            # TutorError taxonomy
    │   ├── schemas.test.ts      # contract tests
    │   └── fixtures/            # ⭐ sample payloads — SHARE with Express teammate
    └── config/
        ├── topics.ts            # fallback topic list (service owns the real one)
        └── env.ts               # transport mode
```

### Integrating into the team's React app

1. Copy `src/features/tutor/` into the team app.
2. `import { TutorFeature } from '@/features/tutor'` and mount it on a route.
3. Delete `src/main.tsx` and `index.html`.
4. Merge the `@theme` block and `:root` tokens from `index.css`.

Nothing else is standalone-specific. No component calls `fetch` directly — all
backend access goes through the transport adapter.

## Status

| Step | State |
|---|---|
| F1 scaffold + shell | ✅ done |
| F2 contract types + Zod schemas | ✅ done (15 tests passing) |
| F3 mock transport + fault switch | ✅ done |
| F4 reducer + `useEpisode` | ✅ done |
| F5–F9 conversation, actions, chips, panel, degradation | ✅ done |
| F10 direct + Express adapters | ✅ done; live verification needs the team services |
| F11 Markdown/Java rendering, accessibility, responsive/dark mode | ✅ done |
| F12 mock-mode demo path | ✅ ready to rehearse |

The standalone frontend now runs end to end in `mock` mode. F10's live-service
verification remains dependent on the team's FastAPI and Express servers.

## For the Express teammate

Two files are the contract: `src/features/tutor/api/types.ts` and
`src/features/tutor/api/fixtures/*.json`. Use the fixtures in your own contract
tests so a contract change breaks a test immediately rather than surfacing
during integration.

Three things must survive the Express hop unchanged:

1. `updated_state` round-trips byte-for-byte — store it, don't normalise it.
2. `episode_log` stays `null` except when the episode ends.
3. `meta.latency_ms` stays the tutor service's own figures. If you add Express
   hop latency, use a separate field — overwriting makes the NFR evidence wrong
   in a direction that flatters us.

-->
