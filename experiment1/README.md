# Experiment 1: baseline confusion classifier

A baseline classifier (TF-IDF + Logistic Regression) that detects learner confusion in student
messages for an AI Java tutor (J26-IT-304 PP1). It sets the reference point that later experiments
are compared against, and its pickled pipeline is the artifact the tutor service will load.

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
`--env PYTHONNOUSERSITE 1` because Jupyter does not go through conda activation.

`requirements.txt` is the single source of pinned versions. After changing it, with the variable set:
`conda env update -f environment.yml --prune`.
The scikit-learn pin matters most: the model must be unpickled under the version it was trained with.
Notebooks use the kernel `exp1-confusion` and import `confusion_baseline` via the editable install,
with no `sys.path` edits.

## Layout

```
confusion_baseline/   shared package (loading, cleaning, splitting, evaluation)
notebooks/            analysis notebooks
scripts/              scripts, e.g. train_baseline.py
data/                 README committed; data/raw and data/processed are gitignored
models/               trained artifacts: models/clf-*/pipeline.joblib
probe/                probe inputs and outputs
reports/experiments/  metrics CSVs and reports
```

## Status

Status: U0 scaffold
