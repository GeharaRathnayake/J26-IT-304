"""Load, verify and sanity-check the confusion-classifier artifact.

HONESTY CAVEAT: the classifier is a *prototype component*. It is a TF-IDF +
LogisticRegression pipeline trained on a SYNTHETIC dataset, where "not fully
correct answer" is used as a proxy for "confused". It separates correct from
not-fully-correct synthetic answers; it has never seen a real student message
and is not a validated confusion detector (it scores "that makes sense" at
~0.99 confused).

Loading is strict: every failure raises ModelLoadError, with no
warning-and-continue. The caller (the app lifespan) decides what to do with it;
a model that failed any check must never be stored or used.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import sklearn

from app.classifier.errors import ModelLoadError
from app.classifier.rules import Rules, parse_rules

logger = logging.getLogger(__name__)

# --- Class-order assertion inputs ------------------------------------------------
# These catch the disaster this stage exists to prevent: P(confused) read from the
# wrong column (swapped index), a corrupt file, or the wrong model directory. Any
# of these makes the whole tutor invert while still appearing to work.
# Both strings are hand-written and used RAW (no lowercasing/stripping). Nothing
# here comes from the experiment1 dataset or notebooks (unlicensed, gitignored).
CORRECT_TEXT = "A for loop repeats a block of code while its condition is true."
CONFUSED_TEXT = "i dont get it"
ASSERT_BOUND = 0.5  # correct must score < bound; confused must score > bound
# ---------------------------------------------------------------------------------

# The only column layout this service supports; the metadata must say so.
EXPECTED_PROBA_INDEX_CONFUSED = 1


@dataclass(frozen=True)
class LoadedModel:
    pipeline: Any
    metadata: dict
    version: str
    threshold: float
    proba_index_confused: int
    rules: Rules

    def predict_confused(self, text: str) -> float:
        """P(confused) for raw text. Proxy score from a synthetic-data classifier."""
        return float(self.pipeline.predict_proba([text])[0, self.proba_index_confused])


def _sha256(data: bytes) -> str:
    # Raw bytes for every file, so `sha256sum` gives the published value. A
    # line-ending rewrite (e.g. core.autocrlf) is therefore caught, not tolerated;
    # backend/.gitattributes (`models/** -text`) stops Git doing that.
    return hashlib.sha256(data).hexdigest()


def assert_class_order(
    predict_confused: Callable[[str], float],
    correct_text: str = CORRECT_TEXT,
    confused_text: str = CONFUSED_TEXT,
    bound: float = ASSERT_BOUND,
) -> dict[str, float]:
    """Raise ModelLoadError unless the predictor has the right way round.

    Returns the measured scores and prediction durations (ms), for logging only;
    timings are never asserted on.
    """
    t0 = time.perf_counter()
    p_correct = float(predict_confused(correct_text))
    t1 = time.perf_counter()
    p_confused = float(predict_confused(confused_text))
    t2 = time.perf_counter()
    logger.info(
        "class-order check: correct sentence P(confused)=%.4f (%.1f ms); "
        "'%s' P(confused)=%.4f (%.1f ms)",
        p_correct, (t1 - t0) * 1000, confused_text, p_confused, (t2 - t1) * 1000,
    )
    if not p_correct < bound:
        raise ModelLoadError(
            f"class-order assertion failed: plainly correct sentence scored "
            f"P(confused)={p_correct:.4f}, expected < {bound}. Swapped index, "
            f"corrupt file or wrong model directory."
        )
    if not p_confused > bound:
        raise ModelLoadError(
            f"class-order assertion failed: {confused_text!r} scored "
            f"P(confused)={p_confused:.4f}, expected > {bound}. Swapped index, "
            f"corrupt file or wrong model directory."
        )
    return {
        "p_correct": p_correct,
        "p_confused": p_confused,
        "correct_ms": (t1 - t0) * 1000,
        "confused_ms": (t2 - t1) * 1000,
    }


def load_model(model_dir: Path) -> LoadedModel:
    """Load and verify a model directory. Raises ModelLoadError on any failure."""
    started = time.perf_counter()
    model_dir = Path(model_dir)

    # 1. metadata
    meta_path = model_dir / "metadata.json"
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        expected_sklearn = metadata["runtime"]["scikit_learn"]
        expected_hashes: dict[str, str] = metadata["files"]
        proba_index = metadata["input"]["proba_index_confused"]
        version = metadata["version"]
        threshold = float(metadata["threshold"])
    except (OSError, ValueError, KeyError) as exc:
        raise ModelLoadError(f"cannot read metadata {meta_path}: {exc!r}") from exc

    # 2. scikit-learn version must match exactly
    if sklearn.__version__ != expected_sklearn:
        raise ModelLoadError(
            f"scikit-learn version mismatch: running {sklearn.__version__}, "
            f"artifact requires exactly {expected_sklearn}"
        )

    # 3. hash both files BEFORE unpickling or parsing anything. Each is read once;
    #    Both files are later used from these same bytes (rules.yaml is parsed,
    #    pipeline.joblib is unpickled from memory), so neither can change between
    #    check and use.
    file_bytes: dict[str, bytes] = {}
    for name in ("pipeline.joblib", "rules.yaml"):
        path = model_dir / name
        try:
            file_bytes[name] = path.read_bytes()
        except OSError as exc:
            raise ModelLoadError(f"cannot read {name}: {exc!r}") from exc
        actual = _sha256(file_bytes[name])
        expected = expected_hashes.get(name)
        if actual != expected:
            raise ModelLoadError(
                f"hash mismatch for {name}: expected sha256={expected}, actual sha256={actual}"
            )
        logger.info("hash OK %s sha256=%s", name, actual)

    # 3b. parse the rule layer from the bytes that were just hashed
    rules = parse_rules(file_bytes["rules.yaml"])
    logger.info(
        "rules %s: %d confusion, %d understanding",
        rules.version, len(rules.confusion_phrases), len(rules.understanding_phrases),
    )

    # 4. only now unpickle, from the verified bytes, never by re-opening the file
    try:
        pipeline = joblib.load(io.BytesIO(file_bytes["pipeline.joblib"]))
    except Exception as exc:  # unpickling can raise almost anything
        raise ModelLoadError(f"cannot unpickle pipeline.joblib: {exc!r}") from exc

    # 5. column index comes from the metadata
    if proba_index != EXPECTED_PROBA_INDEX_CONFUSED:
        raise ModelLoadError(
            f"metadata proba_index_confused={proba_index!r}, "
            f"expected {EXPECTED_PROBA_INDEX_CONFUSED}"
        )
    classes = [int(c) for c in getattr(pipeline, "classes_", [])]
    logger.info("pipeline classes_=%s proba_index_confused=%d", classes, proba_index)
    if len(classes) != 2:
        raise ModelLoadError(f"expected 2 classes, pipeline has {classes}")

    model = LoadedModel(
        pipeline=pipeline,
        metadata=metadata,
        version=version,
        threshold=threshold,
        proba_index_confused=proba_index,
        rules=rules,
    )

    # 6. class-order assertion on raw text
    assert_class_order(model.predict_confused)

    logger.info(
        "model %s loaded and verified in %.1f ms (threshold=%s; prototype proxy "
        "classifier trained on synthetic data)",
        version, (time.perf_counter() - started) * 1000, threshold,
    )
    return model
