"""TF-IDF + Logistic Regression baseline, its fixed hyperparameter grid, and the length-only baseline.

Only sklearn built-ins are used, so a pickled pipeline loads with sklearn alone.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.pipeline import Pipeline

from confusion_baseline import SEED

# Fixed in code before any run.
PARAM_GRID = {
    "tfidf__ngram_range": [(1, 1), (1, 2)],
    "tfidf__min_df": [1, 2],
    "tfidf__stop_words": [None, "english"],
    "tfidf__sublinear_tf": [False, True],
    "clf__C": [0.01, 0.1, 1, 10, 100],
    "clf__class_weight": [None, "balanced"],
}
N_SPLITS = 5


def build_pipeline(**params) -> Pipeline:
    """TfidfVectorizer -> LogisticRegression. Extra keyword params use sklearn's step__param names."""
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="word", lowercase=True)),
        ("clf", LogisticRegression(max_iter=5000, random_state=SEED)),
    ])
    if params:
        pipe.set_params(**params)
    return pipe


def cv_folds(train_df: pd.DataFrame, n_splits: int = N_SPLITS) -> list:
    """Group-aware, stratified folds inside TRAIN: groups = group_key. Returned as a fixed list."""
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    return list(sgkf.split(train_df["Answer"], train_df["y"], groups=train_df["group_key"]))


def cv_search(train_df: pd.DataFrame) -> GridSearchCV:
    """Grid search with group-aware folds. Selection metric is MACRO F1 (refit='macro_f1').

    F1(confused) is also recorded but not used to select: the always-confused predictor already
    scores about 0.75 on it, so selecting on it would reward collapsing to 'confused'.
    """
    search = GridSearchCV(
        build_pipeline(),
        PARAM_GRID,
        scoring={"macro_f1": "f1_macro", "f1_confused": "f1"},
        refit="macro_f1",
        cv=cv_folds(train_df),
        n_jobs=1,
        return_train_score=False,
    )
    return search.fit(train_df["Answer"], train_df["y"])


def token_count(answers: pd.Series) -> np.ndarray:
    """Whitespace token count of Answer (the measure used in the EDA), as an (n, 1) feature."""
    return answers.str.split().str.len().to_numpy(dtype=float).reshape(-1, 1)


def length_baseline(train_df: pd.DataFrame) -> LogisticRegression:
    """Logistic Regression on one feature, token count. No tuning. Not part of the artifact."""
    return LogisticRegression(random_state=SEED).fit(token_count(train_df["Answer"]), train_df["y"])


def save_params(params: dict, path: Path, **meta) -> None:
    """Write chosen hyperparameters as JSON (tuples become lists)."""
    clean = {k: list(v) if isinstance(v, tuple) else v for k, v in params.items()}
    Path(path).write_text(json.dumps({"params": clean, **meta}, indent=2) + "\n", encoding="utf-8")


def load_params(path: Path) -> dict:
    """Read chosen hyperparameters back; ngram_range becomes a tuple again."""
    params = json.loads(Path(path).read_text(encoding="utf-8"))["params"]
    if "tfidf__ngram_range" in params:
        params["tfidf__ngram_range"] = tuple(params["tfidf__ngram_range"])
    return params
