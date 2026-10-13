# Experiment 1: baseline confusion classifier

A baseline classifier (TF-IDF + Logistic Regression) for an AI Java tutor (J26-IT-304 PP1). It classifies a student's
answer as *confused* or *understood*, but **the label is a proxy**: it is built from answer correctness (Correct → understood;
Partial Correct and Wrong → confused) on a **synthetic** dataset, so it is **not a measurement of confusion**. The experiment sets the
reference point that later work (PP2: does conversational context help?) is compared against, and its pickled pipeline,
`models/clf-v1.0.0/`, is the artifact the tutor service loads.

## Result at a glance

Test set: 216 answers to 72 questions the model never saw (question-disjoint split, seed 42). Threshold 0.5.

| System | Accuracy | Precision | Recall | F1 (confused) | Macro F1 |
|---|---|---|---|---|---|
| Majority class (always "confused") | 0.5972 | 0.5972 | 1.0000 | 0.7478 | 0.3739 |
| Stratified random (seed 42) | 0.4583 | 0.5441 | 0.5736 | 0.5585 | 0.4289 |
| Length-only logistic regression | 0.6759 | 0.6746 | 0.8837 | 0.7651 | 0.6214 |
| **TF-IDF + Logistic Regression** | **0.6898** | **0.7095** | **0.8140** | **0.7581** | **0.6629** |

Margins of TF-IDF + LR (95% cluster bootstrap over the 72 test questions, notebook 04 §9):

| | F1 (confused) | Macro F1 |
|---|---|---|
| over the majority predictor | +0.010 [-0.035, +0.056], includes 0 | **+0.289 [+0.222, +0.356]**, excludes 0 |
| over the length-only baseline | -0.007 [-0.066, +0.053], includes 0 | +0.042 [-0.060, +0.147], includes 0 |

In words: the model separates correct from not-fully-correct answers far better than always answering "confused" (macro F1), but on F1(confused)
it is indistinguishable from it, and the data cannot show that the words add anything beyond answer length. Dropping Partial Correct leaves macro F1
at 0.655 (notebook 06). On 40 hand-written student messages (the OOD probe) the model flags 34 as confused and recognises only 2 of 10
explicit-understanding messages, so a rule layer is shipped with the model (notebook 05, 07). Notebook 09 is the slide-ready summary.

## Setup

One conda environment is the only environment for this experiment (no `.venv`). Run from this directory.

**Step 0: set `PYTHONNOUSERSITE=1` in your shell before anything else.** A user-site Python folder
(e.g. `AppData\Roaming\Python\Python313\site-packages`) would otherwise leak into the env: pip
treats packages found there as already installed and skips them, so the env is built incomplete and
imports of unlisted packages silently succeed. `environment.yml` also sets the variable, but
`conda env create` can run pip before that takes effect, so the shell variable is required.

```
# PowerShell
$env:PYTHONNOUSERSITE = "1"
# bash
export PYTHONNOUSERSITE=1

conda env create -f environment.yml
conda run -n exp1-confusion pip install -e .
conda run -n exp1-confusion python -m ipykernel install --user --name exp1-confusion --display-name "Python (exp1-confusion)" --env PYTHONNOUSERSITE 1
conda run -n exp1-confusion pip check
conda run -n exp1-confusion python scripts/fetch_data.py
```

`pip check` must print "No broken requirements found." The kernel is registered with
`--env PYTHONNOUSERSITE 1` because Jupyter does not go through conda activation. Do not run other conda commands while
`conda env create` is running.

`requirements.txt` is the single source of pinned versions. After changing it, with the variable set:
`conda env update -f environment.yml --prune`.
The scikit-learn pin (1.9.1) matters most: the model must be unpickled under the version it was trained with.
Notebooks use the kernel `exp1-confusion` and import `confusion_baseline` via the editable install, with no `sys.path` edits.

## Reproduce

**Without Jupyter** (a marker who will not open a notebook). `scripts/train_baseline.py` reuses the package functions, fetches the data if
missing, trains, evaluates on the test set once, and runs 5 checks against the published artifact and committed reports (PASS/FAIL, exit code 1 on any FAIL):

```
conda run -n exp1-confusion python scripts/train_baseline.py --skip-search   # reuse chosen_params_primary.json, a few seconds
conda run -n exp1-confusion python scripts/train_baseline.py                 # full 160-config group-aware search, about 2 minutes
```

Outputs go only to a temp directory (`--out-dir` to choose one); the script never writes into `models/` or `reports/`. The checks compare *behaviour*,
not pickle bytes (a rebuild of the same model pickles to different bytes). `--skip-search --c-override 1.0` is a self-test: it perturbs one
hyperparameter and the checks must FAIL (exit 1).

**With notebooks**, in order 01 → 09, each from a clean kernel:
`conda run -n exp1-confusion python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=exp1-confusion --ExecutePreprocessor.timeout=1800 notebooks/<name>.ipynb`
Notebook 07 never overwrites a published artifact (it verifies it); 08 reads the committed blind-judging annotations.

## Notebooks

One notebook per pipeline stage. Section numbers run continuously across the series, so "§3.5" means the same place everywhere. Each notebook runs on its own
from a clean kernel (its first code cell rebuilds its inputs with the package functions).

| Notebook | Sections | Stage |
|---|---|---|
| `01_data_and_eda.ipynb` | §1–§3 | provenance, load, exploratory analysis, leakage demonstration |
| `02_cleaning_and_labels.ipynb` | §4–§5 | deduplication, group key, label mapping, proxy caveat |
| `03_split_and_baselines.ipynb` | §6–§7 | group-aware split, trivial baselines, frozen OOD probe |
| `04_model_training_and_evaluation.ipynb` | §8–§9 | TF-IDF + LR, group-aware CV, the single test evaluation |
| `05_features_and_ood_probe.ipynb` | §10–§11 | coefficient inspection and stability, length check, OOD probe |
| `06_sensitivity_check.ipynb` | §12 | robustness of the label mapping: Partial Correct dropped |
| `07_publish_artifact.ipynb` | §13 | the `clf-v1.0.0` artifact: pipeline, metadata, rules, verification |
| `08_error_analysis.ipynb` | §14 | error analysis, blind judging with a control sample, motivation for Experiment 2 |
| `09_summary.ipynb` | §15 | slide-ready summary; reads committed files only, computes nothing new |

## The artifact: `models/clf-v1.0.0/`

| File | What |
|---|---|
| `pipeline.joblib` | scikit-learn `Pipeline` (TfidfVectorizer → LogisticRegression), **fitted on the 860-row train split only**, the object whose test metrics are reported |
| `metadata.json` | version, dataset revision, split (with test fingerprint), hyperparameters, test metrics, baselines, OOD probe and sensitivity results, runtime, file hashes, caveat, and a `model_info` block that matches the frontend's `ModelInfo` contract exactly |
| `rules.yaml` | explicit-phrase rules for **both** directions (confusion and understanding), with the exact matching rule and the known false triggers in its header; reference implementation `confusion_baseline/rules.py` |

**Input contract for the service.**
- The pipeline takes the student's **raw text**. Do not preprocess: text normalisation changes no TF-IDF token (notebook 02 §4) and the vectoriser lowercases internally.
- `predict_proba(...)[:, 1]` is **P(confused)** (`classes_` is `[0, 1]`; 0 = understood, 1 = confused). **Threshold 0.5.**
- **Rules are checked first** (`rules.yaml`: normalise, whole-word phrase match, confusion list before understanding list, first match decides), then the model for everything else.
- Load with **scikit-learn 1.9.1** exactly (recorded in the metadata); `pickle`/`joblib` of another version is not guaranteed to load.
- A published version is never overwritten; a change means a new version directory.

## Data and licence

The dataset is **JavaQuestionSynthFinal** (`nitinnovtech-ai-space/JavaQuestionSynthFinal`, mirror `Pragades/JavaQuestionSynthFinal`, pinned revision
`e29cfdd4ec4179f54b2ea0409329207104de8bed`). It has **no stated licence** and appears synthetic, so it is **not redistributed**: `data/raw/` and `data/processed/` are gitignored,
and the committed CSVs and annotations contain **only row ids, labels, judgements, codes and numbers, never question or answer text** (short excerpts appear only in notebook output).
`scripts/fetch_data.py` downloads the pinned revision. See `data/README.md`.

## What is NOT claimed

- That this **detects confusion**. The label is correctness on synthetic answers; the OOD probe shows the model alone cannot recognise explicit understanding and answers "confused" to short or unfamiliar text.
- That the words add anything **beyond answer length** (a one-feature baseline scores the same within the intervals).
- That **missing context** is the main failure mode: it is higher among errors (11.9% vs 3.0% of controls) but not significantly, and most errors are content judgements a lexical model cannot make. The error judgements were made by an AI assistant as a single unvalidated annotator.
- Anything about **real students or multi-turn tutoring**: no real student turn was used. That is the question for PP2.

## Layout

```
confusion_baseline/   shared package: data, text, prep, split, evaluate, model, probe, rules, artifact, errors
notebooks/            01-09, one per pipeline stage
scripts/              fetch_data.py, train_baseline.py (headless reproduction and checks)
data/                 README committed; data/raw and data/processed are gitignored
models/               clf-v1.0.0/ (pipeline.joblib, metadata.json, rules.yaml)
probe/                ood_probe.yaml (40 frozen items)
reports/experiments/  metrics and annotation CSVs, figures (no dataset text)
```

## Status

Experiment 1 is complete: every number is final and the `clf-v1.0.0` artifact is published and verified. Next: PP2 (conversational context), on real student data.
