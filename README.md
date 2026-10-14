# AlergenRisk Celiac Pilot

Samostatný paralelný výskumný projekt k aplikácii AlergenRisk. Pôvodné používateľské rozhranie AlergenRisk nemení. Pilot premieňa celiakálny panel na reprodukovateľný balík obsahujúci:

- verzovaný a strojovo čitateľný modelový register,
- referenčný genetický výpočet (oracle),
- anotovaný syntetický dataset s oddelenými `train`, `validation` a `test` množinami,
- porovnanie jednoduchého baseline, aditívneho modelu a modelu so štruktúrovanými HLA interakciami,
- confusion matrix, precision, recall, F1, ROC-AUC, PR-AUC, false-negative rate a Brier score,
- samostatné hodnotenie vysoko predisponovanej triedy s prahom zvoleným na validačnej množine,
- dátovú a modelovú kartu, procesnú mapu, grantovú akceptačnú maticu a statický validačný dashboard.

## Dôležité metodické rozlíšenie

Výsledky na syntetickom datasete merajú **algorithmic fidelity** - schopnosť modelu reprodukovať vopred definovanú genetickú logiku. Nepredstavujú klinickú citlivosť, diagnostickú presnosť ani pravdepodobnosť vzniku celiakie. Klinická validácia vyžaduje nezávislú fenotypovanú kohortu.

## Model

Pilot vychádza z celiakálneho panelu AlergenRisk v25:

- 38 aditívnych lokusov jadra PGS000316/GRS42,
- 8 HLA tag markerov pre DQ2.5, DQ8, DQ2.2 a DQ7.5,
- 4 transparentne označené výskumné lokusy,
- spoločný HLA diplotypový člen,
- populačný referenčný model EUR/CEU.

HLA diplotyp je jediná biologicky štruktúrovaná neaditívna vrstva. Dodatočné ML interakčné príznaky sú označené ako výskumné štatistické príznaky, nie ako preukázaná epistáza.

## Spustenie

```powershell
python -m pip install -e .
python scripts/run_pipeline.py --samples 12000 --seed 20261014
python -m unittest discover -s tests -v
```

Pipeline vytvorí:

- `data/synthetic/celiac_pilot_v1.csv.gz`,
- `data/splits/*.csv.gz`,
- `artifacts/models/*.npz`,
- `artifacts/metrics/evaluation.json`,
- `artifacts/reports/evaluation.md`,
- `site/index.html`.

## Repozitár a nasadenie

Workflow `validate.yml` reprodukuje testy a validačný beh. Workflow `pages.yml` publikuje statický dashboard zo `site/` bez zmeny pôvodného webu AlergenRisk.

Kľúčové auditné dokumenty sú v `docs/dataset-card.md`, `docs/model-card.md`, `docs/process-map.md`, `docs/grant-acceptance-matrix.md` a `docs/integration-contract.md`.

## Zdroje

- PGS Catalog PGS000316: https://www.pgscatalog.org/score/PGS000316/
- Sharp et al. 2020: https://doi.org/10.1111/apt.15826
- Monsuur et al. 2008: https://doi.org/10.1371/journal.pone.0002270
- PRS Reporting Standards: https://doi.org/10.1038/s41586-021-03243-6
- TRIPOD+AI: https://doi.org/10.1136/bmj-2023-078378
- PROBAST+AI: https://doi.org/10.1136/bmj-2024-082505

