# J26-IT-304: Adaptive AI Tutor for Java Programming

This repository holds one component of the J26-IT-304 research project (SLIIT): an **adaptive AI
tutor for Java**. A student chats with the tutor about a Java topic. When the student seems
confused, the tutor explains the idea again **using a different teaching strategy** (theory, then
an example, then a simpler version, then an analogy) instead of repeating itself.

**New here? Start with [SETUP.md](SETUP.md)**: it takes you from a fresh clone to a working chat
in the browser.

---

## How it works

```
Student ──► Frontend (React)  ──►  Backend (FastAPI)  ──►  Ollama (llama3.2:3b, local)
                                     │
                                     ├─ 1. classify the message: confused or understood?
                                     ├─ 2. escalation engine: pick the next teaching strategy
                                     └─ 3. generate the explanation with the LLM
                                           (or a bundled template if the LLM is slow or unusable)
```

1. **Classify.** Each student message goes through a rule layer of explicit phrases ("i don't
   get it", "got it") and then a TF-IDF + Logistic Regression classifier.
2. **Escalate.** If the student is still confused, the engine moves to the next strategy
   (theory → example → simplified → analogy), for up to two cycles. A student can also ask for a
   strategy directly ("can you give me an analogy?").
3. **Explain.** A local LLM (`llama3.2:3b` through Ollama) writes the explanation in that
   strategy. Everything runs on the machine; no student text is sent to an online service.
4. **Fall back.** Any reply that is too slow (over 18 s), or not usable (for example, a code
   block cut off mid-way), is replaced by a pre-written template, so the student always gets
   an answer.

## Repository layout

| Folder | What is in it |
|---|---|
| [`frontend/`](frontend/) | The chat UI: React 19, TypeScript, Vite, Tailwind. Runs on its own with a mock backend, or against the real one. |
| [`backend/`](backend/) | The tutor service: FastAPI on Python 3.13, with the classifier, the escalation engine, LLM generation and the template fallback. Includes the LLM benchmarks. |
| [`experiment1/`](experiment1/) | Experiment 1: the notebooks and scripts that trained and evaluated the confusion classifier the backend loads. |
| [`Summary/`](Summary/) | Project notes: the Git workflow, review notes and the experiment summary. |

## Honest limitations

- **The classifier is a prototype, not a validated confusion detector.** It was trained on a
  **synthetic** dataset of answers, where "not fully correct" stands in for "confused". It has
  never seen a real student message. That is why a rule layer of explicit phrases sits in front of
  it, and why the tutor only treats a student as having understood when they use one of those
  phrases. Results and caveats: [`experiment1/README.md`](experiment1/README.md).
- **Latency.** Replies typically take 2 to 6 seconds on the test laptop's GPU (RTX 3050 6 GB),
  above the project's 3-second target. On a CPU they are slower, and more replies fall back to
  templates.
- **Template replies are generic.** They are a safety net; they are not tailored to what the
  student asked.

## Documentation

| Read this | For |
|---|---|
| [SETUP.md](SETUP.md) | Installing and running everything; troubleshooting. |
| [backend/README.md](backend/README.md) | Backend settings, endpoints, startup checks and engine rules. |
| [frontend/README.md](frontend/README.md) | Frontend structure, transport modes, and how to embed it in the team app. |
| [experiment1/README.md](experiment1/README.md) | How the classifier was built and how well it does. |
| [Summary/GitSummary/git.md](Summary/GitSummary/git.md) | Branches, commit rules and the Git log. |
