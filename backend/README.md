# Tutor service (backend)

FastAPI service for J26-IT-304, *Adaptive AI Voice Tutor for Java Programming*.

**What it does:** at startup it loads the confusion classifier `clf-v1.0.0` and proves it is
the right file and the right way round. It then serves `GET /health`, `GET /topics`,
`GET /model-info` and `POST /tutor/message`. Explanations come from `llama3.2:3b` on Ollama, with a
template fallback for any reply that would not ship.

> **Honesty caveat.** The classifier is a *prototype component*: a TF-IDF +
> LogisticRegression pipeline trained on a **synthetic** dataset, where "answer not fully
> correct" is used as a proxy for "confused". It separates correct from not-fully-correct
> synthetic answers. It has never seen a real student message and is **not** a validated
> confusion detector (for example it scores `"that makes sense"` at ~0.99 confused).

## Demo path (rehearsed): venv + `python -m app` on `127.0.0.1:8001`

The demo runs uvicorn directly from the venv, not Docker. Building an image needs a
network (which sits badly with an offline-operation claim), reaching Ollama from a
container needs extra plumbing, and the venv has fewer moving parts on demo day.

Requires Python 3.13 and scikit-learn **exactly 1.9.1** (the version the artifact was
pickled with). Run from `dev/backend/`. Bare `python` on the lab machine is 3.10, so use
the venv's interpreter:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt   # runtime pins + pytest + httpx
.\.venv\Scripts\python -c "import sklearn; print(sklearn.__version__)"   # must print 1.9.1
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m app          # the demo command: http://127.0.0.1:8001
curl.exe http://127.0.0.1:8001/health
```

### Why the port is 8001

**8001 is fixed.** The frontend's committed default is `VITE_TUTOR_URL=http://localhost:8001`
(`frontend/src/features/tutor/config/env.ts`; `ARCHITECTURE.md` §7 says the same). Do not
pick another port. `HOST` (default `127.0.0.1`) and `PORT` (default `8001`) are settings;
the Docker image sets `HOST=0.0.0.0`.

### Windows port reservation: re-check on the day

Windows reserves dynamic TCP port ranges, and **the reserved ranges move after a reboot**.
On 2026-10-14 the range 7964-8063 (covering 8000 and 8001) was reserved. Before any demo:

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
```

8001 must appear as its **own row marked `*`** (administered). If 8001 falls inside a
dynamic range, or the service fails to bind with "forbidden by its access permissions",
a human runs this in an **administrator** shell (never the service):

```
net stop winnat
netsh int ipv4 add excludedportrange protocol=tcp startport=8001 numberofports=1
net start winnat
netsh interface ipv4 show excludedportrange protocol=tcp
```

## Development convenience: build, test, optional run (Docker)

Run from `dev/backend/`. The image is `python:3.13.16-slim` (pinned by digest), the exact
Python the artifact was trained on, with scikit-learn 1.9.1.

```powershell
docker compose build          # both targets: runtime (api) and test
docker compose run --rm test  # python -m pytest inside the test image
docker compose up -d api      # serves on 127.0.0.1:8001 (localhost only)
curl.exe http://127.0.0.1:8001/health
docker compose down
```

> **Build the image in advance on any demo machine.** Building needs a network (base image
> and pip); running does not.

- The container runs as a non-root user. Its `HEALTHCHECK` passes only if `/health`
  returns `"status": "ok"`, so a degraded start (the process still exits 0) shows as
  `unhealthy` in `docker ps`.
- The `runtime` target holds `app/` and `models/` only; the `test` target adds dev
  dependencies and `tests/`.
- The `api` container reaches the host's Ollama at `http://host.docker.internal:11434`
  (`extra_hosts: host-gateway` in `compose.yaml`).
- If the host port is unavailable, `API_PORT` overrides it for Docker only
  (`$env:API_PORT='8200'; docker compose up -d api`); the frontend still expects 8001.
- `models/` must stay byte-exact (`.gitattributes` keeps Git from rewriting line endings).
## The tutoring endpoint

`POST /tutor/message` classifies the student's message (the hybrid: explicit phrases first, then
the model, a **prototype proxy trained on synthetic answers**, not a validated confusion
detector), decides the next move with the escalation engine, and returns a full `TutorResponse`
(`frontend/src/features/tutor/api/types.ts`). It is **stateless**: the client echoes
`updated_state` and `history` each turn, so a restart mid-episode loses nothing.

| Setting (env var) | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` generates explanations with a local model; `template` serves the bundled template replies (`meta.fallback: true` on every turn); `mock` uses a test adapter. Any other value fails at startup. |
| `LLM_MODEL` | `llama3.2:3b` | Decision D2 (see below). |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | `127.0.0.1`, not `localhost` (an IPv6 lookup delay on Windows). Docker sets `http://host.docker.internal:11434`. |
| `LLM_MAX_TOKENS` | `220` | `num_predict`. r3, owner decision B (2026-10-17): 220 (r2 used 110). On the GPU, r3 was 100% / 97.9% shippable in form (cycle 1 / cycle 2), with 33.3% / 39.6% of replies stopped at this cap and wall p95 about 6 s (see "The LLM and its safety net" and `benchmarks/llm/README.md`). r2 at 110 was 87.5% shippable in form. |
| `LLM_TIMEOUT_S` | `18.0` | Cutoff for a generation call: `ceil(max(p95_cycle1, p95_cycle2_same) × 1.2)` at r2's 110 tokens (dGPU off) = `ceil(max(11.0, 14.6) × 1.2)` (S8b; see `benchmarks/llm/README.md`). Not re-derived for r3 (lead ruling): it guards the dGPU-off case, and r3's GPU p95 is about 6 s. Never derive it from the 3 s latency target. |
| `LLM_THINKING_MODEL` | `qwen3:4b` | Thinking mode only (T1, opt-in per request): the model used when a turn is sent with `thinking: true`. |
| `LLM_THINKING_TIMEOUT_S` | `180.0` | Thinking mode only: the probe's uncapped 120 s x 1.5. Separate from `LLM_TIMEOUT_S`, which stays 18 s and is not re-derived. Must be > 0. |
| `LLM_THINKING_KEEP_ALIVE` | `10m` | Thinking mode only: how long Ollama keeps the thinking model loaded. An Ollama duration (`10m`, `30s`, `1h`), `0` or `-1`. |
| `TURN_LOG_PATH` | unset | Opt-in per-turn research log (see below). |
| `WEAK_THRESHOLD` | `3` | `is_weak` when counted strategies reach this or the episode ends unresolved. |
| `MAX_CYCLES` | `2` | Explanation cycles per episode. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Browser origins allowed to call the service (decision D5: the frontend calls it cross-origin). Comma-separated, no JSON quoting. **Exact origins only: no `*`, no trailing slash, no path, scheme required** (a trailing slash never matches the browser's `Origin`); any of these fails at startup with a message naming `CORS_ORIGINS`. Only a **browser** enforces CORS: curl and the tests pass whether or not it is right, so use the browser check below. |

**The LLM and its safety net (D2).** Benchmark: `benchmarks/llm/SUMMARY.md`. `qwen3:4b` was
disqualified (untagged reasoning in 100% of replies). `llama3.2:3b` showed no reasoning leak. **Where D2
stands for `llama3.2:3b` (r2 and r3, both results) is the block "D2, as at 2026-10-17" in
`benchmarks/llm/README.md`; read it there, it is not paraphrased here.** The template is the
deterministic safety net either way: every reply is post-processed, and
one that would not ship (`app/generation/postprocess.py::would_ship`: not shippable in form, or
untagged reasoning), a timeout or any error is replaced by the template with `meta.fallback: true` and one
WARNING naming the reason (`not_usable`, `reasoning_leak`, `timeout` or the error type; never the
student's text or the model's output). `meta.llm` is `ollama:llama3.2:3b` on every turn, including
fallback turns. At startup a background warm-up loads the model (`keep_alive: 30m`); it never
blocks or fails startup. With Ollama stopped the service still answers every turn, with templates.

**Thinking mode (T1): opt-in, off by default, slow by design.** A request may carry `"thinking": true`
(additive; an old frontend that never sends it gets `false`, and a non-boolean is a 422). Such a turn is generated
by `LLM_THINKING_MODEL` (`qwen3:4b`) with `think: true` and **no token cap**, under its **own** timeout
`LLM_THINKING_TIMEOUT_S` (180 s) and `LLM_THINKING_KEEP_ALIVE` (10m), using the same prompt (r3 plus the M1
conversation block) and the same shippable-in-form gate. **Slow by design: 1 to 2+ minutes per reply on this
GPU.** The probe (`benchmarks/llm/thinking_probe/`, backend lead, 2026-10-16, with the **r2** prompt): capped at
1500 tokens, 0 of 5 answered (the whole budget went on thinking, 39.8 to 45.6 s each); uncapped, 4,229 tokens,
119.9 s, then a correct 35-word reply (n = 1: **thinking mode's accuracy is not measured**, and nothing here
claims it is more accurate). The template fallback still applies: a thinking turn that times out or is not
shippable in form serves the template with `meta.fallback: true`. `meta.thinking` is true iff the turn was
requested with thinking, and `meta.llm` names the model that was asked (`ollama:qwen3:4b`), so the two flags
together say what the student got. **The thinking text is discarded**: never returned, logged, put in the turn
log or the episode log, or put in an error message. The thinking model is not warmed at startup (it would compete
for VRAM with the default model); the first thinking turn pays the load. The classifier still sees the current
message only. **VRAM finding (measured live, 2026-10-17, RTX 3050 6 GB):** the two models do NOT stay resident together. `ollama ps` after a default turn showed `llama3.2:3b` only (2.6 GB, 100% GPU); after a thinking turn `qwen3:4b` only (3.2 GB, 100% GPU), so a thinking turn **evicts the default model**; after the next default turn `llama3.2:3b` only again. Whichever model was resident was 100% GPU. That next default turn took **15.0 s** wall (a warm one is 2 to 6 s) and did **not** fall back (under the 18 s timeout), but the reload alone is about **10.7 s** (Ollama `load_duration` 10.65 s, reproduced directly; `qwen3:4b`'s first load was 10.8 s, not the ~5 s assumed), so the margin under 18 s is only a few seconds and a longer reply right after a thinking turn can serve the template. **The demo must re-warm (about 11 s) after using the toggle.** No Ollama environment variable was changed.
**Demo rule (B11, lead ruling): the brain toggle is demonstrated LAST.** After it either the demo ends, or the
presenter re-warms before the next normal turn; it is never pressed mid-episode with the default path
continuing. In B11, a turn after a toggle use includes a model load, so it is discardable under the existing
rule, and the discard is noted.

**Memory (M1): what the generator sees, and what the classifier never does.** The generator's prompt now
carries the earlier turns of the **current episode** as a bounded `<conversation>` block: the last **6**
turns, each cut to its first **600** characters (at a word boundary, marked with an ellipsis), and every
turn is neutralised so a student typing a closing tag cannot end the block early. After SF1 the frontend sends
`history: []` when a new episode starts, so memory reaches back to the start of the current episode and no
further (memory across episodes would need a contract change; it is PP2). With no history the prompt is
byte-identical to the r3 prompt. **The classifier still sees the current message only** (C2/C5): history
never reaches `classify`, which `tests/test_purity.py` (its shape) and the request-level C2/C5 tests (its
behaviour) guard. The cost was measured on the GPU and is reported, with the one thing that got worse, in
`benchmarks/llm/README.md` (section "Memory (M1)").

**Cycle-2 prompts (S8b).** From cycle 2, a delivery's prompt carries only the earlier
explanation(s) of the *same strategy*, not every earlier explanation of the episode
(`app/generation/prompts.py::same_strategy_priors`); see `benchmarks/llm/README.md` for the
re-measured timeout this made possible. With Ollama down, each explain turn costs about 2 s on
Windows (the refused-connection wait) before falling back to the template, which is slower than
setting `LLM_PROVIDER=template` directly — that setting is the rehearsal escape hatch. See
"What this means for C3" in `benchmarks/llm/README.md` for what the cycle-2 numbers do and do not
support.

**R6, the question guard (a question never resolves an episode).** The engine resolves an episode on
the first `understood` label after a delivery, and the prototype proxy classifier (trained on synthetic
answers) labels some questions `understood` ("where does the actual value come from?" scores
P(confused) 0.115). So when the current message is a **question** (it ends with `?` or `？` once
trailing `! . ) ] } " ' ” ’ » …` and spaces are ignored) and carries no strategy request, the engine
**declines to resolve and escalates** to the next strategy (or offers a new cycle when the cycle is
exhausted). It fires whether the `understood` label came from the model or from the rule layer
(`that makes sense, but why does it work?`). Two additive fields record both facts, and neither
changes the classifier's label: `meta.resolution_declined` (`"question_guard"` or `null`, every turn) and
`episode_log.deliveries[].reaction_override` (`"question_guard"` on the delivery whose reaction was
declined, `null` otherwise; the current message never carries it). The R4 turn log gains
`"question_guard": true|false`, and the guard logs one INFO line (`R6 question guard: resolution declined
(episode <id>)`, never any student text). `schema_version` stays `"1.0"`: the frontend's Zod schema
ignores unknown keys but rejects another literal. **Accepted direction of error:** a trailing `?` will
sometimes escalate someone who meant to stop ("got it, thanks?", "can we move on?"); a false confused
costs one explanation, a false understood abandons a lost student, and since SF1 an escalation never
blocks the conversation. R6 does **not** unlock R1 (short-message uncertainty) or R3 (negation guard),
which stay held: one finding justifies one rule.

**R7, a model-only `understood` never resolves (only a rule-matched one does).** The model half of the
prototype proxy classifier hands out `understood` inconsistently ("ask me questions related to the topic"
0.051, "quiz me on inheritance" 0.305, but "test me" 0.609 confused) while being close to inverted on
real understanding ("that makes sense" 0.992 confused, "got it" 0.946 confused). So the engine resolves
**only when the RULE layer matched an understanding phrase** (`label == "understood"` and
`source == "rule"`); a model-sourced `understood` escalates to the next strategy (or offers a new cycle)
instead. **To resolve, a student uses a listed understanding phrase**: they live in
`models/clf-v1.0.0/rules.yaml` under `understanding_phrases`. **Precedence: R6 first, then R7**, so a
model-sourced `understood` that is also a question stays `question_guard`, and R7 covers the model-sourced
non-questions; a message that carries a strategy request follows the request branch, and a reply to a
cycle offer is read by cycle intent (neither guard is consulted). Audit, reusing R6's fields: the value
`"model_understood_not_trusted"` joins `"question_guard"` in `meta.resolution_declined` and in
`episode_log.deliveries[].reaction_override` (never on the current message), the classifier's label is
never altered, and the R4 turn log gains `"model_understood_guard"` next to `"question_guard"` (each is
true only for its own guard). One INFO line fires with no student text. **Measured side effect** (30
natural "I understand" phrasings): 26 were already labelled `confused` by the model and never resolved;
R7 newly blocks only "that helped a lot" (0.197, model), and the rule phrases tested ("got it, thanks",
"that makes sense", "i get it now") still resolve. A student who expresses understanding in unlisted
words gets one more explanation, and since SF1 that never blocks them. **There is no phrase list** (by
ruling), and R7 does not unlock R1 or R3.
**Metrics hazard: episodes are not conversations.** Since SF1 a conversation can contain several
episodes (the next message after a resolution starts a new one). `is_weak`, `outcome` and
`counted_strategies` in the episode log are **per episode**, so the episode count is not the
conversation count; analyses must not double-count a student or a conversation.
**Per-turn research log (off by default).** When `TURN_LOG_PATH` is set, one JSON line per turn is
appended (message, the preceding tutor turn, label/probability/source, whether the model and the
rules disagreed, and the decision). It records **real student messages, so it needs ethics approval
before it is switched on.** A failed write is logged at ERROR and never fails the turn.

**Smoke test** (a full episode against a running server; exits non-zero on any contract violation):

```powershell
.\.venv\Scripts\python -m app                              # one shell
.\.venv\Scripts\python scripts\smoke_episode.py            # another shell
```

It prints `meta.llm`, `meta.fallback` and the latencies per turn, and how many explain turns were
generated and how many fell back. `--expect-fallback true` requires every explain turn to fall back
(for a run with Ollama unreachable).
## Endpoints

| Method and path | Purpose |
|---|---|
| `GET /health` | Model verification status and Ollama reachability (see Behaviour). |
| `GET /topics` | The topic list the frontend shows. |
| `GET /model-info` | The classifier's `model_info` block from `metadata.json`, **served unchanged**: `version`, `trained_at`, `dataset`, `threshold`, `metrics`. It is parsed and validated once at startup (a malformed block starts the service degraded) and never re-read from disk. `503` when the model is not loaded. The metrics are those of a prototype proxy trained on synthetic answers. |
| `POST /tutor/message` | One tutoring turn (above). |

## Browser check (CORS)

The tests and curl cannot prove CORS; only a browser can. This is the procedure:

1. Make sure nothing else holds port 5173 (a second Vite silently moves to 5174, and that origin is
   not allowed; see below), and start the service: `.\.venv\Scripts\python -m app`.
2. In `dev/frontend`, in PowerShell (the variable is set for this shell only; no file is written):
   `$env:VITE_TUTOR_MODE='direct'; npm run dev`
3. Open `http://localhost:5173` with DevTools open (Network and Console tabs). Confirm:
   - `/topics` and `/health` show status **200** in the Network tab on page load;
   - one typed turn shows an `OPTIONS` preflight followed by a `POST` to `/tutor/message` with
     status **200**;
   - the Console has **no CORS error**;
   - `/model-info`: the UI does not call it in this build, so check it from the page. In the
     Console run `await fetch('http://localhost:8001/model-info').then(r => r.status)` and expect
     `200`.
4. **Optional**: repeat from the `http://127.0.0.1:5173` origin. Stop the first Vite, then run (same
   `VITE_TUTOR_MODE` shell variable): `npm run dev -- --host 127.0.0.1`. This leg is
   **environment-dependent**: whether plain `npm run dev` serves `127.0.0.1` depends on how Node
   resolves `localhost` (here it listens on `[::1]:5173` only, so `127.0.0.1` is refused); another
   machine may serve both without the flag. The `localhost` leg is the check that matters.

**If Vite moved to 5174** (its console says `Port 5173 is in use, trying another one`), every
request fails with a CORS error. The fix is to **free 5173**, not to widen `CORS_ORIGINS`.

An **unhandled 500** response carries no CORS header, because Starlette's `ServerErrorMiddleware`
sits outside CORS, so a browser would show a network error rather than a 500. No current route
raises one. **If a future route can raise an unhandled 500, this stops being theoretical and needs a
custom 500 handler inside the CORS layer.** The 422 and 503 responses the frontend maps do carry the
header (tested).

## Behaviour

Expected: `{"status":"ok","model_loaded":true,"llm_reachable":true,"model_version":"clf-v1.0.0","llm_gpu_fraction":1.0}`.
`llm_gpu_fraction` is a backend-only diagnostic (the frontend's Zod schema strips it): Ollama's
`size_vram / size` for the model from `GET /api/ps`, `1.0` = fully on the GPU, `0.0` = fully on the CPU,
`null` = unknown (probe failed, model not resident, or not the `ollama` provider). **A value below
1.0 means slower replies** (about 13 tok/s on the CPU against about 41 on the GPU on the lab machine);
the warm-up also logs the placement at startup, at WARNING when it is below 1.0.
`llm_reachable` is a real check on every call (`GET {OLLAMA_URL}/api/tags`, 1 s timeout): true only
if Ollama answers **and** `LLM_MODEL` is pulled; always false under the `template` or `mock`
provider. It does not change `status`: without the LLM the service still answers, with templates
(the frontend shows its "running with template responses" banner from this flag).

Startup logs one `hash OK` line per verified file, the class order, both class-order
assertion scores and the load time. If **any** verification fails, the failure is logged at
ERROR level (the check, the file, expected vs actual), the model is **not** stored or used, and the
service still starts in a degraded state. `GET /health` then returns exactly
`{"status":"degraded","model_loaded":false,"llm_reachable":false,"model_version":null}`.
Any other startup exception still stops the process.

Settings (env vars): `HOST`, `PORT`, `MODEL_VERSION` (default `clf-v1.0.0`), `MODELS_DIR` (default: the
`models/` directory next to `app/`, independent of the working directory).

## Test

```powershell
python -m pytest
```

No network or Ollama needed, and **none is ever contacted, even when Ollama is running**:
`tests/conftest.py` forces `LLM_PROVIDER=template` and `OLLAMA_URL=http://127.0.0.1:9` for every
test, and the ollama tests talk to `httpx.MockTransport`. The Docker `test` service also has no
network. The tests include negative controls, each of which must
produce the degraded `/health` and an ERROR log: a corrupted `pipeline.joblib`, a modified or
CRLF `rules.yaml`, a wrong scikit-learn version, and
deliberately inverted/constant predictors that the class-order assertion must reject.

## Startup checks, in order

1. read `metadata.json`;
2. `sklearn.__version__` must equal `metadata.runtime.scikit_learn`;
3. SHA-256 of `pipeline.joblib` and `rules.yaml` must match `metadata.files`
   (checked **before** anything is unpickled). Hashes are over the **raw bytes**, so
   `sha256sum` gives the published value; a CRLF rewrite of `rules.yaml` fails the check.
   `.gitattributes` (`models/** -text`) stops Git rewriting line endings;
4. `joblib.load` the pipeline (an unpickle failure is also a verification failure);
5. `metadata.input.proba_index_confused` must be `1`; that index selects P(confused);
6. class-order assertion on raw text: a hand-written correct Java sentence must score
   P(confused) < 0.5 and `"i dont get it"` must score > 0.5. This catches a swapped
   index, a corrupt file or the wrong model directory.

## Model artifact in Git

`models/clf-v1.0.0/` is committed (a fresh clone must start). The root `.gitignore`
ignores `backend/models/` and `*.joblib`, so `backend/.gitignore` re-includes them. `.gitattributes` marks `models/**` as `-text` so the bytes stay as hashed.
