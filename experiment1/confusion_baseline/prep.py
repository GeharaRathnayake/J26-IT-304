"""Cleaning and label preparation (notebook sections 4 and 5)."""

import pandas as pd

from confusion_baseline import DATA_PROCESSED
from confusion_baseline.text import normalize_key

POS_LABEL = "confused"
LABEL_MAP_PRIMARY = {"Correct": "understood", "Partial Correct": "confused", "Wrong": "confused"}
LABEL_MAP_DROP_PARTIAL = {"Correct": "understood", "Wrong": "confused"}

_LABEL_MAPS = {"primary": LABEL_MAP_PRIMARY, "drop_partial": LABEL_MAP_DROP_PARTIAL}
_DEDUP_KEY = ["Question", "Answer", "Correctness"]


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int, str]]]:
    """Missing-value check, dedup, group key. Returns (clean_df, attrition).

    attrition is a list of (step, rows_after, note). The model consumes the raw Answer
    text, so no text normalisation happens here.
    """
    leaked = [c for c in df.columns if "follow" in c.lower()]
    assert not leaked, leaked
    assert df["row_id"].is_unique, "row_id must be unique"

    attrition = [("loaded (FollowUp already removed)", len(df), f"columns: {list(df.columns)}")]

    required = ["Question", "Answer", "Correctness"]
    n_missing = int(df[required].isna().any(axis=1).sum())
    out = df.dropna(subset=required)
    attrition.append(("missing-value check", len(out), f"{n_missing} rows with a missing {required} value dropped"))

    n_conflicts = int((out.groupby(["Question", "Answer"])["Correctness"].nunique() > 1).sum())
    assert n_conflicts == 0, f"{n_conflicts} (Question, Answer) pairs with conflicting Correctness"

    n_before = len(out)
    out = out.sort_values("row_id").drop_duplicates(subset=_DEDUP_KEY, keep="first")
    attrition.append((
        "dedup on (Question, Answer, Correctness)", len(out),
        f"{n_before - len(out)} duplicate rows dropped, lowest row_id kept; label conflicts = {n_conflicts}",
    ))

    out = out.reset_index(drop=True)
    out["group_key"] = out["Question"].map(normalize_key)
    assert out["row_id"].is_unique
    return out, attrition


def map_labels(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Add `label` ('confused'/'understood') and y = (label == POS_LABEL) as int.

    mode 'primary': Correct -> understood; Partial Correct + Wrong -> confused.
    mode 'drop_partial': Partial Correct rows are removed (count in out.attrs['dropped_partial']).
    """
    mapping = _LABEL_MAPS[mode]
    out = df[df["Correctness"].isin(mapping)].copy()
    out.attrs["dropped_partial"] = len(df) - len(out)
    out["label"] = out["Correctness"].map(mapping)
    assert out["label"].notna().all()
    out["y"] = (out["label"] == POS_LABEL).astype(int)
    return out.reset_index(drop=True)


def save_processed(df: pd.DataFrame, name: str):
    """Write data/processed/<name>.parquet (gitignored) and return the path."""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    path = DATA_PROCESSED / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return path
