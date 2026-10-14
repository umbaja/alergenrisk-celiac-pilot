# AlergenRisk Research Pilot

Samostatný paralelný výskumný projekt k aplikácii AlergenRisk. Pôvodné používateľské rozhranie AlergenRisk nemení. Verzia 0.2.0 aplikuje auditovateľný pilotný prístup na všetkých sedem modulov: vajce, arašidy, kravské mlieko, spoločnú potravinovú predispozíciu, laktózu, celiakiu a histamín/DAO.

Balík obsahuje:

- verzovaný a strojovo čitateľný modelový register,
- referenčný genetický výpočet (oracle),
- sedem anotovaných syntetických datasetov s oddelenými `train`, `validation` a `test` množinami,
- porovnanie jednoduchého baseline, aditívneho modelu a modelu so štruktúrovanými HLA interakciami,
- confusion matrix, precision, recall, F1, ROC-AUC, PR-AUC, false-negative rate a Brier score,
- samostatné hodnotenie vysoko predisponovanej triedy s prahom zvoleným na validačnej množine,
- lokálny výpočet zo surového genotypového exportu bez odosielania súboru,
- verejný prehliadač syntetických dát a audit 71 panel-lokus záznamov s proxy katalógmi,
- dátovú a modelovú kartu, štyri formálne PDF výstupy, procesnú mapu a grantovú akceptačnú maticu.

## Dôležité metodické rozlíšenie

Výsledky na syntetickom datasete merajú **algorithmic fidelity** - schopnosť modelu reprodukovať vopred definovanú genetickú logiku. Nepredstavujú klinickú citlivosť, diagnostickú presnosť ani pravdepodobnosť vzniku celiakie. Klinická validácia vyžaduje nezávislú fenotypovanú kohortu.

## Modely

Celiakálny pilot naďalej vychádza z panelu AlergenRisk v25:

- 38 aditívnych lokusov jadra PGS000316/GRS42,
- 8 HLA tag markerov pre DQ2.5, DQ8, DQ2.2 a DQ7.5,
- 4 transparentne označené výskumné lokusy,
- spoločný HLA diplotypový člen,
- populačný referenčný model EUR/CEU.

HLA diplotyp je jediná biologicky štruktúrovaná neaditívna vrstva. Dodatočné ML interakčné príznaky sú označené ako výskumné štatistické príznaky, nie ako preukázaná epistáza.

Ostatné moduly majú samostatný register `config/trait_models_v1.json`. Vajce, arašidy, mlieko a spoločný panel sú multilokusové experimentálne modely. Laktóza zostáva jednovariantovým genotypovým pravidlom. Histamín/DAO zostáva kandidátnym panelom aktivity DAO. Projekt nepredstiera polygénnosť alebo klinickú kalibráciu tam, kde pre ňu nie je opora.

## Spustenie

```powershell
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
python scripts/run_pipeline.py --samples 12000 --seed 20261014
python scripts/run_multitrait_pipeline.py --samples-per-trait 6000 --seed 20261014
python scripts/build_multitrait_assets.py
python scripts/build_release_assets.py
python scripts/build_pdfs.py
python -m unittest discover -s tests -v
node --test tests/web_app.test.mjs
```

Pipeline vytvorí:

- `data/synthetic/celiac_pilot_v1.csv.gz`,
- `data/synthetic/{egg,peanut,milk,shared,lactose,histamine}_pilot_v1.csv.gz`,
- `data/splits/*.csv.gz`,
- `artifacts/models/*.npz`,
- `artifacts/metrics/evaluation.json`,
- `artifacts/reports/evaluation.md`,
- `site/assets/*.json`,
- `site/downloads/*`,
- `output/pdf/*.pdf`.

## Repozitár a nasadenie

Workflow `validate.yml` reprodukuje testy a validačný beh. Workflow `pages.yml` publikuje statický dashboard zo `site/` bez zmeny pôvodného webu AlergenRisk.

- Verejná aplikácia: https://umbaja.github.io/alergenrisk-celiac-pilot/ (názov URL zostáva kvôli spätnej kompatibilite)
- Lokálny výpočet: https://umbaja.github.io/alergenrisk-celiac-pilot/calculator.html
- Prehliadač dát: https://umbaja.github.io/alergenrisk-celiac-pilot/data.html
- SNP/proxy audit: https://umbaja.github.io/alergenrisk-celiac-pilot/audit.html
- Dokumentácia: https://umbaja.github.io/alergenrisk-celiac-pilot/docs.html

Projekt zámerne nepoužíva Railway ani inú aplikačnú serverovú službu. Produkčné prepojenie s externou platformou je v tejto etape vynechané; pilot zostáva samostatným GitHub Pages projektom.

Kľúčové auditné dokumenty sú v `docs/multitrait-methodology.md`, `docs/multitrait-validation.md`, `docs/trait-model-cards.md`, `docs/dataset-card.md`, `docs/model-card.md`, `docs/process-map.md`, `docs/grant-acceptance-matrix.md` a `docs/integration-contract.md`.

Pred vytvorením nemenného release musí vlastník projektu zvoliť licenciu. Kým sa tak nestane, repozitár neposkytuje automatický grant práv na ďalšie použitie.

## Zdroje

- PGS Catalog PGS000316: https://www.pgscatalog.org/score/PGS000316/
- Sharp et al. 2020: https://doi.org/10.1111/apt.15826
- Monsuur et al. 2008: https://doi.org/10.1371/journal.pone.0002270
- Marenholz et al. 2017: https://doi.org/10.1038/s41467-017-01220-0
- Hong et al. 2015: https://doi.org/10.1038/ncomms7304
- Henneman et al. 2016: https://doi.org/10.1186/s13601-016-0096-9
- Enattah et al. 2002: https://pubmed.ncbi.nlm.nih.gov/11788828/
- Maintz et al. 2011: https://doi.org/10.1111/j.1398-9995.2011.02548.x
- PRS Reporting Standards: https://doi.org/10.1038/s41586-021-03243-6
- TRIPOD+AI: https://doi.org/10.1136/bmj-2023-078378
- PROBAST+AI: https://doi.org/10.1136/bmj-2024-082505

