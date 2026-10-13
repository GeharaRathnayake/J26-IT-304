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

## Setup

Requires Python 3.13 and scikit-learn **exactly 1.9.1** (the version the artifact was
pickled with). Run from `dev/backend/`:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt     # runtime pins + pytest + httpx
python -c "import sklearn; print(sklearn.__version__)"   # must print 1.9.1
```

## Run

```powershell
python -m uvicorn app.main:app --port 8000
curl.exe http://127.0.0.1:8000/health
```

Expected: `{"status":"ok","model_loaded":true,"llm_reachable":false,"model_version":"clf-v1.0.0"}`.
`llm_reachable` is hard-coded `false` until the Ollama stage.

Startup logs one `hash OK` line per verified file, the class order, both class-order
assertion scores and the load time. If **any** verification fails, the failure is logged at
ERROR level (the check, the file, expected vs actual), the model is **not** stored or used, and the
service still starts in a degraded state. `GET /health` then returns exactly
`{"status":"degraded","model_loaded":false,"llm_reachable":false,"model_version":null}`.
Any other startup exception still stops the process.

Settings (env vars): `MODEL_VERSION` (default `clf-v1.0.0`), `MODELS_DIR` (default: the
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
