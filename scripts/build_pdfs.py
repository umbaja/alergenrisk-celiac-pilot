from __future__ import annotations

import json
import shutil
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"
DOWNLOADS = ROOT / "site" / "downloads"

BLUE = colors.HexColor("#338FBA")
DARK = colors.HexColor("#2D6B84")
INK = colors.HexColor("#2D3D45")
MUTED = colors.HexColor("#687A83")
LINE = colors.HexColor("#CDDDE3")
PALE = colors.HexColor("#E6F2F7")
MINT = colors.HexColor("#DFF1ED")
BG = colors.HexColor("#F3F8FA")
WHITE = colors.white


def register_fonts() -> None:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("Nu3Regular", regular))
        pdfmetrics.registerFont(TTFont("Nu3Bold", bold))
    else:
        pdfmetrics.registerFont(TTFont("Nu3Regular", "DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("Nu3Bold", "DejaVuSans-Bold.ttf"))


register_fonts()

STYLES = getSampleStyleSheet()
STYLES.add(ParagraphStyle(name="CoverBrand", fontName="Nu3Bold", fontSize=9, leading=12, textColor=DARK, spaceAfter=28))
STYLES.add(ParagraphStyle(name="Eyebrow", fontName="Nu3Bold", fontSize=8, leading=11, textColor=BLUE, spaceBefore=8, spaceAfter=7, tracking=1.0))
STYLES.add(ParagraphStyle(name="CoverTitle", fontName="Nu3Bold", fontSize=33, leading=34, textColor=INK, spaceAfter=16))
STYLES.add(ParagraphStyle(name="CoverLead", fontName="Nu3Regular", fontSize=12, leading=18, textColor=MUTED, spaceAfter=20))
STYLES.add(ParagraphStyle(name="H1x", fontName="Nu3Bold", fontSize=23, leading=27, textColor=INK, spaceBefore=2, spaceAfter=12))
STYLES.add(ParagraphStyle(name="H2x", fontName="Nu3Bold", fontSize=14, leading=18, textColor=DARK, spaceBefore=15, spaceAfter=8))
STYLES.add(ParagraphStyle(name="H3x", fontName="Nu3Bold", fontSize=10, leading=14, textColor=DARK, spaceBefore=9, spaceAfter=5))
STYLES.add(ParagraphStyle(name="Bodyx", fontName="Nu3Regular", fontSize=9.2, leading=14, textColor=INK, spaceAfter=7))
STYLES.add(ParagraphStyle(name="Smallx", fontName="Nu3Regular", fontSize=7.5, leading=10.5, textColor=MUTED, spaceAfter=4))
STYLES.add(ParagraphStyle(name="Whitex", fontName="Nu3Regular", fontSize=9, leading=13, textColor=WHITE))
STYLES.add(ParagraphStyle(name="WhiteBold", fontName="Nu3Bold", fontSize=10, leading=13, textColor=WHITE))
STYLES.add(ParagraphStyle(name="CenterSmall", fontName="Nu3Regular", fontSize=7.5, leading=10, alignment=TA_CENTER, textColor=MUTED))


def p(text: str, style: str = "Bodyx") -> Paragraph:
    return Paragraph(text, STYLES[style])


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(f"• {item}", ParagraphStyle(name=f"bullet-{index}-{len(item)}", parent=STYLES["Bodyx"], leftIndent=11, firstLineIndent=-8, spaceAfter=4)) for index, item in enumerate(items)]


def banner(title: str, text: str, color=DARK) -> Table:
    table = Table([[p(title, "WhiteBold"), p(text, "Whitex")]], colWidths=[48 * mm, 119 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def info_cards(items: list[tuple[str, str]], width=55 * mm) -> Table:
    cells = []
    for label, value in items:
        cells.append(Paragraph(f"<font color='#2D6B84' size='7'><b>{label}</b></font><br/><font size='15'><b>{value}</b></font>", STYLES["Bodyx"]))
    table = Table([cells], colWidths=[width] * len(cells), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE), ("BOX", (0, 0), (-1, -1), .7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), .7, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 11), ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    return table


def data_table(rows: list[list[object]], widths: list[float], small=False) -> Table:
    formatted = []
    for row_index, row in enumerate(rows):
        style = "WhiteBold" if row_index == 0 else ("Smallx" if small else "Bodyx")
        formatted.append([cell if hasattr(cell, "wrap") else p(str(cell), style) for cell in row])
    table = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND", (0, 1), (-1, -1), WHITE), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F7FBFC")]),
        ("GRID", (0, 0), (-1, -1), .5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def metrics_chart(models: dict) -> Drawing:
    drawing = Drawing(470, 145)
    drawing.add(Rect(0, 0, 470, 145, fillColor=WHITE, strokeColor=LINE, strokeWidth=.6))
    metrics = [("Accuracy", "accuracy"), ("Macro F1", "macro_f1")]
    names = ["baseline", "additive", "structured"]
    shades = [colors.HexColor("#A7CAD8"), colors.HexColor("#70AAC3"), BLUE]
    x0 = 54
    for metric_index, (label, key) in enumerate(metrics):
        group_x = x0 + metric_index * 205
        drawing.add(String(group_x, 120, label, fontName="Nu3Bold", fontSize=9, fillColor=DARK))
        for index, name in enumerate(names):
            value = float(models[name]["test"][key])
            y = 91 - index * 27
            drawing.add(String(group_x, y + 3, name, fontName="Nu3Regular", fontSize=7.5, fillColor=MUTED))
            drawing.add(Rect(group_x + 58, y, 112, 11, fillColor=PALE, strokeColor=None))
            drawing.add(Rect(group_x + 58, y, 112 * value, 11, fillColor=shades[index], strokeColor=None))
            drawing.add(String(group_x + 174, y + 2, f"{value:.3f}", fontName="Nu3Bold", fontSize=7.5, fillColor=INK))
    return drawing


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
    canvas.drawString(doc.leftMargin, 10 * mm, "NU3GEN / ALERGENRISK CELIAC PILOT")
    canvas.setFont("Nu3Regular", 7)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - doc.rightMargin, 10 * mm, f"VÝSKUMNÝ VÝSTUP  |  {canvas.getPageNumber():02d}")
    canvas.restoreState()


def document(path: Path, pagesize=A4) -> BaseDocTemplate:
    doc = BaseDocTemplate(str(path), pagesize=pagesize, leftMargin=21 * mm, rightMargin=21 * mm, topMargin=20 * mm, bottomMargin=23 * mm, title=path.stem, author="NU3GEN")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")
    doc.addPageTemplates(PageTemplate(id="standard", frames=[frame], onPage=page_background))
    return doc


def cover(title: str, subtitle: str, code: str, facts: list[tuple[str, str]]) -> list:
    return [
        p("NU3GEN / ALERGENRISK / PARALELNÝ VÝSKUMNÝ PILOT", "CoverBrand"),
        Spacer(1, 24 * mm), p(code.upper(), "Eyebrow"), p(title, "CoverTitle"), p(subtitle, "CoverLead"),
        Spacer(1, 8 * mm), info_cards(facts), Spacer(1, 14 * mm),
        banner("STATUS DOKUMENTU", "Verzia 0.1.0, 14. október 2026. Verejný výskumný výstup. Výsledky nie sú klinickou validáciou ani diagnózou."),
        PageBreak(),
    ]


def section(title: str, kicker: str) -> list:
    return [p(kicker.upper(), "Eyebrow"), p(title, "H1x")]


def build_research(metrics: dict) -> Path:
    path = OUT / "AlergenRisk_Celiac_Pilot_Vyskumna_studia.pdf"
    story = cover("Výskumná štúdia", "Holistický polygénny model celiakálnej predispozície a jeho syntetická algoritmická validácia.", "dokument 01 / vedecký rámec", [("PRÍPADY", "12 000"), ("MARKERY", "50"), ("MODELY", "3")])
    story += section("Abstrakt", "01 / kontext")
    story += [p("Cieľom pilotu je overiť, či možno genetickú logiku celiakálneho panelu previesť do explicitného, reprodukovateľného a strojovo čitateľného procesu. Model neredukuje výsledok na prítomnosť jednej rizikovej mutácie. Kombinuje 42 aditívnych lokusov, 8 HLA tag markerov, diplotypový HLA člen a kvalitu každého genetického dôkazu."),
              p("Na 12 000 syntetických prípadoch sa porovnali tri modely. Najlepší structured model dosiahol macro F1 0,880 a ROC-AUC 0,980 pre rozlíšenie vysoko predisponovanej triedy. Tieto hodnoty merajú vernosť voči syntetickému oracle, nie klinickú predikciu celiakie."),
              banner("HLAVNÝ ZÁVER", "Pilot spĺňa reprodukovateľnú dátovú a validačnú vrstvu grantového zámeru pre celiakiu. Klinické tvrdenia zostávajú podmienené externou fenotypovanou kohortou.", BLUE)]
    story += section("Vedecké východiská", "02 / zdroje")
    story += [p("Jadro aditívneho skóre vychádza z publikovaného GRS42 a záznamu PGS000316. Sharp a kol. opísali 42-SNP genetické rizikové skóre celiakie a jeho výkon v európskych súboroch. HLA komponent využíva tagovacie princípy opísané Monsuurom a kol. Referenčné hranice sú odvodené z modelovanej EUR/CEU distribúcie."),
              data_table([["Vrstva", "Rozsah", "Úloha"], ["Aditívne jadro", "42 lokusov", "Súčet dávka efektovej alely x logaritmická váha"], ["HLA", "8 tag SNP", "Odhad DQ2.5, DQ8, DQ2.2 a DQ7.5"], ["Neistota", "50 indikátorov", "Rozlíšenie direct, proxy a population"], ["Interakcie", "6 príznakov", "HLA páry, HLA x jadro, chýbanie x jadro"]], [33 * mm, 35 * mm, 99 * mm])]
    story += section("Metódy", "03 / experiment")
    story += [p("Generátor vytvoril genotypové dávky podľa EUR frekvencií a HLA diplotypov. Každá syntetická vzorka prešla jedným z piatich stresových profilov pokrytia. Oracle skóre a trieda boli určené nezávisle od trénovania. Dáta boli stratifikovane rozdelené na train, validation a test. Prah vysokej triedy sa vybral výlučne na validačnom splite s cieľom recall aspoň 0,95."),
              info_cards([("TRAIN", "7 198"), ("VALIDATION", "2 401"), ("TEST", "2 401")]),
              p("Rozhodovacie hranice referenčného modelu sú q20 = 1,20 a q80 = 4,06. Pozorované skóre sa zaokrúhľuje na mriežku 0,02 bodu. Ak chýba cieľový marker, poradie spracovania je direct, auditovaná proxy, potom neisté populačné očakávanie."), PageBreak()]
    story += section("Výsledky", "04 / komparatívna analýza")
    rows = [["Model", "Príznaky", "Accuracy", "Macro F1", "High recall", "High precision", "FNR", "ROC-AUC"]]
    for name in ("baseline", "additive", "structured"):
        model = metrics["models"][name]
        test = model["test"]
        high = test["high_risk"]
        rows.append([name, model["feature_count"], f"{test['accuracy']:.3f}", f"{test['macro_f1']:.3f}", f"{high['recall']:.3f}", f"{high['precision']:.3f}", f"{high['false_negative_rate']:.3f}", f"{high['roc_auc']:.3f}"])
    story += [data_table(rows, [24 * mm, 17 * mm, 21 * mm, 21 * mm, 22 * mm, 24 * mm, 16 * mm, 21 * mm], small=True), Spacer(1, 7 * mm), metrics_chart(metrics["models"]),
              p("Baseline dosiahol recall 1,000 iba pri prahu, ktorý označil všetkých testovaných ako pozitívnych, a preto má precision 0,200 a špecificitu 0. Structured model zachoval recall približne 0,95 a zvýšil precision na 0,71."),
              banner("INTERPRETÁCIA", "Zlepšenie structured modelu ukazuje prínos agregovaného panelu a explicitnej štruktúry. Nejde o dôkaz biologickej epistázy ani o klinickú účinnosť.", DARK)]
    story += section("Diskusia a obmedzenia", "05 / hranice")
    story += bullets(["Syntetické triedy kopírujú definovaný genetický oracle; nejde o diagnózu.", "Referenčné frekvencie a LD sú viazané na EUR/CEU a nemožno ich bez validácie preniesť na iné populácie.", "Štyri research-extension lokusy nie sú súčasťou pôvodnej klinickej validácie GRS42.", "Simulované čipové profily sú stresové scenáre, nie meranie konkrétnej komerčnej revízie.", "Pred klinickým použitím je potrebná externá kohorta, kalibrácia absolútneho rizika a odborné posúdenie."])
    story += section("Referencie", "06 / primárne zdroje")
    story += [p("1. PGS Catalog. PGS000316 - Coeliac disease genetic risk score. https://www.pgscatalog.org/score/PGS000316/", "Smallx"), p("2. Sharp SA et al. A single nucleotide polymorphism genetic risk score to aid diagnosis of coeliac disease. Aliment Pharmacol Ther. 2020. PMID 32790217.", "Smallx"), p("3. Monsuur AJ et al. Effective detection of human leukocyte antigen risk alleles in celiac disease using tag SNPs. PLoS One. 2008. PMID 18509540.", "Smallx"), p("4. 1000 Genomes Project Phase 3. GRCh37 phased reference data. https://www.internationalgenome.org/data-portal/data-collection/phase3/", "Smallx")]
    story += section("Dostupnosť a audit", "07 / výstup")
    story += [p("Modelový register, syntetický dataset, zdrojový kód, metriky a kontrolné súčty sú publikované v jednom verzovanom GitHub repozitári. Verejná aplikácia umožňuje stiahnuť dátový slovník, syntetickú demo vzorku a metodické dokumenty."),
              data_table([["Artefakt", "Úloha"], ["celiac_model_v1.json", "Definícia genetickej logiky"], ["celiac_pilot_v1.csv.gz", "Anotovaný syntetický tréningový materiál"], ["evaluation.json", "Úplné validačné metriky"], ["checksums.sha256", "Kontrola integrity release balíka"]], [65 * mm, 102 * mm], small=True),
              banner("TRVALÁ HRANICA", "Bez nezávislej klinickej kohorty sa výstup smie označovať iba ako výskumná genetická predispozícia a algorithmic fidelity.", DARK)]
    document(path).build(story)
    return path


def build_technical(metrics: dict) -> Path:
    path = OUT / "AlergenRisk_Celiac_Pilot_Technicka_sprava.pdf"
    story = cover("Technická správa", "Architektúra dát, inferenčný algoritmus, modelové artefakty a reprodukovateľnosť GitHub vydania.", "dokument 02 / implementácia", [("SCHÉMA", "217"), ("ML VSTUP", "111"), ("BUILD", "GRCh37")])
    story += section("Rozsah systému", "01 / účel")
    story += [p("Pilot je samostatný statický projekt publikovaný cez GitHub Pages. Pôvodné rozhranie AlergenRisk nemení. Verejná aplikácia poskytuje lokálny výpočet, prehliadač syntetických dát, audit SNP/proxy a dokumentačný balík. Nie je potrebný server ani cloudová analytická služba."), banner("OCHRANA VSTUPU", "Genotypový súbor sa parsuje a vyhodnocuje v prehliadači. Aplikácia ho neodosiela na server.", BLUE)]
    story += section("Architektúra", "02 / vrstvy")
    story += [data_table([["Vrstva", "Artefakt", "Zodpovednosť"], ["Register", "config/celiac_model_v1.json", "Lokusy, alely, váhy, HLA a populácia"], ["Proxy audit", "config/celiac_proxy_audit_v1.json", "EUR r², D', mapovanie alel, zdroj"], ["Dáta", "data/synthetic/*.csv.gz", "Syntetické prípady a fixné splity"], ["Model", "artifacts/models/*.npz", "Normalizácia, váhy a threshold"], ["Web export", "site/assets/*.json", "Prenositeľné artefakty pre prehliadač"], ["Audit", "artifacts/release-manifest.json", "SHA-256, veľkosť a verzia"]], [30 * mm, 59 * mm, 78 * mm], small=True)]
    story += section("Inferenčný algoritmus", "03 / pravidlá")
    story += [p("Parser prijíma bežné textové, CSV a TSV exporty s rsID a dvojpísmenovým genotypom. Každý z 50 cieľov sa vyhodnotí presne raz."),
              data_table([["Priorita", "Zdroj", "Výpočet", "Kvalita"], ["1", "direct", "Celé číslo 0, 1 alebo 2 podľa efektovej alely", "1,00"], ["2", "proxy", "Očakávaná dávka z podmienených pravdepodobností", "EUR r²"], ["3", "population", "2 x referenčná frekvencia alebo HLA frekvencia", "0,00"]], [18 * mm, 32 * mm, 86 * mm, 31 * mm]),
              p("Transparentné skóre sa počíta ako HLA diplotypová váha plus vážený súčet aditívnych dávok. Genetické vstupy zostávajú oddelené od indikátorov kvality. Výsledok s pokrytím menším než 50 % sa označí ako nedostatočný."), PageBreak()]
    story += section("Modelové príznaky", "04 / structured model")
    story += [info_cards([("DÁVKY", "50"), ("KVALITA", "50"), ("PROFIL", "5")]), Spacer(1, 5 * mm), info_cards([("HLA PÁRY", "4"), ("HLA X JADRO", "1"), ("MISSING X JADRO", "1")]),
              p("Spolu 111 príznakov. Päť profilových indikátorov opisuje complete, 23andme_like, myheritage_like, dnaera_like a sparse_stress. Identifikácia profilu je pomocná stresová vrstva; reálna dostupnosť markerov sa určuje z obsahu súboru."),
              banner("ODDELENÉ VÝSTUPY", "Rozhranie zobrazuje transparentné referenčné skóre a výskumnú ML triedu osobitne. ML pravdepodobnosti sú pravdepodobnosti tried syntetického oracle, nie ochorenia.", DARK)]
    story += section("Reprodukcia", "05 / build a test")
    story += [p("Referenčný postup pre Python 3.11:"), data_table([["Krok", "Príkaz"], ["Inštalácia", "python -m pip install -r requirements-lock.txt"], ["Pipeline", "python scripts/run_pipeline.py --samples 12000 --seed 20261014"], ["Web export", "python scripts/build_release_assets.py"], ["Python testy", "python -m unittest discover -s tests -v"], ["Web testy", "node --test tests/web_app.test.mjs"]], [35 * mm, 132 * mm], small=True),
              p(f"Referenčný dataset: {metrics['dataset']['rows']} riadkov, {metrics['dataset']['columns']} stĺpcov. Manifest SHA-256: {metrics['manifest_sha256']}. Dataset SHA-256: {metrics['dataset']['sha256']}.", "Smallx")]
    story += section("Prevádzkové kontroly", "06 / release")
    story += bullets(["GitHub Actions spúšťa Python testy, zmenšený validačný beh, export release artefaktov a JavaScript testy.", "GitHub Pages publikuje výhradne obsah priečinka site.", "Release manifest eviduje verziu, SHA-256 a veľkosť kľúčových súborov.", "Licencia musí byť pred formálnym odovzdaním potvrdená vlastníkom projektu.", "Externá klinická validácia a integrácia s inou platformou nie sú súčasťou verzie 0.1.0."])
    document(path).build(story)
    return path


def flow_diagram() -> Drawing:
    drawing = Drawing(470, 320)
    labels = ["1. Vedecké zdroje", "2. Modelový register", "3. Syntetický generátor", "4. Fixné splity", "5. Tréning modelov", "6. Validácia", "7. Release a audit"]
    colors_list = [PALE, MINT, PALE, MINT, PALE, MINT, colors.HexColor("#CFE8F2")]
    for index, label in enumerate(labels):
        x = 5 + index * 115 if index < 4 else 62 + (index - 4) * 120
        y = 220 if index < 4 else 85
        drawing.add(Rect(x, y, 105, 52, rx=5, ry=5, fillColor=colors_list[index], strokeColor=DARK, strokeWidth=.8))
        drawing.add(String(x + 52.5, y + 30, label, textAnchor="middle", fontName="Nu3Bold", fontSize=7.1, fillColor=INK))
        if index < 3:
            drawing.add(String(x + 107, y + 24, "→", fontName="Nu3Bold", fontSize=14, fillColor=BLUE))
        if 4 <= index < 6:
            drawing.add(String(x + 108, y + 24, "→", fontName="Nu3Bold", fontSize=14, fillColor=BLUE))
    drawing.add(String(232, 185, "↓", fontName="Nu3Bold", fontSize=18, fillColor=BLUE))
    drawing.add(String(235, 30, "Každý krok vytvára verzovaný a auditovateľný artefakt", textAnchor="middle", fontName="Nu3Regular", fontSize=9, fillColor=MUTED))
    return drawing


def build_process() -> Path:
    path = OUT / "AlergenRisk_Celiac_Pilot_Procesna_mapa.pdf"
    story = cover("Procesná mapa", "Riadený tok od vedeckých dôkazov cez syntetické dáta po testovateľný GitHub release.", "dokument 03 / proces", [("BRÁNY", "6"), ("KROKY", "7"), ("VÝSTUP", "v0.1.0")])
    story += section("End-to-end tok", "01 / mapa")
    story += [flow_diagram(), banner("ZÁSADA", "Tréningový model sa učí reprodukovať explicitný oracle. Testovacia množina zostáva uzamknutá až do zafixovania prahu na validačnej množine.", DARK), PageBreak()]
    story += section("Procesné kroky", "02 / zodpovednosť a dôkaz")
    story += [data_table([["Krok", "Vstup", "Kontrola", "Výstup"], ["1 Zdroje", "GWAS, PGS, HLA literatúra", "Primárny zdroj a populácia", "Evidence register"], ["2 Register", "Efektové alely, váhy", "Schéma a unikátnosť rsID", "celiac_model_v1.json"], ["3 Generátor", "Register, seed", "Deterministická reprodukcia", "Syntetické genotypy"], ["4 Splity", "Anotovaný dataset", "Stratifikácia a neprekrývanie", "Train, validation, test"], ["5 Tréning", "Train split", "Rovnaké cieľové triedy", "3 modely"], ["6 Validácia", "Validation a test", "Threshold bez leakage", "Metriky a predikcie"], ["7 Release", "Artefakty", "Testy a SHA-256", "GitHub Pages + PDF"]], [24 * mm, 45 * mm, 52 * mm, 46 * mm], small=True)]
    story += section("Kontrolné brány", "03 / quality gates")
    story += [data_table([["Brána", "Podmienka prijatia", "Stav"], ["Evidence", "Každý marker má alelu, váhu alebo HLA úlohu a zdroj", "splnené"], ["Data", "Rovnaký seed vytvorí rovnaké dáta", "testované"], ["Leakage", "Test neovplyvňuje výber high-risk prahu", "splnené"], ["Performance", "Confusion matrix, precision, recall, F1, AUC a FNR", "splnené"], ["Interpretation", "Syntetická fidelity sa neoznačuje ako klinická validácia", "splnené"], ["Release", "Manifest, testy, checksumy a dokumentácia", "splnené"]], [28 * mm, 108 * mm, 31 * mm])]
    story += section("Rozhodovanie pri chýbajúcom SNP", "04 / proxy vetva")
    story += [data_table([["Rozhodnutie", "Áno", "Nie"], ["Je prítomný cieľový rsID?", "Použiť direct dávku 0/1/2", "Skontrolovať proxy katalóg"], ["Je prítomná proxy s EUR r² >= 0,90?", "Použiť očakávanú dávku a kvalitu r²", "Použiť population a kvalitu 0"], ["Je pokrytie aspoň 50 %?", "Zobraziť relatívnu triedu", "Označiť ako nedostatočné"]], [58 * mm, 55 * mm, 54 * mm]), banner("AUDITNÁ STOPA", "Pre každý cieľ sa uchová rsID, pôvod, dávka, proxy genotyp, r² a kvalita. Populačná hodnota sa nikdy neprezentuje ako genotyp osoby.", BLUE)]
    story += section("Prevádzkový checklist", "05 / odovzdanie")
    story += bullets(["Spustiť Python a JavaScript testy na čistom checkout-e.", "Porovnať SHA-256 kľúčových artefaktov s release manifestom.", "Overiť dostupnosť datasetu, dátového slovníka, SNP auditu a štyroch PDF na GitHub Pages.", "Zachovať upozornenie, že výstup nie je diagnóza ani klinická pravdepodobnosť.", "Pred nemenným release potvrdiť licenčný režim vlastníkom projektu."])
    document(path).build(story)
    return path


def build_validation(metrics: dict) -> Path:
    path = OUT / "AlergenRisk_Celiac_Pilot_Validacna_sprava.pdf"
    story = cover("Validačná správa", "Komparatívne metriky, confusion matrices, high-risk prah a akceptačné hranice syntetického pilotu.", "dokument 04 / validácia", [("TEST", "2 401"), ("BEST F1", "0,880"), ("HIGH RECALL", "95,0 %")])
    story += section("Validačný dizajn", "01 / protokol")
    story += [p("Hodnotenie je algoritmickou validáciou voči syntetickému referenčnému oracle. Train split slúžil na odhad parametrov. Validation split slúžil na výber high-risk prahu. Test split bol použitý jednorazovo na finálne porovnanie."),
              info_cards([("TRAIN", "59,98 %"), ("VALIDATION", "20,01 %"), ("TEST", "20,01 %")]),
              banner("PRIORITA FALSE NEGATIVES", "Prah sa vyberal s cieľom recall vysoko predisponovanej triedy aspoň 0,95. Výsledná precision sa reportuje súčasne, aby sa zabránilo zavádzajúcej interpretácii samotného recall.", DARK)]
    story += section("Výsledky modelov", "02 / test split")
    rows = [["Model", "Accuracy", "Macro F1", "High precision", "High recall", "High FNR", "ROC-AUC", "PR-AUC"]]
    for name in ("baseline", "additive", "structured"):
        test = metrics["models"][name]["test"]
        high = test["high_risk"]
        rows.append([name, f"{test['accuracy']:.3f}", f"{test['macro_f1']:.3f}", f"{high['precision']:.3f}", f"{high['recall']:.3f}", f"{high['false_negative_rate']:.3f}", f"{high['roc_auc']:.3f}", f"{high['pr_auc']:.3f}"])
    story += [data_table(rows, [25 * mm, 20 * mm, 21 * mm, 24 * mm, 21 * mm, 18 * mm, 19 * mm, 19 * mm], small=True), Spacer(1, 5 * mm), metrics_chart(metrics["models"])]
    story += section("Confusion matrices", "03 / tri triedy")
    for name in ("baseline", "additive", "structured"):
        matrix = metrics["models"][name]["test"]["confusion_matrix"]
        story += [KeepTogether([p(name.upper(), "H3x"), data_table([["Skutočná / predikovaná", "low", "typical", "high"], ["low", *matrix[0]], ["typical", *matrix[1]], ["high", *matrix[2]]], [57 * mm, 36 * mm, 37 * mm, 37 * mm], small=True), Spacer(1, 3 * mm)])]
    story += [PageBreak()]
    story += section("High-risk analýza", "04 / minimalizácia FN")
    high_rows = [["Model", "Threshold", "TP", "FP", "FN", "TN", "Recall", "Precision", "Specificity"]]
    for name in ("baseline", "additive", "structured"):
        high = metrics["models"][name]["test"]["high_risk"]
        high_rows.append([name, f"{high['threshold']:.2f}", high["tp"], high["fp"], high["fn"], high["tn"], f"{high['recall']:.3f}", f"{high['precision']:.3f}", f"{high['specificity']:.3f}"])
    story += [data_table(high_rows, [24 * mm, 18 * mm, 14 * mm, 14 * mm, 14 * mm, 14 * mm, 21 * mm, 22 * mm, 26 * mm], small=True),
              p("Structured model identifikoval 457 z 481 high prípadov a vynechal 24. Pri tom zachoval 1 733 true negatives a vytvoril 187 false positives. Baseline síce nevynechal žiadny high prípad, ale označil všetkých 2 401 testovaných za pozitívnych."),
              banner("AKCEPTÁCIA", "Structured model je vybraný ako preferovaný model pre ďalšiu výskumnú etapu, pretože spĺňa cieľ recall a má najvyššie macro F1, ROC-AUC aj PR-AUC.", BLUE)]
    story += section("Grantová akceptačná matica", "05 / stav")
    story += [data_table([["Požiadavka", "Dôkaz", "Stav"], ["Holistické skóre", "42 lokusov + HLA diplotyp", "splnené pre pilot"], ["Interakcie", "HLA páry a 2 štatistické interakcie", "pilotne splnené"], ["Forenzná logika", "JSON register, provenance, checksum", "splnené"], ["Syntetické dáta", "12 000 anotovaných prípadov", "splnené"], ["Metriky", "CM, precision, recall, F1, AUC, FNR", "splnené"], ["Komparatívna štúdia", "3 modely na rovnakom test splite", "splnené"], ["Externá integrácia", "zámerne vynechaná v tejto etape", "mimo rozsahu"], ["Klinická validácia", "nezávislá fenotypovaná kohorta", "otvorené"]], [49 * mm, 86 * mm, 32 * mm], small=True)]
    story += section("Reziduálne riziká", "06 / ďalší krok")
    story += bullets(["Potvrdiť licenciu a vytvoriť nemenný GitHub release v0.1.0.", "Vykonať odbornú revíziu research-extension lokusov.", "Pred klinickými tvrdeniami pripraviť protokol externej validácie, kalibráciu a subgroup analýzy.", "Po získaní reálnych dát oddeliť technické pokrytie čipu od klinickej diskriminácie modelu."])
    document(path).build(story)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    metrics = json.loads((ROOT / "artifacts" / "metrics" / "evaluation.json").read_text(encoding="utf-8"))
    outputs = [build_research(metrics), build_technical(metrics), build_process(), build_validation(metrics)]
    for output in outputs:
        shutil.copyfile(output, DOWNLOADS / output.name)
        print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
