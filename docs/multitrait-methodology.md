# AlergenRisk Research Pilot - viacznaková metodika v0.2.0

## Rozsah

Projekt rozširuje pôvodný celiakálny pilot na sedem samostatných genetických modulov: vajce, arašidy, kravské mlieko, spoločná potravinová predispozícia, laktóza, celiakia a histamín/DAO. Pôvodné používateľské rozhranie AlergenRisk zostáva samostatné; tento repozitár je paralelný výskumný a grantový výstup.

## Spoločná auditná architektúra

Každý znak má strojovo čitateľný register, ktorý obsahuje fenotyp, typ modelu, silu dôkazu, efektové alely, váhy, populačné alebo syntetické frekvencie, povolené proxy, politiku chýbajúcich hodnôt, rozhodovacie pásma, zdroje a obmedzenia. Výsledok je spätne naviazaný na verziu registra a seed generátora.

Pre každý cieľ sa uchováva:

- simulovaná pravá dávka efektovej alely 0, 1 alebo 2,
- numerický vstup modelu,
- pôvod `direct`, `proxy`, `population` alebo `missing`,
- kvalita 1 pre priamy genotyp, EUR r2 pre proxy a 0 pre chýbajúce alebo populačné očakávanie,
- celý počet alel použitý v transparentnom skóre,
- vážený agregovaný príznak pre porovnávacie modely.

Populačné očakávanie je iba numerický ML príznak. Nikdy sa nevydáva za individuálny genotyp ani nepridáva fiktívny bod do zobrazeného celého skóre.

## Syntetické datasety

Celiakia používa 12 000 prípadov. Každý ďalší znak používa 6 000 prípadov. Každý dataset má fixný stratifikovaný split 60 % train, 20 % validation a 20 % test. Profil `complete`, `23andme_like`, `myheritage_like`, `dnaera_like` alebo `sparse_stress` určuje iba syntetické stresové pokrytie. Nejde o meranie konkrétnej verzie komerčného čipu.

Oracle vzniká z explicitnej logiky registra:

- multilokusové panely používajú celý počet efektových alel a zachovávajú aj vážený súčet,
- celiakia používa publikované aditívne jadro a HLA diplotypový člen,
- laktóza používa presné genotypové pravidlo rs4988235,
- histamín/DAO používa opisný počet efektových alel, nie klinické riziko intolerancie.

## Porovnávané modely

`baseline` používa vedúci marker, jeho kvalitu a pokrytie. `additive` používa všetky pozorované dávky, kvalitu a stresový profil. `structured` navyše pridáva párové štatistické interakcie, vážené agregované skóre a interakciu skóre s chýbajúcimi vstupmi.

Interakcie sú výskumné príznaky. Neoznačujú sa za preukázanú biologickú epistázu. Ak structured model na testovacej množine neprekoná additive model, projekt to reportuje bez výberového skreslenia.

## Vyhodnotenie

Prah najvyššej triedy sa volí iba na validation splite so zámerom dosiahnuť recall aspoň 0,95, ak to model umožní. Test split sa používa až po zafixovaní prahu. Výstup obsahuje confusion matrix, precision, recall, F1, macro F1, ROC-AUC, PR-AUC, Brier score a false-negative rate.

Všetky metriky merajú algorithmic fidelity voči syntetickému oracle. Nie sú klinickou senzitivitou, špecificitou ani AUC pre ochorenie.

## Politika jednotlivých znakov

| Znak | Logika | Chýbajúci marker | Zásadné obmedzenie |
|---|---|---|---|
| Vajce | 4-lokusový aditívny panel | populačné očakávanie iba pre ML | opisné pásma bez klinickej kalibrácie |
| Arašidy | 5-lokusový panel | populačné očakávanie iba pre ML | dva HLA markery môžu predstavovať jeden LD signál |
| Kravské mlieko | 5 cieľov, 3 povinné proxy | populačné očakávanie iba pre ML | dve kandidátne asociácie z malej štúdie |
| Spoločná predispozícia | 3 spoločné GWAS lokusy | populačné očakávanie iba pre ML | nerozlišuje konkrétnu potravinu |
| Laktóza | rs4988235 genotypové pravidlo | bez imputácie | populačne špecifický marker, nie intenzita symptómov |
| Celiakia | GRS + HLA diplotyp | direct, proxy, population s auditom | relatívna predispozícia, nie diagnóza |
| Histamín / DAO | 3 AOC1 varianty | bez imputácie | aktivita DAO nie je diagnóza intolerancie |

## Vedecké zdroje

- Marenholz et al. 2017, DOI 10.1038/s41467-017-01220-0.
- Hong et al. 2015, DOI 10.1038/ncomms7304.
- Asai et al. 2018, DOI 10.1016/j.jaci.2017.09.015.
- Henneman et al. 2016, DOI 10.1186/s13601-016-0096-9.
- Enattah et al. 2002, PMID 11788828.
- Maintz et al. 2011, DOI 10.1111/j.1398-9995.2011.02548.x.
- PGS Catalog PGS000316; Sharp et al. 2020; Monsuur et al. 2008.

## Neuzavreté kroky

Pred klinickými tvrdeniami je potrebná nezávislá fenotypovaná kohorta, kalibrácia absolútneho rizika, externá validácia, subgroup analýzy, prospektívny protokol a odborná revízia kandidátnych panelov. Pred nemenným release musí vlastník zvoliť licenciu.
