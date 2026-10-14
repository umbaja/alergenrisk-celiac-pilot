# Model card — AlergenRisk Celiac Pilot v0.1.0

## Účel a hranice použitia

Model je výskumný pilot na overenie, či sa explicitná logika celiakálneho genetického panelu dá reprodukovateľne preniesť do ML pipeline. Klasifikuje relatívnu genetickú predispozíciu do tried `low`, `typical` a `high`. Nie je diagnostickým zdravotníckym prostriedkom a neposkytuje absolútnu pravdepodobnosť vzniku celiakie.

## Vstupy

- pozorované dávky 42 aditívnych SNP,
- 8 HLA tag markerov,
- kvalita a pôvod každého pozorovania (`direct`, `proxy`, `population`),
- syntetický profil pokrytia čipu,
- pri štruktúrovanom modeli aj párové HLA tag príznaky a transparentne označené štatistické interakcie.

Zdrojová genetická logika je verzovaná v `config/celiac_model_v1.json`. Jadro odkazuje na PGS000316, Sharp et al. 2020 a Monsuur et al. 2008. Štyri rozširujúce lokusy sú označené ako výskumné a pred klinickým použitím vyžadujú samostatnú odbornú revíziu.

## Referenčný experiment

- generátor: `alergenrisk-celiac-synthetic-v1`,
- 12 000 syntetických prípadov,
- seed `20261014`,
- split približne 60 % / 20 % / 20 %,
- rozhodovacie hranice EUR/CEU modelu: q20 = 1,20 a q80 = 4,06,
- prah vysokej triedy bol zvolený iba na validačnom splite s cieľom recall ≥ 0,95,
- testovací split sa použil až po zafixovaní prahu.

## Výsledky na testovacom splite

| Model | Accuracy | Macro F1 | High recall | High precision | High FNR | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| dvoj-SNP baseline | 70,5 % | 0,515 | 100,0 % | 20,0 % | 0,0 % | 0,882 | 0,723 |
| additive | 85,7 % | 0,843 | 94,8 % | 57,6 % | 5,2 % | 0,963 | 0,882 |
| structured | 89,2 % | 0,880 | 95,0 % | 71,0 % | 5,0 % | 0,980 | 0,945 |

Baseline dosahuje nulový počet falošne negatívnych výsledkov iba pri extrémne nízkom prahu, ktorý označí všetkých 2 401 testovacích prípadov za pozitívne. Jeho vysoký recall preto nie je sám osebe známkou užitočného modelu. Štruktúrovaný model zachováva približne 95 % recall a súčasne zvyšuje precision na približne 71 %.

## Férovosť, populácia a bezpečnosť

Referenčné frekvencie sú modelované ako EUR/CEU. Výkon sa nesmie bez validácie prenášať na iné ancestrálne skupiny. Vstupný genotyp sa má spracovať lokálne alebo sa majú odovzdávať iba odvodené príznaky. Pri chýbajúcom priamom SNP sa musí uviesť pôvod náhrady a kvalita; populačný odhad nesmie byť prezentovaný ako pozorovaný genotyp.

## Čo metriky dokazujú a čo nie

Metriky dokazujú algoritmickú zhodu s deterministickým syntetickým oracle za zvolených stresových podmienok. Nedokazujú klinickú senzitivitu, špecificitu, kalibráciu ochorenia ani prínos pre pacienta. Klinické tvrdenia vyžadujú nezávislú fenotypovanú kohortu, externú validáciu, kalibráciu a odborné posúdenie.

## Reprodukovateľnosť

- manifest SHA-256: `87c607a0805b8729284a39ff73637b37be846ed3dfea09bb4b40ea89e6baeb59`,
- dataset SHA-256: `bba1ff01636b5eed3f71ec5730d28d31940b5aed6e6b52a43eb2ac56bdd2388f`,
- úplné metriky: `artifacts/metrics/evaluation.json`,
- confusion matrices a interpretácia: `artifacts/reports/evaluation.md`.
