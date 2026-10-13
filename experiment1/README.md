# Experiment 1: baseline confusion classifier

A baseline classifier (TF-IDF + Logistic Regression) that detects learner confusion in student
messages for an AI Java tutor (J26-IT-304 PP1). It sets the reference point that later experiments
are compared against, and its pickled pipeline is the artifact the tutor service will load.

## Setup

One conda environment is the only environment for this experiment (no `.venv`). Run from this directory:

```
conda env create -f environment.yml
conda run -n exp1-confusion pip install -e .
conda run -n exp1-confusion python -m ipykernel install --user --name exp1-confusion --display-name "Python (exp1-confusion)"
```

`requirements.txt` is the single source of pinned versions. After changing it:
`conda env update -f environment.yml --prune`.
The scikit-learn pin matters most: the model must be unpickled under the version it was trained with.
`PYTHONNOUSERSITE=1` is set (in `environment.yml` and in the kernelspec) because this machine has a user-site Python 3.13 package folder (`AppData\Roaming\Python`) that would otherwise leak into the env and hide unlisted dependencies.
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
