"""Group-aware train/test split. All rows of one question stay on one side."""

import hashlib

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from confusion_baseline import SEED


def group_split(df: pd.DataFrame, test_size: float = 0.2, seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """GroupShuffleSplit on df.group_key (n_splits=1). NOT stratified.

    test_size is a fraction of GROUPS, so the test ROW share is not exactly test_size.
    """
    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(gss.split(df, groups=df["group_key"]))
    return df.iloc[train_idx].reset_index(drop=True), df.iloc[test_idx].reset_index(drop=True)


def apply_split(df: pd.DataFrame, test_groups) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assign rows to train/test by group_key membership in test_groups."""
    in_test = df["group_key"].isin(set(test_groups))
    return df[~in_test].reset_index(drop=True), df[in_test].reset_index(drop=True)


def split_fingerprint(test_df: pd.DataFrame) -> str:
    """sha256 of the sorted unique test group keys, newline-joined, UTF-8."""
    payload = "\n".join(sorted(test_df["group_key"].unique())).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
