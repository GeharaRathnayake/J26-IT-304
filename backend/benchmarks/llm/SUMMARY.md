# LLM benchmark summary

| model (run date) | cold start | wall median | wall p95 | over 12 s | wall spread | TTFT median | tok/s median | truncated | empty | Check ok raw / final | 2-4 sentences raw / final | java fenced (example) | no unfenced code (others) | `<think>` raw / final | untagged leak raw / final | human rating (mean) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama3.2:3b (2026-10-15) | 12.4 s | 6.9 s | 8.8 s | 0% | 1.6 s | 0.16 s | 12.1 | 100% | 0% | 0% / 100% | 79% / 79% | 33% | 100% | 0% / 0% | 0% / 0% | |
| qwen3:4b (2026-10-15) | 14.4 s | 9.3 s | 11.9 s | 4% | 1.2 s | 0.19 s | 9.3 | 100% | 0% | 0% / 100% | 56% / 56% | 0% | 100% | 0% / 0% | 100% / 100% | |

How to read this table:

- Every number is over the successful generations of that run (16 prompts x runs). Timings are wall clock on the benchmark machine, with whatever else it was running.
- **over 12 s** is the share of generations the service would have replaced with a template (its fallback timeout). It is a reference, not a pass mark, and no generation is stopped at 12 s.
- **Untagged preamble disqualifies a model** (lead ruling): a reasoning leak is a reliability criterion, not something to patch at runtime. Read the leak and truncated columns first.
- **The format scores are mechanical.** They say nothing about whether an explanation is correct or good; that is the human rating, filled in from the `*_outputs.md` sheets.
- **Untagged leak is a heuristic** (a line starting with a phrase such as `We are`, `Let me`, `The user`); it has false positives and false negatives.
- `finalise` always appends a Check line when one is missing, so "Check ok final" is near 100% by construction; read it together with `empty` and the raw columns. A reply that was entirely reasoning becomes a bare default question.
- Call parameters are fixed and recorded in each result JSON: `/api/chat`, one user message, `think: false`, `stream: true`, `num_predict: 80`, 60 s client timeout. The service's adapter must use the same.
