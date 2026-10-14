# LLM benchmark summary

| model @num_predict prompt-revision (run date) | cold start | wall median | wall p95 | over 12 s | wall spread | TTFT median | tok/s median | truncated | empty | **usable (would ship)** | example complete java | headings (raw) | Check ok raw / final | 2-4 sentences raw / final | java fenced (example) | no unfenced code (others) | `<think>` raw / final | untagged leak raw / final | human rating (mean) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama3.2:3b @80 r1 (2026-10-15) | 12.4 s | 6.9 s | 8.8 s | 0% | 1.6 s | 0.16 s | 12.1 | 100% | 0% | **77%** | 33% | 96% | 0% / 100% | 79% / 79% | 33% | 100% | 0% / 0% | 0% / 0% | |
| llama3.2:3b @80 r2 (2026-10-15) | 12.9 s | 7.0 s | 8.6 s | 0% | 1.8 s | 0.15 s | 12.2 | 88% | 0% | **81%** | 67% | 0% | 4% / 100% | 77% / 77% | 67% | 94% | 0% / 0% | 0% / 0% | |
| llama3.2:3b @110 r2 (2026-10-15) | 15.0 s | 8.8 s | 11.0 s | 0% | 1.9 s | 0.15 s | 12.8 | 69% | 0% | **88%** | 75% | 0% | 27% / 100% | 73% / 75% | 75% | 100% | 0% / 0% | 0% / 0% | |
| qwen3:4b @80 r1 (2026-10-15) | 14.4 s | 9.3 s | 11.9 s | 4% | 1.2 s | 0.19 s | 9.3 | 100% | 0% | **0%** | 0% | 0% | 0% / 100% | 56% / 56% | 0% | 100% | 0% / 0% | 100% / 100% | |
| qwen3:4b @80 r2 (2026-10-15) | 17.3 s | 9.0 s | 11.0 s | 0% | 2.5 s | 0.17 s | 9.9 | 100% | 0% | **0%** | 0% | 0% | 0% / 100% | 56% / 44% | 0% | 100% | 0% / 0% | 100% / 96% | |
| qwen3:4b @110 r2 (2026-10-15) | 19.1 s | 12.2 s | 15.5 s | 60% | 3.2 s | 0.20 s | 9.3 | 100% | 0% | **0%** | 0% | 0% | 0% / 100% | 29% / 21% | 0% | 100% | 0% / 0% | 100% / 96% | |

How to read this table:

- Every number is over the successful generations of that run (16 prompts x runs). Timings are wall clock on the benchmark machine, with whatever else it was running.
- **over 12 s** is the share of generations the service would have replaced with a template (its fallback timeout). It is a reference, not a pass mark, and no generation is stopped at 12 s.
- **usable (would ship)** is the decisive column: the reply, after the deterministic post-processing (headings stripped; if the model stopped at the token cap, an unclosed code block dropped and the prose trimmed to the last complete sentence), has at least one complete prose sentence, an `example` has a closed java block, and it is not an untagged reasoning leak. A reply that is not usable is replaced by the template (`meta.fallback: true`), never served.
- **r1 / r2** is the prompt revision (r1 = the original prompt, r2 = the S7b revision); **@N** is `num_predict`. For r1 rows the usable / headings / example columns are recomputed from the stored raw text with today's post-processing, so they show what post-processing alone would have achieved.
- **Untagged preamble disqualifies a model** (lead ruling): a reasoning leak is a reliability criterion, not something to patch at runtime. Read the leak and truncated columns first.
- **The format scores are mechanical.** They say nothing about whether an explanation is correct or good; that is the human rating, filled in from the `*_outputs.md` sheets.
- **Untagged leak is a heuristic** (a line starting with a phrase such as `We are`, `Let me`, `The user`); it has false positives and false negatives.
- `finalise` always appends a Check line when one is missing, so "Check ok final" is near 100% by construction; read it together with `empty` and the raw columns. A reply that was entirely reasoning becomes a bare default question.
- Call parameters are fixed and recorded in each result JSON: `/api/chat`, one user message, `think: false`, `stream: true`, `num_predict` as in the row label, 60 s client timeout. The service's adapter must use the same.
