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

## How to read `SUMMARY.md`

- **Row label** `model @N rX (date)`: `N` = `num_predict`, `rX` = prompt revision.
- **usable (would ship)** is the decisive column. The reply, after the deterministic post-processing
  (`app/generation/postprocess.py`: headings stripped; when the model stopped at the token cap, an unclosed
  code block dropped and the prose trimmed to the last complete sentence), has at least one complete prose
  sentence outside code and the Check line, an `example` has a closed ```` ```java ```` block, and it is not
  an untagged reasoning leak. Anything not usable is replaced by the template, never shown to a student.
- **example complete java**: share of `example` replies whose shipped text has a closed java block.
- **headings (raw)**: share of raw replies that opened with a heading or title line.
- **untagged leak** is a heuristic (a line starting with `We are`, `Let me`, `The user`, ...) with false
  positives and negatives. An untagged preamble disqualifies a model (lead ruling).
- **over 12 s**: share of generations the service would replace with a template (its fallback timeout).
  A reference, not a pass mark; no generation is stopped at 12 s.
- The format scores are mechanical. Whether an explanation is correct and good is the human rating.
- For r1 rows, usable / headings / example columns are recomputed from the stored raw text with today's
  post-processing, so they show what post-processing alone would have achieved.
- Timings are wall clock on the benchmark machine, with whatever else it was running.
