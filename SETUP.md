# Developer setup: backend + frontend

How to get the J26-IT-304 Java tutor running on your own machine, from a fresh clone to a
working chat in the browser. Written for Windows (the team's machines); macOS/Linux notes are
given where commands differ.

If you only want to see the UI, you can skip straight to [Quick start: frontend only](#quick-start-frontend-only-no-backend).

---

## 1. What you are setting up

```
Browser ──► Frontend (React + Vite)   http://localhost:5173
               │  POST /tutor/message, GET /topics, GET /health
               ▼
            Backend (FastAPI)         http://127.0.0.1:8001
               │  confusion classifier (in-process, models/clf-v1.0.0)
               │  escalation engine
               ▼
            Ollama (local LLM)        http://127.0.0.1:11434
               model: llama3.2:3b
```

| Part | Folder | What it does |
|---|---|---|
| Frontend | `frontend/` | The chat UI. Can run on its own with a built-in mock backend. |
| Backend | `backend/` | Classifies each student message, picks the next teaching strategy, and asks the LLM for an explanation. Falls back to a bundled template reply if the LLM is slow, missing or produces something unusable. |
| Ollama | (installed separately) | Runs the `llama3.2:3b` model locally. Optional: without it the backend still answers, with templates. |

The ports are **fixed**: the frontend expects the backend on **8001**, and the backend only
accepts browser requests from **5173**. Do not change them.

---

## 2. Prerequisites

| Tool | Version | Check with | Notes |
|---|---|---|---|
| Git | any recent | `git --version` | |
| Python | **3.13** | `py -3.13 --version` | Must be 3.13. The classifier file was saved with scikit-learn **1.9.1** and the backend refuses to load it with any other version. |
| Node.js | **24.x** (tested 24.11.1, npm 11.6) | `node -v` | Node 22 LTS will probably work, but 24 is what is tested. |
| Ollama | 0.40.x (tested 0.40.5) | `ollama --version` | Only needed for real LLM replies. |
| GPU | optional | `nvidia-smi` | Tested on an RTX 3050 6 GB. On CPU only the model is about 3x slower, so more replies hit the 18 s timeout and show a template instead. |

Disk: about 2 GB for `llama3.2:3b`, plus about 300 MB for `node_modules` and the Python venv.

> **Windows tip.** Plain `python` on many machines is a different version (the lab machine's is
> 3.10). This guide always calls the venv's own interpreter (`.\.venv\Scripts\python`), so you never
> need to "activate" the venv and PowerShell's script execution policy does not matter.

---

## 3. Get the code

```powershell
git clone https://github.com/GeharaRathnayake/J26-IT-304.git
cd J26-IT-304
git checkout main
```

Branches:

| Branch | Contents |
|---|---|
| `main` | The integrated, working version. **Start here.** |
| `dev1` | Frontend work in progress. |
| `backend/pp1-service` | Backend work in progress. |
| `notebooks/confusion-classifier` | The notebooks that trained the classifier (`experiment1/`). |

> **Do not edit or re-save anything in `backend/models/`.** The backend checks the SHA-256 hash of
> those files at startup. `.gitattributes` stops Git from changing their line endings, but an editor
> that "fixes" line endings in `rules.yaml` will make the backend start in a degraded state.

---

## 4. Install Ollama and the model

1. Install Ollama from <https://ollama.com/download> and let it start (it runs in the system tray on
   Windows).
2. Download the model (about 2 GB):

   ```powershell
   ollama pull llama3.2:3b
   ```

3. Check it:

   ```powershell
   ollama list                                     # llama3.2:3b must be listed
   curl.exe http://127.0.0.1:11434/api/tags         # returns JSON, not an error
   ```

**Optional, thinking mode:** `ollama pull qwen3:4b` (about 2.6 GB). Only needed if you turn on the
brain toggle (see [section 8](#8-configuration-reference)). It is slow by design (1 to 2+ minutes per
reply) and is off by default.

---

## 5. Backend

All commands run from the `backend/` folder.

### 5.1 Create the virtual environment and install

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
```

macOS/Linux: `python3.13 -m venv .venv`, then use `.venv/bin/python` instead of `.\.venv\Scripts\python`
everywhere below.

`requirements.txt` holds the exact runtime versions; `requirements-dev.txt` adds pytest.

### 5.2 Check the scikit-learn version

```powershell
.\.venv\Scripts\python -c "import sklearn; print(sklearn.__version__)"
```

It **must** print `1.9.1`. Anything else and the classifier will not load.

### 5.3 Run the tests

```powershell
.\.venv\Scripts\python -m pytest
```

All tests should pass. They need neither the network nor Ollama, and never contact Ollama even if
it is running.

### 5.4 Start the backend

```powershell
.\.venv\Scripts\python -m app
```

Leave this window open. You should see one `hash OK` line per model file, the class-order checks,
and `Uvicorn running on http://127.0.0.1:8001`. A background warm-up then loads the LLM; it never
blocks startup.

### 5.5 Check it is healthy

In a second terminal:

```powershell
curl.exe http://127.0.0.1:8001/health
```

Expected (once the warm-up has finished, a few seconds after startup):

```json
{"status":"ok","model_loaded":true,"llm_reachable":true,"model_version":"clf-v1.0.0","llm_gpu_fraction":1.0}
```

| Field | Meaning if it is wrong |
|---|---|
| `status: "degraded"`, `model_loaded: false` | The classifier failed verification. Read the ERROR line in the backend window (usually the scikit-learn version or a changed `rules.yaml`). |
| `llm_reachable: false` | Ollama is not running, or `llama3.2:3b` is not pulled. The tutor still works, with template replies. |
| `llm_gpu_fraction` below `1.0` | Part or all of the model is on the CPU, so replies are slower. `null` means unknown (for example, the model is not loaded yet). |

Other endpoints you can try: `GET /topics`, `GET /model-info`.

### 5.6 Optional: a full scripted conversation

With the backend running, in another terminal:

```powershell
.\.venv\Scripts\python scripts\smoke_episode.py
```

It runs a whole episode, prints the latency and whether each reply came from the LLM or the
template, and exits non-zero if any response breaks the API contract.

---

## 6. Frontend

All commands run from the `frontend/` folder.

### 6.1 Install

```powershell
cd frontend
npm ci
```

`npm ci` installs exactly what `package-lock.json` lists. Use `npm install` only when you mean to
change dependencies.

### 6.2 Point it at the backend

The frontend has three transport modes:

| Mode | Talks to | Use it for |
|---|---|---|
| `mock` (default) | an in-memory fake backend | UI work with no backend at all |
| `direct` | the FastAPI backend on 8001 | **normal development and the demo** |
| `express` | the team's Express server | the future integrated app (not used yet) |

To use the real backend, create `frontend/.env` from the example and set the mode to `direct`:

```powershell
copy .env.example .env
```

Then edit `.env` so it says:

```
VITE_TUTOR_MODE=direct
VITE_TUTOR_URL=http://localhost:8001
VITE_SHOW_THINKING_TOGGLE=false
```

`.env` is git-ignored, so this stays on your machine. (For a one-off run instead of a file, in
PowerShell: `$env:VITE_TUTOR_MODE='direct'; npm run dev`.)

### 6.3 Start it

```powershell
npm run dev
```

Open **<http://localhost:5173>**.

> Vite reads `.env` only at startup. After changing it, stop the dev server (Ctrl+C) and start it
> again.

### 6.4 Other frontend commands

| Command | Does |
|---|---|
| `npm test` | Unit and contract tests (Vitest) |
| `npm run typecheck` | TypeScript check with no build |
| `npm run build` | Typecheck, then a production build into `dist/` |
| `npm run preview` | Serve the production build |

---

## 7. Check the whole thing works

With Ollama, the backend and the frontend all running:

1. Open <http://localhost:5173> with the browser DevTools open (Network and Console tabs).
2. On page load, `/topics` and `/health` return **200**. There is no "running with template
   responses" banner (that banner means `llm_reachable` is false).
3. Click **New chat**, then type `I don't understand how inheritance works` and press Enter.
4. A reply appears within a few seconds. In the Network tab you see an `OPTIONS` request followed by
   a `POST /tutor/message` with status **200**, and the Console has **no CORS errors**.
5. Open the research panel: the latency card shows the timings, and `fallback` is `false` (the
   reply came from the LLM, not the template).
6. Refresh the page. The chat is still there and is listed under **Recent** in the sidebar.

Steps 5 and 6 are what tell you the LLM and the saved-chat feature are both working.

### How a conversation behaves (so you are not surprised)

- **Saying you understand.** The tutor only treats you as having understood when you use one of
  the listed understanding phrases (for example `got it, thanks`, `that makes sense`,
  `i get it now`). They are listed under `understanding_phrases` in
  `backend/models/clf-v1.0.0/rules.yaml`. Anything else, including any question ending in `?`,
  gets another explanation with a different strategy.
- **Asking for a strategy.** `can you give me an analogy?` or `show me an example` switches to that
  strategy directly.
- **Template replies.** If the LLM is slow (more than 18 s), unreachable, or produces something
  unusable (for example, a code block cut off mid-way), you get a pre-written template reply and the
  research panel shows `fallback: true`. This is the intended safety net, not a crash.
- **Saved chats** are stored in this browser's `localStorage` (up to 20). They never leave the
  browser. Clearing site data deletes them.
- **The classifier is a prototype** trained on synthetic data. It is not a validated confusion
  detector, so some of its labels will look wrong. See `backend/README.md`.

---

## 8. Configuration reference

### Backend (environment variables)

The backend reads **environment variables only. It does not read a `.env` file.** Set them in the
same terminal before `python -m app`:

| Shell | Example |
|---|---|
| PowerShell | `$env:LLM_PROVIDER='template'; .\.venv\Scripts\python -m app` |
| cmd | `set LLM_PROVIDER=template` then `.venv\Scripts\python -m app` |
| Git Bash / macOS / Linux | `LLM_PROVIDER=template .venv/Scripts/python -m app` |

The ones you are most likely to need:

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` = real LLM; `template` = always use the template replies (no Ollama needed, instant); `mock` = test adapter. |
| `LLM_MODEL` | `llama3.2:3b` | The Ollama model for normal replies. |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Keep `127.0.0.1`: `localhost` adds an IPv6 lookup delay on Windows. |
| `LLM_MAX_TOKENS` | `220` | Maximum reply length in tokens. |
| `LLM_TIMEOUT_S` | `18.0` | After this, the reply is replaced by the template. |
| `LLM_THINKING_MODEL` | `qwen3:4b` | Only used when the brain toggle is on. |
| `LLM_THINKING_TIMEOUT_S` | `180.0` | Timeout for thinking-mode replies. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Browser origins allowed to call the backend. Exact origins only: no `*`, no trailing slash. |
| `HOST` / `PORT` | `127.0.0.1` / `8001` | Do not change the port; the frontend expects 8001. |
| `TURN_LOG_PATH` | unset | **Leave unset.** It writes every student message to a file and needs ethics approval before it is ever used with real students. |

The full list, with the reasoning behind each value, is in `backend/README.md`.

### Frontend (`frontend/.env`)

| Variable | Default | Meaning |
|---|---|---|
| `VITE_TUTOR_MODE` | `mock` | `mock`, `direct` or `express` (see 6.2). |
| `VITE_TUTOR_URL` | `http://localhost:8001` | Backend URL for `direct` mode. |
| `VITE_EXPRESS_BASE` | `/api` | Base path for `express` mode. |
| `VITE_SHOW_THINKING_TOGGLE` | `false` | Shows the brain (thinking-mode) toggle. Only the exact string `true` turns it on. A thinking reply takes 1 to 2+ minutes and pushes the normal model out of GPU memory, so the next normal reply takes about 15 s. Keep it off unless you are testing it. |

---

## Quick start: frontend only (no backend)

```powershell
cd frontend
npm ci
npm run dev
```

With no `.env` file the mode is `mock`, so the UI runs end to end against an in-memory fake of the
backend. Good for UI and styling work. The replies are canned.

## Quick start: backend without Ollama

```powershell
cd backend
$env:LLM_PROVIDER='template'
.\.venv\Scripts\python -m app
```

Every reply is a template (`fallback: true`), returned instantly. Useful when you are working on
the classifier, the engine or the UI flow and do not need real explanations.

## Optional: backend in Docker

For building and testing only (the demo runs from the venv). From `backend/`:

```powershell
docker compose build
docker compose run --rm test       # runs pytest in the container
docker compose up -d api           # serves on 127.0.0.1:8001
docker compose down
```

The container reaches Ollama on the host automatically. Details are in `backend/README.md`.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Backend fails to start with *"An attempt was made to access a socket in a way forbidden by its access permissions"* | Windows has reserved a port range that includes 8001 (the reserved ranges move after a reboot). | Check with `netsh interface ipv4 show excludedportrange protocol=tcp`. To fix, in an **administrator** terminal: `net stop winnat`, then `netsh int ipv4 add excludedportrange protocol=tcp startport=8001 numberofports=1`, then `net start winnat`. |
| Backend says the address is already in use | Another backend is still running. | Close the other window, or find it with `netstat -ano \| findstr :8001` and end that process. |
| Every request in the browser fails with a **CORS error** | Vite started on **5174** because 5173 was busy (its console says *"Port 5173 is in use, trying another one"*). The backend only accepts 5173. | Stop whatever holds 5173 (usually an old `npm run dev`) and restart the frontend. Do **not** add 5174 to `CORS_ORIGINS`. |
| `/health` shows `"status":"degraded"` | The classifier failed one of its startup checks. | Read the ERROR line in the backend window. Usually the scikit-learn version is not 1.9.1 (recreate the venv with Python 3.13 and reinstall), or `backend/models/` was modified (run `git checkout -- backend/models`). |
| `pip install` fails to find `scikit-learn==1.9.1` | The venv is not Python 3.13. | `.\.venv\Scripts\python --version`. If wrong, delete `.venv` and recreate it with `py -3.13 -m venv .venv`. |
| The UI shows a "running with template responses" banner | `llm_reachable` is false. | Start Ollama, check `ollama list` shows `llama3.2:3b`, then refresh the page. |
| Replies are slow or often show `fallback: true` | The model is running on the CPU, or the GPU is hot and throttling. | Check `llm_gpu_fraction` in `/health` and `ollama ps` (look for `100% GPU`). Plug in the laptop and close other GPU-heavy apps. |
| First reply after starting is slow | The model is still loading. | Wait a few seconds after startup, or send one message to warm it up. |
| The next normal reply after a thinking-mode reply takes about 15 s | The thinking model pushed `llama3.2:3b` out of GPU memory. | Expected. Send one throwaway message to reload the normal model. |
| Frontend still uses mock replies after editing `.env` | Vite reads `.env` only at startup. | Stop `npm run dev` and start it again. |
| The page opens on an old chat | The app reopens the most recent saved chat. | Click **New chat**. |
| `npm ci` fails | The Node version is too old, or `package-lock.json` is out of sync. | Use Node 24. If you changed `package.json`, run `npm install` instead. |

---

## 10. Before you commit

- Run both test suites: `.\.venv\Scripts\python -m pytest` in `backend/`, and `npm test` plus
  `npm run typecheck` in `frontend/`.
- Never commit `.env`, `.venv/`, `node_modules/`, datasets or new model files. `.gitignore`
  already covers them; check `git status` before committing.
- Never change files in `backend/models/`.
- Keep commit messages short (three lines at most).

## 11. Where to read more

| File | About |
|---|---|
| `backend/README.md` | Every backend setting with its reasoning, the endpoints, the startup checks, CORS, Docker. |
| `backend/benchmarks/llm/README.md` | How the LLM settings were measured. |
| `frontend/README.md` | Frontend structure, transport modes, how to embed it in the team app. |
| `frontend/.env.example` | The frontend settings, with comments. |
