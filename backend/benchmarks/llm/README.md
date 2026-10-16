# LLM benchmarks (decision D2)

Evidence for "which local model generates the tutor's explanations", chosen by measurement. **The current prompt is r3 (2026-10-17, section below); every r2 figure in this file is r2's and is labelled as such.**
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
  11.0 s at 110 tokens, r2), and placement was **not recorded** at the time. With the GPU enabled, a live
  probe measured about **41 tok/s, about 2.8 s for 110 tokens** (`ollama ps`: `100% GPU`). The
  **form** columns (shippable in form, leak, complete Java, Check line) are **unaffected**: placement changes
  speed, not output, so **D2 stands**. From now on every run records `placement` in its result JSON
  (`size` and `size_vram` as Ollama reports them, `gpu_fraction` from
  `app/generation/placement.py::gpu_fraction`, `null` when unknown, never a guess). No run was
  repeated for this note and `SUMMARY.md` was not regenerated.

### What this means for C3

From `llama3.2_3b_2026-10-15_np110_r2_c2same.json` (48 generations, what the service now sends):
**r2: shippable in form (would ship) 85% (41/48)**; **over the 18 s service timeout 0% (0/48)**, wall p95 14.6 s;
**truncated at the r2 110-token cap 88%** (cycle 1: 69%); **example with complete Java 83%**. For
`c2all` (what S8 sent): 33% over the 18 s timeout, p95 26.3 s.

In plain words: at 18 s, cycle-2 replies are generated rather than timing out, but about 1 in 7 is
still replaced by the template because it fails `would_ship`. On the template path C3 (dynamically
different explanations across cycles) holds only for `inheritance` and `general`, which have a second
variant: the other 13 topics repeat their cycle-1 template in cycle 2 (generalising them is PP2). The
approved scope of C3 is: shown on the LLM path, and on the template path for `inheritance` and
`general`. Each turn's `meta.fallback` records which one — template or model — the student actually got. These numbers say
nothing about whether a generated cycle-2 reply reads as different or non-repetitive from its
cycle-1 counterpart; nothing here measured that.

## GPU re-run (S10c, 2026-10-16)

Two **r2** runs of `llama3.2:3b` at `num_predict` 110 (3 runs x 16 prompts = 48 generations each), with the
discrete GPU on and `placement` recorded. **These are the figures for the shipped configuration.** The
committed 2026-10-15 CPU figures above remain as the record of the dGPU-off state; no existing file was
changed.

| | cycle 1 (`np110_r2`) | cycle 2, same-strategy priors (`np110_r2_c2same`) |
|---|---|---|
| `placement` | `size` = `size_vram` = 2561000078, `gpu_fraction` 1.0 | the same |
| tok/s, median | 52.9 | 41.6 |
| wall, median | 2.17 s | 2.43 s |
| wall, p95 (nearest rank, `llm_scoring.percentile`) | 2.42 s | 2.79 s |
| wall, max | 2.77 s | 2.80 s |
| walls above 18 s | 0 of 48 | 0 of 48 |
| wall drift, median of first / middle / last 16 | 2.20 / 2.10 / 2.19 s (flat) | 2.25 / 2.55 / 2.77 s (rising) |
| GPU before the run | 70 C, slowdown not active | 79 C, slowdown not active |
| GPU after the run | 86 C, slowdown **active** | 87 C, slowdown **active** |

**Drift.** The cycle-2 run's wall time rose by about 23% across its 48 generations while
`gpu_fraction` stayed 1.0 and the GPU reached 87 C with `sw_thermal_slowdown` active: that is the
thermal effect, not a placement change. No generation was discarded. The GPU was waited down between
the runs (1 minute each time, as the preflight required); a longer back-to-back session would keep
climbing, so these are figures for a cool start.

**What this does and does not say.** The form columns in the r2 GPU files (shippable in form 87.5% in both, 79% and
90% truncated at the 110-token cap) were recorded as they came out and were **not a re-scoring of D2**:
r2 missed the 90% bar (87.5%), and the template fallback ships either way. The r3 result follows below.
`LLM_TIMEOUT_S` stays 18 s. The timing basis is unchanged: the benchmark streams, the service does not
(see "The timing caveat").

## r3 (2026-10-17): shipped as measured, 5 of 6 pre-registered bars

Prompt revision r3 (owner decision, 2026-10-16: the replies were too short; `app/generation/prompts.py`)
asks for about 80 to 120 words (12 lines of Java for an example, then 2 to 4 sentences), adds an
`ANSWER_THE_QUESTION` line and a `QUIZ_INSTRUCTION` line, harmonises `STRATEGY_INTENT["example"]`, and
raises `LLM_MAX_TOKENS` from 110 to 220. It was measured **once**, on the GPU, against six bars written
beforehand. It passed bars 1 to 5 and **missed bar 6**; the stop rule held (nothing was built after the
miss) and the owner then chose option B: **r3 ships as measured. There is no r4** (no change to the prompt
wording, the cap or any bar). `LLM_TIMEOUT_S` stays 18 s.

| | r2 @110 (GPU, 2026-10-16) | r3 @220 (GPU, 2026-10-17) |
|---|---|---|
| Untagged leak (raw / final) | 0% / 0% | 0% / 0% |
| Shippable in form (cycle 1 / cycle 2) | 87.5% / 87.5% | 100% / 97.9% |
| **`example` replies that SHIP and contain a closed Java block** ¹ | 50% / 50% (6 of 12) | 100% / 92% (12, 11 of 12) |
| `pct_example_java_complete` (stored aggregate, for reference) ² | 91.7% / 75.0% | 100% / 100% |
| Wall p95 (GPU) | 2.42 s / 2.79 s | 5.87 s / 5.97 s |
| **Median words: prose outside fenced code, Check line removed, shipped replies only** ³ | 56 / 61 | 110 / 119 |
| Cap-stops (cycle 1 / cycle 2) | 79.2% / 89.6% | **33.3% / 39.6%** |
| 2-4 sentences (`sentences_ok`, after post-processing) | 70.8% / 70.8% | **29.2% / 18.8%** |

¹ One metric for all four cells. "Shipped": `would_ship` true. "Closed Java block": a
```` ```java ... ``` ```` pair in the finalised text. r2 shipped only 6 of 12 examples, which is why it is 50%
here.

² The benchmark's own stored field (closed Java block in the finalised `example` text, whether or not the
reply shipped), copied from each JSON's `aggregates`. **Do not mix ¹ and ² in one column.**

³ Other definitions give other numbers; bar 5 passes on all of them. Recomputed for this record, over shipped
replies: prose outside fenced code with the Check line KEPT is r2 68 / 72.5 and r3 121.5 / 130; every
whitespace-separated token is r2 76 / 81 and r3 140.5 / 141. (The lead's reading of the prose-with-Check
count was r2 66 / 72 and r3 122 / 128: a few words apart, a definitional difference, not a conflict.) This
record keeps the one definition named in the row.

Both columns are GPU runs: r2 = `llama3.2_3b_2026-10-16_np110_r2.json` and `_c2same.json`; r3 =
`llama3.2_3b_2026-10-17_np220_r3.json` and `_c2same.json` (`gpu_fraction` 1.0 in all four). The 87.5% that
D2 cites is the 2026-10-15 CPU run; the GPU r2 run gives the same 87.5%. Shippable in form = `would_ship` on
the raw reply (`app/generation/postprocess.py`); cap-stops = `done_reason == "length"`. On the raw text the
r2 cycle-2 "2-4 sentences" figure is 66.7%; the table uses the post-processed text.
1. **The bars.** r3 passed bars 1 to 5 (leak 0%; shippable in form >= 90%: 100% / 97.9%; complete Java
   >= 75%: 100% / 100%; wall p95 <= 12 s with 0 walls over 18 s: 5.87 s / 5.97 s; median shipped words in
   80..150: 110 / 116.5 over all replies) and **missed bar 6**: cycle-1 cap-stops were 33.3% against <= 25%.
   The cycle-2 figure (39.6%) is worse and is reported although the bar covered cycle 1 only. r3 was
   measured once with a pre-registered stop rule, and there is **no further revision**.
2. **Bar 5, how words were counted.** Prose outside fenced code, without the Check line (see above). The
   bar's own figures (110 / 116.5) count every reply; the table's (110 / 119) count shipped replies only.
3. **Guiding principle 2 ("processing within three seconds", proposal section 4.1) is NOT met with r3.**
   GPU p95 is about 6 s (5.87 / 5.97 s), against r2's 2.42 / 2.79 s, which met it. This was the owner's
   trade: longer replies over the 3 s principle. The UI's 3000 ms label is unchanged (changing it to match
   the result would be tuning the display).
4. **A sentence regression, a prompt self-contradiction exposed by measurement.** r3 asks for 80 to 120
   words AND (for examples) 2 to 4 sentences, and the general "2-4 sentences" check fell from 70.8% to
   29.2% / 18.8%: the model keeps the word count and drops the sentence count. **Not fixed (that would be
   r4).** PP2 note: a 140-word reply is about 50 s of synthesised speech, and the 2-4 sentence rule came
   from `05` section 5.2 as spoken-length control, so voice will need its own length policy.
5. **The confound.** r3 = longer limits + an `ANSWER_THE_QUESTION` line + a `QUIZ_INSTRUCTION` line + the
   `STRATEGY_INTENT["example"]` harmonisation, so the rise in shippable-in-form cannot be attributed to
   length alone. Do not write that longer replies raised shippability to 100%.
6. **Shippable in form is not accuracy.** It checks form only. Content accuracy is measured only by the
   blind rating (criterion 5), still pending.

**The D2 wording (team lead's text, 2026-10-17; verbatim).**

```
D2, as at 2026-10-17 (llama3.2:3b):
- r2 @110: 87.5% SHIPPABLE IN FORM - MISSED criterion 2's 90% bar.
- r3 @220: 100% (cycle 1) / 97.9% (cycle 2) shippable in form - MEETS criterion 2.
  Criteria 1 (leak 0%), 3 (complete Java) and 4 (timeout >= p95 x 1.2) also met.
- Criterion 5 (blind rating) is UNRATED. D2 is therefore FOUR OF FIVE MET, ONE
  PENDING - not "passed".
- r3 missed its own pre-registered bar 6 (cap-stops 33.3% cycle 1, 39.6% cycle 2,
  against <= 25%) and the proposal's guiding principle 2 (p95 ~5.9 s against 3 s).
  Both were the owner's accepted trade for longer replies, made knowingly.
- Measured ONCE. No r4, no cap change, no re-tuning after the result.
- "Shippable in form" = a complete prose sentence, a closed Java block, no reasoning
  leak. It does NOT measure whether the Java is true.
- CONFOUNDED: r3 changed reply length AND harmonised STRATEGY_INTENT["example"], so the
  improvement cannot be attributed to length alone.
- The template fallback ships either way, as a deterministic safety net - not as the
  reason the LLM is allowed out.
```
**A note on the two new r3 instruction lines (lead ruling 5, 2026-10-17).** Both new r3 instruction lines
were measured after shipping and are weak. `ANSWER_THE_QUESTION`: for "I don't understand how super works"
(inheritance, theory, 220 tokens), the reply explains the `super` keyword in its body in **2 of 10** runs
(team lead, keyword with a word boundary, "superclass" excluded; the backend lead's 3 runs gave 1). In one
reply `super` appeared only in the `**Check:**` question: the student was quizzed on the word they asked
about. `QUIZ_INSTRUCTION`: "ask me questions related to the topic" produced student-directed questions in
**0 of 10** replies. R7 escalates that message to a strategy (`example`), and the strategy intent overrides the
quiz line. So r3's gains come from the token cap and the `STRATEGY_INTENT` harmonisation, **not** from these
two lines. Both stay in the prompt: they are part of the measured configuration, and removing them would be r4.
Fixing either is PP2 (a dedicated quiz strategy). Measured on 2026-10-17 by the team lead and the backend lead
(the scripts were not committed); it was not re-run or re-measured in the M1 stage, and no relevance metric
was added to any script (relevance is a human judgement; the blind rating is the instrument).

## Memory (M1, 2026-10-17): the generator sees the episode so far

From M1 the generator's prompt carries the earlier turns of the **current episode** (the last 6 turns, each cut
to its first 600 characters at a word boundary, inside a `<conversation>` block before the student's message).
The classifier still sees the current message only (C2/C5). Measured on the GPU (`llama3.2:3b`, r3, 220 tokens,
3 runs x 16 prompts per variant, `gpu_fraction` 1.0 for both) with `scripts/benchmark_memory.py`; the
files are in `benchmarks/llm/memory/`. A = no history; B = the scripted 4-turn history built from the cycle-1
templates (two fixed student turns, "I don't understand" and "can you explain differently?"). There is no pass
bar.

| metric | A: no history | B: with history | B - A |
|---|---|---|---|
| median prompt characters | 1035 | 2084 | +1050 |
| wall p50 (s) | 4.67 | 4.25 | -0.42 |
| wall p95 (s) | 5.74 | 5.82 | +0.08 |
| wall max (s) | 5.77 | 5.95 | +0.18 |
| shippable in form (%) | 100.0 | 97.9 | **-2.1** |
| median shipped words | 106 | 106 | 0 |
| untagged leak (%) | 0.0 | 0.0 | 0.0 |
| cap-stops (%) | 37.5 | 27.1 | -10.4 |
| median tok/s | 39.6 | 39.4 | -0.2 |

Reading, in plain words. History doubles the prompt (1035 to 2084 characters) and leaves latency flat on the
GPU: p95 5.74 s to 5.82 s, with the median lower in B. **B is worse on one thing:** one reply of 48
(`loops` / `example`, run 3) stopped normally with no closed Java block, so it was not shippable in form and
the service would have served the template instead (97.9% against 100%). Everything else is equal or better,
but these are one run of 48 per variant, A ran first, and the GPU ended each run at 89 C with
`sw_thermal_slowdown` active, so differences of a few tenths of a second (and the cap-stop difference) are
within order and thermal noise and are not claims. The earlier caution (c2all, four priors, p95 26.3 s against
14.6 s) was measured on the CPU and did not repeat here with about 1 KB of extra context on the GPU. The
overlap between cycle-2 priors and the conversation was not exercised (priors exist only from cycle 2; this set
is cycle 1), so it is not reported. Whether the replies actually use the history is not measured: that is a
human judgement. "Shippable in form" is not accuracy.

## How to read `SUMMARY.md`

- **Row label** `model @N rX [c2same|c2all] (date)`: `N` = `num_predict`, `rX` = prompt revision, the
  optional `c2...` suffix marks a cycle-2 row (absent = cycle 1, unchanged from S8).
- **prompt length (median chars)**: median character length of that run's 16 prompts. Compares
  `c2same` against `c2all` directly: the prior block itself shrinks fourfold (one cycle-1 template
  instead of four), but the whole prompt only about **1.9×** (1352 vs 2562 median characters), since
  the fixed instructions, topic and student message are the same size either way.
- **usable (would ship)** (the column keeps this name, pinned by tests) is the decisive column for the template fallback and checks FORM only: read it as "shippable in form", never as accuracy or quality. The reply, after the deterministic post-processing
  (`app/generation/postprocess.py`: headings stripped; when the model stopped at the token cap, an unclosed
  code block dropped and the prose trimmed to the last complete sentence), has at least one complete prose
  sentence outside code and the Check line, an `example` has a closed ```` ```java ```` block, and it is not
  an untagged reasoning leak. Anything that does not ship is replaced by the template, never shown to a student. Content accuracy is measured only by the blind rating (criterion 5).
- **example complete java**: share of `example` replies whose shipped text has a closed java block.
- **headings (raw)**: share of raw replies that opened with a heading or title line.
- **untagged leak** is a heuristic (a line starting with `We are`, `Let me`, `The user`, ...) with false
  positives and negatives. An untagged preamble disqualifies a model (lead ruling).
- **over 12 s**: a **fixed reference carried from S7**, not the service's timeout (`LLM_TIMEOUT_S`,
  `app/config.py`: 14 s in S8, 18 s since S8b). It is a reference point, not a pass mark, and no
  generation is stopped at 12 s; read `LLM_TIMEOUT_S` in `app/config.py` for what the service actually
  falls back at.
- The format scores are mechanical. Whether an explanation is correct and good is the human rating.
- For r1 rows, the shippable-in-form / headings / example columns are recomputed from the stored raw text with today's
  post-processing, so they show what post-processing alone would have achieved.
- Timings are wall clock on the benchmark machine, with whatever else it was running.

## Blind rating (criterion 5)

Pre-registered D2 criterion 5 (its pre-registered name): "blind quality rating ≥ 3/5, and not below templates", rated by a
human. Built by `scripts/blind_sheet.py build` (`python scripts/blind_sheet.py build --force` to
rebuild; it refuses to overwrite an existing sheet or key without `--force`, so a sheet that already
has ratings in it is never silently wiped):

- **Source**: `llama3.2_3b_2026-10-17_np220_r3.json` (r3), run 1 only, the three topics `inheritance`,
  `loops`, `exception_handling`, all four strategies — 12 generations, paired with the matching 12
  cycle-1 templates, 24 items in total. The reply that fails `would_ship` is included as it is: the
  rating judges what the model actually produced, not what the fallback hides.
- **Seed**: `20261017`, pre-registered in `scripts/blind_sheet.py` (`SEED`). The 24 items are
  shuffled with this seed and labelled `R01`-`R24` so neither the order nor the label gives away
  which side an item came from.
- **Files**: `blind_rating_2026-10-17.md` (the sheet a human rates) and `blind_key_2026-10-17.json`
  (which `R..` id is which side). **Do not open the key before rating** — the sheet says so too.
- **The r2 sheet and key are VOID.** `blind_rating_2026-10-15.md` and `blind_key_2026-10-15.json` (seed
  `20261015`, built from r2) stay on disk, unedited, as history. They were built from r2, which no longer
  ships; **rate the r3 sheet above, not those.**

**To rate it:** open `blind_rating_2026-10-17.md`, read each item, and fill in its
`Rating (1-5): ` line (1 = poor, 5 = excellent) — nothing else on the sheet changes. Do this for all
24 items before opening the key.

**To score it:** `python scripts/blind_sheet.py score benchmarks/llm/blind_rating_2026-10-17.md
benchmarks/llm/blind_key_2026-10-17.json`. It prints `n_llm`, `n_template`, `mean_llm`,
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
