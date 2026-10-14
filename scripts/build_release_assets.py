from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from celiac_pilot.model import load_manifest, reference_distribution, reference_thresholds  # noqa: E402


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def export_model(root: Path) -> dict[str, Any]:
    archive = np.load(root / "artifacts" / "models" / "structured.npz", allow_pickle=True)
    payload = {
        "schema_version": "1.0",
        "model_id": "alergenrisk-celiac-pilot-structured-v1",
        "feature_names": archive["feature_names"].tolist(),
        "mean": archive["mean"].tolist(),
        "scale": archive["scale"].tolist(),
        "weights": archive["weights"].tolist(),
        "metadata": json.loads(str(archive["metadata"][0])),
        "interpretation": "algorithmic-fidelity research probabilities; not disease probability",
    }
    write_json(root / "site" / "assets" / "structured-model.json", payload)
    return payload


def column_definition(column: str) -> dict[str, str]:
    fixed = {
        "sample_id": ("string", "Syntetický identifikátor; nevzťahuje sa na skutočnú osobu."),
        "generation_seed": ("integer", "Seed deterministického generátora."),
        "model_version": ("string", "Verzia modelového registra."),
        "chip_profile": ("category", "Syntetický stresový profil pokrytia; nie meranie komerčného čipu."),
        "true_hla_diplotype": ("category", "Simulovaný pravý HLA diplotyp použitý oracle modelom."),
        "predicted_hla_diplotype": ("category", "HLA diplotyp odvodený z pozorovaných tag SNP."),
        "hla_confidence": ("number", "Technická stabilita HLA odhadu v rozsahu 0 až 1."),
        "oracle_score": ("number", "Referenčné syntetické skóre na mriežke 0,02 bodu."),
        "observed_reference_score": ("number", "Skóre vypočítané z priamych, proxy a populačných vstupov."),
        "oracle_class": ("integer", "Kód triedy: 0 low, 1 typical, 2 high."),
        "oracle_label": ("category", "Relatívna trieda syntetického oracle."),
        "direct_count": ("integer", "Počet priamo pozorovaných cieľových markerov."),
        "proxy_count": ("integer", "Počet markerov získaných prostredníctvom proxy."),
        "population_imputed_count": ("integer", "Počet markerov nahradených populačným očakávaním."),
        "coverage_fraction": ("number", "Podiel priamych a proxy markerov zo všetkých 50 cieľov."),
        "label_rationale": ("string", "Textové pravidlo rozhodovacej hranice."),
        "split": ("category", "Fixné rozdelenie train, validation alebo test."),
    }
    if column in fixed:
        dtype, description = fixed[column]
    elif column.startswith("true_rs"):
        dtype, description = "integer", "Simulovaná pravá dávka efektovej alely 0, 1 alebo 2."
    elif column.startswith("obs_rs"):
        dtype, description = "number", "Pozorovaná alebo odhadnutá dávka efektovej alely použitá modelom."
    elif column.startswith("quality_rs"):
        dtype, description = "number", "Kvalita genetického vstupu: 1 direct, proxy accuracy, 0 population."
    elif column.startswith("source_rs"):
        dtype, description = "category", "Pôvod hodnoty: direct, proxy alebo population."
    else:
        dtype, description = "unknown", "Premenná generátora celiakálneho pilotu."
    return {"column": column, "type": dtype, "description": description}


def build_data_assets(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    frame = pd.read_csv(root / "data" / "synthetic" / "celiac_pilot_v1.csv.gz")
    preview_columns = [
        "sample_id",
        "split",
        "chip_profile",
        "oracle_label",
        "oracle_score",
        "observed_reference_score",
        "predicted_hla_diplotype",
        "hla_confidence",
        "direct_count",
        "proxy_count",
        "population_imputed_count",
        "coverage_fraction",
        "label_rationale",
    ]
    preview = (
        frame.sort_values("sample_id")
        .groupby(["split", "oracle_label"], observed=True, sort=True)
        .head(8)[preview_columns]
        .round(5)
        .to_dict(orient="records")
    )
    dictionary = [column_definition(column) for column in frame.columns]
    write_json(
        root / "site" / "assets" / "data-preview.json",
        {
            "synthetic_only": True,
            "clinical_validation": False,
            "full_rows": int(len(frame)),
            "full_columns": int(len(frame.columns)),
            "preview_rows": preview,
        },
    )
    write_json(root / "site" / "assets" / "data-dictionary.json", dictionary)
    downloads = root / "site" / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        root / "data" / "synthetic" / "celiac_pilot_v1.csv.gz",
        downloads / "celiac_pilot_v1.csv.gz",
    )
    pd.DataFrame(dictionary).to_csv(downloads / "data-dictionary-full.csv", index=False)
    return preview, dictionary


def build_reference_asset(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    distribution = reference_distribution(manifest)
    low_cut, high_cut = reference_thresholds(manifest)
    payload = {
        "population": manifest["population_reference"],
        "low_cut": low_cut,
        "high_cut": high_cut,
        "distribution": distribution,
        "assumptions": [
            "Hardy-Weinberg equilibrium within loci",
            "between-locus independence outside the explicit HLA diplotype term",
            "EUR allele frequencies and approximate CEU HLA frequencies",
        ],
    }
    write_json(root / "site" / "assets" / "reference-distribution.json", payload)
    return payload


def build_audit(root: Path, manifest: dict[str, Any], proxy_catalog: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    markers = [
        *[{**row, "kind": row["group"]} for row in manifest["additive_loci"]],
        *[{**row, "kind": "hla"} for row in manifest["hla"]["tag_markers"]],
    ]
    for marker in markers:
        proxies = proxy_catalog["proxies"].get(marker["id"], [])
        rows.append(
            {
                "target": marker["id"],
                "group": marker["kind"],
                "gene": marker["gene"],
                "risk_allele": marker["risk_allele"],
                "weight": marker.get("beta"),
                "haplotype": marker.get("haplotype"),
                "automatic_proxy": bool(proxies),
                "proxies": proxies,
                "chip_availability": {
                    "23andMe": "runtime-detected",
                    "MyHeritage": "runtime-detected",
                    "DNAERA": "runtime-detected",
                },
                "evidence_status": "published-core" if marker["kind"] in {"core", "hla"} else "research-extension",
            }
        )
    write_json(
        root / "site" / "assets" / "locus-audit.json",
        {
            "catalog": {key: value for key, value in proxy_catalog.items() if key != "proxies"},
            "rows": rows,
        },
    )

    lines = [
        "# SNP a proxy audit - celiakálny pilot v1",
        "",
        "> Dostupnosť sa určuje z konkrétneho nahratého exportu. Označenie značky čipu samo osebe nie je dôkazom, že daná revízia marker obsahuje.",
        "",
        "| Cieľ | Skupina | Gén/región | Efektová alela | Váha/HLA | Automatické proxy (EUR r²; D') | Stav dôkazu |",
        "|---|---|---|---|---:|---|---|",
    ]
    for row in rows:
        if row["proxies"]:
            proxies = "; ".join(
                f"{proxy['id']} ({proxy['r2']:.3f}; {proxy['d_prime']:.3f})" for proxy in row["proxies"]
            )
        else:
            proxies = "bez automatickej proxy"
        weight = row["haplotype"] if row["haplotype"] else f"{row['weight']:.3f}"
        lines.append(
            f"| {row['target']} | {row['group']} | {row['gene']} | {row['risk_allele']} | "
            f"{weight} | {proxies} | {row['evidence_status']} |"
        )
    lines.extend(
        [
            "",
            "## Metodické pravidlá",
            "",
            "- Priamy cieľ má vždy prednosť pred proxy.",
            "- Proxy sa skúšajú v poradí podľa EUR r² a použijú sa iba raz.",
            "- Automatický prah je r² >= 0,90 v 1000 Genomes Phase 3 EUR.",
            "- Ak chýba cieľ aj proxy, populačné očakávanie je označené ako neisté a nie ako genotyp osoby.",
            "- Štyri research-extension lokusy nie sú súčasťou pôvodnej klinickej validácie GRS42.",
        ]
    )
    audit_path = root / "docs" / "snp-proxy-audit.md"
    audit_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def build_sample(root: Path, manifest: dict[str, Any]) -> None:
    rows = [*manifest["additive_loci"], *manifest["hla"]["tag_markers"]]
    lines = [
        "# AlergenRisk Celiac Pilot - synteticka demonstracna vzorka",
        "# Tento subor neobsahuje udaje skutocnej osoby.",
        "# rsid genotype",
    ]
    for index, marker in enumerate(rows):
        risk = marker["risk_allele"]
        other = next(base for base in "ACGT" if base != risk)
        target_dosage = index % 3
        genotype = other * 2 if target_dosage == 0 else (risk + other if target_dosage == 1 else risk * 2)
        lines.append(f"{marker['id']}\t{genotype}")
    output = root / "site" / "downloads" / "synthetic-demo-genotype.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    fixture = root / "tests" / "fixtures" / "synthetic-demo-genotype.txt"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output, fixture)


def build_checksums(root: Path) -> None:
    candidates = [
        root / "config" / "celiac_model_v1.json",
        root / "config" / "celiac_proxy_audit_v1.json",
        root / "data" / "synthetic" / "celiac_pilot_v1.csv.gz",
        root / "artifacts" / "models" / "structured.npz",
        root / "site" / "assets" / "structured-model.json",
    ]
    candidates.extend(sorted((root / "output" / "pdf").glob("*.pdf")))
    rows = [
        {"path": path.relative_to(root).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in candidates
        if path.exists()
    ]
    write_json(
        root / "artifacts" / "release-manifest.json",
        {"release": "v0.1.0", "files": rows, "clinical_validation": False},
    )
    checksum_path = root / "artifacts" / "checksums.sha256"
    checksum_path.write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in rows), encoding="ascii"
    )
    (root / "site" / "downloads").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(checksum_path, root / "site" / "downloads" / "checksums.sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = load_manifest(root / "config" / "celiac_model_v1.json")
    proxy_catalog = json.loads((root / "config" / "celiac_proxy_audit_v1.json").read_text(encoding="utf-8"))
    shutil.copyfile(root / "config" / "celiac_model_v1.json", root / "site" / "assets" / "celiac-model.json")
    shutil.copyfile(root / "config" / "celiac_proxy_audit_v1.json", root / "site" / "assets" / "proxy-audit.json")
    shutil.copyfile(root / "artifacts" / "metrics" / "evaluation.json", root / "site" / "assets" / "evaluation.json")
    export_model(root)
    build_data_assets(root)
    build_reference_asset(root, manifest)
    build_audit(root, manifest, proxy_catalog)
    build_sample(root, manifest)
    build_checksums(root)
    print("Release assets generated.")


if __name__ == "__main__":
    main()
