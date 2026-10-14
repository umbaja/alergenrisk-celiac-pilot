from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .model import band_for_score, diplotype_key, reference_thresholds


def _corrupt_dosage(values: np.ndarray, accuracy: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    result = values.astype(float).copy()
    wrong = rng.random(values.size) > accuracy
    if wrong.any():
        direction = rng.choice(np.array([-1, 1]), size=int(wrong.sum()))
        changed = np.clip(result[wrong] + direction, 0, 2)
        unchanged = changed == result[wrong]
        changed[unchanged] = np.where(result[wrong][unchanged] == 0, 1, 1)
        result[wrong] = changed
    return result


def _simulate_observation(
    truth: np.ndarray,
    population_expectation: float,
    proxy_eligible: bool,
    profiles: np.ndarray,
    profile_config: dict[str, Any],
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = truth.size
    call_rate = np.array([profile_config[p]["direct_call_rate"] for p in profiles], dtype=float)
    proxy_rate = np.array([profile_config[p]["proxy_recovery_rate"] for p in profiles], dtype=float)
    proxy_accuracy = np.array([profile_config[p]["proxy_accuracy"] for p in profiles], dtype=float)
    direct = rng.random(n) < call_rate
    proxy = (~direct) & proxy_eligible & (rng.random(n) < proxy_rate)
    population = ~(direct | proxy)

    observed = np.full(n, population_expectation, dtype=float)
    quality = np.zeros(n, dtype=float)
    source = np.full(n, "population", dtype=object)
    observed[direct] = truth[direct]
    quality[direct] = 1.0
    source[direct] = "direct"
    if proxy.any():
        observed[proxy] = _corrupt_dosage(truth[proxy], proxy_accuracy[proxy], rng)
        quality[proxy] = proxy_accuracy[proxy]
        source[proxy] = "proxy"
    return observed, quality, source


def _infer_hla_diplotypes(frame: pd.DataFrame, manifest: dict[str, Any]) -> tuple[list[str], np.ndarray]:
    order = manifest["hla"]["haplotype_order"]
    tags = manifest["hla"]["tag_markers"]
    by_haplotype: dict[str, list[str]] = {}
    for marker in tags:
        by_haplotype.setdefault(marker["haplotype"], []).append(marker["id"])

    evidence = {
        haplotype: frame[[f"obs_{marker}" for marker in markers]].mean(axis=1).to_numpy()
        for haplotype, markers in by_haplotype.items()
    }
    keys: list[str] = []
    confidence = np.zeros(len(frame), dtype=float)
    for row_index in range(len(frame)):
        ranked = sorted(
            ((float(values[row_index]), haplotype) for haplotype, values in evidence.items()),
            reverse=True,
        )
        copies: list[str] = []
        for value, haplotype in ranked:
            copies.extend([haplotype] * int(np.clip(np.rint(value), 0, 2)))
        copies = copies[:2]
        while len(copies) < 2:
            copies.append("X")
        copies.sort(key=order.index)
        key = "/".join(copies)
        keys.append(key)
        confidence[row_index] = min(1.0, sum(value for value, _ in ranked[:2]) / 2.0)
    return keys, confidence


def generate_dataset(n_samples: int, manifest: dict[str, Any], seed: int) -> pd.DataFrame:
    if n_samples < 300:
        raise ValueError("Use at least 300 samples so every split contains all three classes")
    rng = np.random.default_rng(seed)
    profiles_config = manifest["synthetic_profiles"]
    profile_names = np.array(list(profiles_config), dtype=object)
    profile_weights = np.array([profiles_config[name]["weight"] for name in profile_names], dtype=float)
    profile_weights /= profile_weights.sum()
    profiles = rng.choice(profile_names, size=n_samples, p=profile_weights)

    haplotype_names = np.array(list(manifest["hla"]["haplotype_frequencies"]), dtype=object)
    haplotype_probabilities = np.array(
        [manifest["hla"]["haplotype_frequencies"][name] for name in haplotype_names], dtype=float
    )
    hap_a = rng.choice(haplotype_names, size=n_samples, p=haplotype_probabilities)
    hap_b = rng.choice(haplotype_names, size=n_samples, p=haplotype_probabilities)
    hla_keys = [diplotype_key(str(a), str(b), manifest) for a, b in zip(hap_a, hap_b)]

    data: dict[str, Any] = {
        "sample_id": [f"CEL-{index + 1:08d}" for index in range(n_samples)],
        "generation_seed": np.full(n_samples, seed, dtype=int),
        "model_version": np.full(n_samples, manifest["model_version"], dtype=object),
        "chip_profile": profiles,
        "true_hla_diplotype": hla_keys,
    }

    true_score = np.array([manifest["hla"]["diplotype_weights"][key] for key in hla_keys], dtype=float)
    direct_count = np.zeros(n_samples, dtype=int)
    proxy_count = np.zeros(n_samples, dtype=int)
    population_count = np.zeros(n_samples, dtype=int)

    for locus in manifest["additive_loci"]:
        marker = locus["id"]
        frequency = float(locus["eur_frequency"])
        truth = rng.binomial(2, frequency, size=n_samples)
        observed, quality, source = _simulate_observation(
            truth, 2 * frequency, bool(locus["proxy_eligible"]), profiles, profiles_config, rng
        )
        data[f"true_{marker}"] = truth
        data[f"obs_{marker}"] = observed
        data[f"quality_{marker}"] = quality
        data[f"source_{marker}"] = source
        true_score += truth * float(locus["beta"])
        direct_count += source == "direct"
        proxy_count += source == "proxy"
        population_count += source == "population"

    for marker in manifest["hla"]["tag_markers"]:
        marker_id = marker["id"]
        haplotype = marker["haplotype"]
        truth = (hap_a == haplotype).astype(int) + (hap_b == haplotype).astype(int)
        frequency = float(manifest["hla"]["haplotype_frequencies"][haplotype])
        observed, quality, source = _simulate_observation(
            truth, 2 * frequency, bool(marker["proxy_eligible"]), profiles, profiles_config, rng
        )
        data[f"true_{marker_id}"] = truth
        data[f"obs_{marker_id}"] = observed
        data[f"quality_{marker_id}"] = quality
        data[f"source_{marker_id}"] = source
        direct_count += source == "direct"
        proxy_count += source == "proxy"
        population_count += source == "population"

    frame = pd.DataFrame(data)
    predicted_hla, hla_confidence = _infer_hla_diplotypes(frame, manifest)
    frame["predicted_hla_diplotype"] = predicted_hla
    frame["hla_confidence"] = hla_confidence

    observed_score = np.array(
        [manifest["hla"]["diplotype_weights"].get(key, 0.0) for key in predicted_hla], dtype=float
    )
    for locus in manifest["additive_loci"]:
        observed_score += frame[f"obs_{locus['id']}"].to_numpy() * float(locus["beta"])

    low_cut, high_cut = reference_thresholds(manifest)
    rounded_true_score = np.round(true_score * 50.0) / 50.0
    labels = [band_for_score(float(score), low_cut, high_cut) for score in rounded_true_score]
    frame["oracle_score"] = rounded_true_score
    frame["observed_reference_score"] = np.round(observed_score * 50.0) / 50.0
    frame["oracle_class"] = np.array([label[0] for label in labels], dtype=int)
    frame["oracle_label"] = np.array([label[1] for label in labels], dtype=object)
    frame["direct_count"] = direct_count
    frame["proxy_count"] = proxy_count
    frame["population_imputed_count"] = population_count
    frame["coverage_fraction"] = (direct_count + proxy_count) / 50.0
    frame["label_rationale"] = np.where(
        rounded_true_score <= low_cut,
        f"score <= EUR q20 ({low_cut:.2f})",
        np.where(
            rounded_true_score <= high_cut,
            f"EUR q20 < score <= EUR q80 ({high_cut:.2f})",
            f"score > EUR q80 ({high_cut:.2f})",
        ),
    )
    return frame


def assign_stratified_splits(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
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


def write_dataset(frame: pd.DataFrame, output_root: str | Path, manifest: dict[str, Any]) -> dict[str, str]:
    root = Path(output_root)
    synthetic_dir = root / "data" / "synthetic"
    split_dir = root / "data" / "splits"
    synthetic_dir.mkdir(parents=True, exist_ok=True)
    split_dir.mkdir(parents=True, exist_ok=True)
    full_path = synthetic_dir / "celiac_pilot_v1.csv.gz"
    frame.to_csv(full_path, index=False, compression="gzip")
    paths = {"full": str(full_path)}
    for split_name in ("train", "validation", "test"):
        path = split_dir / f"{split_name}.csv.gz"
        frame.loc[frame["split"] == split_name].to_csv(path, index=False, compression="gzip")
        paths[split_name] = str(path)

    card = {
        "dataset_id": "alergenrisk-celiac-synthetic-v1",
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "classes": frame["oracle_label"].value_counts().to_dict(),
        "splits": frame["split"].value_counts().to_dict(),
        "profiles": frame["chip_profile"].value_counts().to_dict(),
        "manifest_sha256": manifest["_sha256"],
        "synthetic_only": True,
        "contains_personal_data": False,
        "clinical_validation": False,
        "purpose": "Algorithmic-fidelity training and evaluation",
        "simulation_disclaimer": manifest["simulation_disclaimer"],
    }
    card_path = synthetic_dir / "dataset-card.json"
    card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["dataset_card"] = str(card_path)
    return paths

