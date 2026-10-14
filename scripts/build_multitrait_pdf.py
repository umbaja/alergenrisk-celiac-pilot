from __future__ import annotations

import json
import shutil
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Spacer

from build_pdfs import (
    BG,
    BLUE,
    DARK,
    INK,
    LINE,
    MINT,
    MUTED,
    PALE,
    STYLES,
    banner,
    bullets,
    data_table,
    info_cards,
    p,
    section,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"
DOWNLOADS = ROOT / "site" / "downloads"
OUTPUT = OUT / "AlergenRisk_Multitrait_Pilot_Metodika_a_validacia.pdf"


def page_background(canvas, doc) -> None:
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setFillColor(BG)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setStrokeColor(BLUE)
    canvas.setLineWidth(1.2)
    canvas.line(doc.leftMargin, 16 * mm, width - doc.rightMargin, 16 * mm)
    canvas.setFont("Nu3Bold", 7)
    canvas.setFillColor(DARK)
    canvas.drawString(doc.leftMargin, 10 * mm, "NU3GEN / ALERGENRISK RESEARCH PILOT")
    canvas.setFont("Nu3Regular", 7)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - doc.rightMargin, 10 * mm, f"METODIKA A VALIDACIA  |  {canvas.getPageNumber():02d}")
    canvas.restoreState()


def document(path: Path) -> BaseDocTemplate:
    doc = BaseDocTemplate(
        str(path), pagesize=A4, leftMargin=21 * mm, rightMargin=21 * mm,
        topMargin=20 * mm, bottomMargin=23 * mm, title=path.stem, author="NU3GEN",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")
    doc.addPageTemplates(PageTemplate(id="standard", frames=[frame], onPage=page_background))
    return doc


def cover() -> list:
    return [
        p("NU3GEN / ALERGENRISK / PARALELNY VYSKUMNY PILOT", "CoverBrand"),
        Spacer(1, 22 * mm),
        p("DOKUMENT 05 / VIACZNAKOVA METODIKA", "Eyebrow"),
        p("AlergenRisk Research Pilot", "CoverTitle"),
        p("Jednotna metodika, synteticke datasety a komparativna validacia pre sedem genetickych modulov od vajca po histamin/DAO.", "CoverLead"),
        Spacer(1, 8 * mm),
        info_cards([("ZNAKY", "7"), ("PRIPADY", "48 000"), ("PANEL-LOKUSY", "71")]),
        Spacer(1, 14 * mm),
        banner("STATUS DOKUMENTU", "Verzia 0.2.0, 14. oktober 2026. Verejny vyskumy vystup. Metriky nie su klinickou validaciou ani diagnozou."),
        PageBreak(),
    ]


def metric_chart(overview: dict) -> Drawing:
    drawing = Drawing(470, 205)
    drawing.add(Rect(0, 0, 470, 205, fillColor=colors.white, strokeColor=LINE, strokeWidth=.6))
    trait_names = {
        "egg": "Vajce", "peanut": "Arasidy", "milk": "Mlieko", "shared": "Spolocny",
        "lactose": "Laktoza", "histamine": "Histamin",
    }
    for index, (trait_id, row) in enumerate(overview["traits"].items()):
        best_name = max(row["models"], key=lambda name: row["models"][name]["test"]["macro_f1"])
        best = row["models"][best_name]["test"]
        y = 168 - index * 27
        drawing.add(String(18, y + 3, trait_names[trait_id], fontName="Nu3Bold", fontSize=7.5, fillColor=INK))
        drawing.add(Rect(92, y, 245, 11, fillColor=PALE, strokeColor=None))
        drawing.add(Rect(92, y, 245 * best["macro_f1"], 11, fillColor=BLUE, strokeColor=None))
        drawing.add(String(345, y + 2, f"F1 {best['macro_f1']:.3f}", fontName="Nu3Bold", fontSize=7.3, fillColor=DARK))
        drawing.add(String(402, y + 2, best_name, fontName="Nu3Regular", fontSize=7.1, fillColor=MUTED))
    drawing.add(String(18, 188, "Najlepsi model podla macro F1 na fixnom test splite", fontName="Nu3Bold", fontSize=9, fillColor=DARK))
    return drawing


def build() -> Path:
    overview = json.loads((ROOT / "artifacts" / "multitrait" / "evaluation.json").read_text(encoding="utf-8"))
    story = cover()
    story += section("Vyskumy ciel a rozsah", "01 / suhrn")
    story += [
        p("Projekt aplikuje jednu reprodukovatelnu auditnu architekturu na vajce, arasidy, kravske mlieko, spolocnu potravinovu predispoziciu, laktozu, celiakiu a histamin/DAO. Nezjednocuje vsak biologiu nasilu. Kazdy znak si zachovava vlastny typ modelu, silu dokazov, politiku proxy a pravidlo pre chybajuci marker."),
        p("Celiakia pouziva rozsiahle vazene jadro a HLA diplotyp. Vajce, arasidy, mlieko a spolocny panel su experimentálne multilokusove modely. Laktoza ostava jednovariantovym genotypovym pravidlom. Histamin/DAO ostava kandidatnym panelom aktivity enzymu."),
        banner("HLAVNY PRINCIP", "Rovnaky proces neznamena rovnake vedecke tvrdenie. Register, data, validacia a audit su jednotne; interpretacia zostava primerana dokazom.", BLUE),
    ]
    story += section("Modelova mapa", "02 / sedem modulov")
    story += [data_table([
        ["Znak", "Ciele", "Model", "Chybajuci ciel", "Hlavna hranica"],
        ["Vajce", "4", "multilokusovy aditivny", "population iba pre ML", "bez klinickej kalibracie"],
        ["Arasidy", "5", "HLA + kandidati", "population iba pre ML", "HLA markery mozu byt jeden LD signal"],
        ["Kravske mlieko", "5", "3 povinne proxy + 2 direct", "population iba pre ML", "mala kandidatna studia"],
        ["Spolocny panel", "3", "vseobecna potravinova alergia", "population iba pre ML", "nerozlisuje potraviny"],
        ["Laktoza", "1", "genotypove pravidlo", "bez imputacie", "populacna specificita"],
        ["Celiakia", "50", "GRS + HLA diplotyp", "direct/proxy/population", "relativna predispozicia"],
        ["Histamin / DAO", "3", "AOC1 alelovy sucet", "bez imputacie", "DAO aktivita nie diagnoza"],
    ], [29 * mm, 13 * mm, 40 * mm, 40 * mm, 45 * mm], small=True), PageBreak()]

    story += section("Forenzna datova logika", "03 / register a povod")
    story += [
        p("Kazdy zaznam uchovava simulovanu pravu davku, numericky vstup modelu, povod direct/proxy/population/missing, kvalitu, cele geneticke skore, vazene skore, triedu a fixny split. Populacne ocakavanie je numericky ML priznak s kvalitou 0, nie individualny genotyp."),
        data_table([
            ["Povod", "Numericky vstup", "Cele skore", "Kvalita", "Interpretacia"],
            ["direct", "davka 0/1/2", "0/1/2", "1,00", "priamo zisteny ciel"],
            ["proxy", "najpravdepodobnejsia davka", "0/1/2", "EUR r2", "odhad ciela, neistota osobitne"],
            ["population", "2 x frekvencia", "0", "0,00", "iba ML stabilizacia"],
            ["missing", "neutralny numericky vstup", "0", "0,00", "ziadna individualna informacia"],
        ], [27 * mm, 39 * mm, 29 * mm, 22 * mm, 50 * mm]),
        banner("MLIEKO", "Proxy rs115288876, rs63582760/rs10588133 a rs17388568 prispievaju do genetickeho skore vzdy celym cislom. Pravdepodobnost proxy odhadu zostava oddelena.", DARK),
    ]
    story += section("Synteticky experiment", "04 / data a splity")
    story += [
        info_cards([("CELIAKIA", "12 000"), ("KAZDY DALSÍ", "6 000"), ("SPOLU", "48 000")]),
        Spacer(1, 5 * mm),
        p("Kazdy dataset ma stratifikovane rozdelenie 60 % train, 20 % validation a 20 % test. Pat profilov pokrytia vytvara technicke stresove scenare. Ich nazvy pripominaju bezne exporty, ale nie su meranim kvality konkretnej znacky alebo revizie cipu."),
    ]
    story += bullets(["baseline: veduci marker, jeho kvalita a pokrytie", "additive: vsetky davky, kvalita a profil", "structured: additive vrstva plus parove statisticke interakcie a chybajucnost", "prah najvyssej triedy: zvoleny iba na validation splite", "test split: pouzity az po zafixovani prahu"])
    story += [PageBreak()]

    story += section("Komparativna validacia", "05 / test vysledky")
    rows = [["Znak", "Najlepsi", "Macro F1", "High recall", "High precision", "High FNR"]]
    names = {"egg":"Vajce","peanut":"Arasidy","milk":"Mlieko","shared":"Spolocny","lactose":"Laktoza","histamine":"Histamin"}
    for trait_id, row in overview["traits"].items():
        best_name = max(row["models"], key=lambda name: row["models"][name]["test"]["macro_f1"])
        test = row["models"][best_name]["test"]
        high = test["high_risk"]
        rows.append([names[trait_id], best_name, f"{test['macro_f1']:.3f}", f"{high['recall']:.3f}", f"{high['precision']:.3f}", f"{high['false_negative_rate']:.3f}"])
    story += [data_table(rows, [31 * mm, 27 * mm, 27 * mm, 28 * mm, 30 * mm, 24 * mm], small=True), Spacer(1, 6 * mm), metric_chart(overview)]
    story += [
        p("Structured interakcie neboli automaticky najlepsie. Pri piatich zo siestich novych modulov bol podla macro F1 lepsi aditivny alebo pravidlovy pristup. Tento negativny vysledok sa zachovava, pretoze projekt nesmie prisudzovat interakciam hodnotu bez dokazov."),
        banner("FALSE NEGATIVES", "Mliecny high-sensitivity prah dosahuje vysoky recall za cenu nizkej precision. Histaminovy panel nedosiahol ciel recall 0,95 a nesmie sa prezentovat ako vysokocitlivy skrining.", DARK),
    ]
    story += section("Interpretacia metrik", "06 / co vysledky znamenaju")
    story += bullets([
        "Confusion matrix, precision, recall, F1, ROC-AUC, PR-AUC a Brier score hodnotia zhodu so syntetickym oracle.",
        "Vysledky nie su klinickou citlivostou, specificitou ani diagnostickou AUC.",
        "Vyssie macro F1 nepotvrdzuje biologicku kauzalitu lokusov.",
        "Proxy r2 je technicka kvalita odhadu, nie klinicka spolahlivost interpretacie.",
        "Absolutne riziko vyzaduje fenotypovanu kohortu a kalibracny model.",
    ])
    story += [PageBreak()]

    story += section("Vedecke zdroje a sila dokazov", "07 / provenance")
    story += [data_table([
        ["Panel", "Primarny zdroj", "Pouzitie"],
        ["Vajce / spolocny", "Marenholz et al. 2017, 10.1038/s41467-017-01220-0", "GWAS lokusy a efekty"],
        ["Arasidy", "Hong et al. 2015, 10.1038/ncomms7304", "replikovane HLA markery"],
        ["Arasidy", "Asai et al. 2018, 10.1016/j.jaci.2017.09.015", "sugestivne kandidatne lokusy"],
        ["Mlieko", "Henneman et al. 2016, 10.1186/s13601-016-0096-9", "kandidatne asociacie"],
        ["Laktoza", "Enattah et al. 2002, PMID 11788828", "rs4988235 pravidlo"],
        ["Histamin / DAO", "Maintz et al. 2011, 10.1111/j.1398-9995.2011.02548.x", "AOC1 a aktivita DAO"],
        ["Celiakia", "PGS000316; Sharp 2020; Monsuur 2008", "GRS a HLA logika"],
    ], [28 * mm, 84 * mm, 55 * mm], small=True)]
    story += section("Akceptacny stav", "08 / grantovy vystup")
    story += [data_table([
        ["Poziadavka", "Doklad v projekte", "Stav"],
        ["Agregovane geneticke skore", "sedem explicitnych oracle modelov", "splnene metodicky"],
        ["Interakcie", "structured comparator; HLA diplotyp pri celiakii", "otestovane"],
        ["Forenzna presnost", "JSON registre, provenance, checksumy", "splnene"],
        ["Synteticke datasety", "48 000 pripadov a fixne splity", "splnene"],
        ["Metriky", "CM, precision, recall, F1, AUC, FNR, Brier", "splnene"],
        ["Komparativna studia", "baseline/additive/structured", "splnene"],
        ["Klinicka validacia", "nezavisla fenotypovana kohorta", "otvorene"],
        ["Externy system", "bod 6 bol zamerne vynechany", "mimo rozsahu"],
    ], [50 * mm, 82 * mm, 35 * mm], small=True)]
    story += section("Dalsie kroky", "09 / hranice odovzdania")
    story += bullets([
        "Odborna revizia kandidatnych panelov mlieko, arasidy a histamin/DAO.",
        "Nezavisla fenotypovana kohorta pre kazdy klinicky zamyslany vystup.",
        "Kalibracia absolutneho rizika, subgroup analyzy a prospektivny protokol.",
        "Oddelenie technickeho pokrytia cipu od klinickej diskriminacie.",
        "Volba licencie vlastnikom pred nemennym GitHub release.",
    ])
    story += [PageBreak()]
    story += section("Odovzdany balík", "10 / reprodukovatelnost")
    story += [
        p("Verzia 0.2.0 je publikovatelny GitHub balík bez serverovej zavislosti. Kazdy vystup ma jasny zdroj, verziu a kontrolny sucet. Staticka aplikacia vykona analyzu genotypoveho suboru lokalne v prehliadaci."),
        data_table([
            ["Artefakt", "Obsah", "Auditna funkcia"],
            ["trait_models_v1.json", "6 registrov mimo celiakie", "alely, vahy, proxy, zdroje"],
            ["celiac_model_v1.json", "50-markerovy celiakalny register", "GRS a HLA logika"],
            ["*_pilot_v1.csv.gz", "7 syntetickych datasetov", "train/validation/test material"],
            ["evaluation.json", "kompletne metriky modelov", "CM, F1, AUC, FNR, Brier"],
            ["site/assets/*.json", "browserove modely a audity", "lokalna reprodukcia vysledku"],
            ["checksums.sha256", "kontrolne sucty", "integrita release balika"],
        ], [47 * mm, 58 * mm, 62 * mm], small=True),
    ]
    story += section("Kontrolny zoznam pred klinickou etapou", "11 / stop podmienky")
    story += bullets([
        "Schvalit protokol a primarny klinicky endpoint pre kazdy znak.",
        "Ziskat nezavisle fenotypovane a populacne primerane data.",
        "Zafixovat model pred otvorenim externej testovacej kohorty.",
        "Reportovat kalibraciu, subgroup vykon a rozhodovacie krivky.",
        "Zachovat oddelenie vyskumneho skore od diagnozy a liecebneho rozhodnutia.",
    ])
    story += [banner("ZAVER", "Projekt ma teraz spolocnu reprodukovatelnu vyskumy vrstvu pre vsetky znaky. Akceptovatelnost klinickych tvrdeni vsak zostava zavisla od realnych fenotypovanych dat.", BLUE)]
    OUT.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    document(OUTPUT).build(story)
    shutil.copyfile(OUTPUT, DOWNLOADS / OUTPUT.name)
    return OUTPUT


if __name__ == "__main__":
    print(build().relative_to(ROOT))
