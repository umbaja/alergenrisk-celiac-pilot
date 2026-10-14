# Dataset card - AlergenRisk Celiac Synthetic v1

## Účel

Dataset je určený na tréning a hodnotenie schopnosti ML modelu reprodukovať transparentnú logiku celiakálneho genetického oracle. Nie je určený na odhad klinickej účinnosti ani prevalencie.

## Obsah

- 42 pravých syntetických aditívnych dávok alel,
- 8 syntetických HLA tag markerov,
- pozorované dávky po simulácii priameho nálezu, proxy alebo populačného odhadu,
- kvalita a zdroj každého vstupu,
- pravý a odhadnutý HLA diplotyp,
- oracle skóre a trieda,
- čipový stresový profil,
- fixovaný split a seed,
- vysvetlenie rozhodovacej hranice.

## Pôvod

Genotypy sú generované z modelových EUR frekvencií a HLA haplotypových frekvencií. Neobsahujú genotyp žiadnej skutočnej osoby. Profily `23andme_like`, `myheritage_like` a `dnaera_like` sú syntetické scenáre pokrytia, nie tvrdenia o reálnej výkonnosti konkrétnej verzie čipu.

## Label

Label `low`, `typical` alebo `high` vzniká z pravého syntetického skóre voči 20. a 80. percentilu modelovej EUR/CEU distribúcie. Nejde o diagnózu ani absolútnu pravdepodobnosť ochorenia.

## GDPR

Dataset neobsahuje priame ani nepriame identifikátory, skutočné genómy ani pozorované klinické údaje. Pri každom vydaní sa musí zachovať dokumentácia generátora a potvrdenie, že do datasetu neboli primiešané reálne vzorky.

## Známe obmedzenia

- Väčšina aditívnych lokusov sa generuje nezávisle podľa HWE.
- HLA tagy sú odvodené zo syntetického diplotypu zjednodušeným pravidlom.
- Missingness a proxy presnosť sú stresové parametre pilotu.
- Výsledky nemožno preniesť na klinickú výkonnosť bez externej kohorty.

