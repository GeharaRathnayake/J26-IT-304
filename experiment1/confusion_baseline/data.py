"""Fetch and load JavaQuestionSynthFinal at a pinned revision."""

import json
from pathlib import Path

import pandas as pd
from huggingface_hub import snapshot_download

from confusion_baseline import DATA_RAW

DATASET_REPO = "nitinnovtech-ai-space/JavaQuestionSynthFinal"
DATASET_MIRROR = "Pragades/JavaQuestionSynthFinal"
# Commit SHA resolved 2026-10-13; the mirror resolved to the same SHA.
DATASET_REVISION = "e29cfdd4ec4179f54b2ea0409329207104de8bed"

RAW_DIR = DATA_RAW / "JavaQuestionSynthFinal"


def fetch() -> Path:
    """Download the dataset snapshot at DATASET_REVISION into data/raw. Idempotent."""
    path = snapshot_download(
        repo_id=DATASET_REPO,
        repo_type="dataset",
        revision=DATASET_REVISION,
        local_dir=RAW_DIR,
    )
    return Path(path)


def _is_followup(name: str) -> bool:
    return "followup" in name.lower().replace(" ", "").replace("_", "")


def load_raw() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load the raw parquet and split off the leaking FollowUp field.

    Returns (df, followup_quarantine, load_report). ``row_id`` (position in the raw file)
    is assigned before anything else and is the stable key for all later units. ``df``
    contains no FollowUp-derived column; those live only in ``followup_quarantine``.
    """
    files = sorted(RAW_DIR.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet under {RAW_DIR}; run scripts/fetch_data.py")
    raw = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    raw.insert(0, "row_id", range(len(raw)))

    followup_cols = [c for c in raw.columns if _is_followup(c)]
    parts = [raw[["row_id"]]]
    for col in followup_cols:
        # A struct column arrives in pandas as one dict per row.
        flat = pd.DataFrame(raw[col].tolist(), index=raw.index).add_prefix("followup_")
        parts.append(flat)
    followup_quarantine = pd.concat(parts, axis=1)

    # Duplicates on the FULL raw record, FollowUp included (dict cells are unhashable,
    # so serialise them for the comparison only).
    record = raw.drop(columns="row_id").copy()
    for col in followup_cols:
        record[col] = record[col].map(lambda v: json.dumps(v, sort_keys=True))
    load_report = {
        "format": ", ".join(sorted({f.suffix.lstrip(".") for f in files})),
        "files": [f.relative_to(RAW_DIR).as_posix() for f in files],
        "rows_raw": len(raw),
        "raw_columns": [c for c in raw.columns if c != "row_id"],
        "followup_columns_raw": followup_cols,
        "followup_structure": {c: type(raw[c].iloc[0]).__name__ for c in followup_cols},
        "duplicates_full_record_incl_followup": int(record.duplicated().sum()),
    }

    df = raw.drop(columns=followup_cols)
    return df, followup_quarantine, load_report
