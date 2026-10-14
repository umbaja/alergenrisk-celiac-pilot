# AlergenRisk Research Pilot - viacznaková validačná správa

## Výsledky na testovacej množine

| Znak | Najlepší model podľa macro F1 | Macro F1 | Recall najvyššej triedy | Precision najvyššej triedy |
|---|---|---:|---:|---:|
| Vajce | additive | 0,922 | 0,952 | 0,656 |
| Arašidy | additive | 0,913 | 0,936 | 0,810 |
| Kravské mlieko | additive | 0,739 | 0,975 | 0,190 |
| Spoločná predispozícia | additive | 0,906 | 0,931 | 0,842 |
| Laktóza | rule / baseline | 0,915 | 1,000 | 0,585 |
| Celiakia | structured | 0,880 | 0,950 | 0,710 |
| Histamín / DAO | additive | 0,804 | 0,842 | 0,593 |

Výsledky sú algoritmickou validáciou proti syntetickému oracle. Nízka precision mliečneho high-sensitivity prahu ukazuje cenu za minimalizáciu false negatives. Histamínový panel na validation splite nedosiahol cieľ 0,95 recall ani pri najnižšom skúšanom prahu; preto sa nesmie prezentovať ako vysoko citlivý skríning.

## Komparatívny záver

Pri piatich z šiestich nových modulov nepriniesli párové štatistické interakcie vyššie macro F1 než aditívny alebo pravidlový model. To je dôležitý negatívny výsledok: pipeline interakcie testuje, ale neprisudzuje im hodnotu bez dôkazu. Celiakia zostáva jediným modulom s biologicky štruktúrovaným HLA diplotypovým členom.

## Akceptačné hranice

- Úplná reprodukcia registra, dát a metrík z fixného seedu.
- Žiadne osobné alebo klinické dáta v syntetických datasetoch.
- Oddelenie celého genetického skóre od proxy neistoty.
- Explicitné označenie populačného očakávania ako ML príznaku, nie genotypu.
- Žiadne klinické tvrdenie bez externej fenotypovanej validácie.
