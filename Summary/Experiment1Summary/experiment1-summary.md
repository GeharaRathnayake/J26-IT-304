# Experiment 1: Baseline Confusion Classifier — Handover

**Audience:** the backend agent who will load and serve the model (`backend/pp1-service`), and an examiner or supervisor who wants to understand the result without running anything.
**Last updated:** 2026-10-13
**Status:** complete. Every number below is final, and the model artifact `clf-v1.0.0` is published on branch `notebooks/confusion-classifier` (commits U0–U10, see `GitSummary/git.md` §9).
**Scope of verification:** every number here was produced by the notebooks in `dev/experiment1/notebooks/` and then checked independently by the supervisor: re-executed from a clean kernel, and for the key results rebuilt with separate code. `scripts/train_baseline.py` reproduces the test metrics headless and passes all 5 of its checks against the published artifact (full search about 140 s). The artifact was loaded in a separate process with only `joblib` imported. **Nothing here has been run against the real tutor service, which does not exist yet.** The error-analysis judgements were made by an AI assistant as a single, unvalidated annotator (§9).

Related documents:

- `dev/experiment1/README.md`: run instructions, the result table, the artifact contract (shorter version of §10 below).
- `dev/experiment1/notebooks/09_summary.ipynb`: the slide-ready summary (PP1 slide 6).
- `research 2027/experiment1Plan/00`–`08`: the specification this was built against. Where the build deviates from it, §12 says so.
- `frontendSummary/frontend-and-api-guide.md` §4.5: what `GET /model-info` must return.

---

## 1. What was built

A **TF-IDF + Logistic Regression** text classifier that labels a student's answer as `confused` or `understood`, together with everything needed to defend the number it produces:

| Deliverable | Where |
|---|---|
| Nine notebooks, one per pipeline stage (01 → 09) | `experiment1/notebooks/` |
| Shared code used by every notebook and the script, so they cannot drift | `experiment1/confusion_baseline/` |
| The model artifact the service loads | `experiment1/models/clf-v1.0.0/` |
| Headless reproduction with self-checks | `experiment1/scripts/train_baseline.py` |
| Figures, metrics tables, annotation codes (no dataset text) | `experiment1/reports/experiments/` |
| The frozen out-of-distribution probe set | `experiment1/probe/ood_probe.yaml` |

**It is a baseline, deliberately.** It is the lexical model the proposal specifies (Specific Objective 2). No BERT, no embeddings, no LLM, no conversation history: those are later experiments, and this one is what they are measured against.

## 2. The headline, in one paragraph

On 216 held-out answers to 72 questions the model never saw, TF-IDF + LR scores **F1(confused) = 0.758, macro F1 = 0.663, accuracy = 0.690**. A predictor that always says "confused" already gets F1(confused) = 0.748, so the model's claim is **not** its F1 on the confused class. Its claim is **macro F1 +0.289 over that predictor** (95% CI +0.222 to +0.356): it really does separate the two classes. It **cannot be shown to beat a one-feature model that only counts words** (both margins' CIs include 0). On 40 hand-written student-style messages it flags 34 as confused and recognises only 2 of 10 "I understand" messages, which is why a rule layer ships with it. **The proposal's F1 ≥ 80% target is not met, and it was not tuned towards.** The label is answer correctness on a synthetic dataset, a proxy for confusion and not a measurement of it.

## 3. The dataset, as actually found

**JavaQuestionSynthFinal**, `huggingface.co/datasets/nitinnovtech-ai-space/JavaQuestionSynthFinal`, pinned to revision `e29cfdd4ec4179f54b2ea0409329207104de8bed` (resolved 2026-10-13; the mirror `Pragades/JavaQuestionSynthFinal` is the same commit and the same parquet file). One parquet file, **1,078 rows**.

| Field | Found |
|---|---|
| `Question`, `Answer` | text, no missing values |
| `Correctness` | exactly `Correct` 422 · `Partial Correct` 289 · `Wrong` 367 |
| `FollowUp Question` | **one struct column** with `Part1`, `Part2` (the spec said two fields) |
| Licence | **none stated.** The dataset card is YAML metadata only. Appears synthetic. |

### The five known defects, checked

| # | Defect (from the spec) | What the data showed | What was done |
|---|---|---|---|
| 1 | `FollowUp.Part1` leaks the label | **Confirmed, strongly:** a keyword rule on `Part1` alone predicts Correctness with **98.6%** accuracy (binary 99.2%). | Moved out at load into a quarantine read by one demonstration cell, then deleted. Asserted absent everywhere. (01 §2, §3.7) |
| 2 | Grouped questions, duplicates | 360 questions with 1–12 answers each (mode 3; 15 questions recur in separate blocks). A random 80/20 split would put the question of **93.5%** of test rows into training. **One** record appears three times (rows 0, 15, 1060). 0 label conflicts, 0 answers shared across questions, 2 near-duplicate pairs across related questions. | Dedup before the split (1,078 → 1,076); split by question. (01 §3.2–3.3, 02 §4, 03 §6) |
| 3 | No hedging or confusion language | **Confirmed:** 0 hedging words and 0 code fences in 1,078 answers; every answer is a confident statement. | Cannot be fixed; measured with the OOD probe (§8). |
| 4 | Label noise | 3 of 5 sampled `Partial Correct` answers read as `Wrong` (rows 142, 133, 497; row 110 the reverse). The spec's claim that a `Wrong` answer looked correct was **not** reproduced in a 5-answer sample. | Reported, never relabelled. |
| 5 | No provenance or licence | Confirmed. | The data is not redistributed: `data/` is gitignored, and committed CSVs hold only ids, labels and codes. Short excerpts appear only in notebook output. |

**Two findings the spec did not anticipate:**

- **Answer length is the strongest simple signal.** Confused answers are shorter (median 17 vs 22 tokens); length alone has ROC AUC 0.73–0.75. A length-only baseline was therefore added to every comparison.
- **A generator fingerprint.** The curly apostrophe U+2019 is about twice as frequent in confused answers (3.6% Correct, 7.3% Partial, 8.2% Wrong). Word-level TF-IDF cannot see it (0 of 8,548 vocabulary terms are non-ASCII), and character n-grams were excluded for that reason.

## 4. The label mapping and its proxy caveat

```text
Correct                   → understood
Partial Correct, Wrong    → confused
```

After dedup: 656 confused / 420 understood (61.0% confused).

**This is the baseline operationalisation, not a definition of confusion.** Correctness tells you whether an answer matched the expected content; confusion is whether the learner knows they do not understand. A confidently wrong answer is not confusion. A student who says "wait, I don't follow" is confused but has produced no answer to mark. The deployed tutor will mostly see the second kind of message, and this dataset contains none of them. Every number in this document is about the proxy. The caveat travels inside the artifact (`metadata.json` → `caveat`).

**Sensitivity check (notebook 06).** Re-run with `Partial Correct` dropped (787 rows; Correct vs Wrong only, the same test questions): TF-IDF + LR macro F1 **0.655** against 0.663 for the primary mapping, a difference far inside the uncertainty. So treating partial answers as confused does not change what the lexical model can do. The length-only baseline improves on this cleaner contrast (macro F1 0.621 → 0.724), because partial answers sit between the other two in length. Re-tuning on the reduced data changes nothing (0.651 vs 0.655).

## 5. Method and leakage controls

```text
raw parquet (pinned) → quarantine FollowUp → dedup → group key = normalised Question
  → label map → GroupShuffleSplit by question (seed 42, 20% of questions)
  → Pipeline(TfidfVectorizer → LogisticRegression), hyperparameters by group-aware CV on TRAIN
  → one evaluation on TEST → baselines, bootstrap CIs → features, OOD probe, sensitivity, errors
```

- **Input is the answer text only.** The question is never a feature: it is the tutor's preceding turn, i.e. conversational context, which is the PP2 research question.
- **No text preprocessing.** The proposed normalisation (curly quotes, backticks, whitespace) was measured to change the TF-IDF tokens of **0 of 1,076** answers in all four analyser settings tried, so the model takes raw text (02 §4).
- **Search:** 160 configurations (n-grams, min_df, stop words, sublinear tf, C, class weight) × 5 `StratifiedGroupKFold` folds inside train, **selected on macro F1**. Selecting on F1(confused) would reward collapsing towards "always confused". Chosen: word uni+bigrams, min_df 1, no stop-word removal, sublinear tf, **C = 100**, `class_weight='balanced'`; CV macro F1 0.645 ± 0.032. **The choice is weakly determined:** the top 10 configurations lie within 0.008 of each other. Train macro F1 is 1.000, so the model memorises its training answers; the CV and test figures are the honest ones.

| Control | Proved where | Evidence |
|---|---|---|
| `FollowUp` dropped at load | 01 §2 | printed assertion: no FollowUp-derived column |
| Duplicates removed **before** the split | 02 §4 | attrition table, removed row ids 15 and 1060 |
| Train and test share **no question** | 03 §6 | printed assertion: 288 train / 72 test groups, intersection 0; test fingerprint `511fadfe…` |
| Vectoriser fitted on train only | 04 §8 | structurally, by the sklearn `Pipeline` |
| Cross-validation group-aware | 04 §8 | 5 printed PASS lines, one per fold |
| Top coefficients read for artefacts | 05 §10 | categorised term table and a stability check |
| Test set touched once | 04 §9 | one cell; later notebooks only re-score the frozen model to prove identity |

Residual known leakage: one near-duplicate pair (two `floor()` questions, both Correct) crosses the split, at most 1 of 216 test rows. It is documented, not moved. The >0.90 red-flag gate never fired.

## 6. Results

Test set: 216 rows, 72 questions, 59.7% confused. Threshold 0.5.

| System | Accuracy | Precision | Recall | F1 (confused) | Macro F1 |
|---|---|---|---|---|---|
| Majority class (always "confused") | 0.5972 | 0.5972 | 1.0000 | 0.7478 | 0.3739 |
| Stratified random (seed 42) | 0.4583 | 0.5441 | 0.5736 | 0.5585 | 0.4289 |
| Length-only logistic regression | 0.6759 | 0.6746 | 0.8837 | 0.7651 | 0.6214 |
| **TF-IDF + Logistic Regression** | **0.6898** | **0.7095** | **0.8140** | **0.7581** | **0.6629** |

The stratified row at seed 42 is a below-average draw; over 1,000 seeds it averages F1(confused) 0.604 ± 0.032.

Confusion matrix of the model: **TP 105 · FP 43 · FN 24 · TN 44.** It recovers 81% of confused answers but only 51% of understood ones.

**Margins** (95% cluster bootstrap over the 72 test questions, 1,000 resamples):

| TF-IDF + LR minus… | F1 (confused) | Macro F1 |
|---|---|---|
| majority class | +0.010 [−0.035, +0.056], **includes 0** | **+0.289 [+0.222, +0.356], excludes 0** |
| length-only LR | −0.007 [−0.066, +0.053], includes 0 | +0.042 [−0.060, +0.147], includes 0 |

What this supports: on this dataset a lexical model separates correct from not-fully-correct answers clearly better than trivial predictors (macro F1), and it generalises to unseen questions at its cross-validated level (CV 0.645, test 0.663).

## 7. Feature inspection (notebook 05)

- **The top terms are mostly semantic or structural, not a leak.** Of the top 20 terms in each direction: 8 signal wrongness (`only`, `but`, `error`, all toward confused), 8 signal complete answers (`implementation`, `declared`, `typically`), 8 are length-proxy function words (`of`, `to`, `which`, `or`, all toward understood), 12 are topic words, and **4 are generator artefacts** (`program` / `the program` from a "The program will…" template in wrong answers, the tokeniser fragment `doesn`, and `that is`). Strongest weights: `rounds the` +6.54, `makes` +5.50, `program` +5.35 → confused; `of` −6.56, `implementation` −5.93 → understood.
- **Stability:** refitted on each of the 5 training folds, 24 of the 40 top terms stay in the top 20 in 4–5 folds, and 2 are noise. Rare topic terms rest on 2–7 answers and should not be quoted.
- **It is not just length:** the model's P(confused) correlates only −0.15 with answer length, and it disagrees with the length-only model on 83 of 216 test rows (both right 106, only TF-IDF 43, only length 40, both wrong 27). Similar scores, different signals. Combining them is a PP2 question and was not built.

## 8. The OOD probe: the proxy gap, measured

40 hand-written messages of the kind the deployed tutor will receive, **written and frozen before any model existed** (sha256 `cbccf0a0…`) and never trained on.

| Category (10 items each) | Model correct | Length-only correct | Mean P(confused) |
|---|---|---|---|
| explicit confusion ("I'm lost", "no idea") | 9/10 | 10/10 | 0.82 |
| confusion about a Java topic | 9/10 | 10/10 | 0.76 |
| hedged attempt ("maybe it's static? not sure") | 8/10 | 10/10 | 0.83 |
| **explicit understanding ("got it", "that makes sense")** | **2/10** | 0/10 | 0.69 |

Overall the model flags **34 of 40** as confused: accuracy 0.70, **below** the 0.75 of always saying "confused"; specificity 0.20; ROC AUC 0.57. The high recall is a **bias, not detection**. The model defaults to "confused" for short or unfamiliar text (probe items have a median of 7 tokens against 19 in training), and generator-style weights misfire: `makes` pushes "that makes sense" to P = 0.992 confused. Length-only flags all 40 and is the constant predictor here.

**Consequence (ARCHITECTURE ADR-04, IRWA Lecture 06's rule-based vs ML-based classification):** the service must check an explicit-phrase rule layer **first, in both directions**, and use the model only when no rule matches. The rules are deliberately **not** scored on this probe: their phrases were seeded from it, so that would be circular.

## 9. Error analysis (notebook 08)

The 67 test errors: **43 false positives** (Correct answers called confused) and **24 false negatives** (10 Partial, 14 Wrong called understood).

- **Costs.** A false *understood* (FN) means the tutor moves on while the student is lost: the worse error per event. A false *confused* (FP) means an unnecessary strategy escalation, which the weakness logger then counts. By count, FPs dominate (FP : FN = 1.79 : 1), and they are confident (mean P 0.77), so a threshold change would not fix them. None was tried.
- **Categories** (multi-label, errors): short 16%, partially correct 15%, confident-but-incorrect 21% (14 Wrong answers passed as understood), needs-context 12%, ambiguous 13%. Error rate rises with length (Q1 19% → Q3/Q4 38–39%), mostly FPs on long correct answers.
- **The share of errors that need prior context.** The judging was blind: answer only first, then with the question, never seeing the gold label or the prediction. A **control sample** of 67 correctly classified rows was judged the same way:

| | Cannot judge from the answer alone | Ambiguous even with the question |
|---|---|---|
| Errors | **8/67 = 11.9%** [6.2%, 21.8%] | 9/67 = 13.4% |
| Correct predictions (control) | 2/67 = 3.0% [0.8%, 10.2%] | 12/67 = 17.9% |
| Difference | **+9.0 pp [−0.3, +19.1], Fisher p = 0.096** | −4.5 pp |

**Reading:** the difference points the way the PP2 hypothesis predicts, but it is **not significant**. And 88% of the errors could be judged from the answer alone, with that reading agreeing with the gold label 90% of the time. So these errors are mostly **content judgements a vocabulary model cannot make**, not missing context. **On this data, missing context is not shown to be the main failure mode, and this document does not claim it is.**

What this means for PP2: the context question has to be tested on **real multi-turn student data**, where most turns are not answers ("I don't get it", "that makes sense") and refer to the preceding tutor turn. That setting is absent from this dataset. PP2 needs real student turns, the preceding tutor turn stored with each, human confusion labels from two annotators with reported agreement, and the blind-pass-plus-control design used here.

**Limitation:** the judgements were made by an AI assistant as a **single annotator, not validated** by a human expert. A human could shift the "cannot judge" counts either way.

## 10. The artifact contract (for the backend agent)

Path: `dev/experiment1/models/clf-v1.0.0/` on branch `notebooks/confusion-classifier`. **Do not copy or wire it into `backend/` from this branch** (git.md §4 rule 1). Select it by `MODEL_VERSION=clf-v1.0.0`.

| File | sha256 (prefix) | What |
|---|---|---|
| `pipeline.joblib` | `2c168f13` | sklearn `Pipeline(TfidfVectorizer, LogisticRegression)`, **fitted on the 860-row train split only**, the exact object whose test metrics are reported. 283 KB. Contains only sklearn classes, so no project code is needed to load it. |
| `metadata.json` | `815b40da` | Provenance, split, hyperparameters, metrics, baselines, probe, sensitivity, runtime, file hashes, caveat, and `model_info`. |
| `rules.yaml` | `2f08da40` | 51 confusion phrases and 19 understanding phrases, with the matching rule and known false triggers in the header. |

### 10.1 Inference, exactly

```python
import joblib, json, re, yaml
pipe = joblib.load("pipeline.joblib")          # scikit-learn 1.9.1 exactly
meta = json.load(open("metadata.json"))

def classify(text: str):
    p = float(pipe.predict_proba([text])[0, 1])   # column 1 = P(confused); always computed, it is cheap
    label = match_rules(text)                  # rules decide FIRST, see 10.2
    if label is not None:
        return {"label": label, "probability": p, "source": "rule"}
    return {"label": "confused" if p >= meta["threshold"] else "understood",
            "probability": p, "source": "model"}
```

- **Pass the raw student text.** Do not lowercase, strip or rewrite it; the vectoriser does its own lowercasing. **Do not apply ARCHITECTURE §9.1's code-fence → `<code>` mapping**: the training data contained zero code fences, and the replacement token would be an unseen input pattern. This is a deliberate deviation from §9.1 (see §12).
- `classes_` is `[0, 1]`: 0 = understood, 1 = confused. `meta["input"]["proba_index_confused"]` is 1.
- **Threshold 0.5**, from `meta["threshold"]`. It was never tuned.
- **`probability` must always be a number.** The frontend contract (`ConfusionResult` in `frontend/src/features/tutor/api/types.ts`) types it `probability: number` in [0, 1], not nullable, so a rule decision cannot send `null`. The sketch above reports the **model's** P(confused) even when a rule decided. The research panel then shows what the model alone would have said: for "that makes sense" it shows label `understood`, `source: rule`, probability 0.99, which is exactly the evidence for the rule layer. The alternative is a fixed 1.0 / 0.0 on rule decisions. Either is valid under the contract; the choice belongs to the backend, but it must be documented there.

### 10.2 The rule layer (`rules.yaml`)

Implement exactly what its header says. `experiment1/confusion_baseline/rules.py` is the reference implementation (read it; do not import it into the service).

1. Normalise: lowercase; replace U+2018 and U+2019 with `'`; collapse whitespace; strip. Nothing else.
2. Match each phrase as a whole-word sequence: `\b<re.escape(phrase)>\b`, not a substring (`no idea` must not match `no ideal`).
3. Check `confusion_phrases` first, then `understanding_phrases`, in file order. The first match decides. No match means the model decides, with `source = "model"`.

Known false triggers, documented in the file: `got it` fires on "I got it from the docs"; `that makes sense` fires on "that makes sense in theory but…"; inserted words defeat a phrase ("I am **so** lost" falls through to the model); and a student *challenging* the tutor ("that doesn't make sense, 2+2 is 4") is treated as confused on purpose. "I got it wrong" is **not** a false trigger: `got it wrong` is a confusion phrase, checked first. That case was fixed during verification.

### 10.3 `GET /model-info` and `GET /health`

- `metadata.json["model_info"]` already has **exactly** the frontend's `ModelInfo` shape (`version`, `trained_at`, `dataset` as a string, `threshold`, `metrics` as `Record<string, number>`), validated in notebook 07. **Return it verbatim.** The spec's top-level `created_at` and nested `dataset` object do not match `ModelInfo`, which is why this block exists.
- `/health`: `model_loaded = true` once `joblib.load` succeeds; `model_version = "clf-v1.0.0"`.
- `ARCHITECTURE.md` §13's metrics-regression test should read `metadata.json["metrics"]`. `scripts/train_baseline.py` asserts the same numbers.

### 10.4 Runtime facts that will bite

- **Pin `scikit-learn==1.9.1`** in the service. A pickle is not guaranteed to load under another version. Python 3.13.16 was used.
- **Pickle bytes are not reproducible:** rebuilding the identical model produces a `pipeline.joblib` with different bytes. Identity is checked by **behaviour** (predictions on the test set) and by the hash recorded **once** at publication. Never rebuild into `clf-v1.0.0/`; notebook 07 refuses to and only verifies.
- In sklearn 1.9.1 the recorded LR hyperparameters show `"penalty": "deprecated"` and `"l1_ratio": 0.0`. That is plain L2 regularisation, recorded as the library reports it.
- **Versioning** (ARCHITECTURE §9.3): patch = threshold or rule-list change; minor = retrained on new data; major = new input features (adding context will be `clf-v2.0.0`). A change always means a new directory.

## 11. What is explicitly not claimed

- **That this detects confusion.** It separates correct from not-fully-correct synthetic answers. The OOD probe shows the model alone cannot recognise explicit understanding and defaults to "confused" on short text.
- **That F1 ≥ 80% was achieved.** It was not (0.758), and no tuning was done towards it. The always-"confused" predictor already scores 0.748 on that metric, so the target was never a meaningful bar on this data.
- **That the words add anything beyond answer length.** A one-feature length model is indistinguishable within the intervals.
- **That missing context explains the errors.** The difference is in the hypothesised direction but not significant (p = 0.096); most errors are content judgements.
- **Anything about real students or multi-turn tutoring.** No real student message was used. The probe is 40 hand-written items, a diagnostic and not a benchmark.
- **Validated error categories.** Single AI annotator.

## 12. Deviations from the specification, and why

| Spec said | Built | Why |
|---|---|---|
| Two notebooks, `01_baseline_confusion_classifier` and `02_error_analysis` | Nine notebooks, one per stage, with continuous section numbers | The lead asked for the single notebook to be split. All 45 moved cells were verified to print identical output after the split. |
| Normalise answer text | Raw text in; no preprocessing in the model or the service | Measured as a no-op for TF-IDF tokens (0 of 1,076 changed); keeps the pickle plain sklearn. |
| ARCHITECTURE §9.1: service maps code fences to `<code>` | Do not | 0 code fences in training data (§10.1). |
| Select class weight / C on F1(confused) (implied) | Selected on macro F1 | F1(confused) rewards "always confused" here (0.748). |
| `metadata.json` per spec shape | Spec shape **plus** split sizes and fingerprint, input contract, runtime, file hashes, probe detail, sensitivity, and `model_info` | `model_info` matches the frozen frontend `ModelInfo`; the rest lets the service self-check. |
| Rules seeded from the spec's 9 phrases, confusion-oriented | Both directions, 51 + 19 phrases | The probe showed the model calls 8 of 10 "I understand" messages confused. |
| Re-split for the sensitivity check (implied) | Same test questions reused | The difference is then attributable to the label mapping alone. |
| Artifact trained on all data (often assumed) | Trained on the 860-row train split | The reported metrics then describe the shipped object. |
| Proposal target F1 ≥ 80% | Not met, not tuned towards | Spec 05 §3. |

## 13. Reproducing

```text
cd dev/experiment1
$env:PYTHONNOUSERSITE = "1"            # PowerShell; bash: export PYTHONNOUSERSITE=1  (see README, Step 0)
conda env create -f environment.yml
conda run -n exp1-confusion pip install -e .
conda run -n exp1-confusion python scripts/fetch_data.py
conda run -n exp1-confusion python scripts/train_baseline.py --skip-search    # seconds; 4 PASS + 1 n/a
conda run -n exp1-confusion python scripts/train_baseline.py                  # ~2.5 min; 5 PASS
```

The notebooks run in order 01 → 09, each from a clean kernel (the command is in the README). Everything is seeded (42), and a clean re-run reproduces every printed number and every committed report file byte for byte. The one exception is the artifact, which notebook 07 verifies rather than rewrites.

## 14. Quick checklist for the backend agent

- [ ] Pin `scikit-learn==1.9.1`; load `pipeline.joblib` with `joblib.load`, no project imports.
- [ ] Verify `sha256(pipeline.joblib)` and `sha256(rules.yaml)` against `metadata.json["files"]` at startup.
- [ ] Pass **raw** student text to `predict_proba`; take column 1; threshold `metadata["threshold"]`.
- [ ] Implement `rules.yaml` exactly as its header says, **rules first**, both directions; report `source`.
- [ ] Do **not** apply the §9.1 `<code>` mapping.
- [ ] Serve `metadata["model_info"]` verbatim at `GET /model-info`.
- [ ] Repeat the caveat wherever metrics are shown: correctness proxy, synthetic data.
- [ ] Do not edit anything under `experiment1/` or `frontend/` (git.md §4).

## 15. Is Experiment 1 finished?

Yes, for PP1. The number is defensible: the leakage controls are proved in printed output, trivial and length baselines sit in the same table with bootstrap margins, the proxy gap is measured, and there is a loadable, verified artifact whose metadata matches the frontend contract. What it shows is modest, and it is reported as modest. The open questions are PP2's, not unfinished work here: real student data, human confusion labels, and whether the preceding tutor turn helps.
