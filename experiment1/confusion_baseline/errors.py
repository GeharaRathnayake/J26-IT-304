"""Error analysis helpers: the error table, the control sample and the blinded judging sheets."""

import numpy as np
import pandas as pd

from confusion_baseline import SEED


def error_table(test: pd.DataFrame, proba: np.ndarray, threshold: float = 0.5) -> pd.DataFrame:
    """One row per test row: gold, prediction, P(confused), token length, correct flag and error type."""
    out = test[["row_id", "Correctness", "y"]].copy()
    out["pred"] = (proba >= threshold).astype(int)
    out["p_confused"] = proba
    out["tokens"] = test["Answer"].str.split().str.len().to_numpy()
    out["correct"] = out["pred"] == out["y"]
    out["error_type"] = np.where(out["correct"], "", np.where(out["pred"] == 1, "FP", "FN"))
    return out.reset_index(drop=True)


def control_ids(err: pd.DataFrame, n: int, seed: int = SEED) -> list[int]:
    """n correctly classified test row_ids, sampled without replacement (seeded)."""
    ok = np.sort(err.loc[err["correct"], "row_id"].to_numpy())
    rng = np.random.default_rng(seed)
    return sorted(int(i) for i in rng.choice(ok, size=n, replace=False))


def blind_sheet(test: pd.DataFrame, error_ids: list[int], ctrl_ids: list[int], seed: int = SEED) -> pd.DataFrame:
    """Errors and controls shuffled together under opaque item ids (B001, B002, ...).

    Columns: item_id, row_id, set ('error'/'control'), Question, Answer. The judging sheets shown to the
    annotator drop row_id and set; the key stays in data/processed (text is never committed).
    """
    rows = test.set_index("row_id").loc[list(error_ids) + list(ctrl_ids), ["Question", "Answer"]].reset_index()
    rows["set"] = ["error"] * len(error_ids) + ["control"] * len(ctrl_ids)
    order = np.random.default_rng(seed).permutation(len(rows))
    rows = rows.iloc[order].reset_index(drop=True)
    rows.insert(0, "item_id", [f"B{i + 1:03d}" for i in range(len(rows))])
    return rows[["item_id", "row_id", "set", "Question", "Answer"]]
