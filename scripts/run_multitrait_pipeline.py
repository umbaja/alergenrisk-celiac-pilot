from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from celiac_pilot.multitrait import run_multitrait_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build all non-coeliac AlergenRisk research pilots")
    parser.add_argument("--samples-per-trait", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=20261014)
    parser.add_argument("--training-steps", type=int, default=900)
    args = parser.parse_args()
    result = run_multitrait_pipeline(
        ROOT,
        samples_per_trait=args.samples_per_trait,
        seed=args.seed,
        training_steps=args.training_steps,
    )
    for trait_id, row in result["traits"].items():
        best = max(row["models"], key=lambda name: row["models"][name]["test"]["macro_f1"])
        score = row["models"][best]["test"]["macro_f1"]
        print(f"{trait_id}: {best}, macro F1={score:.3f}")


if __name__ == "__main__":
    main()
