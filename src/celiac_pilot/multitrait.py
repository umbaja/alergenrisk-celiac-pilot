from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .ml import SoftmaxClassifier


PROFILE_ORDER = ("complete", "23andme_like", "myheritage_like", "dnaera_like", "sparse_stress")


def load_trait_bundle(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    ids = [trait["id"] for trait in payload.get("traits", [])]
    if ids != ["egg", "peanut", "milk", "shared", "lactose", "histamine"]:
        raise ValueError(f"Unexpected trait order: {ids}")
    for trait in payload["traits"]:
        locus_ids = [row["id"] for row in trait["loci"]]
        if len(locus_ids) != len(set(locus_ids)):
            raise ValueError(f"Duplicate marker in {trait['id']}")
        for locus in trait["loci"]:
            frequency = locus.get("eur_frequency", locus.get("simulation_frequency"))
            if frequency is None or not 0 < float(frequency) < 1:
                raise ValueError(f"Invalid simulation frequency for {trait['id']} / {locus['id']}")
    payload["_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    payload["_path"] = str(source.resolve())
    return payload


def _frequency(locus: dict[str, Any]) -> float:
    value = locus.get("eur_frequency")
    return float(value if value is not None else locus["simulation_frequency"])


def _corrupt(values: np.ndarray, accuracy: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    result = values.astype(float).copy()
    wrong = rng.random(values.size) > accuracy
    if wrong.any():
        current = result[wrong].astype(int)
        alternatives = np.array([[1, 2], [0, 2], [0, 1]], dtype=int)
        pick = rng.integers(0, 2, size=len(current))
        result[wrong] = alternatives[current, pick]
    return result


def _band_for_count(count: int, trait: dict[str, Any]) -> tuple[int, str]:
    if trait["id"] == "lactose":
        return (1, "nonpersistent") if count == 2 else (0, "persistent")
    for class_id, label in enumerate(trait["classes"]):
        low, high = trait["bands"][label]
        if low <= count <= high:
            return class_id, label
    raise ValueError(f"No band for score {count} in {trait['id']}")


def generate_trait_dataset(
    trait: dict[str, Any], profiles_config: dict[str, Any], n_samples: int, seed: int
) -> pd.DataFrame:
    if n_samples < 300:
        raise ValueError("Use at least 300 synthetic samples")
    rng = np.random.default_rng(seed)
    profile_names = np.array(list(profiles_config), dtype=object)
    profile_weights = np.array([profiles_config[name]["weight"] for name in profile_names], dtype=float)
    profile_weights /= profile_weights.sum()
    profiles = rng.choice(profile_names, size=n_samples, p=profile_weights)
    data: dict[str, Any] = {
        "sample_id": [f"{trait['id'].upper()}-{index + 1:08d}" for index in range(n_samples)],
        "trait_id": np.full(n_samples, trait["id"], dtype=object),
        "generation_seed": np.full(n_samples, seed, dtype=int),
        "chip_profile": profiles,
    }
    true_count = np.zeros(n_samples, dtype=int)
    true_weighted = np.zeros(n_samples, dtype=float)
    observed_count = np.zeros(n_samples, dtype=int)
    direct_count = np.zeros(n_samples, dtype=int)
    proxy_count = np.zeros(n_samples, dtype=int)
    population_count = np.zeros(n_samples, dtype=int)
    missing_count = np.zeros(n_samples, dtype=int)

    for locus in trait["loci"]:
        marker = locus["id"]
        frequency = _frequency(locus)
        truth = rng.binomial(2, frequency, size=n_samples)
        call_rate = np.array([profiles_config[p]["direct_call_rate"] for p in profiles], dtype=float)
        proxy_rate = np.array([profiles_config[p]["proxy_recovery_rate"] for p in profiles], dtype=float)
        profile_accuracy = np.array([profiles_config[p]["proxy_accuracy"] for p in profiles], dtype=float)
        proxies = locus.get("proxies", [])
        required_proxy = bool(locus.get("required_proxy"))
        direct = np.zeros(n_samples, dtype=bool) if required_proxy else rng.random(n_samples) < call_rate
        if required_proxy:
            proxy = rng.random(n_samples) < call_rate
        else:
            proxy = (~direct) & bool(proxies) & (rng.random(n_samples) < proxy_rate)
        unresolved = ~(direct | proxy)
        population_allowed = trait["missing_policy"] == "population-expectation-for-ML-only"
        population = unresolved if population_allowed else np.zeros(n_samples, dtype=bool)
        missing = np.zeros(n_samples, dtype=bool) if population_allowed else unresolved

        observed = np.full(n_samples, 2 * frequency, dtype=float)
        quality = np.zeros(n_samples, dtype=float)
        source = np.full(n_samples, "missing", dtype=object)
        observed[direct] = truth[direct]
        quality[direct] = 1.0
        source[direct] = "direct"
        if proxy.any():
            proxy_r2 = float(proxies[0]["r2"])
            accuracy = np.minimum(profile_accuracy[proxy], max(0.50, proxy_r2))
            observed[proxy] = _corrupt(truth[proxy], accuracy, rng)
            quality[proxy] = proxy_r2
            source[proxy] = "proxy"
        source[population] = "population"

        data[f"true_{marker}"] = truth
        data[f"obs_{marker}"] = observed
        data[f"quality_{marker}"] = quality
        data[f"source_{marker}"] = source
        true_count += truth
        true_weighted += truth * float(locus["beta"])
        observed_count += np.where(direct | proxy, np.rint(observed), 0).astype(int)
        direct_count += direct
        proxy_count += proxy
        population_count += population
        missing_count += missing

    labels = [_band_for_count(int(value), trait) for value in true_count]
    locus_count = len(trait["loci"])
    data.update(
        {
            "oracle_genetic_score": true_count,
            "oracle_weighted_score": np.round(true_weighted, 6),
            "observed_integer_score": observed_count,
            "oracle_class": np.array([item[0] for item in labels], dtype=int),
            "oracle_label": np.array([item[1] for item in labels], dtype=object),
            "direct_count": direct_count,
            "proxy_count": proxy_count,
            "population_imputed_count": population_count,
            "missing_count": missing_count,
            "coverage_fraction": (direct_count + proxy_count) / locus_count,
        }
    )
    return pd.DataFrame(data)


def assign_trait_splits(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 1)
    split = np.empty(len(frame), dtype=object)
    for class_id in sorted(frame["oracle_class"].unique()):
        indices = frame.index[frame["oracle_class"] == class_id].to_numpy(copy=True)
        rng.shuffle(indices)
        train_end = int(len(indices) * 0.60)
        validation_end = int(len(indices) * 0.80)
        split[indices[:train_end]] = "train"
        split[indices[train_end:validation_end]] = "validation"
        split[indices[validation_end:]] = "test"
    result = frame.copy()
    result["split"] = split
    return result


def trait_feature_matrix(
    frame: pd.DataFrame, trait: dict[str, Any], feature_set: str, profiles_config: dict[str, Any]
) -> tuple[np.ndarray, list[str]]:
    ids = [row["id"] for row in trait["loci"]]
    if feature_set == "baseline":
        lead = ids[0]
        names = [f"obs_{lead}", f"quality_{lead}", "coverage_fraction"]
        return frame[names].to_numpy(dtype=float), names
    observed_names = [f"obs_{marker}" for marker in ids]
    quality_names = [f"quality_{marker}" for marker in ids]
    profile_names = [f"profile_{name}" for name in profiles_config]
    profile_matrix = np.column_stack(
        [(frame["chip_profile"].to_numpy() == name).astype(float) for name in profiles_config]
    )
    base = np.column_stack(
        [frame[observed_names].to_numpy(dtype=float), frame[quality_names].to_numpy(dtype=float), profile_matrix]
    )
    names = observed_names + quality_names + profile_names
    if feature_set == "additive":
        return base, names
    if feature_set != "structured":
        raise ValueError(f"Unknown feature set: {feature_set}")
    extras: list[np.ndarray] = []
    extra_names: list[str] = []
    for left, right in combinations(ids, 2):
        extras.append(frame[f"obs_{left}"].to_numpy(dtype=float) * frame[f"obs_{right}"].to_numpy(dtype=float))
        extra_names.append(f"interaction_{left}_{right}")
    beta = np.array([float(row["beta"]) for row in trait["loci"]], dtype=float)
    weighted = frame[observed_names].to_numpy(dtype=float) @ beta
    extras.extend([weighted, weighted * (1 - frame["coverage_fraction"].to_numpy(dtype=float))])
    extra_names.extend(["aggregate_weighted_score", "interaction_missingness_x_weighted_score"])
    return np.column_stack([base, *extras]), names + extra_names


def _safe(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _binary_auc(y: np.ndarray, scores: np.ndarray) -> float:
    positives = int(y.sum())
    negatives = len(y) - positives
    if not positives or not negatives:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=float)
    start = 0
    while start < len(scores):
        end = start + 1
        while end < len(scores) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2
        start = end
    return float((ranks[y == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives))


def _pr_auc(y: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(-scores, kind="mergesort")
    ranked = y[order].astype(int)
    positives = int(ranked.sum())
    if not positives:
        return float("nan")
    tp = np.cumsum(ranked)
    fp = np.cumsum(1 - ranked)
    recall = np.concatenate([[0.0], tp / positives])
    precision = np.concatenate([[1.0], tp / np.maximum(tp + fp, 1)])
    return float(np.trapezoid(precision, recall))


def tune_high_threshold(y: np.ndarray, probabilities: np.ndarray, target_recall: float = 0.95) -> dict[str, float]:
    high_id = probabilities.shape[1] - 1
    truth = (y == high_id).astype(int)
    rows = []
    for threshold in np.linspace(0.02, 0.98, 97):
        predicted = probabilities[:, high_id] >= threshold
        tp = int(((predicted == 1) & (truth == 1)).sum())
        fp = int(((predicted == 1) & (truth == 0)).sum())
        fn = int(((predicted == 0) & (truth == 1)).sum())
        rows.append({"threshold": float(threshold), "recall": _safe(tp, tp + fn), "precision": _safe(tp, tp + fp)})
    feasible = [row for row in rows if row["recall"] >= target_recall]
    if feasible:
        return max(feasible, key=lambda row: (row["precision"], row["threshold"]))
    return max(rows, key=lambda row: (row["recall"], row["precision"], row["threshold"]))


def evaluate_trait(y: np.ndarray, probabilities: np.ndarray, threshold: float, labels: list[str]) -> dict[str, Any]:
    predicted = probabilities.argmax(axis=1)
    count = len(labels)
    matrix = np.zeros((count, count), dtype=int)
    for truth, guess in zip(y, predicted):
        matrix[int(truth), int(guess)] += 1
    per_class: dict[str, Any] = {}
    for class_id, label in enumerate(labels):
        tp = int(matrix[class_id, class_id])
        fp = int(matrix[:, class_id].sum() - tp)
        fn = int(matrix[class_id].sum() - tp)
        precision = _safe(tp, tp + fp)
        recall = _safe(tp, tp + fn)
        per_class[label] = {
            "support": int(matrix[class_id].sum()),
            "precision": precision,
            "recall": recall,
            "f1": _safe(2 * precision * recall, precision + recall),
        }
    high_id = count - 1
    high_truth = (y == high_id).astype(int)
    high_guess = (probabilities[:, high_id] >= threshold).astype(int)
    tp = int(((high_guess == 1) & (high_truth == 1)).sum())
    tn = int(((high_guess == 0) & (high_truth == 0)).sum())
    fp = int(((high_guess == 1) & (high_truth == 0)).sum())
    fn = int(((high_guess == 0) & (high_truth == 1)).sum())
    clipped = np.clip(probabilities[np.arange(len(y)), y], 1e-12, 1.0)
    return {
        "samples": int(len(y)),
        "accuracy": float((predicted == y).mean()),
        "macro_f1": float(np.mean([row["f1"] for row in per_class.values()])),
        "multiclass_log_loss": float(-np.log(clipped).mean()),
        "confusion_matrix": matrix.tolist(),
        "per_class": per_class,
        "high_risk": {
            "label": labels[-1],
            "threshold": float(threshold),
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "precision": _safe(tp, tp + fp),
            "recall": _safe(tp, tp + fn),
            "specificity": _safe(tn, tn + fp),
            "false_negative_rate": _safe(fn, fn + tp),
            "roc_auc": _binary_auc(high_truth, probabilities[:, high_id]),
            "pr_auc": _pr_auc(high_truth, probabilities[:, high_id]),
            "brier": float(np.mean((probabilities[:, high_id] - high_truth) ** 2)),
        },
    }


def reference_distribution(trait: dict[str, Any]) -> list[list[float]]:
    distribution = np.array([1.0])
    for locus in trait["loci"]:
        p = _frequency(locus)
        distribution = np.convolve(distribution, np.array([(1 - p) ** 2, 2 * p * (1 - p), p**2]))
    return [[int(score), float(probability)] for score, probability in enumerate(distribution)]


def run_multitrait_pipeline(
    project_root: str | Path, *, samples_per_trait: int = 6000, seed: int = 20261014, training_steps: int = 900
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    bundle = load_trait_bundle(root / "config" / "trait_models_v1.json")
    overview: dict[str, Any] = {
        "bundle_id": bundle["bundle_id"],
        "model_version": bundle["model_version"],
        "manifest_sha256": bundle["_sha256"],
        "clinical_validation": False,
        "seed": seed,
        "traits": {},
        "limitations": [
            "Synthetic labels reproduce explicit model logic and do not measure clinical prediction.",
            "Chip profiles are stress-test assumptions, not measured vendor performance.",
            "Candidate-gene and descriptive panels retain their original evidence limitations.",
        ],
    }
    for trait_index, trait in enumerate(bundle["traits"]):
        trait_seed = seed + (trait_index + 1) * 100
        frame = assign_trait_splits(
            generate_trait_dataset(trait, bundle["synthetic_profiles"], samples_per_trait, trait_seed), trait_seed
        )
        synthetic_dir = root / "data" / "synthetic"
        split_dir = root / "data" / "splits" / trait["id"]
        synthetic_dir.mkdir(parents=True, exist_ok=True)
        split_dir.mkdir(parents=True, exist_ok=True)
        dataset_path = synthetic_dir / f"{trait['id']}_pilot_v1.csv.gz"
        frame.to_csv(dataset_path, index=False, compression="gzip")
        for split_name in ("train", "validation", "test"):
            frame.loc[frame["split"] == split_name].to_csv(
                split_dir / f"{split_name}.csv.gz", index=False, compression="gzip"
            )
        train = frame.loc[frame["split"] == "train"].reset_index(drop=True)
        validation = frame.loc[frame["split"] == "validation"].reset_index(drop=True)
        test = frame.loc[frame["split"] == "test"].reset_index(drop=True)
        models: dict[str, Any] = {}
        for offset, feature_set in enumerate(("baseline", "additive", "structured")):
            x_train, names = trait_feature_matrix(train, trait, feature_set, bundle["synthetic_profiles"])
            x_validation, _ = trait_feature_matrix(validation, trait, feature_set, bundle["synthetic_profiles"])
            x_test, _ = trait_feature_matrix(test, trait, feature_set, bundle["synthetic_profiles"])
            classifier = SoftmaxClassifier(names).fit(
                x_train,
                train["oracle_class"].to_numpy(dtype=int),
                seed=trait_seed + offset,
                steps=training_steps + (100 if feature_set == "structured" else 0),
            )
            validation_probabilities = classifier.predict_proba(x_validation)
            selected = tune_high_threshold(validation["oracle_class"].to_numpy(dtype=int), validation_probabilities)
            probabilities = classifier.predict_proba(x_test)
            metrics = evaluate_trait(
                test["oracle_class"].to_numpy(dtype=int), probabilities, selected["threshold"], trait["classes"]
            )
            artifact = root / "artifacts" / "multitrait" / trait["id"] / "models" / f"{feature_set}.npz"
            classifier.save(
                artifact,
                {
                    "trait_id": trait["id"],
                    "feature_set": feature_set,
                    "manifest_sha256": bundle["_sha256"],
                    "high_risk_threshold": selected["threshold"],
                    "clinical_validation": False,
                },
            )
            models[feature_set] = {
                "feature_count": len(names),
                "high_threshold_selection_on_validation": selected,
                "test": metrics,
                "artifact": str(artifact.relative_to(root)).replace("\\", "/"),
            }
        digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        overview["traits"][trait["id"]] = {
            "name_sk": trait["name_sk"],
            "model_type": trait["model_type"],
            "evidence_tier": trait["evidence_tier"],
            "dataset": {
                "rows": int(len(frame)),
                "columns": int(len(frame.columns)),
                "sha256": digest,
                "class_distribution": frame["oracle_label"].value_counts().to_dict(),
                "split_distribution": frame["split"].value_counts().to_dict(),
            },
            "models": models,
        }
    metrics_path = root / "artifacts" / "multitrait" / "evaluation.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(overview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return overview
