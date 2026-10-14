from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


@dataclass
class SoftmaxClassifier:
    feature_names: list[str]
    mean_: np.ndarray | None = None
    scale_: np.ndarray | None = None
    weights_: np.ndarray | None = None

    def fit(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        seed: int,
        steps: int = 1400,
        learning_rate: float = 0.025,
        batch_size: int = 512,
        l2: float = 0.001,
        high_class_weight: float = 1.6,
    ) -> "SoftmaxClassifier":
        rng = np.random.default_rng(seed)
        self.mean_ = x.mean(axis=0)
        self.scale_ = x.std(axis=0)
        self.scale_[self.scale_ < 1e-8] = 1.0
        normalized = (x - self.mean_) / self.scale_
        design = np.column_stack([np.ones(len(normalized)), normalized])
        classes = int(y.max()) + 1
        self.weights_ = rng.normal(0.0, 0.01, size=(design.shape[1], classes))
        first_moment = np.zeros_like(self.weights_)
        second_moment = np.zeros_like(self.weights_)
        class_weights = np.ones(classes, dtype=float)
        class_weights[-1] = high_class_weight

        for step in range(1, steps + 1):
            indices = rng.choice(len(design), size=min(batch_size, len(design)), replace=False)
            batch_x = design[indices]
            batch_y = y[indices]
            probabilities = _softmax(batch_x @ self.weights_)
            target = np.zeros_like(probabilities)
            target[np.arange(len(batch_y)), batch_y] = 1.0
            sample_weights = class_weights[batch_y][:, None]
            gradient = batch_x.T @ ((probabilities - target) * sample_weights) / sample_weights.sum()
            gradient[1:] += l2 * self.weights_[1:]

            first_moment = 0.9 * first_moment + 0.1 * gradient
            second_moment = 0.999 * second_moment + 0.001 * (gradient * gradient)
            corrected_first = first_moment / (1 - 0.9**step)
            corrected_second = second_moment / (1 - 0.999**step)
            self.weights_ -= learning_rate * corrected_first / (np.sqrt(corrected_second) + 1e-8)
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.scale_ is None or self.weights_ is None:
            raise RuntimeError("Model is not fitted")
        normalized = (x - self.mean_) / self.scale_
        design = np.column_stack([np.ones(len(normalized)), normalized])
        return _softmax(design @ self.weights_)

    def save(self, path: str | Path, metadata: dict[str, Any]) -> None:
        if self.mean_ is None or self.scale_ is None or self.weights_ is None:
            raise RuntimeError("Model is not fitted")
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            output,
            mean=self.mean_,
            scale=self.scale_,
            weights=self.weights_,
            feature_names=np.array(self.feature_names, dtype=object),
            metadata=np.array([json.dumps(metadata, ensure_ascii=False)], dtype=object),
        )


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, classes: int = 3) -> np.ndarray:
    matrix = np.zeros((classes, classes), dtype=int)
    for truth, prediction in zip(y_true, y_pred):
        matrix[int(truth), int(prediction)] += 1
    return matrix


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _rank_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = y_true.astype(int)
    positives = int(y.sum())
    negatives = len(y) - positives
    if positives == 0 or negatives == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=float)
    start = 0
    while start < len(scores):
        end = start + 1
        while end < len(scores) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        ranks[order[start:end]] = average_rank
        start = end
    positive_rank_sum = ranks[y == 1].sum()
    return float((positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives))


def _pr_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(-scores, kind="mergesort")
    y = y_true[order].astype(int)
    positives = int(y.sum())
    if positives == 0:
        return float("nan")
    true_positive = np.cumsum(y)
    false_positive = np.cumsum(1 - y)
    recall = true_positive / positives
    precision = true_positive / np.maximum(true_positive + false_positive, 1)
    recall = np.concatenate([[0.0], recall])
    precision = np.concatenate([[1.0], precision])
    return float(np.trapezoid(precision, recall))


def tune_high_risk_threshold(
    y_true: np.ndarray, probabilities: np.ndarray, target_recall: float = 0.95
) -> dict[str, float]:
    binary_true = (y_true == 2).astype(int)
    candidates: list[dict[str, float]] = []
    for threshold in np.linspace(0.02, 0.98, 97):
        predicted = probabilities[:, 2] >= threshold
        tp = int(((predicted == 1) & (binary_true == 1)).sum())
        fp = int(((predicted == 1) & (binary_true == 0)).sum())
        fn = int(((predicted == 0) & (binary_true == 1)).sum())
        recall = _safe_divide(tp, tp + fn)
        precision = _safe_divide(tp, tp + fp)
        candidates.append({"threshold": float(threshold), "recall": recall, "precision": precision})
    feasible = [row for row in candidates if row["recall"] >= target_recall]
    if feasible:
        return max(feasible, key=lambda row: (row["precision"], row["threshold"]))
    return max(candidates, key=lambda row: (row["recall"], row["precision"]))


def evaluate_probabilities(
    y_true: np.ndarray, probabilities: np.ndarray, high_threshold: float
) -> dict[str, Any]:
    y_pred = probabilities.argmax(axis=1)
    matrix = confusion_matrix(y_true, y_pred, classes=3)
    class_names = ["low", "typical", "high"]
    class_results: dict[str, dict[str, float | int]] = {}
    for class_id, name in enumerate(class_names):
        tp = int(matrix[class_id, class_id])
        fp = int(matrix[:, class_id].sum() - tp)
        fn = int(matrix[class_id, :].sum() - tp)
        precision = _safe_divide(tp, tp + fp)
        recall = _safe_divide(tp, tp + fn)
        f1 = _safe_divide(2 * precision * recall, precision + recall)
        class_results[name] = {
            "support": int(matrix[class_id, :].sum()),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    high_true = (y_true == 2).astype(int)
    high_pred = (probabilities[:, 2] >= high_threshold).astype(int)
    tp = int(((high_pred == 1) & (high_true == 1)).sum())
    tn = int(((high_pred == 0) & (high_true == 0)).sum())
    fp = int(((high_pred == 1) & (high_true == 0)).sum())
    fn = int(((high_pred == 0) & (high_true == 1)).sum())
    high_precision = _safe_divide(tp, tp + fp)
    high_recall = _safe_divide(tp, tp + fn)
    high_f1 = _safe_divide(2 * high_precision * high_recall, high_precision + high_recall)
    clipped = np.clip(probabilities[np.arange(len(y_true)), y_true], 1e-12, 1.0)

    return {
        "samples": int(len(y_true)),
        "accuracy": float((y_pred == y_true).mean()),
        "macro_f1": float(np.mean([row["f1"] for row in class_results.values()])),
        "multiclass_log_loss": float(-np.log(clipped).mean()),
        "confusion_matrix": matrix.tolist(),
        "per_class": class_results,
        "high_risk": {
            "threshold": float(high_threshold),
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "precision": high_precision,
            "recall": high_recall,
            "specificity": _safe_divide(tn, tn + fp),
            "false_negative_rate": _safe_divide(fn, fn + tp),
            "f1": high_f1,
            "roc_auc": _rank_auc(high_true, probabilities[:, 2]),
            "pr_auc": _pr_auc(high_true, probabilities[:, 2]),
            "brier": float(np.mean((probabilities[:, 2] - high_true) ** 2)),
        },
    }

