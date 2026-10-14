from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .features import feature_matrix
from .generate import assign_stratified_splits, generate_dataset, write_dataset
from .ml import SoftmaxClassifier, evaluate_probabilities, tune_high_risk_threshold
from .model import load_manifest, reference_thresholds


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _percentage(value: float) -> str:
    return f"{value * 100:.1f}%"


def _matrix_table(matrix: list[list[int]]) -> str:
    labels = ["Low", "Typical", "High"]
    header = "| Skutočná / predikovaná | " + " | ".join(labels) + " |\n"
    rule = "|---|---:|---:|---:|\n"
    rows = "".join(
        f"| {label} | " + " | ".join(str(value) for value in row) + " |\n"
        for label, row in zip(labels, matrix)
    )
    return header + rule + rows


def _write_markdown_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# AlergenRisk Celiac Pilot - validačná správa",
        "",
        f"Modelový register: `{result['model_id']}` / {result['model_version']}",
        f"Dataset: {result['dataset']['rows']} syntetických prípadov, seed {result['seed']}",
        "",
        "> Táto správa hodnotí algorithmic fidelity voči syntetickému referenčnému oracle. "
        "Nejde o klinickú validáciu ani diagnostickú presnosť.",
        "",
        "## Referenčné hranice",
        "",
        f"EUR/CEU q20: **{result['reference']['low_cut']:.2f}**, q80: **{result['reference']['high_cut']:.2f}**.",
        "",
        "## Porovnanie modelov",
        "",
        "| Model | Príznaky | Accuracy | Macro F1 | High recall | High precision | FN rate | ROC-AUC | PR-AUC |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, model in result["models"].items():
        metrics = model["test"]
        high = metrics["high_risk"]
        lines.append(
            f"| {name} | {model['feature_count']} | {_percentage(metrics['accuracy'])} | "
            f"{metrics['macro_f1']:.3f} | {_percentage(high['recall'])} | {_percentage(high['precision'])} | "
            f"{_percentage(high['false_negative_rate'])} | {high['roc_auc']:.3f} | {high['pr_auc']:.3f} |"
        )
    lines.extend(["", "## Confusion matrices", ""])
    for name, model in result["models"].items():
        lines.extend([f"### {name}", "", _matrix_table(model["test"]["confusion_matrix"]), ""])
    lines.extend(
        [
            "## Interpretácia",
            "",
            "- `baseline` používa iba starší dvoj-SNP HLA tag prístup rs2187668/rs7454108 a kvalitu dôkazu.",
            "- `additive` používa pozorované dávky 42 aditívnych a 8 HLA tag markerov, kvalitu dôkazu a profil čipu.",
            "- `structured` pridáva párové HLA tag príznaky a transparentne označené štatistické interakcie.",
            "- Prah vysoko predisponovanej triedy bol zvolený iba na validačnej množine s cieľom recall >= 0,95.",
            "- Testovacia množina bola použitá až po zafixovaní prahu.",
            "",
            "## Obmedzenia",
            "",
            "- Datasety neobsahujú skutočné osoby ani klinické fenotypy.",
            "- Simulované profily čipov nie sú meraním kvality konkrétnych komerčných produktov.",
            "- Modelová zhoda nemôže byť interpretovaná ako AUC pre diagnózu celiakie.",
            "- Externá fenotypovaná kohorta zostáva podmienkou klinickej validácie.",
            "",
            "## Reprodukovateľnosť",
            "",
            f"Manifest SHA-256: `{result['manifest_sha256']}`  ",
            f"Dataset SHA-256: `{result['dataset']['sha256']}`",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _html_table(result: dict[str, Any]) -> str:
    rows = []
    for name, model in result["models"].items():
        metrics = model["test"]
        high = metrics["high_risk"]
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(name)}</strong></td><td>{model['feature_count']}</td>"
            f"<td>{_percentage(metrics['accuracy'])}</td><td>{metrics['macro_f1']:.3f}</td>"
            f"<td>{_percentage(high['recall'])}</td><td>{_percentage(high['precision'])}</td>"
            f"<td>{_percentage(high['false_negative_rate'])}</td><td>{high['roc_auc']:.3f}</td>"
            "</tr>"
        )
    return "".join(rows)


def _write_site(result: dict[str, Any], path: Path) -> None:
    best_name = max(result["models"], key=lambda name: result["models"][name]["test"]["macro_f1"])
    best = result["models"][best_name]["test"]
    page = f"""<!doctype html>
<html lang="sk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AlergenRisk Celiac Pilot</title>
<style>
:root{{--bg:#f4f9fb;--ink:#2f3e45;--muted:#60717a;--blue:#2f8ab7;--dark:#2b6680;--line:#cedde3;--soft:#e8f3f7;--mint:#ddefea}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Arial,sans-serif;line-height:1.48}}
main{{max-width:1120px;margin:auto;padding:34px 22px 70px}}header{{border-top:1px solid var(--line);padding-top:34px;position:relative}}
.brand{{color:var(--dark);font-size:.78rem;font-weight:800;letter-spacing:.08em}}.eyebrow{{color:var(--blue);font-weight:800;font-size:.78rem;margin-top:42px}}
h1{{font-size:clamp(2.4rem,7vw,5.5rem);line-height:.95;margin:12px 0 20px;letter-spacing:-.055em}}h1 span{{color:var(--blue)}}
.lead{{font-size:1.15rem;color:var(--muted);max-width:760px}}.notice{{margin:28px 0;padding:18px 20px;background:var(--dark);color:white}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:26px 0}}.card{{background:white;border:1px solid var(--line);padding:20px}}
.card small{{color:var(--dark);font-weight:800}}.value{{font-size:2rem;font-weight:800;margin-top:7px}}h2{{color:var(--dark);font-size:1.7rem;margin-top:45px}}
table{{width:100%;border-collapse:collapse;background:white;font-size:.9rem}}th{{background:var(--dark);color:white;text-align:left}}th,td{{padding:10px;border:1px solid var(--line)}}tr:nth-child(even){{background:var(--soft)}}
.flow{{background:var(--mint);border:1px solid #9dcbbd;padding:20px;font-family:Consolas,monospace;white-space:pre-wrap}}footer{{margin-top:54px;padding-top:14px;border-top:2px solid var(--blue);color:var(--muted);font-size:.8rem}}
@media(max-width:760px){{.grid{{grid-template-columns:1fr}}table{{font-size:.75rem}}th,td{{padding:7px}}}}
</style></head><body><main><header><div class="brand">NU3GEN / ALERGENRISK / PARALELNÝ VÝSKUMNÝ PILOT</div>
<div class="eyebrow">CELIAKIA · ALGORITHMIC FIDELITY / 2026</div><h1>Celiac <span>Pilot</span></h1>
<p class="lead">Reprodukovateľný syntetický dataset, modelový register a porovnávacia ML validácia celiakálneho panelu AlergenRisk.</p></header>
<div class="notice"><strong>Výskumné obmedzenie:</strong> výsledky dokazujú zhodu AI s definovaným genetickým oracle. Nie sú klinickou validáciou ani diagnostickou presnosťou.</div>
<section class="grid"><div class="card"><small>SYNTETICKÉ PRÍPADY</small><div class="value">{result['dataset']['rows']:,}</div></div>
<div class="card"><small>REFERENČNÉ MARKERY</small><div class="value">50</div></div>
<div class="card"><small>NAJLEPŠÍ MODEL</small><div class="value">{html.escape(best_name)}</div></div></section>
<section class="grid"><div class="card"><small>MACRO F1</small><div class="value">{best['macro_f1']:.3f}</div></div>
<div class="card"><small>HIGH RECALL</small><div class="value">{_percentage(best['high_risk']['recall'])}</div></div>
<div class="card"><small>FALSE NEGATIVE RATE</small><div class="value">{_percentage(best['high_risk']['false_negative_rate'])}</div></div></section>
<h2>Komparatívna analýza</h2><table><thead><tr><th>Model</th><th>Príznaky</th><th>Accuracy</th><th>Macro F1</th><th>High recall</th><th>High precision</th><th>FN rate</th><th>ROC-AUC</th></tr></thead><tbody>{_html_table(result)}</tbody></table>
<h2>Procesná mapa</h2><div class="flow">vedecké zdroje
  -> verzovaný modelový register
  -> referenčný oracle a EUR hranice
  -> syntetické genotypy + čipové stresové profily
  -> stratifikovaný train / validation / test
  -> baseline / additive / structured model
  -> výber prahu na validation
  -> jednorazové test hodnotenie
  -> metriky, modelové artefakty a integračný kontrakt</div>
<h2>Reprodukovateľnosť</h2><p>Model <strong>{html.escape(result['model_id'])}</strong>, verzia {html.escape(result['model_version'])}; seed {result['seed']}. EUR/CEU hranice: q20 {result['reference']['low_cut']:.2f}, q80 {result['reference']['high_cut']:.2f}.</p>
<footer>NU3GEN / ALERGENRISK CELIAC PILOT · výskumný a grantový validačný výstup · bez klinických tvrdení</footer></main></body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")


def run_pipeline(
    project_root: str | Path,
    *,
    samples: int = 12000,
    seed: int = 20261014,
    training_steps: int = 1400,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    manifest = load_manifest(root / "config" / "celiac_model_v1.json")
    frame = assign_stratified_splits(generate_dataset(samples, manifest, seed), seed)
    paths = write_dataset(frame, root, manifest)

    train = frame.loc[frame["split"] == "train"].reset_index(drop=True)
    validation = frame.loc[frame["split"] == "validation"].reset_index(drop=True)
    test = frame.loc[frame["split"] == "test"].reset_index(drop=True)
    y_train = train["oracle_class"].to_numpy(dtype=int)
    y_validation = validation["oracle_class"].to_numpy(dtype=int)
    y_test = test["oracle_class"].to_numpy(dtype=int)

    models: dict[str, Any] = {}
    prediction_frame = pd.DataFrame(
        {"sample_id": test["sample_id"], "oracle_class": y_test, "oracle_label": test["oracle_label"]}
    )
    for offset, feature_set in enumerate(("baseline", "additive", "structured")):
        x_train, feature_names = feature_matrix(train, manifest, feature_set)
        x_validation, _ = feature_matrix(validation, manifest, feature_set)
        x_test, _ = feature_matrix(test, manifest, feature_set)
        classifier = SoftmaxClassifier(feature_names).fit(
            x_train,
            y_train,
            seed=seed + 10 + offset,
            steps=training_steps + (200 if feature_set == "structured" else 0),
        )
        validation_probabilities = classifier.predict_proba(x_validation)
        threshold_selection = tune_high_risk_threshold(y_validation, validation_probabilities, target_recall=0.95)
        test_probabilities = classifier.predict_proba(x_test)
        metrics = evaluate_probabilities(y_test, test_probabilities, threshold_selection["threshold"])
        artifact_path = root / "artifacts" / "models" / f"{feature_set}.npz"
        classifier.save(
            artifact_path,
            {
                "feature_set": feature_set,
                "seed": seed,
                "manifest_sha256": manifest["_sha256"],
                "high_risk_threshold": threshold_selection["threshold"],
                "clinical_validation": False,
            },
        )
        models[feature_set] = {
            "feature_count": len(feature_names),
            "high_threshold_selection_on_validation": threshold_selection,
            "test": metrics,
            "artifact": str(artifact_path.relative_to(root)),
        }
        for class_id, class_name in enumerate(("low", "typical", "high")):
            prediction_frame[f"{feature_set}_p_{class_name}"] = test_probabilities[:, class_id]

    prediction_path = root / "artifacts" / "predictions" / "test_predictions.csv.gz"
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    prediction_frame.to_csv(prediction_path, index=False, compression="gzip")

    low_cut, high_cut = reference_thresholds(manifest)
    dataset_path = Path(paths["full"])
    result: dict[str, Any] = {
        "report_type": "algorithmic-fidelity-evaluation",
        "clinical_validation": False,
        "model_id": manifest["model_id"],
        "model_version": manifest["model_version"],
        "manifest_sha256": manifest["_sha256"],
        "seed": seed,
        "reference": {"low_cut": low_cut, "high_cut": high_cut, "population": manifest["population_reference"]},
        "dataset": {
            "rows": int(len(frame)),
            "columns": int(len(frame.columns)),
            "sha256": _sha256(dataset_path),
            "class_distribution": frame["oracle_label"].value_counts().to_dict(),
            "split_distribution": frame["split"].value_counts().to_dict(),
        },
        "models": models,
        "limitations": [
            "Synthetic labels reproduce a deterministic genetic oracle.",
            "Metrics are not clinical sensitivity, specificity, or disease-prediction AUC.",
            "Chip profiles are stress-test assumptions, not measured vendor performance.",
            "External evaluation on an independently phenotyped cohort is required for clinical claims.",
        ],
    }
    metrics_path = root / "artifacts" / "metrics" / "evaluation.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown_report(result, root / "artifacts" / "reports" / "evaluation.md")
    site_metrics = root / "site" / "assets" / "evaluation.json"
    site_metrics.parent.mkdir(parents=True, exist_ok=True)
    site_metrics.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

