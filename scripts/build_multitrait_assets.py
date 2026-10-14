from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from celiac_pilot.multitrait import load_trait_bundle, reference_distribution  # noqa: E402


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_structured_models() -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for path in sorted((ROOT / "artifacts" / "multitrait").glob("*/models/structured.npz")):
        trait_id = path.parts[-3]
        archive = np.load(path, allow_pickle=True)
        payload[trait_id] = {
            "feature_names": archive["feature_names"].tolist(),
            "mean": archive["mean"].tolist(),
            "scale": archive["scale"].tolist(),
            "weights": archive["weights"].tolist(),
            "metadata": json.loads(str(archive["metadata"][0])),
            "interpretation": "probabilities of synthetic oracle classes, not disease probability",
        }
    return payload


def column_definition(column: str) -> dict[str, str]:
    fixed = {
        "sample_id": "Syntetický identifikátor bez väzby na skutočnú osobu.",
        "trait_id": "Identifikátor hodnoteného znaku.",
        "generation_seed": "Seed deterministického generátora.",
        "chip_profile": "Syntetický stresový profil pokrytia; nejde o meranie komerčného čipu.",
        "oracle_genetic_score": "Celý počet efektových alel 0 až 2 na lokus.",
        "oracle_weighted_score": "Agregovaný súčet dávka krát publikovaná alebo deklarovaná váha.",
        "observed_integer_score": "Celý počet alel zistených priamo alebo cez proxy; chýbajúce lokusy nepridávajú body.",
        "oracle_class": "Číselný kód triedy syntetického oracle.",
        "oracle_label": "Textová trieda syntetického oracle.",
        "direct_count": "Počet priamo zistených cieľov.",
        "proxy_count": "Počet cieľov odvodených auditovanou proxy.",
        "population_imputed_count": "Počet numerických populačných očakávaní použitých iba pre ML príznaky.",
        "missing_count": "Počet chýbajúcich cieľov bez populačnej imputácie.",
        "coverage_fraction": "Podiel cieľov zistených priamo alebo cez proxy.",
        "split": "Fixné rozdelenie train, validation alebo test.",
    }
    if column in fixed:
        return {"column": column, "type": "derived", "description": fixed[column]}
    if column.startswith("true_rs"):
        return {"column": column, "type": "integer", "description": "Simulovaná pravá dávka efektovej alely 0, 1 alebo 2."}
    if column.startswith("obs_rs"):
        return {"column": column, "type": "number", "description": "Numerický vstup modelu; nie vždy individuálny genotyp."}
    if column.startswith("quality_rs"):
        return {"column": column, "type": "number", "description": "Kvalita pôvodu: 1 direct, r² proxy alebo 0 pri chýbaní/population."}
    if column.startswith("source_rs"):
        return {"column": column, "type": "category", "description": "Pôvod direct, proxy, population alebo missing."}
    return {"column": column, "type": "unknown", "description": "Premenná syntetického generátora."}


def build() -> None:
    bundle = load_trait_bundle(ROOT / "config" / "trait_models_v1.json")
    overview = json.loads((ROOT / "artifacts" / "multitrait" / "evaluation.json").read_text(encoding="utf-8"))
    site_assets = ROOT / "site" / "assets"
    downloads = ROOT / "site" / "downloads"
    site_assets.mkdir(parents=True, exist_ok=True)
    downloads.mkdir(parents=True, exist_ok=True)
    clean_bundle = {key: value for key, value in bundle.items() if not key.startswith("_")}
    write_json(site_assets / "trait-models.json", clean_bundle)
    write_json(site_assets / "multitrait-evaluation.json", overview)
    write_json(site_assets / "trait-structured-models.json", export_structured_models())
    write_json(
        site_assets / "trait-references.json",
        {
            trait["id"]: {
                "distribution": reference_distribution(trait),
                "frequency_basis": "EUR" if all("eur_frequency" in row for row in trait["loci"]) else "synthetic-stress-assumption",
            }
            for trait in bundle["traits"]
        },
    )

    audit_rows = []
    previews: dict[str, Any] = {}
    dictionaries: dict[str, Any] = {}
    for trait in bundle["traits"]:
        trait_id = trait["id"]
        for locus in trait["loci"]:
            audit_rows.append(
                {
                    "trait_id": trait_id,
                    "trait_name": trait["name_sk"],
                    "target": locus["id"],
                    "gene": locus["gene"],
                    "risk_allele": locus["risk_allele"],
                    "beta": locus["beta"],
                    "frequency": locus.get("eur_frequency", locus.get("simulation_frequency")),
                    "frequency_status": locus.get("frequency_status", "EUR-model"),
                    "required_proxy": bool(locus.get("required_proxy")),
                    "proxies": locus.get("proxies", []),
                    "evidence_tier": trait["evidence_tier"],
                    "missing_policy": trait["missing_policy"],
                }
            )
        source = ROOT / "data" / "synthetic" / f"{trait_id}_pilot_v1.csv.gz"
        frame = pd.read_csv(source)
        preview_columns = [
            "sample_id", "split", "chip_profile", "oracle_label", "oracle_genetic_score",
            "oracle_weighted_score", "observed_integer_score", "direct_count", "proxy_count",
            "population_imputed_count", "missing_count", "coverage_fraction",
        ]
        previews[trait_id] = {
            "full_rows": int(len(frame)),
            "full_columns": int(len(frame.columns)),
            "rows": frame.sort_values("sample_id").groupby(["split", "oracle_label"], observed=True).head(5)[preview_columns].round(6).to_dict(orient="records"),
        }
        dictionaries[trait_id] = [column_definition(column) for column in frame.columns]
        shutil.copyfile(source, downloads / source.name)

    write_json(site_assets / "trait-audit.json", {"rows": audit_rows})
    write_json(site_assets / "trait-data-preview.json", previews)
    write_json(site_assets / "trait-data-dictionaries.json", dictionaries)

    demo_rows = ["# Synthetic AlergenRisk multi-trait demo; no real person"]
    seen: set[str] = set()
    for trait in bundle["traits"]:
        for locus in trait["loci"]:
            marker = locus["proxies"][0] if locus.get("required_proxy") else locus
            marker_id = marker["id"]
            if marker_id in seen:
                continue
            seen.add(marker_id)
            risk = marker.get("proxy_risk_allele", locus["risk_allele"])
            other = locus["other_allele"]
            if risk == other:
                other = "A" if risk != "A" else "C"
            demo_rows.append(f"{marker_id}\t{risk}{other}")
    multitrait_demo = "\n".join(demo_rows) + "\n"
    (downloads / "multitrait-demo-genotype.txt").write_text(multitrait_demo, encoding="utf-8")
    celiac_demo = (ROOT / "tests" / "fixtures" / "synthetic-demo-genotype.txt").read_text(encoding="utf-8")
    celiac_calls = [line for line in celiac_demo.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    (downloads / "all-traits-demo-genotype.txt").write_text(
        "# AlergenRisk Research Pilot - synteticka demonstracna vzorka vsetkych modulov\n"
        "# Tento subor neobsahuje udaje skutocnej osoby.\n"
        + "\n".join(celiac_calls + demo_rows[1:]) + "\n",
        encoding="utf-8",
    )

    checksum_rows = []
    for path in sorted(downloads.glob("*_pilot_v1.csv.gz")):
        checksum_rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (downloads / "multitrait-checksums.sha256").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
