# LLM benchmarks (decision D2)

Evidence for "which local model generates the tutor's explanations", chosen by measurement.
Produced by `scripts/benchmark_llm.py` (never edit these files by hand):

- `<model>_<date>_np<N>_<rev>.json`: every generation with measurements, scores, raw and shipped text,
  the fixed call parameters, the Ollama version and the prompt set. `N` is `num_predict`; `rev` is the
  prompt revision.
- `<model>_<date>_np<N>_<rev>_outputs.md`: the rating sheet. Human ratings (1-5) are filled in by hand.
- `SUMMARY.md`: one row per result file, regenerated from all the JSONs.
- Files without `_np<N>_<rev>` in the name are the first run (prompt revision r1, `num_predict` 80).
  They are kept, so the table shows before and after.

## The revision rule (S7b): one revision, one re-run, stop

The first run (r1) showed `qwen3:4b` answering with untagged reasoning (disqualified) and `llama3.2:3b`
ignoring the length and format instructions. The lead ruled: **one prompt revision, applied to every
model, then one re-run, then stop.** The revision (r2) is concrete instead of polite: no headings, a word
ceiling instead of a sentence count, and a required final `**Check:**` line. The re-run measures two token
caps (80 and 110) in the same pass, so it is still one re-run.

**No further prompt or post-processing change is made after seeing the re-run.** If no model is good
enough, PP1 ships the templates (`meta.fallback: true`), which is already the default. Choosing the model is
the lead's decision, from the table.

## Cycle-2 prompts (S8b): same-strategy priors only, re-measured

S8's live smoke run measured a cycle-2 theory reply at 12.9 s against the (then) 14 s timeout:
cycle-2 prompts are longer because the orchestrator used to pass **every** earlier explanation into
the prompt, not just the earlier explanation(s) of the strategy being delivered. The lead's ruling:
fix the prompt's input, not the timeout. `app/orchestrator.py` now passes only the same strategy's
earlier explanation(s) (`app/generation/prompts.py::same_strategy_priors`); `build_prompt` itself is
unchanged (prompt revision r2 is still final).

`--cycle {1,2}` (default 1) and `--priors {same,all}` (default `same`, cycle 2 only) measure this:

```powershell
.venv\Scripts\python scripts\benchmark_llm.py --models llama3.2:3b --runs 3 --num-predict 110 --cycle 2 --priors same
.venv\Scripts\python scripts\benchmark_llm.py --models llama3.2:3b --runs 3 --num-predict 110 --cycle 2 --priors all
```

- **`same`** is what the service now sends: one strategy's cycle-1 template as the prior.
- **`all`** is what S8 sent (kept as the before case): all four cycle-1 templates, in delivery order.
- Both use the deterministic cycle-1 **templates** as the prior text (real tutor texts, identical
  every run, no generation needed) — not generated text, so the comparison isolates the prompt-size
  effect from generation variance.
- Cycle-2 result files and SUMMARY rows are named/labelled `c2same` / `c2all` (e.g.
  `llama3.2_3b_<date>_np110_r2_c2same.json`, row label suffix ` c2same`). **Cycle-1 files and rows are
  never touched by a cycle-2 run** — they are the S8 evidence.
- **The timing caveat.** The benchmark streams (`stream: true`, no `keep_alive`); the service calls
  `stream: false` with `keep_alive: "30m"`. The text produced should match, but the timing basis does
  not: these figures are indicative for the service's generation time, not exact.
- **Placement caveat (lead ruling, 2026-10-16).** The **discrete GPU was disabled** on this machine
  during every committed run, so **every committed timing is a CPU timing** (median 12.8 tok/s, p95
  11.0 s at 110 tokens), and placement was **not recorded** at the time. With the GPU enabled, a live
  probe measured about **41 tok/s, about 2.8 s for 110 tokens** (`ollama ps`: `100% GPU`). The
  **quality** columns (usable, leak, complete Java, Check line) are **unaffected**: placement changes
  speed, not output, so **D2 stands**. From now on every run records `placement` in its result JSON
  (`size` and `size_vram` as Ollama reports them, `gpu_fraction` from
  `app/generation/placement.py::gpu_fraction`, `null` when unknown, never a guess). No run was
  repeated for this note and `SUMMARY.md` was not regenerated.

### What this means for C3

From `llama3.2_3b_2026-10-15_np110_r2_c2same.json` (48 generations, what the service now sends):
**usable (would ship) 85% (41/48)**; **over the 18 s service timeout 0% (0/48)**, wall p95 14.6 s;
**truncated at the 110-token cap 88%** (cycle 1: 69%); **example with complete Java 83%**. For
`c2all` (what S8 sent): 33% over the 18 s timeout, p95 26.3 s.

In plain words: at 18 s, cycle-2 replies are generated rather than timing out, but about 1 in 7 is
still replaced by the template because it fails `would_ship`. On the template path C3 (dynamically
different explanations across cycles) holds only for `inheritance` and `general`, which have a second
variant: the other 13 topics repeat their cycle-1 template in cycle 2 (generalising them is PP2). The
approved scope of C3 is: shown on the LLM path, and on the template path for `inheritance` and
`general`. Each turn's `meta.fallback` records which one — template or model — the student actually got. These numbers say
nothing about whether a generated cycle-2 reply reads as different or non-repetitive from its
cycle-1 counterpart; nothing here measured that.

## How to read `SUMMARY.md`

- **Row label** `model @N rX [c2same|c2all] (date)`: `N` = `num_predict`, `rX` = prompt revision, the
  optional `c2...` suffix marks a cycle-2 row (absent = cycle 1, unchanged from S8).
- **prompt length (median chars)**: median character length of that run's 16 prompts. Compares
  `c2same` against `c2all` directly: the prior block itself shrinks fourfold (one cycle-1 template
  instead of four), but the whole prompt only about **1.9×** (1352 vs 2562 median characters), since
  the fixed instructions, topic and student message are the same size either way.
- **usable (would ship)** is the decisive column. The reply, after the deterministic post-processing
  (`app/generation/postprocess.py`: headings stripped; when the model stopped at the token cap, an unclosed
  code block dropped and the prose trimmed to the last complete sentence), has at least one complete prose
  sentence outside code and the Check line, an `example` has a closed ```` ```java ```` block, and it is not
  an untagged reasoning leak. Anything not usable is replaced by the template, never shown to a student.
- **example complete java**: share of `example` replies whose shipped text has a closed java block.
- **headings (raw)**: share of raw replies that opened with a heading or title line.
- **untagged leak** is a heuristic (a line starting with `We are`, `Let me`, `The user`, ...) with false
  positives and negatives. An untagged preamble disqualifies a model (lead ruling).
- **over 12 s**: a **fixed reference carried from S7**, not the service's timeout (`LLM_TIMEOUT_S`,
  `app/config.py`: 14 s in S8, 18 s since S8b). It is a reference point, not a pass mark, and no
  generation is stopped at 12 s; read `LLM_TIMEOUT_S` in `app/config.py` for what the service actually
  falls back at.
- The format scores are mechanical. Whether an explanation is correct and good is the human rating.
- For r1 rows, usable / headings / example columns are recomputed from the stored raw text with today's
  post-processing, so they show what post-processing alone would have achieved.
- Timings are wall clock on the benchmark machine, with whatever else it was running.

## Blind rating (criterion 5)

Pre-registered D2 criterion 5: "blind quality rating ≥ 3/5, and not below templates", rated by a
human. Built by `scripts/blind_sheet.py build` (`python scripts/blind_sheet.py build --force` to
rebuild; it refuses to overwrite an existing sheet or key without `--force`, so a sheet that already
has ratings in it is never silently wiped):

- **Source**: `llama3.2_3b_2026-10-15_np110_r2.json`, run 1 only, the three topics `inheritance`,
  `loops`, `exception_handling`, all four strategies — 12 generations, paired with the matching 12
  cycle-1 templates, 24 items in total. The reply that fails `would_ship` is included as it is: the
  rating judges what the model actually produced, not what the fallback hides.
- **Seed**: `20261015`, pre-registered in `scripts/blind_sheet.py` (`SEED`). The 24 items are
  shuffled with this seed and labelled `R01`-`R24` so neither the order nor the label gives away
  which side an item came from.
- **Files**: `blind_rating_2026-10-15.md` (the sheet a human rates) and `blind_key_2026-10-15.json`
  (which `R..` id is which side). **Do not open the key before rating** — the sheet says so too.

**To rate it:** open `blind_rating_2026-10-15.md`, read each item, and fill in its
`Rating (1-5): ` line (1 = poor, 5 = excellent) — nothing else on the sheet changes. Do this for all
24 items before opening the key.

**To score it:** `python scripts/blind_sheet.py score benchmarks/llm/blind_rating_2026-10-15.md
benchmarks/llm/blind_key_2026-10-15.json`. It prints `n_llm`, `n_template`, `mean_llm`,
`mean_template`, `llm_ge_3`, `llm_ge_template` and `criterion_5` (`PASS`/`FAIL`), and exits 1 on any
unrated, out-of-range or mis-keyed item rather than scoring a partial sheet.

**This is non-blocking evidence.** The owner has already chosen to ship llama3.2:3b with the
template fallback (decision D2); this sheet does not decide anything on its own, and the lead reads
the result alongside the other four (already-measured) D2 criteria.

**The limits of the blinding.** Length and style differences between a model reply and a template
are deliberately kept (they are part of what is being rated), and that alone can give the side
away — the templates tend to be shorter and more uniform. A rater who has already read the
templates (while writing or reviewing `fallbacks.yaml`) may recognise them outright. The blinding
hides the LABEL, not every statistical tell.
