"""Evaluation metrics. The key names go into the model's metadata.json; keep them stable."""

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


def metrics(y_true, y_pred) -> dict:
    """Metrics with the confused class (y == 1) as positive.

    zero_division=0: a constant "understood" predictor never predicts the positive class,
    so its precision is undefined; it is reported as 0.
    """
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_confused": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall_confused": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1_confused": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }
