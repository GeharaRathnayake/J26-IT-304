# Git Strategy — J26-IT-304 (Adaptive AI Voice Tutor for Java)

**Audience:** Yasindu (supervisor/frontend) and any agent committing into this repo.
**Status:** repo initialised; work in progress on `dev1`.
**Last updated:** 2026-10-13

This file is the authority on how we use Git here. It has two parts: the rules we
follow (§1–§8), and a running log of what has actually been done (§9). Whoever
commits updates §9 in the same commit.

---

## 1. The core fact: Git needs no account

Git is a local program. GitHub is one optional hosting service. A repo with
complete history, branches and tags works entirely offline, forever.

The only thing Git asks for is a name and email on each commit. These are
**plain text labels, not credentials** — nothing verifies them, nothing is
contacted. So we build the whole project locally across all three branches, and
attach a GitHub account whenever we choose. No history is lost or rewritten when
we do.

**One thing that is not reversible, so decide it now:** the author email is baked
into every commit object. If we commit under a placeholder, those commits will
not link to the GitHub profile later (no contribution graph, no avatar) unless
we rewrite history — which changes every commit hash. So we commit under the
**real email from the first commit**, even though no account exists yet.

```
user.name   Yasindu
user.email  mykkularathne@gmail.com
```

Set **per-repo**, not globally, so other projects on this machine are untouched.

---

## 2. Repository root and layout

**Repo root is `dev/`** — this directory. Everything above it (the PDFs,
`files.zip`, `plandocs.zip`, `Plan/`, `frontendPlan/`) stays outside Git. Those
are source material and binary submissions; they bloat a code repo and some are
not ours to redistribute.

The plan documents we actively work against get **copied** into `dev/docs/` and
versioned there, so the repo is self-contained and a reader does not need the
parent folder.

Target layout, matching `Plan/PP1_Research_and_Development_Plan.md` §17:

```text
dev/                              <-- repo root (.git lives here)
├── .gitignore
├── README.md                     <-- project-level, written at first commit
├── git.md                        <-- this file
├── frontend/                     <-- exists, partially built
├── backend/
│   ├── app/{main.py,api/,classifier/,tutoring/,strategies/}
│   ├── models/                   <-- IGNORED (trained artifacts)
│   ├── tests/
│   └── requirements.txt
├── notebooks/
│   ├── 01_baseline_confusion_classifier.ipynb
│   └── 02_error_analysis.ipynb
├── data/                         <-- IGNORED (datasets)
│   ├── raw/
│   └── processed/
├── reports/experiments/          <-- committed: metrics, plots, confusion matrices
└── docs/                         <-- committed: plan docs, contract, decisions
```

> **Alternative considered:** repo root at `research 2027/`, pulling the PDFs and
> plan folders in. Rejected — it mixes submission binaries with source, and the
> `.zip` files would be tracked. If we later want the plans under version
> control, they go in `dev/docs/` as above.

---

## 3. `.gitignore` — written before the first commit, not after

A secret or a 200 MB dataset committed once lives in history permanently and
needs history surgery to remove. This file goes in first.

```gitignore
# ---- Node / frontend ----
node_modules/
dist/
dist-ssr/
*.local
coverage/

# ---- Secrets ----
.env
.env.*
!.env.example

# ---- Python / backend ----
__pycache__/
*.py[cod]
.venv/
venv/
env/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# ---- Datasets and model artifacts (plan §17) ----
data/raw/
data/processed/
backend/models/
*.pt
*.bin
*.safetensors
*.joblib
*.pkl
*.h5
*.csv
*.parquet
!reports/**/*.csv

# ---- Notebooks ----
.ipynb_checkpoints/

# ---- Editors / OS ----
.vscode/*
!.vscode/extensions.json
.idea/
.DS_Store
Thumbs.db
*.log

# ---- Tooling leftovers ----
.playwright-mcp/
```

`frontend/.gitignore` already covers the Node side and can stay as a nested file;
the root one is the backstop.

**Datasets are ignored, so reproducibility needs a different mechanism:**
`data/README.md` (committed) records for each dataset its exact name, source URL,
version/revision, licence, and the command to fetch it. The data itself never
enters Git.

**Notebook outputs: keep them.** Outputs are the examiner-facing evidence — the
accuracy numbers, the confusion matrix, the plots. Stripping them makes the repo
useless as proof. The cost is noisy diffs and larger blobs. Mitigation: before
committing a notebook, **Restart & Run All** so outputs are coherent with the
code, and keep plot images small. If diffs become unmanageable we add
`nbstripout` and move the evidence into `reports/experiments/` — but not before
that is actually a problem.

---

## 4. Branches

Three workstreams, three branches, each with its own agent. `main` is the
integration branch and must always be in a demoable state.

| Branch | Owner | Scope |
|---|---|---|
| `main` | Yasindu (supervisor) | Integration only. Nothing is written here directly after the first commit. |
| `frontend/refinement` | Sonnet agent A | Refine and finalise the existing `frontend/` — search bar animation, polish, F10 live verification, accessibility, demo path |
| `backend/pp1-service` | Sonnet agent B | FastAPI service: `POST /tutor/message`, classifier integration, strategy selection, LLM call, tests |
| `notebooks/confusion-classifier` | Sonnet agent C | `01_baseline_confusion_classifier.ipynb`, `02_error_analysis.ipynb`, metrics into `reports/experiments/` |

> **Deviation, 2026-10-13.** The first working branch was created as **`dev1`**,
> not `frontend/refinement`. The table above is the intended scheme and still
> applies to the backend and notebook streams; `dev1` is the frontend stream
> under a different name. Either rename it (`git branch -m dev1
> frontend/refinement`) or rewrite this table — but do not leave the document
> and the repo disagreeing, because the ownership rule in point 1 below is
> enforced by nothing except this table.

**Rules:**

1. An agent commits **only inside its own top-level directory**. The backend
   agent does not touch `frontend/`. This is what keeps three parallel branches
   from colliding.
2. The one genuinely shared surface is the API contract —
   `frontend/src/features/tutor/api/types.ts` and `api/fixtures/*.json`. It is
   **frozen**. If the backend needs it changed, the agent stops and raises it
   rather than editing it; the change is made on `main` and merged outward.
   The existing `frontend/README.md` already states why: `updated_state` must
   round-trip byte-for-byte, `episode_log` stays `null` until episode end, and
   `meta.latency_ms` stays the tutor service's own figure.
3. Merges go **branch → `main`**, never branch → branch.
4. Merge with `--no-ff` so each workstream's integration is one identifiable
   commit in the history of `main`. That history is a deliverable — it is the
   evidence of incremental development for the viva.
5. No rebasing or force-pushing a branch that has been merged.

```text
main  ──●────────────────────●──────────●────────●──
         \                  /          /        /
          ● frontend/refinement       /        /
           \                         /        /
            ●── backend/pp1-service ─        /
             \                              /
              ●── notebooks/confusion-classifier
```

---

## 5. Commit convention

Conventional Commits with a scope that names the workstream:

```
<type>(<scope>): <imperative summary, 72 chars or fewer>

Optional body: why, not what. The diff shows what.
```

`type` is one of `feat` `fix` `refactor` `test` `docs` `chore` `perf` `style`
`scope` is one of `frontend` `backend` `notebooks` `docs` `repo`

```
feat(backend): add POST /tutor/message with classifier passthrough
fix(frontend): keep search bar focus ring visible in dark mode
docs(notebooks): record baseline accuracy and confusion matrix
```

Commits are small and single-purpose. "End of day dump" commits destroy the
incremental-development evidence that the mark sheet rewards.

**No AI attribution footer on these commits** unless asked — this is academic
work and authorship should read as ours.

---

## 6. Phase 1 — initialise locally, no account (do this now)

```bash
cd "C:/Users/Yasindu/Desktop/Stuff/research 2027/dev"

git init -b main
git config user.name  "Yasindu"
git config user.email "mykkularathne@gmail.com"

# write .gitignore from §3 FIRST, then:
git status            # <-- READ THIS. Confirm no node_modules, no .env, no data.
git add .
git commit -m "chore(repo): initialise repo with frontend scaffold and gitignore"

git branch frontend/refinement
git branch backend/pp1-service
git branch notebooks/confusion-classifier
```

The `git status` check before the first `git add .` is not optional. `frontend/`
contains `node_modules/` and `dist/`; if the ignore rules are wrong we find out
now rather than after a 50,000-file commit.

Each agent then works on its own branch:

```bash
git switch frontend/refinement     # or its own branch
```

---

## 7. Phase 2 — attach GitHub later (when the account is given)

Nothing below rewrites history. All existing commits, timestamps and messages go
up as they are.

```bash
# 1. Create an EMPTY repo on github.com — no README, no .gitignore, no licence.
#    An initialised remote causes an unrelated-histories conflict on first push.

cd "C:/Users/Yasindu/Desktop/Stuff/research 2027/dev"
git remote add origin https://github.com/<account>/<repo>.git

# 2. Push main plus every branch, and set tracking.
git push -u origin main
git push -u origin frontend/refinement backend/pp1-service notebooks/confusion-classifier

# 3. Verify
git remote -v
git log --oneline --graph --all | head -30
```

**Pre-push checklist:**

- [ ] Account confirmed with me, and the email in §1 matches one of its verified
      addresses — otherwise commits show as unattributed.
- [ ] Repo visibility decided — **private** unless we deliberately want it public.
      A public repo of an in-progress research project is a plagiarism surface.
- [ ] `git ls-files | grep -iE "\.env|\.csv|\.pt|\.pkl"` returns nothing.
- [ ] Repo size sane: `git count-objects -vH`. If it is over ~100 MB, stop and
      investigate before pushing.
- [ ] GitHub hard-blocks any single file over 100 MB. Check before pushing, not
      during.

If the account is a university or organisation account with SSO, use the SSH
remote or a personal access token — Git's password prompt will not accept a
GitHub password.

---

## 8. If something goes wrong

| Problem | Fix |
|---|---|
| Committed `node_modules` or a dataset | Not yet pushed: `git reset --soft HEAD~1`, fix `.gitignore`, recommit. Already pushed: needs `git filter-repo`; ask first. |
| Committed a secret | Rotate the secret immediately — it is compromised regardless of what we do to history. Then clean history. |
| Two agents edited the same file | Resolve on `main` during the merge. Then fix the ownership rule in §4 that allowed it. |
| Wrong author on commits | Fixable only by rewriting history. Avoided by §1. |

---

## 9. Log — what has actually been done

Append here, newest last. One row per real Git action.

| Date | Branch | Action | Notes |
|---|---|---|---|
| 2026-10-12 | — | Strategy written (`dev/git.md`) | Repo not yet initialised at the time of this entry. |
| 2026-10-13 | `main` | `git init -b main`, root `.gitignore`, first commit `dc2c9f8` | Identity set per-repo as `YasinduKaveesha <yasinduksl2002@gmail.com>` — the existing global identity, **not** the address named in §1. §1 is wrong; this is the address that will be used. 41 files; `node_modules/` and `dist/` correctly excluded. |
| 2026-10-13 | `dev1` | `git switch -c dev1` | Chosen instead of the §4 scheme below. See the note under §4. |
| 2026-10-13 | `dev1` | 18 commits: frontend review fixes (`075fc27`…`ba674ea`) | Findings F1–F9 / G1–G3 of `frontend-review-2026-10-13.md`. Tests 19 → 37, typecheck and build clean. F7 (screen-reader announcement) implemented but **unverified** — no NVDA/Narrator available. |
| 2026-10-13 | `dev1` | 5 commits: send-path hardening (`ec074b8`…`4a5681f`) | Fixes the latch wedge found in review: topics seeded so `resolveTurnTopic` is synchronous, `AbortSignal.timeout` budgets (30 s turn / 5 s metadata), generation guard for superseded responses. Tests 37 → 49. Negative control: reverting the abort signal hangs 6 of 7 new tests at the vitest timeout. |
| 2026-10-13 | `main` | `git merge --no-ff dev1` → `ac21954` | 24 commits integrated. `dev1` **kept, not deleted**, by request. |
| 2026-10-13 | `main` | Docs reorganised into `dev/Summary/{GitSummary,frontendSummary,Experiment1Summary,backendSumary}/` | `git.md` now lives at `Summary/GitSummary/git.md`. Any document referring to `dev/git.md` is stale. |
| 2026-10-13 | `notebooks/confusion-classifier` | `git switch -c notebooks/confusion-classifier`, 12 commits (`2187018`…`80e4ce9`) | Experiment 1. Nine notebooks, one per pipeline stage; `confusion_baseline/` package; `clf-v1.0.0` artifact; handover in `Summary/Experiment1Summary/`. Branch touched only `experiment1/` and `Summary/Experiment1Summary/` — §4 rule 1 held. |
| 2026-10-13 | `main` | `git merge --no-ff notebooks/confusion-classifier` → `6ed535a` | Experiment 1 integrated. Independently verified by the lead: artifact loads and predicts, `train_baseline.py` passes 5/5 checks including `predict_proba` matching the published pipeline to 1e-12. Result: macro F1 0.663, F1(confused) 0.758 — **target F1 ≥ 80% not met, not tuned toward**. |
| 2026-10-14 | `backend/pp1-service` | `git switch -c backend/pp1-service` | Backend stream (FastAPI tutor service), per the §4 scheme. All backend commits below were verified independently by the backend lead before commit (re-run tests, mutation checks on a scratch copy). |
| 2026-10-14 | `backend/pp1-service` | S1 `0a37b32`: scaffold, verified `clf-v1.0.0` load, `/health` | Raw-byte SHA-256 check against `metadata.json`; "parse what you hashed"; degraded start instead of a hard fail. |
| 2026-10-14 | `backend/pp1-service` | S1b `3839fce`: Docker build, test and serve | `python:3.13.16-slim` pinned by digest; Docker is the dev/test convenience, the venv is the demo path. |
| 2026-10-14 | `backend/pp1-service` | S1c `220c0de`: serve on `127.0.0.1:8001` via `python -m app` | Port 8001 fixed by the frontend default. |
| 2026-10-14 | `backend/pp1-service` | S2 `33fcf0b`: rules-first hybrid classifier | 51 confusion / 19 understanding phrases checked first; model P(confused) always returned; classify sees only the current message (C2, C5). |
| 2026-10-14 | `backend/pp1-service` | S3 `d23e7ab`: `/topics`, `/tutor/message` validation | Strict Pydantic v2; frontend contract fixtures copied byte-exact with drift guards. |
| 2026-10-14 | `backend/pp1-service` | S4 `0566f9e`: escalation engine and request detector | theory → example → simplified → analogy; requested strategies do not use a slot (C6). |
| 2026-10-14 | `backend/pp1-service` | S5a `5a10e25`: hedges are unclear at a cycle offer | Cycle intent is accept / decline / unclear. |
| 2026-10-14 | `backend/pp1-service` | S5b `9880682`: episode log by re-classifying reactions | Never copies the current label onto every delivery. |
| 2026-10-14 | `backend/pp1-service` | S6a `220eb70`: generation layer, templates and prompts | `fallbacks.yaml` 60 entries incl. `general`; Java blocks compiled with JDK 21. |
| 2026-10-14 | `backend/pp1-service` | S6b `7554414`: `POST /tutor/message` end to end on templates | `episode_log` non-null iff terminal; 422 mappings; C2/C5 request-level tests; R4 logging opt-in, off by default. |
| 2026-10-15 | `backend/pp1-service` | S7 `37c4da9`: reproducible LLM benchmark + qwen3:4b results | qwen3:4b disqualified (100% untagged reasoning leak). |
| 2026-10-15 | `backend/pp1-service` | S7 results `9df1c40`: llama3.2:3b benchmark | Input to D2. |
| 2026-10-15 | `backend/pp1-service` | S7b `38c648a`: prompt r2, post-processing, D2 re-run | llama3.2:3b usable 88% @110 against a 90% bar: did NOT pass D2; ships with a template fallback (owner decision). |
| 2026-10-15 | `backend/pp1-service` | S8 `58c815e`: Ollama adapter, LLM default with template fallback | `would_ship` gate shared with the benchmark; tests never reach a real Ollama. |
| 2026-10-15 | `backend/pp1-service` | S8b `2e27371`: cycle-2 same-strategy priors; `LLM_TIMEOUT_S` 18 s | Timeout pre-registered as ceil(p95 × 1.2) from the cycle-2 re-measure. |
| 2026-10-15 | `backend/pp1-service` | BS `21dd41c`: blind rating sheet (D2 criterion 5) | Seeded 24-item sheet, key, scorer. Rating is by a human, never an agent; pending. |
| 2026-10-16 | `backend/pp1-service` | S9 `fe5fa20`: CORS, `GET /model-info`, compose `name: j26-tutor` | Real-browser CORS check passed (Chromium, not curl). Docker NOT run at commit time (daemon down); closed 2026-10-16 below. |
| 2026-10-16 | `backend/pp1-service` | Docker gap CLOSED for S8, S8b, BS, S9 (HEAD `fe5fa20` via `git archive`) | Verification, not a commit: build exit 0 (`j26-tutor` builds); 909 passed + 4 drift skips. |
| 2026-10-16 | `backend/pp1-service` | S10 `f89f0fa`: Zod contract check on real responses, C2/C5 AST purity guard | Docker allowed skips become SIX (4 drift guards + 2 Zod tests); shared `gpu_fraction`. |
| 2026-10-16 | `backend/pp1-service` | S10g `904701f`: cycle-2 template variants for `general` | C3 on the template path: `inheritance` and `general` only (lead ruling). |
| 2026-10-16 | `backend/pp1-service` | S10b + S10r `3c10a70` (combined: both edit `README.md`) | `/health` `llm_gpu_fraction` + warm-up placement log; C3 wording to the approved scope; unhandled-500 CORS note. |
| 2026-10-16 | `backend/pp1-service` | S10c `eb91c42`: GPU re-run of the llama3.2:3b benchmark with placement | `gpu_fraction` 1.0; p95 2.42 s (cycle 1), 2.79 s (cycle 2). Every earlier timing was CPU (dGPU was off). D2 not re-scored. |
| 2026-10-16 | `backend/pp1-service` | SF1 backend `e6d951c`: pin continuing after a resolved episode | Owner requirement: the conversation never ends on `resolved`; a post-resolution state would reopen the episode, so the frontend starts a new one. |
| 2026-10-16 | `dev1` | SF1 frontend `97c860c`: keep the conversation open after an episode ends | Owner-approved exception (six files, `api/` contract untouched); committed on the frontend stream per §4 rule 1. |
| 2026-10-16 | `backend/pp1-service` | R6 `ab92801`: question guard, a question never resolves an episode | Lead ruling `04` §3.5; audited via `reaction_override`, `meta.resolution_declined`, turn log. Does not unlock R1/R3. venv 1025; Docker 1019 + 6. |
| 2026-10-16 | `main` | `git merge --no-ff backend/pp1-service` → `0a1a892` | 23 backend commits integrated (S1 → R6). `backend/pp1-service` kept. |
| 2026-10-16 | `main` | `git merge --no-ff dev1` → `a52578c` | SF1 frontend (one commit) integrated. Verified on `main`: backend 1025 passed, frontend 55 passed, typecheck clean, model hashes intact, `experiment1/` and `Summary/` untouched. |

### Pre-Git state of the work, for the record

So the contents of the first commit are explainable:

- **`frontend/`** — React 19 + Vite 6 + TypeScript + Tailwind v4. Its own
  `README.md` reports steps F1–F12 complete: shell, contract types with 15
  passing Zod tests, mock transport, reducer and `useEpisode`, conversation and
  action rendering, strategy chips, research panel, degradation handling, direct
  and Express adapters, Markdown/Java rendering, accessibility and dark mode.
  Runs end to end in `mock` mode with no backend. **Outstanding:** search bar
  animation refinement (`dev/searchbar-animation-refinement-guide.md`), general
  polish and finalisation, and F10 live-service verification, which is blocked
  on the backend existing.
- **`backend/`** — does not exist yet.
- **`notebooks/`** — do not exist yet.

All of the above was produced before version control, so the first commit is
necessarily a large one. That is expected, and worth stating plainly in the
commit message rather than faking granularity by splitting it artificially.
