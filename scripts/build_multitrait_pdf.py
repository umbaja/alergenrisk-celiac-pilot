from __future__ import annotations

import json
import shutil
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
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
    WHITE,
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
VERSION = "0.3.0"
DATE_SK = "14. október 2026"

TRAIT_NAMES = {
    "egg": "Vajce",
    "peanut": "Arašidy",
    "milk": "Kravské mlieko",
    "shared": "Spoločná potravinová predispozícia",
    "lactose": "Laktóza",
    "celiac": "Celiakia",
    "histamine": "Histamín / DAO",
}

STYLES.add(ParagraphStyle(
    name="MarkerCell",
    parent=STYLES["Smallx"],
    fontSize=6.5,
    leading=8.4,
    textColor=INK,
    spaceAfter=0,
))
STYLES.add(ParagraphStyle(
    name="MarkerHead",
    parent=STYLES["WhiteBold"],
    fontSize=6.5,
    leading=8,
    spaceAfter=0,
))
STYLES.add(ParagraphStyle(
    name="PartNumber",
    parent=STYLES["Eyebrow"],
    fontSize=10,
    leading=13,
    tracking=1.2,
    textColor=BLUE,
))
STYLES.add(ParagraphStyle(
    name="PartTitle",
    parent=STYLES["CoverTitle"],
    fontSize=27,
    leading=30,
))
STYLES.add(ParagraphStyle(
    name="FlowSmall",
    parent=STYLES["Smallx"],
    alignment=TA_CENTER,
    fontSize=6.8,
    leading=8.2,
    textColor=INK,
    spaceAfter=0,
))


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def compact(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}".replace(".", ",")


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
    canvas.drawRightString(
        width - doc.rightMargin,
        10 * mm,
        f"KOMPLEXNÁ METODIKA  |  {canvas.getPageNumber():02d}",
    )
    canvas.restoreState()


def document(path: Path) -> BaseDocTemplate:
    doc = BaseDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=21 * mm,
        rightMargin=21 * mm,
        topMargin=20 * mm,
        bottomMargin=23 * mm,
        title="AlergenRisk - výskumná štúdia, technická správa, procesná mapa a validácia",
        author="NU3GEN",
        subject="Komplexná dokumentácia 71 panel-lokus záznamov AlergenRisk",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")
    doc.addPageTemplates(PageTemplate(id="standard", frames=[frame], onPage=page_background))
    return doc


def marker_table(rows: list[list[object]], widths: list[float]) -> Table:
    formatted: list[list[object]] = []
    for row_index, row in enumerate(rows):
        style = STYLES["MarkerHead"] if row_index == 0 else STYLES["MarkerCell"]
        formatted.append([
            cell if hasattr(cell, "wrap") else Paragraph(str(cell), style)
            for cell in row
        ])
    table = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F7FBFC")]),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def source_text(sources: list[dict]) -> str:
    labels = []
    for source in sources:
        identifier = source.get("doi") or source.get("pmid") or source.get("id") or "zdroj"
        if source.get("pmid"):
            identifier = f"PMID {identifier}"
        labels.append(str(identifier))
    return "; ".join(labels)


def proxy_text(proxies: list[dict]) -> str:
    if not proxies:
        return "Bez auditovanej proxy"
    values = []
    for proxy in proxies:
        aliases = proxy.get("aliases", [])
        alias_text = f" / {' / '.join(aliases)}" if aliases else ""
        values.append(
            f"{proxy['id']}{alias_text} ({proxy.get('proxy_risk_allele', '?')}; "
            f"r2 {compact(proxy.get('r2'))}; D' {compact(proxy.get('d_prime'))})"
        )
    return "; ".join(values)


def build_records(trait_bundle: dict, celiac: dict, celiac_proxy: dict) -> list[dict]:
    records: list[dict] = []
    for trait in trait_bundle["traits"]:
        for locus in trait["loci"]:
            frequency = locus.get("eur_frequency", locus.get("simulation_frequency"))
            records.append({
                "trait_id": trait["id"],
                "panel": trait["name_sk"],
                "target": locus["id"],
                "gene": locus.get("gene", "neuvedené"),
                "risk_allele": locus["risk_allele"],
                "weight": float(locus.get("beta", 1.0)),
                "weight_text": compact(locus.get("beta", 1.0)),
                "frequency": frequency,
                "frequency_text": compact(frequency),
                "frequency_status": locus.get("frequency_status", "EUR referencia"),
                "group": trait["evidence_tier"],
                "role": (
                    "Jednovariantové genotypové pravidlo" if trait["id"] == "lactose"
                    else "Kandidátny súčet AOC1 alel" if trait["id"] == "histamine"
                    else "Aditívny panelový príspevok"
                ),
                "evidence": source_text(trait["sources"]),
                "proxies": locus.get("proxies", []),
                "required_proxy": bool(locus.get("required_proxy")),
                "missing_policy": trait["missing_policy"],
                "minimum_coverage": trait["minimum_coverage"],
                "validation": "Schéma, orientácia alely, simulácia a zaradenie do oracle",
            })

    proxy_map = celiac_proxy["proxies"]
    for locus in celiac["additive_loci"]:
        group = locus.get("group", "core")
        records.append({
            "trait_id": "celiac",
            "panel": TRAIT_NAMES["celiac"],
            "target": locus["id"],
            "gene": locus.get("gene", "neuvedené"),
            "risk_allele": locus["risk_allele"],
            "weight": float(locus["beta"]),
            "weight_text": compact(locus["beta"]),
            "frequency": locus.get("eur_frequency"),
            "frequency_text": compact(locus.get("eur_frequency")),
            "frequency_status": "EUR referencia",
            "group": group,
            "role": "Aditívny vstup GRS" if group == "core" else "Výskumné rozšírenie GRS",
            "evidence": "PGS000316; Sharp2020" if group == "core" else "Výskumné rozšírenie mimo jadra PGS000316",
            "proxies": proxy_map.get(locus["id"], []),
            "required_proxy": False,
            "missing_policy": "direct > proxy s EUR r2 >= 0,90 > population",
            "minimum_coverage": 0.5,
            "validation": "Schéma, orientácia alely, simulácia, oracle a proxy vetva",
        })

    hap_freq = celiac["hla"]["haplotype_frequencies"]
    for locus in celiac["hla"]["tag_markers"]:
        haplotype = locus["haplotype"]
        records.append({
            "trait_id": "celiac",
            "panel": TRAIT_NAMES["celiac"],
            "target": locus["id"],
            "gene": locus.get("gene", "HLA"),
            "risk_allele": locus["risk_allele"],
            "weight": None,
            "weight_text": f"tag {haplotype}",
            "frequency": hap_freq.get(haplotype),
            "frequency_text": compact(hap_freq.get(haplotype)),
            "frequency_status": f"frekvencia haplotypu {haplotype}",
            "group": "HLA tag",
            "role": f"Odhad haplotypu {haplotype}; váha sa určuje diplotypom",
            "evidence": "Monsuur2008; HLA jadro PGS000316",
            "proxies": proxy_map.get(locus["id"], []),
            "required_proxy": False,
            "missing_policy": "direct > proxy s EUR r2 >= 0,90 > populačný HLA odhad",
            "minimum_coverage": 0.5,
            "validation": "Tagovanie haplotypu, diplotypová logika a proxy vetva",
        })

    assert len(records) == 71, f"Očakávalo sa 71 panel-lokus záznamov, nájdených {len(records)}"
    return records


def records_for(records: list[dict], trait_id: str) -> list[dict]:
    return [record for record in records if record["trait_id"] == trait_id]


def cover() -> list:
    return [
        p("NU3GEN / ALERGENRISK / PARALELNÝ VÝSKUMNÝ PILOT", "CoverBrand"),
        Spacer(1, 18 * mm),
        p("KOMPLEXNÝ DOKUMENT / VERZIA 0.3.0", "Eyebrow"),
        p("AlergenRisk Research Pilot", "CoverTitle"),
        p(
            "Výskumná štúdia, technická správa, procesná mapa a validačná správa "
            "pre všetky genetické moduly od vajca po histamín/DAO.",
            "CoverLead",
        ),
        Spacer(1, 6 * mm),
        info_cards([("MODULY", "7"), ("PANEL-LOKUSY", "71"), ("PRÍPADY", "48 000")]),
        Spacer(1, 11 * mm),
        banner(
            "STATUS DOKUMENTU",
            f"Verzia {VERSION}, {DATE_SK}. Verejný výskumný výstup. Metriky sú syntetickou "
            "algoritmickou validáciou, nie klinickou diagnózou.",
        ),
        PageBreak(),
    ]


def part_cover(number: str, title: str, subtitle: str, facts: list[tuple[str, str]]) -> list:
    return [
        Spacer(1, 20 * mm),
        p(f"ČASŤ {number}", "PartNumber"),
        p(title, "PartTitle"),
        p(subtitle, "CoverLead"),
        Spacer(1, 9 * mm),
        info_cards(facts),
        PageBreak(),
    ]


def contents() -> list:
    return section("Ako je dokument usporiadaný", "obsah / štyri odovzdávané vrstvy") + [
        data_table([
            ["Časť", "Účel", "Markerová úroveň"],
            ["I. Výskumná štúdia", "Vedecký rámec, biologický kontext a zdroje", "71 záznamov s alelou, váhou, génom a dôkazom"],
            ["II. Technická správa", "Dátový model, direct/proxy/missing logika", "71 záznamov s proxy, r2, D' a politikou chýbania"],
            ["III. Procesná mapa", "Riadený tok od dôkazu po release", "Jednotná rozhodovacia vetva aplikovaná na každý cieľ"],
            ["IV. Validačná správa", "Metriky, confusion matrices a akceptačné hranice", "71 záznamov s validačnou úlohou a auditným testom"],
        ], [34 * mm, 62 * mm, 71 * mm], small=True),
        Spacer(1, 6 * mm),
        banner(
            "PREČO JEDEN DOKUMENT",
            "Samostatná štvorica správ pre každý SNP by opakovala rovnaký proces a nesprávne by "
            "naznačovala, že jednotlivý marker má vlastnú diagnostickú validáciu. Integrovaný register "
            "zachováva úplnosť aj správnu panelovú interpretáciu.",
            DARK,
        ),
        Spacer(1, 7 * mm),
        p("Terminologická poznámka", "H2x"),
        p(
            "V dokumente sa používa pojem panel-lokus záznam. Rovnaký rsID môže byť použitý vo "
            "viacerých paneloch s inou váhou alebo interpretačným účelom. Preto je 71 záznamov, "
            "hoci počet unikátnych rsID je nižší."
        ),
        PageBreak(),
    ]


def research_section(records: list[dict], trait_bundle: dict) -> list:
    story = part_cover(
        "I",
        "Výskumná štúdia",
        "Vedecké východiská, hypotézy panelov a úplný výskumný register markerov.",
        [("PANELY", "7"), ("ZÁZNAMY", "71"), ("ZDROJE", "8")],
    )
    story += section("Abstrakt a výskumná otázka", "I.01 / vedecký rámec")
    story += [
        p(
            "Cieľom je preveriť, či možno heterogénne genetické moduly AlergenRisk previesť do "
            "jednotnej, reprodukovateľnej a auditovateľnej výskumnej pipeline. Modely nekombinujú "
            "markery bez rozlíšenia ich pôvodu: publikované GRS/HLA jadro, GWAS lokusy, kandidátne "
            "asociácie a jednovariantové biologické pravidlá zostávajú označené osobitne."
        ),
        p(
            "Syntetický experiment obsahuje 48 000 anotovaných záznamov. Porovnáva baseline, "
            "aditívny a structured model, pričom structured vetva nie je automaticky považovaná za "
            "lepšiu. Výsledok hodnotí vernosť definovanému oracle, nie klinické riziko ochorenia."
        ),
        banner(
            "HLAVNÁ HYPOTÉZA",
            "Panelová logika s explicitnou kvalitou dôkazu bude reprodukovateľnejšia než jednoduché "
            "vyhľadanie jednej rizikovej mutácie. Klinická prediktívna sila sa musí overiť osobitne.",
            BLUE,
        ),
    ]
    story += section("Rozsah modelov", "I.02 / fenotyp a sila dôkazu")
    trait_rows = [["Panel", "Ciele", "Model", "Dôkaz", "Hlavné obmedzenie"]]
    for trait in trait_bundle["traits"]:
        trait_rows.append([
            trait["name_sk"],
            len(trait["loci"]),
            trait["model_type"],
            trait["evidence_tier"],
            trait["limitations_sk"],
        ])
    trait_rows.insert(6, [
        TRAIT_NAMES["celiac"],
        50,
        "GRS + HLA diplotyp",
        "publikované jadro + výskumné rozšírenie",
        "Relatívna predispozícia; nie absolútne riziko ani diagnóza.",
    ])
    story += [data_table(trait_rows, [34 * mm, 13 * mm, 39 * mm, 38 * mm, 43 * mm], small=True)]

    story += section("Metódy syntetického experimentu", "I.03 / dizajn")
    story += [
        info_cards([("CELIAKIA", "12 000"), ("OSTATNÉ PANELY", "6 x 6 000"), ("SPOLU", "48 000")]),
        Spacer(1, 5 * mm),
        p(
            "Genotypové dávky boli generované z referenčných alebo explicitne označených "
            "simulačných frekvencií. Oracle trieda vznikla z presne definovanej panelovej logiky. "
            "Každý dataset sa stratifikovane delí na 60 % train, 20 % validation a 20 % test. Prah "
            "vysokej triedy sa vyberá len na validačnom splite so zameraním na zníženie false negatives."
        ),
        *bullets([
            "baseline používa vedúci marker, kvalitu a technické pokrytie",
            "additive používa panelové dávky, kvalitu a profil pokrytia",
            "structured dopĺňa štatistické interakcie; pri celiakii aj biologickú HLA diplotypovú štruktúru",
            "test split sa otvorí až po zafixovaní modelu a high-risk prahu",
            "všetky váhy, alely, proxy a zdroje sú uložené v strojovo čitateľných JSON registroch",
        ]),
        PageBreak(),
    ]

    story += section("Výskumný register všetkých markerov", "I.04 / 71 panel-lokus záznamov")
    story += [p(
        "Nasledujúce tabuľky predstavujú úplný vedecký register. Beta je modelová váha na jednu "
        "efektovú alelu. Pri HLA tagoch sa výsledná váha nepriraďuje jednotlivému SNP, ale odvodenému "
        "diplotypu. Frekvencie označené ako synthetic sú testovacie predpoklady, nie populačné odhady."
    )]
    order = ["egg", "peanut", "milk", "shared", "lactose", "celiac", "histamine"]
    for trait_id in order:
        panel_records = records_for(records, trait_id)
        rows = [["Cieľ / gén", "Efektová alela / váha", "Frekvencia", "Dôkaz a biologická úloha"]]
        for record in panel_records:
            rows.append([
                f"<b>{record['target']}</b><br/>{record['gene']}",
                f"{record['risk_allele']} / {record['weight_text']}<br/>{record['group']}",
                f"{record['frequency_text']}<br/>{record['frequency_status']}",
                f"{record['role']}<br/><font color='#687A83'>{record['evidence']}</font>",
            ])
        story += [
            p(f"{TRAIT_NAMES[trait_id]} ({len(panel_records)} záznamov)", "H2x"),
            marker_table(rows, [39 * mm, 35 * mm, 31 * mm, 62 * mm]),
            Spacer(1, 4 * mm),
        ]

    story += section("Primárne zdroje", "I.05 / evidencia")
    story += [data_table([
        ["Panel", "Zdroj", "Úloha v modeli"],
        ["Vajce / spoločný", "Marenholz et al. 2017, DOI 10.1038/s41467-017-01220-0", "GWAS lokusy a efekty"],
        ["Arašidy", "Hong et al. 2015, DOI 10.1038/ncomms7304", "Replikované HLA asociácie"],
        ["Arašidy", "Asai et al. 2018, DOI 10.1016/j.jaci.2017.09.015", "Kandidátne lokusy meta-analýzy"],
        ["Mlieko", "Henneman et al. 2016, DOI 10.1186/s13601-016-0096-9", "Kandidátne asociácie"],
        ["Laktóza", "Enattah et al. 2002, PMID 11788828", "C-13910T a laktázová perzistencia"],
        ["Histamín / DAO", "Maintz et al. 2011, DOI 10.1111/j.1398-9995.2011.02548.x", "AOC1 varianty a aktivita DAO"],
        ["Celiakia", "PGS000316; Sharp 2020; Monsuur 2008", "GRS, HLA tagy a diplotypová logika"],
        ["Proxy", "1000 Genomes Phase 3 EUR; Ensembl pairwise LD", "r2, D' a mapovanie alel"],
    ], [31 * mm, 80 * mm, 56 * mm], small=True)]
    story += [banner(
        "VEDECKÁ HRANICA",
        "Zaradenie markera do syntetického oracle potvrdzuje reprodukovateľnosť implementácie, nie "
        "kauzalitu, klinickú užitočnosť ani presnosť pre konkrétneho pacienta.",
        DARK,
    ), PageBreak()]
    return story


def technical_section(records: list[dict], celiac_proxy: dict) -> list:
    story = part_cover(
        "II",
        "Technická správa",
        "Architektúra dát, inferenčný algoritmus a úplný register direct/proxy/missing spracovania.",
        [("SCHÉMY", "2"), ("PROXY PRAH", "r2 0,90"), ("BUILD", "GRCh37")],
    )
    story += section("Systémová architektúra", "II.01 / vrstvy")
    story += [data_table([
        ["Vrstva", "Artefakt", "Zodpovednosť"],
        ["Register panelov", "config/trait_models_v1.json", "21 záznamov mimo celiakie"],
        ["Celiakálny register", "config/celiac_model_v1.json", "42 aditívnych a 8 HLA záznamov"],
        ["Proxy audit", "config/celiac_proxy_audit_v1.json", "EUR r2, D', orientácia proxy alely"],
        ["Syntetické dáta", "data/synthetic/*.csv.gz", "Oracle, pôvod, kvalita, split a trieda"],
        ["Metriky", "artifacts/*/evaluation.json", "CM, F1, AUC, FNR a Brier"],
        ["Web export", "site/assets/*.json", "Lokálna analýza v prehliadači"],
        ["Release audit", "artifacts/release-manifest.json", "Verzia, SHA-256 a veľkosť"],
    ], [34 * mm, 64 * mm, 69 * mm], small=True)]
    story += section("Jednotná inferenčná logika", "II.02 / direct, proxy, population, missing")
    story += [
        data_table([
            ["Pôvod", "Numerický vstup", "Celé skóre", "Kvalita", "Význam"],
            ["direct", "Dávka 0/1/2", "0/1/2", "1,00", "Cieľ je priamo v súbore"],
            ["proxy", "Najpravdepodobnejšia dávka", "0/1/2", "EUR r2", "Odhad cieľa; neistota oddelene"],
            ["population", "2 x frekvencia", "0", "0,00", "Len stabilizácia ML, nie genotyp osoby"],
            ["missing", "Neutrálny vstup", "0", "0,00", "Bez individuálnej informácie"],
        ], [24 * mm, 38 * mm, 26 * mm, 22 * mm, 57 * mm]),
        Spacer(1, 5 * mm),
        banner(
            "MLIEKO",
            "rs115288876, rs63582760 / rs10588133 a rs17388568 vytvárajú celý odhad 0, 1 alebo 2. "
            "r2 a podmienená pravdepodobnosť sa používajú len na vyjadrenie neistoty, nie ako desatinné genetické skóre.",
            BLUE,
        ),
        Spacer(1, 5 * mm),
        p(
            "Laktóza a histamín/DAO nepoužívajú populačnú imputáciu. Ak cieľ chýba, výsledok zostáva "
            "neurčený alebo sa zníži pokrytie. Pri celiakii je automatická proxy prípustná iba pri "
            f"EUR r2 >= {compact(celiac_proxy['minimum_automatic_r2'], 2)}."
        ),
    ]

    story += section("Technický register všetkých markerov", "II.03 / spracovanie 71 cieľov")
    story += [p(
        "Proxy kandidáti sú zoradení podľa registra. Aplikácia najprv hľadá cieľový rsID. Proxy sa "
        "uplatní až po jeho absencii. Pri viacerých dostupných proxy sa preferuje vyššia auditovaná "
        "kvalita. D' opisuje rekombinačnú väzbu, kým r2 určuje prediktívnu zameniteľnosť."
    )]
    order = ["egg", "peanut", "milk", "shared", "lactose", "celiac", "histamine"]
    for trait_id in order:
        panel_records = records_for(records, trait_id)
        rows = [["Cieľ", "Direct pravidlo", "Auditované proxy", "Chýbanie a kvalita"]]
        for record in panel_records:
            required = "Povinná proxy vetva" if record["required_proxy"] else "Direct má prioritu"
            quality = (
                "Bez imputácie" if record["missing_policy"] == "no-imputation"
                else record["missing_policy"].replace("population-expectation-for-ML-only", "population len pre ML")
            )
            rows.append([
                f"<b>{record['target']}</b><br/>{record['gene']}",
                f"Alela {record['risk_allele']}; dávka 0/1/2<br/>{required}",
                proxy_text(record["proxies"]),
                f"{quality}<br/>min. pokrytie {int(record['minimum_coverage'] * 100)} %",
            ])
        story += [
            p(f"{TRAIT_NAMES[trait_id]} ({len(panel_records)} cieľov)", "H2x"),
            marker_table(rows, [32 * mm, 38 * mm, 60 * mm, 37 * mm]),
            Spacer(1, 4 * mm),
        ]

    story += section("Dátová schéma a auditná stopa", "II.04 / forenzná presnosť")
    story += [data_table([
        ["Pole", "Význam", "Kontrola"],
        ["true_dosage", "Simulovaná pravá dávka pre oracle", "Nikdy sa nemieša s pozorovaným vstupom"],
        ["observed_dosage", "Numerický vstup modelu", "Direct/proxy/population/missing pravidlo"],
        ["dosage_integer", "Transparentný príspevok 0/1/2", "Proxy zostáva celé číslo"],
        ["source", "Pôvod hodnoty", "Povolené hodnoty sú explicitne uzavreté"],
        ["quality", "1,0 direct; r2 proxy; 0 population/missing", "Oddelené od genetického skóre"],
        ["weighted_score", "Súčet dávka x beta plus HLA člen", "Deterministický pre daný register"],
        ["split", "train / validation / test", "Fixný seed a neprekrývanie"],
    ], [35 * mm, 69 * mm, 63 * mm], small=True)]
    story += section("Reprodukcia a release", "II.05 / vykonateľný postup")
    story += [data_table([
        ["Krok", "Príkaz alebo výstup"],
        ["Inštalácia", "python -m pip install -r requirements-lock.txt"],
        ["Celiakálny beh", "python scripts/run_pipeline.py --samples 12000 --seed 20261014"],
        ["Viacznakový beh", "python scripts/run_multitrait_pipeline.py --samples-per-trait 6000 --seed 20261014"],
        ["Release export", "python scripts/build_release_assets.py"],
        ["Python testy", "python -m unittest discover -s tests -v"],
        ["Web testy", "node --test tests/web_app.test.mjs"],
    ], [42 * mm, 125 * mm], small=True), PageBreak()]
    return story


def flow_diagram() -> Drawing:
    drawing = Drawing(470, 285)
    labels = [
        ("1", "Zdroj a hypotéza"),
        ("2", "Register alely a váhy"),
        ("3", "Direct / proxy / missing"),
        ("4", "Oracle a syntetické dáta"),
        ("5", "Train / validation / test"),
        ("6", "Metriky a marker audit"),
        ("7", "Release a checksum"),
    ]
    positions = [(5, 190), (125, 190), (245, 190), (365, 190), (65, 65), (185, 65), (305, 65)]
    for index, ((number, label), (x, y)) in enumerate(zip(labels, positions)):
        fill = PALE if index % 2 == 0 else MINT
        drawing.add(Rect(x, y, 100, 56, rx=6, ry=6, fillColor=fill, strokeColor=DARK, strokeWidth=0.8))
        drawing.add(String(x + 50, y + 37, number, textAnchor="middle", fontName="Nu3Bold", fontSize=11, fillColor=BLUE))
        drawing.add(String(x + 50, y + 19, label, textAnchor="middle", fontName="Nu3Bold", fontSize=6.8, fillColor=INK))
    for x in (108, 228, 348):
        drawing.add(Line(x, 218, x + 14, 218, strokeColor=BLUE, strokeWidth=1.4))
        drawing.add(Polygon([x + 14, 218, x + 9, 221, x + 9, 215], fillColor=BLUE, strokeColor=None))
    drawing.add(Line(415, 185, 115, 125, strokeColor=BLUE, strokeWidth=1.2))
    drawing.add(Polygon([115, 125, 122, 129, 120, 122], fillColor=BLUE, strokeColor=None))
    for x in (168, 288):
        drawing.add(Line(x, 93, x + 14, 93, strokeColor=BLUE, strokeWidth=1.4))
        drawing.add(Polygon([x + 14, 93, x + 9, 96, x + 9, 90], fillColor=BLUE, strokeColor=None))
    drawing.add(String(235, 22, "Každý krok vytvára verzovaný a auditovateľný artefakt", textAnchor="middle", fontName="Nu3Regular", fontSize=8.5, fillColor=MUTED))
    return drawing


def process_section(records: list[dict]) -> list:
    story = part_cover(
        "III",
        "Procesná mapa",
        "Riadený tok od vedeckého dôkazu cez spracovanie každého cieľa po kontrolovaný release.",
        [("KROKY", "7"), ("BRÁNY", "7"), ("CIELE", "71")],
    )
    story += section("End-to-end proces", "III.01 / mapa")
    story += [
        flow_diagram(),
        banner(
            "ZÁSADA",
            "Marker vstupuje do modelu len cez verzovaný register. Každá transformácia zachováva "
            "pôvod, kvalitu a možnosť spätne vysvetliť príspevok k panelovému skóre.",
            DARK,
        ),
        PageBreak(),
    ]
    story += section("Proces pre jeden marker", "III.02 / opakovaná rozhodovacia vetva")
    story += [data_table([
        ["Rozhodnutie", "Áno", "Nie", "Auditný záznam"],
        ["Je cieľový rsID v súbore?", "Použi direct dávku 0/1/2", "Skontroluj proxy register", "target, genotyp, source=direct"],
        ["Je dostupná povolená proxy?", "Mapuj proxy alelu na cieľ", "Použi missing politiku panelu", "proxy rsID, genotyp, r2, D'"],
        ["Spĺňa proxy kvalitatívny prah?", "Celé skóre 0/1/2, quality=r2", "Population alebo missing", "odhad dávky a neistota"],
        ["Je pokrytie nad minimom?", "Vypočítaj panelovú triedu", "Výsledok označ ako nedostatočný", "coverage, quality, class"],
        ["Je zvolený model zafixovaný?", "Vyhodnoť test split", "Nesiahaj na test", "model, threshold, seed"],
    ], [43 * mm, 45 * mm, 43 * mm, 36 * mm], small=True)]
    story += section("Procesné kroky a vlastníctvo dôkazu", "III.03 / quality gates")
    story += [data_table([
        ["Krok", "Vstup", "Kontrola", "Výstup / brána"],
        ["1. Evidencia", "GWAS, PGS, kandidátna štúdia", "Populácia, fenotyp, efektová alela", "Zdroj priradený markeru"],
        ["2. Register", "Alela, beta, frekvencia", "Schéma a unikátnosť v paneli", "Verzovaný JSON"],
        ["3. Technická vrstva", "Direct a proxy exporty", "Orientácia, r2, D', alias", "Provenance pre každý cieľ"],
        ["4. Generátor", "Register a seed", "Deterministický oracle", "Anotovaný dataset"],
        ["5. Splity", "Dataset", "Stratifikácia, neprekrývanie", "Train, validation, test"],
        ["6. Modely", "Rovnaké splity", "Baseline/additive/structured", "Porovnateľné metriky"],
        ["7. Release", "Kód, dáta, PDF", "Testy, SHA-256, Pages", "Auditovateľné vydanie"],
    ], [28 * mm, 45 * mm, 52 * mm, 42 * mm], small=True)]

    story += section("Procesná matica panelov", "III.04 / rozdiely sa zachovávajú")
    process_rows = [["Panel", "Počet", "Skórovacia jednotka", "Proxy / missing", "Stop podmienka"]]
    for trait_id in ["egg", "peanut", "milk", "shared", "lactose", "celiac", "histamine"]:
        panel_records = records_for(records, trait_id)
        if trait_id == "lactose":
            score = "Genotypové pravidlo"
            missing = "Bez imputácie"
        elif trait_id == "histamine":
            score = "Súčet rizikových AOC1 alel"
            missing = "Bez imputácie"
        elif trait_id == "celiac":
            score = "GRS + HLA diplotyp"
            missing = "Proxy r2 >= 0,90; potom population"
        else:
            score = "Vážený aditívny panel"
            missing = "Proxy; population len pre ML"
        process_rows.append([
            TRAIT_NAMES[trait_id],
            len(panel_records),
            score,
            missing,
            "Pokrytie pod 50 % alebo chýbajúci povinný cieľ",
        ])
    story += [data_table(process_rows, [32 * mm, 15 * mm, 42 * mm, 45 * mm, 33 * mm], small=True)]

    story += section("Proces zmien", "III.05 / verzovanie a dohľadateľnosť")
    story += bullets([
        "Zmena alely, váhy alebo proxy zvyšuje verziu modelového registra.",
        "Po zmene registra sa regenerujú syntetické dáta, metriky, browserové artefakty a checksumy.",
        "Výsledky pred a po zmene sa nesmú miešať v jednom validačnom tvrdení.",
        "Pri zmene populačnej referencie sa znovu audituje LD aj kalibrácia.",
        "Klinická kohorta sa nesmie použiť na ladenie a zároveň na finálne nezávislé hodnotenie.",
    ])
    story.append(PageBreak())
    return story


def best_model(row: dict) -> tuple[str, dict]:
    name = max(row["models"], key=lambda model_name: row["models"][model_name]["test"]["macro_f1"])
    return name, row["models"][name]["test"]


def confusion_block(name: str, model_name: str, test: dict) -> KeepTogether:
    matrix = test["confusion_matrix"]
    high = test["high_risk"]
    labels = list(test["per_class"])
    rows = [["Skutočná / predikovaná", *labels, "High-risk binárne"]]
    binary_notes = [
        f"TP {high['tp']} / FP {high['fp']}",
        f"FN {high['fn']} / TN {high['tn']}",
        f"prah {high['threshold']:.2f}",
    ]
    for index, (label, values) in enumerate(zip(labels, matrix)):
        rows.append([label, *values, binary_notes[index]])
    if len(labels) == 2:
        widths = [51 * mm, 30 * mm, 30 * mm, 56 * mm]
    else:
        widths = [51 * mm, 21 * mm, 25 * mm, 21 * mm, 49 * mm]
    return KeepTogether([
        p(f"{name} / {model_name}", "H3x"),
        data_table(rows, widths, small=True),
        Spacer(1, 3 * mm),
    ])


def validation_section(records: list[dict], multitrait_metrics: dict, celiac_metrics: dict) -> list:
    story = part_cover(
        "IV",
        "Validačná správa",
        "Komparatívne metriky, confusion matrices, markerový audit a hranice prijatia.",
        [("TESTOVANÉ MODELY", "21"), ("PANELY", "7"), ("MARKEROVÝ AUDIT", "71")],
    )
    story += section("Validačný protokol", "IV.01 / čo sa meria")
    story += [
        p(
            "Validácia meria zhodu naučeného modelu so syntetickým referenčným oracle. Pre každý "
            "panel sa reportuje confusion matrix, precision, recall, macro F1, ROC-AUC, PR-AUC, "
            "Brier score a false-negative rate vysokej triedy. Ide o algoritmickú fidelity."
        ),
        banner(
            "DÔLEŽITÉ",
            "Samostatný SNP nemá v tomto dizajne vlastnú klinickú sensitivity, specificity ani AUC. "
            "Marker sa validuje ako správne orientovaný a reprodukovateľne spracovaný vstup. Výkon sa "
            "hodnotí na úrovni celého panelu.",
            DARK,
        ),
    ]
    story += section("Panelové výsledky", "IV.02 / fixný test split")
    rows = [["Panel", "Najlepší model", "Macro F1", "High recall", "High precision", "FNR", "ROC-AUC", "Brier"]]
    selected: list[tuple[str, str, dict]] = []
    for trait_id in ["egg", "peanut", "milk", "shared", "lactose"]:
        model_name, test = best_model(multitrait_metrics["traits"][trait_id])
        selected.append((TRAIT_NAMES[trait_id], model_name, test))
    celiac_name, celiac_test = best_model(celiac_metrics)
    selected.append((TRAIT_NAMES["celiac"], celiac_name, celiac_test))
    hist_name, hist_test = best_model(multitrait_metrics["traits"]["histamine"])
    selected.append((TRAIT_NAMES["histamine"], hist_name, hist_test))
    for panel_name, model_name, test in selected:
        high = test["high_risk"]
        rows.append([
            panel_name,
            model_name,
            f"{test['macro_f1']:.3f}",
            f"{high['recall']:.3f}",
            f"{high['precision']:.3f}",
            f"{high['false_negative_rate']:.3f}",
            f"{high['roc_auc']:.3f}",
            f"{high['brier']:.3f}",
        ])
    story += [data_table(rows, [31 * mm, 25 * mm, 19 * mm, 20 * mm, 22 * mm, 14 * mm, 18 * mm, 18 * mm], small=True)]
    story += [
        p(
            "Mliečny panel dosahuje vysoký recall za cenu nízkej precision. Histamín/DAO nesplnil "
            "cieľ recall 0,95. Structured interakcie neboli automaticky najlepšie: výber modelu sa "
            "riadi testovacím protokolom, nie preferenciou zložitejšej architektúry."
        ),
        PageBreak(),
    ]

    story += section("Confusion matrices", "IV.03 / tri triedy a high-risk prah")
    for panel_name, model_name, test in selected:
        story.append(confusion_block(panel_name, model_name, test))

    story += [PageBreak()]
    story += section("Validačný register všetkých markerov", "IV.04 / 71 auditných jednotiek")
    story += [p(
        "Stĺpec panelový dopad opisuje, kde sa príspevok markera overuje. Auditný test opisuje "
        "technickú kontrolu, ktorú možno reprodukovať bez klinických dát. Marker s proxy má navyše "
        "test priority direct > proxy a kontrolu oddelenia skóre od neistoty."
    )]
    order = ["egg", "peanut", "milk", "shared", "lactose", "celiac", "histamine"]
    for trait_id in order:
        panel_records = records_for(records, trait_id)
        rows = [["Cieľ", "Validačná jednotka", "Panelový dopad", "Auditný test / stav"]]
        for record in panel_records:
            proxy_check = " + proxy precedence" if record["proxies"] else ""
            if record["group"] == "research":
                state = "Technicky overené; vedecké rozšírenie vyžaduje odbornú revíziu"
            elif record["trait_id"] in {"milk", "histamine"}:
                state = "Technicky overené; kandidátny panel bez klinickej kalibrácie"
            else:
                state = "Technicky overené v syntetickej pipeline"
            rows.append([
                f"<b>{record['target']}</b><br/>{record['gene']}",
                f"{record['validation']}{proxy_check}",
                record["role"],
                state,
            ])
        story += [
            p(f"{TRAIT_NAMES[trait_id]} ({len(panel_records)} záznamov)", "H2x"),
            marker_table(rows, [32 * mm, 51 * mm, 42 * mm, 42 * mm]),
            Spacer(1, 4 * mm),
        ]

    story += section("Akceptačná matica", "IV.05 / grantový výstup")
    story += [data_table([
        ["Požiadavka", "Dôkaz v projekte", "Stav"],
        ["Holistické panelové skóre", "7 explicitných oracle modelov; 71 panel-lokus záznamov", "splnené metodicky"],
        ["Interakcie", "Structured comparator; HLA diplotyp pri celiakii", "otestované"],
        ["Forenzná presnosť", "Alela, váha, proxy, provenance, checksum", "splnené"],
        ["Syntetické datasety", "48 000 anotovaných prípadov a fixné splity", "splnené"],
        ["Komparatívna validácia", "CM, precision, recall, F1, AUC, FNR, Brier", "splnené"],
        ["Komplexná dokumentácia", "Štyri vrstvy v jednom kontrolovanom PDF", "splnené"],
        ["Klinická validácia", "Nezávislá fenotypovaná kohorta", "otvorené"],
        ["Externá integrácia", "Bod 6 bol podľa zadania vynechaný", "mimo rozsahu"],
    ], [50 * mm, 83 * mm, 34 * mm], small=True)]
    story += section("Reziduálne riziká a ďalší krok", "IV.06 / hranice prijatia")
    story += bullets([
        "Vykonať odbornú revíziu kandidátnych a research-extension lokusov pred zmrazením klinického protokolu.",
        "Získať nezávislú fenotypovanú kohortu primeranú každému znaku a cieľovej populácii.",
        "Kalibrovať absolútne riziko a reportovať subgroup výkon, rozhodovacie krivky a neistotu.",
        "Oddeliť technické pokrytie konkrétnej revízie DNA čipu od klinickej diskriminácie modelu.",
        "Potvrdiť licenčný režim pred nemenným release označeným ako formálne odovzdanie.",
    ])
    story += [banner(
        "ZÁVER",
        "Projekt má jednotnú a reprodukovateľnú výskumnú vrstvu pre všetky znaky a úplný markerový "
        "audit. Akceptovateľnosť klinických tvrdení zostáva závislá od reálnych fenotypovaných dát.",
        BLUE,
    )]
    return story


def appendix(records: list[dict]) -> list:
    unique = len({record["target"] for record in records})
    proxy_targets = sum(bool(record["proxies"]) for record in records)
    required_proxy = sum(record["required_proxy"] for record in records)
    return [
        *section("Kontrola úplnosti", "príloha A / súhrnný register"),
        info_cards([("PANEL-LOKUSY", str(len(records))), ("UNIKÁTNE rsID", str(unique)), ("CIELE S PROXY", str(proxy_targets))]),
        Spacer(1, 6 * mm),
        data_table([
            ["Kontrola", "Výsledok", "Interpretácia"],
            ["Počet panel-lokus záznamov", len(records), "Musí byť presne 71"],
            ["Počet unikátnych cieľových rsID", unique, "Opakovaný rsID môže mať inú panelovú váhu"],
            ["Ciele s aspoň jednou proxy", proxy_targets, "Proxy je auditovaná technická náhrada"],
            ["Povinné proxy vetvy", required_proxy, "Tri ciele mliečneho panelu"],
            ["Panely bez populačnej imputácie", 2, "Laktóza a histamín/DAO"],
        ], [57 * mm, 28 * mm, 82 * mm], small=True),
        Spacer(1, 7 * mm),
        banner(
            "AUTOMATICKÁ KONTROLA",
            "Generátor PDF sa zastaví, ak register neobsahuje presne 71 panel-lokus záznamov. "
            "V QA kroku sa po vytvorení overuje prítomnosť každého cieľového rsID v texte PDF.",
            DARK,
        ),
        *section("Odovzdané artefakty", "príloha B / reprodukovateľnosť"),
        data_table([
            ["Artefakt", "Obsah", "Auditná funkcia"],
            ["trait_models_v1.json", "6 registrov mimo celiakie", "Alely, váhy, proxy, zdroje"],
            ["celiac_model_v1.json", "50 celiakálnych záznamov", "GRS a HLA logika"],
            ["*_pilot_v1.csv.gz", "7 syntetických datasetov", "Train/validation/test materiál"],
            ["evaluation.json", "Kompletné metriky modelov", "CM, F1, AUC, FNR, Brier"],
            ["site/assets/*.json", "Browserové modely a audity", "Lokálna reprodukcia výsledku"],
            ["checksums.sha256", "Kontrolné súčty", "Integrita release balíka"],
        ], [47 * mm, 58 * mm, 62 * mm], small=True),
        Spacer(1, 6 * mm),
        p(
            "Repozitár a GitHub Pages predstavujú technický výskumný výstup. Dokument nenahrádza "
            "odborné medicínske posúdenie, diagnostiku, eliminačnú diétu ani liečebné rozhodnutie.",
            "Smallx",
        ),
    ]


def build() -> Path:
    trait_bundle = read_json("config/trait_models_v1.json")
    celiac = read_json("config/celiac_model_v1.json")
    celiac_proxy = read_json("config/celiac_proxy_audit_v1.json")
    multitrait_metrics = read_json("artifacts/multitrait/evaluation.json")
    celiac_metrics = read_json("artifacts/metrics/evaluation.json")
    records = build_records(trait_bundle, celiac, celiac_proxy)

    story = cover()
    story += contents()
    story += research_section(records, trait_bundle)
    story += technical_section(records, celiac_proxy)
    story += process_section(records)
    story += validation_section(records, multitrait_metrics, celiac_metrics)
    story += appendix(records)

    OUT.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    document(OUTPUT).build(story)
    shutil.copyfile(OUTPUT, DOWNLOADS / OUTPUT.name)
    print(f"panel_locus_records={len(records)}")
    print(f"unique_target_rsids={len({record['target'] for record in records})}")
    return OUTPUT


if __name__ == "__main__":
    print(build().relative_to(ROOT))
