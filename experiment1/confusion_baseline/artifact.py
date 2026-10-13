"""Helpers for publishing and verifying the model artifact (models/clf-<version>/)."""

import hashlib
from numbers import Number
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_model_info(info: dict) -> None:
    """Check the block against the frontend's frozen ModelInfo contract (types.ts):
    {version: string, trained_at: string, dataset: string, threshold: number, metrics: Record<string, number>}.
    """
    assert set(info) == {"version", "trained_at", "dataset", "threshold", "metrics"}, sorted(info)
    for k in ("version", "trained_at", "dataset"):
        assert isinstance(info[k], str) and info[k], k
    assert isinstance(info["threshold"], Number) and not isinstance(info["threshold"], bool)
    assert isinstance(info["metrics"], dict) and info["metrics"]
    for k, v in info["metrics"].items():
        assert isinstance(k, str) and isinstance(v, Number) and not isinstance(v, bool), (k, v)
