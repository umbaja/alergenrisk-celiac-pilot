# Karty modelov AlergenRisk v0.2.0

## Vajce

Štyri lokusy z GWAS potravinovej alergie potvrdenej orálnym expozičným testom. Výstup je experimentálna relatívna predispozícia. Cieľová populácia referencie je EUR. Priamy cieľ má prednosť pred proxy. Pásma 0-1, 2-3 a 4-8 sú opisné.

## Arašidy

Päť lokusov: dva replikované HLA markery a tri sugestívne kandidáty. rs7192 a rs9275596 môžu zachytávať jeden HLA signál, preto sa ich súčet nesmie interpretovať ako dve nezávislé biologické príčiny. Pásma 0-2, 3-5 a 6-10 sú opisné.

## Kravské mlieko

Päť cieľov, z ktorých rs12123821, rs11949166 a rs2069772 sú technicky reprezentované povinnými proxy rs115288876, rs63582760/rs10588133 a rs17388568. Každá proxy dáva najpravdepodobnejší celý príspevok 0, 1 alebo 2; r2 ostáva samostatnou technickou kvalitou. Panel nehodnotí laktózovú intoleranciu.

## Spoločná potravinová predispozícia

Tri GWAS lokusy všeobecnej potravinovej alergie. Panel je spoločný pre pôvodné kategórie pšenica, sója, stromové orechy, sezam, ryby, kôrovce a mäkkýše a nerozlišuje ich individuálne riziko.

## Laktóza

Deterministické pravidlo rs4988235 v plus orientácii: GG zodpovedá laktázovej nonperzistencii, AG/AA perzistencii. Chýbajúci marker sa neimputuje. Pravidlo nehodnotí sekundárnu intoleranciu, symptómy ani ďalšie populačne špecifické varianty.

## Celiakia

Samostatná karta zostáva v `docs/model-card.md`. Model spája 38 aditívnych lokusov, 8 HLA tagov, HLA diplotypový člen a 4 výskumné lokusy. Výstup je relatívna genetická predispozícia.

## Histamín / DAO

Tri AOC1 varianty asociované s nižšou sérovou aktivitou DAO. Chýbajúci marker sa neimputuje. Panel nie je diagnostikou histamínovej intolerancie a lokusy v jednom géne sa nepovažujú za nezávislé.
