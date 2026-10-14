from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from celiac_pilot.multitrait import (  # noqa: E402
    assign_trait_splits,
    generate_trait_dataset,
    load_trait_bundle,
    reference_distribution,
    trait_feature_matrix,
)


class MultitraitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = load_trait_bundle(ROOT / "config" / "trait_models_v1.json")

    def test_register_contains_all_non_celiac_traits(self) -> None:
        self.assertEqual(
            [trait["id"] for trait in self.bundle["traits"]],
            ["egg", "peanut", "milk", "shared", "lactose", "histamine"],
        )
        self.assertEqual(sum(len(trait["loci"]) for trait in self.bundle["traits"]), 21)

    def test_generation_is_reproducible_and_score_is_integer(self) -> None:
        trait = self.bundle["traits"][2]
        first = generate_trait_dataset(trait, self.bundle["synthetic_profiles"], 500, 31)
        second = generate_trait_dataset(trait, self.bundle["synthetic_profiles"], 500, 31)
        self.assertTrue(first.equals(second))
        self.assertTrue((first["oracle_genetic_score"] % 1 == 0).all())
        self.assertTrue((first["observed_integer_score"] % 1 == 0).all())
        self.assertTrue((first["proxy_count"] > 0).any())

    def test_lactose_is_binary_rule_without_imputation(self) -> None:
        trait = next(row for row in self.bundle["traits"] if row["id"] == "lactose")
        frame = generate_trait_dataset(trait, self.bundle["synthetic_profiles"], 500, 37)
        self.assertEqual(set(frame["oracle_label"]), {"persistent", "nonpersistent"})
        self.assertTrue((frame["population_imputed_count"] == 0).all())
        expected = frame["true_rs4988235"].eq(2)
        self.assertTrue((frame["oracle_label"].eq("nonpersistent") == expected).all())

    def test_reference_distributions_and_feature_sets(self) -> None:
        for trait in self.bundle["traits"]:
            distribution = reference_distribution(trait)
            self.assertAlmostEqual(sum(row[1] for row in distribution), 1.0, places=9)
            frame = assign_trait_splits(
                generate_trait_dataset(trait, self.bundle["synthetic_profiles"], 600, 43), 43
            )
            self.assertEqual(set(frame["split"]), {"train", "validation", "test"})
            widths = []
            for feature_set in ("baseline", "additive", "structured"):
                matrix, names = trait_feature_matrix(frame, trait, feature_set, self.bundle["synthetic_profiles"])
                self.assertEqual(matrix.shape, (600, len(names)))
                widths.append(len(names))
            self.assertLessEqual(widths[0], widths[1])
            self.assertLessEqual(widths[1], widths[2])


if __name__ == "__main__":
    unittest.main()
