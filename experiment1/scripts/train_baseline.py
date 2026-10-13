"""Reproduce the Experiment 1 result without Jupyter.

What it does: fetches the dataset if missing, then runs the same package functions the notebooks use
(load_raw -> clean -> map_labels("primary") -> group_split(0.2, 42)), asserts the test fingerprint equals the
published artifact's, selects hyperparameters with the full 160-config group-aware grid search (or reuses
chosen_params_primary.json with --skip-search), evaluates the refitted pipeline on the test set once, and
scores the majority, stratified-random and length-only baselines. It then runs 5 checks against the
published artifact and the committed reports, prints PASS/FAIL for each, and exits 1 if any FAIL.

Outputs go ONLY to --out-dir (default: a fresh temp directory): metrics.json, comparison.csv,
chosen_params.json, pipeline.joblib. The script never writes into models/ or reports/ (the dataset fetch,
if needed, writes to the gitignored data/raw/).

Commands (run from experiment1/):
    conda run -n exp1-confusion python scripts/train_baseline.py --skip-search    # fast, a few seconds
    conda run -n exp1-confusion python scripts/train_baseline.py                  # full search, about 2 minutes

Self-test of the checks: `--skip-search --c-override 1.0` perturbs one hyperparameter (C), so check 2 (and
the checks that depend on it) must FAIL and the exit code must be 1.
"""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier

from confusion_baseline import MODELS_DIR, REPORTS_DIR, SEED
from confusion_baseline.data import RAW_DIR, fetch, load_raw
from confusion_baseline.evaluate import metrics
from confusion_baseline.model import build_pipeline, cv_search, length_baseline, load_params, save_params, token_count
from confusion_baseline.prep import clean, map_labels
from confusion_baseline.split import group_split, split_fingerprint

ART = MODELS_DIR / "clf-v1.0.0"
REPORTS = REPORTS_DIR / "experiments"
COLS = {"accuracy": "Accuracy", "precision_confused": "Precision", "recall_confused": "Recall",
        "f1_confused": "F1 (confused)", "macro_f1": "Macro F1"}

results: list[tuple[bool | None, str]] = []


def check(ok: bool | None, label: str) -> None:
    """Record and print one check. ok=None means not applicable in this mode."""
    results.append((ok, label))
    print(("PASS" if ok else "SKIP" if ok is None else "FAIL") + f": {label}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--skip-search", action="store_true", help="use chosen_params_primary.json instead of the grid search")
    ap.add_argument("--out-dir", type=Path, default=None, help="where to write outputs (default: a fresh temp directory)")
    ap.add_argument("--c-override", type=float, default=None,
                    help="SELF-TEST ONLY (needs --skip-search): replace C, so the checks must FAIL")
    args = ap.parse_args()
    if args.c_override is not None and not args.skip_search:
        ap.error("--c-override is a self-test of the checks and requires --skip-search")

    out_dir = (args.out_dir or Path(tempfile.mkdtemp(prefix="exp1_train_"))).resolve()
    for protected in (MODELS_DIR.resolve(), REPORTS_DIR.resolve()):
        if out_dir == protected or protected in out_dir.parents:
            ap.error(f"--out-dir must not be inside {protected.name}/")
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print(f"mode: {'skip-search (chosen_params_primary.json)' if args.skip_search else 'full 160-config group-aware grid search'}"
          + (f"  [SELF-TEST: C overridden to {args.c_override}]" if args.c_override is not None else ""))
    print("outputs ->", out_dir)

    meta = json.loads((ART / "metadata.json").read_text(encoding="utf-8"))

    if not any(RAW_DIR.rglob("*.parquet")):
        print("dataset missing: fetching the pinned revision")
        fetch()
    df, followup_quarantine, _ = load_raw()
    del followup_quarantine                                   # FollowUp leaks the label; never used
    y_primary = map_labels(clean(df)[0], "primary")
    train, test = group_split(y_primary, test_size=0.2, seed=SEED)
    fp = split_fingerprint(test)
    if fp != meta["split"]["test_fingerprint"]:
        print(f"FAIL: test fingerprint {fp} != metadata {meta['split']['test_fingerprint']}")
        return 1
    print(f"split: train {len(train)} rows, test {len(test)} rows; test fingerprint matches the published artifact")

    # ---- model: full search, or the saved params ----
    published_params = load_params(REPORTS / "chosen_params_primary.json")
    if args.skip_search:
        params = dict(published_params)
        if args.c_override is not None:
            params["clf__C"] = args.c_override
        final = build_pipeline(**params).fit(train["Answer"], train["y"])
    else:
        search = cv_search(train)
        params = search.best_params_
        final = search.best_estimator_
    print("hyperparameters:", params)

    # ---- the one test evaluation, plus the baselines ----
    y_te = test["y"].to_numpy()
    X0_tr, X0_te = np.zeros((len(train), 1)), np.zeros((len(test), 1))
    maj = DummyClassifier(strategy="most_frequent").fit(X0_tr, train["y"])
    rnd = DummyClassifier(strategy="stratified", random_state=SEED).fit(X0_tr, train["y"])
    len_clf = length_baseline(train)
    m_model = metrics(y_te, final.predict(test["Answer"]))
    systems = {
        "Majority class": metrics(y_te, maj.predict(X0_te)),
        "Stratified random (seed 42)": metrics(y_te, rnd.predict(X0_te)),
        "Length-only LR": metrics(y_te, len_clf.predict(token_count(test["Answer"]))),
        "TF-IDF + LR": m_model,
    }
    comparison = pd.DataFrame([{"System": n, **{COLS[k]: round(v, 4) for k, v in m.items()}} for n, m in systems.items()])
    print("\ncomparison (test):")
    print(comparison.to_string(index=False))
    print()

    # ---- outputs (out-dir only) ----
    (out_dir / "metrics.json").write_text(json.dumps(m_model, indent=2) + "\n", encoding="utf-8")
    comparison.to_csv(out_dir / "comparison.csv", index=False)
    save_params(params, out_dir / "chosen_params.json", selection_metric="macro_f1", run="train_baseline.py")
    joblib.dump(final, out_dir / "pipeline.joblib")

    # ---- checks ----
    check(None if args.skip_search else params == published_params,
          "1. chosen params equal chosen_params_primary.json" + (" (full-search mode only: not applicable)" if args.skip_search else ""))
    check(m_model == meta["metrics"], "2. test metrics equal models/clf-v1.0.0/metadata.json['metrics'] exactly (5 keys)")
    saved = pd.read_csv(REPORTS / "comparison_primary.csv")
    check(list(saved["System"]) == list(comparison["System"])
          and np.allclose(saved[list(COLS.values())].to_numpy(), comparison[list(COLS.values())].to_numpy(), rtol=0, atol=5e-5),
          "3. the comparison table equals reports/experiments/comparison_primary.csv to 4 decimals")
    # Behaviour, not bytes: a rebuild of the same model pickles to different bytes, so hashes are NOT compared.
    published = joblib.load(ART / "pipeline.joblib")
    check(bool(np.allclose(final.predict_proba(test["Answer"]), published.predict_proba(test["Answer"]), rtol=0, atol=1e-12)),
          "4. predict_proba on test equals the published pipeline.joblib's (np.allclose, atol 1e-12)")
    check(sklearn.__version__ == meta["runtime"]["scikit_learn"],
          f"5. scikit-learn {sklearn.__version__} equals metadata runtime {meta['runtime']['scikit_learn']}")

    failed = [label for ok, label in results if ok is False]
    print(f"\n{sum(ok is True for ok, _ in results)} passed, {len(failed)} failed, {sum(ok is None for ok, _ in results)} not applicable"
          f" | elapsed {time.time() - t0:.1f} s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
