"""Loader for the frozen out-of-distribution probe set (probe/ood_probe.yaml)."""

import hashlib

import pandas as pd
import yaml

from confusion_baseline import PROBE_DIR

PROBE_PATH = PROBE_DIR / "ood_probe.yaml"


def load_probe(path=PROBE_PATH) -> pd.DataFrame:
    """Return DataFrame [id, text, expected, category, y]; y = 1 for expected == 'confused'."""
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    df = pd.DataFrame(doc["items"])[["id", "text", "expected", "category"]]
    assert df["id"].is_unique
    assert set(df["expected"]) <= {"confused", "understood"}
    df["y"] = (df["expected"] == "confused").astype(int)
    return df


def probe_sha256(path=PROBE_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
