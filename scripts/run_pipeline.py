from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from celiac_pilot.pipeline import run_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AlergenRisk celiac synthetic-data and ML fidelity pilot")
    parser.add_argument("--samples", type=int, default=12000)
    parser.add_argument("--seed", type=int, default=20261014)
    parser.add_argument("--training-steps", type=int, default=1400)
    args = parser.parse_args()
    result = run_pipeline(ROOT, samples=args.samples, seed=args.seed, training_steps=args.training_steps)
    summary = {
        name: {
            "macro_f1": round(model["test"]["macro_f1"], 4),
            "high_recall": round(model["test"]["high_risk"]["recall"], 4),
            "high_false_negative_rate": round(model["test"]["high_risk"]["false_negative_rate"], 4),
        }
        for name, model in result["models"].items()
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

