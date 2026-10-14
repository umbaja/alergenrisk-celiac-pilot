# AlergenRisk Celiac Pilot - validačná správa

Modelový register: `alergenrisk-celiac-pilot-v1` / 0.1.0
Dataset: 12000 syntetických prípadov, seed 20261014

> Táto správa hodnotí algorithmic fidelity voči syntetickému referenčnému oracle. Nejde o klinickú validáciu ani diagnostickú presnosť.

## Referenčné hranice

EUR/CEU q20: **1.20**, q80: **4.06**.

## Porovnanie modelov

| Model | Príznaky | Accuracy | Macro F1 | High recall | High precision | FN rate | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 5 | 70.5% | 0.515 | 100.0% | 20.0% | 0.0% | 0.882 | 0.723 |
| additive | 105 | 85.7% | 0.843 | 94.8% | 57.6% | 5.2% | 0.963 | 0.882 |
| structured | 111 | 89.2% | 0.880 | 95.0% | 71.0% | 5.0% | 0.980 | 0.945 |

## Confusion matrices

### baseline

| Skutočná / predikovaná | Low | Typical | High |
|---|---:|---:|---:|
| Low | 0 | 482 | 10 |
| Typical | 0 | 1357 | 71 |
| High | 0 | 145 | 336 |


### additive

| Skutočná / predikovaná | Low | Typical | High |
|---|---:|---:|---:|
| Low | 404 | 88 | 0 |
| Typical | 65 | 1251 | 112 |
| High | 1 | 77 | 403 |


### structured

| Skutočná / predikovaná | Low | Typical | High |
|---|---:|---:|---:|
| Low | 411 | 81 | 0 |
| Typical | 62 | 1308 | 58 |
| High | 2 | 57 | 422 |


## Interpretácia

- `baseline` používa iba starší dvoj-SNP HLA tag prístup rs2187668/rs7454108 a kvalitu dôkazu.
- `additive` používa pozorované dávky 42 aditívnych a 8 HLA tag markerov, kvalitu dôkazu a profil čipu.
- `structured` pridáva párové HLA tag príznaky a transparentne označené štatistické interakcie.
- Prah vysoko predisponovanej triedy bol zvolený iba na validačnej množine s cieľom recall >= 0,95.
- Testovacia množina bola použitá až po zafixovaní prahu.

## Obmedzenia

- Datasety neobsahujú skutočné osoby ani klinické fenotypy.
- Simulované profily čipov nie sú meraním kvality konkrétnych komerčných produktov.
- Modelová zhoda nemôže byť interpretovaná ako AUC pre diagnózu celiakie.
- Externá fenotypovaná kohorta zostáva podmienkou klinickej validácie.

## Reprodukovateľnosť

Manifest SHA-256: `87c607a0805b8729284a39ff73637b37be846ed3dfea09bb4b40ea89e6baeb59`  
Dataset SHA-256: `bba1ff01636b5eed3f71ec5730d28d31940b5aed6e6b52a43eb2ac56bdd2388f`
