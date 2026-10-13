"""Shared code for Experiment 1: baseline confusion classifier."""

from pathlib import Path

SEED = 42

EXP_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = EXP_ROOT / "data" / "raw"
DATA_PROCESSED = EXP_ROOT / "data" / "processed"
MODELS_DIR = EXP_ROOT / "models"
REPORTS_DIR = EXP_ROOT / "reports"
PROBE_DIR = EXP_ROOT / "probe"
