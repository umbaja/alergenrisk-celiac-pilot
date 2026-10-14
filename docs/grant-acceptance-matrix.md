# Grantová akceptačná matica - celiakálny pilot

| Požiadavka | Dôkaz v pilote | Stav pilotu |
|---|---|---|
| Agregované genetické skóre | 42 aditívnych lokusov + spoločný HLA diplotyp | splnené pre celiakiu |
| Vzájomné interakcie | spoločný HLA diplotyp a transparentne označené štatistické interaction features | pilotne splnené; bez tvrdenia o všeobecnej epistáze |
| Explicitná reprodukovateľná logika | verzovaný JSON manifest, seed, kontrolné súčty | splnené |
| Vedecké zdroje | PGS000316, Sharp 2020, Monsuur 2008 | splnené pre jadro; výskumné rozšírenie treba samostatne revidovať |
| Anotovaný syntetický dataset | CSV.gz, dataset card, oracle score, label, provenance | splnené |
| GDPR | bez skutočných osôb; dokumentované generovanie | splnené pre syntetický pilot |
| Confusion matrix | automatický evaluation.json a report | splnené |
| Precision, recall, F1 | automaticky pre tri triedy | splnené |
| ROC-AUC a PR-AUC | binárne pre high-risk triedu | splnené |
| Minimalizácia false negatives | validačný výber prahu s cieľovým recall | splnené na syntetickej fidelity úrovni |
| Komparatívna analýza | baseline vs additive vs structured | splnené |
| Technická dokumentácia pipeline | README, 4 PDF, procesná mapa a zdrojový kód | splnené |
| Produkčný AI model | exportované `.npz` a browser JSON artefakty | pilotne splnené |
| Verejný dátový výstup | GitHub Pages prehliadač, dátový slovník a súbory na stiahnutie | splnené |
| Lokálny výpočet | browser parser, direct/proxy/population audit a JSON export | splnené |
| Prepojenie s obrazovou platformou | bod 6 zámerne vynechaný podľa zadania | mimo rozsahu tejto etapy |
| Klinická validácia | vyžaduje nezávislú fenotypovanú kohortu | mimo syntetického pilotu |

