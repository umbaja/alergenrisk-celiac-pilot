from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def feature_matrix(
    frame: pd.DataFrame, manifest: dict[str, Any], feature_set: str
) -> tuple[np.ndarray, list[str]]:
    additive_ids = [row["id"] for row in manifest["additive_loci"]]
    tag_rows = manifest["hla"]["tag_markers"]
    tag_ids = [row["id"] for row in tag_rows]

    if feature_set == "baseline":
        # Deliberately simple comparator: the older two-tag HLA rule plus evidence quality.
        # It must not receive the already aggregated reference score, which would leak
        # the oracle into the baseline and invalidate the comparison.
        columns = [
            "obs_rs2187668",
            "quality_rs2187668",
            "obs_rs7454108",
            "quality_rs7454108",
            "coverage_fraction",
        ]
        return frame[columns].to_numpy(dtype=float), columns

    dosage_columns = [f"obs_{marker}" for marker in additive_ids + tag_ids]
    quality_columns = [f"quality_{marker}" for marker in additive_ids + tag_ids]
    profile_names = list(manifest["synthetic_profiles"])
    profile_matrix = np.column_stack(
        [(frame["chip_profile"].to_numpy() == profile).astype(float) for profile in profile_names]
    )
    base_matrix = np.column_stack(
        [frame[dosage_columns].to_numpy(dtype=float), frame[quality_columns].to_numpy(dtype=float), profile_matrix]
    )
    names = dosage_columns + quality_columns + [f"profile_{profile}" for profile in profile_names]
    if feature_set == "additive":
        return base_matrix, names
    if feature_set != "structured":
        raise ValueError(f"Unknown feature set: {feature_set}")

    interaction_values: list[np.ndarray] = []
    interaction_names: list[str] = []
    by_haplotype: dict[str, list[str]] = {}
    for marker in tag_rows:
        by_haplotype.setdefault(marker["haplotype"], []).append(marker["id"])
    for haplotype, markers in by_haplotype.items():
        if len(markers) != 2:
            continue
        interaction_values.append(
            frame[f"obs_{markers[0]}"].to_numpy(dtype=float)
            * frame[f"obs_{markers[1]}"].to_numpy(dtype=float)
        )
        interaction_names.append(f"interaction_{haplotype.replace('.', '_')}_tag_pair")

    beta = np.array([float(row["beta"]) for row in manifest["additive_loci"]], dtype=float)
    observed_core_score = frame[[f"obs_{marker}" for marker in additive_ids]].to_numpy(dtype=float) @ beta
    hla_weight = np.array(
        [manifest["hla"]["diplotype_weights"].get(key, 0.0) for key in frame["predicted_hla_diplotype"]],
        dtype=float,
    )
    interaction_values.extend(
        [
            observed_core_score * hla_weight,
            observed_core_score * (1.0 - frame["coverage_fraction"].to_numpy(dtype=float)),
        ]
    )
    interaction_names.extend(["interaction_hla_weight_x_core_score", "interaction_missingness_x_core_score"])
    interaction_matrix = np.column_stack(interaction_values)
    return np.column_stack([base_matrix, interaction_matrix]), names + interaction_names

