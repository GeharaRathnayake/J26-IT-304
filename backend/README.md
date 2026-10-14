# Tutor service (backend)

FastAPI service for J26-IT-304, *Adaptive AI Voice Tutor for Java Programming*.

**Stage S1 scope:** at startup, load the confusion classifier `clf-v1.0.0`, prove it is
the right file and the right way round, and report that on `GET /health`. No tutoring
endpoint, rules or LLM yet.

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
- If the host port is unavailable, `API_PORT` overrides it for Docker only
  (`$env:API_PORT='8200'; docker compose up -d api`); the frontend still expects 8001.
- `models/` must stay byte-exact (`.gitattributes` keeps Git from rewriting line endings).
## Behaviour

Expected: `{"status":"ok","model_loaded":true,"llm_reachable":false,"model_version":"clf-v1.0.0"}`.
`llm_reachable` is hard-coded `false` until the Ollama stage.

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

No network or Ollama needed. The tests include negative controls, each of which must
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
