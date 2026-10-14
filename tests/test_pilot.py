from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from celiac_pilot.features import feature_matrix  # noqa: E402
from celiac_pilot.generate import assign_stratified_splits, generate_dataset  # noqa: E402
from celiac_pilot.ml import SoftmaxClassifier, evaluate_probabilities, tune_high_risk_threshold  # noqa: E402
from celiac_pilot.model import load_manifest, reference_distribution, reference_thresholds  # noqa: E402


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest(ROOT / "config" / "celiac_model_v1.json")

    def test_manifest_and_reference_distribution(self) -> None:
        self.assertEqual(len(self.manifest["additive_loci"]), 42)
        self.assertEqual(len(self.manifest["hla"]["tag_markers"]), 8)
        distribution = reference_distribution(self.manifest)
        self.assertAlmostEqual(sum(probability for _, probability in distribution), 1.0, places=9)
        low, high = reference_thresholds(self.manifest)
        self.assertLess(low, high)

    def test_generation_is_reproducible_and_stratified(self) -> None:
        first = assign_stratified_splits(generate_dataset(600, self.manifest, 17), 17)
        second = assign_stratified_splits(generate_dataset(600, self.manifest, 17), 17)
        self.assertTrue(first.equals(second))
        self.assertEqual(set(first["split"]), {"train", "validation", "test"})
        for split in ("train", "validation", "test"):
            self.assertEqual(set(first.loc[first["split"] == split, "oracle_class"]), {0, 1, 2})
        self.assertTrue(first["sample_id"].is_unique)

    def test_feature_sets_and_model_metrics(self) -> None:
        frame = assign_stratified_splits(generate_dataset(900, self.manifest, 23), 23)
        train = frame.loc[frame["split"] == "train"].reset_index(drop=True)
        validation = frame.loc[frame["split"] == "validation"].reset_index(drop=True)
        test = frame.loc[frame["split"] == "test"].reset_index(drop=True)
        for feature_set in ("baseline", "additive", "structured"):
            x_train, names = feature_matrix(train, self.manifest, feature_set)
            x_validation, _ = feature_matrix(validation, self.manifest, feature_set)
            x_test, _ = feature_matrix(test, self.manifest, feature_set)
            self.assertEqual(x_train.shape[1], len(names))
            model = SoftmaxClassifier(names).fit(
                x_train, train["oracle_class"].to_numpy(dtype=int), seed=41, steps=180, batch_size=128
            )
            validation_probabilities = model.predict_proba(x_validation)
            selected = tune_high_risk_threshold(
                validation["oracle_class"].to_numpy(dtype=int), validation_probabilities, 0.80
            )
            metrics = evaluate_probabilities(
                test["oracle_class"].to_numpy(dtype=int), model.predict_proba(x_test), selected["threshold"]
            )
            self.assertEqual(len(metrics["confusion_matrix"]), 3)
            self.assertGreaterEqual(metrics["high_risk"]["recall"], 0.0)
            self.assertLessEqual(metrics["high_risk"]["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()

