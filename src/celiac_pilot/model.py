from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / "config" / "celiac_model_v1.json"


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_manifest(data)
    data["_path"] = str(manifest_path.resolve())
    data["_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return data


def validate_manifest(manifest: dict[str, Any]) -> None:
    additive = manifest.get("additive_loci", [])
    tags = manifest.get("hla", {}).get("tag_markers", [])
    if len(additive) != 42:
        raise ValueError(f"Expected 42 additive loci, found {len(additive)}")
    if len(tags) != 8:
        raise ValueError(f"Expected 8 HLA tag markers, found {len(tags)}")
    ids = [row["id"] for row in additive + tags]
    if len(ids) != len(set(ids)):
        raise ValueError("Marker identifiers must be unique")
    frequencies = manifest["hla"]["haplotype_frequencies"]
    if abs(sum(frequencies.values()) - 1.0) > 1e-9:
        raise ValueError("HLA haplotype frequencies must sum to 1")
    if any(not 0 < row["eur_frequency"] < 1 for row in additive):
        raise ValueError("All additive allele frequencies must lie between 0 and 1")


def diplotype_key(a: str, b: str, manifest: dict[str, Any]) -> str:
    order = {name: idx for idx, name in enumerate(manifest["hla"]["haplotype_order"])}
    return "/".join(sorted((a, b), key=lambda name: order[name]))


def diplotype_rows(manifest: dict[str, Any]) -> list[dict[str, float | str]]:
    frequencies = manifest["hla"]["haplotype_frequencies"]
    names = list(frequencies)
    weights = manifest["hla"]["diplotype_weights"]
    rows: list[dict[str, float | str]] = []
    for i, a in enumerate(names):
        for j in range(i, len(names)):
            b = names[j]
            prior = (1.0 if i == j else 2.0) * frequencies[a] * frequencies[b]
            key = diplotype_key(a, b, manifest)
            rows.append({"a": a, "b": b, "key": key, "prior": prior, "weight": weights[key]})
    return rows


def _score_grid(value: float) -> float:
    """Match the 0.02-point convolution grid used by AlergenRisk v25."""
    return round(value * 50.0) / 50.0


def reference_distribution(manifest: dict[str, Any]) -> list[tuple[float, float]]:
    distribution: dict[float, float] = {}
    for row in diplotype_rows(manifest):
        score = _score_grid(float(row["weight"]))
        distribution[score] = distribution.get(score, 0.0) + float(row["prior"])

    for locus in manifest["additive_loci"]:
        p = float(locus["eur_frequency"])
        beta = float(locus["beta"])
        options = ((0.0, (1 - p) ** 2), (beta, 2 * p * (1 - p)), (2 * beta, p**2))
        combined: dict[float, float] = {}
        for base_score, base_probability in distribution.items():
            for delta, probability in options:
                score = _score_grid(base_score + delta)
                combined[score] = combined.get(score, 0.0) + base_probability * probability
        distribution = combined

    total = sum(distribution.values())
    return sorted((score, probability / total) for score, probability in distribution.items())


def distribution_quantile(distribution: list[tuple[float, float]], q: float) -> float:
    cumulative = 0.0
    for score, probability in distribution:
        cumulative += probability
        if cumulative >= q:
            return score
    return distribution[-1][0]


def reference_thresholds(manifest: dict[str, Any]) -> tuple[float, float]:
    distribution = reference_distribution(manifest)
    low_q, high_q = manifest["outcome"]["cut_quantiles"]
    return distribution_quantile(distribution, low_q), distribution_quantile(distribution, high_q)


def band_for_score(score: float, low_cut: float, high_cut: float) -> tuple[int, str]:
    if score <= low_cut:
        return 0, "low"
    if score <= high_cut:
        return 1, "typical"
    return 2, "high"


def oracle_score(
    additive_dosages: dict[str, float], hla_diplotype: str, manifest: dict[str, Any]
) -> float:
    score = float(manifest["hla"]["diplotype_weights"][hla_diplotype])
    for locus in manifest["additive_loci"]:
        score += float(additive_dosages[locus["id"]]) * float(locus["beta"])
    return _score_grid(score)

