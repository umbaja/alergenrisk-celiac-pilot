import { runInference } from "./inference.mjs";
import { runTraitBundleInference } from "./multitrait-inference.mjs";

const asset = (name) => `./assets/${name}`;
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[character]));
const percent = (value) => `${(value * 100).toLocaleString("sk-SK", { maximumFractionDigits: 1 })} %`;

async function fetchJson(name) {
  const response = await fetch(asset(name));
  if (!response.ok) throw new Error(`Nepodarilo sa načítať ${name}.`);
  return response.json();
}

function probabilityRows(probabilities) {
  const labels = { low: "znížená", typical: "typická", high: "zvýšená", persistent: "perzistencia", nonpersistent: "nonperzistencia" };
  return Object.entries(probabilities).map(([key, value]) => `
    <div class="probability"><strong>${labels[key]}</strong><div class="bar"><span style="width:${Math.max(0, Math.min(100, value * 100))}%"></span></div><span>${percent(value)}</span></div>
  `).join("");
}

function resultLabel(value) {
  return ({ low: "znížená", typical: "typická", high: "zvýšená", persistent: "laktázová perzistencia", nonpersistent: "laktázová nonperzistencia" })[value] || value;
}

function renderTraitResults(results) {
  const target = document.querySelector("#trait-results");
  target.hidden = false;
  target.innerHTML = `<div class="section-heading"><div><p class="eyebrow">OSTATNÉ ZNAKY</p><h2>Výsledky spoločnej metodiky</h2></div><span class="pill">${results.length} modulov</span></div><div class="trait-result-grid">${results.map((result) => {
    const visibleLabel = result.sufficient ? resultLabel(result.mlLabel) : "nedostatočné pokrytie";
    const tone = result.sufficient ? (result.mlLabel === "high" || result.mlLabel === "nonpersistent" ? "high" : result.mlLabel === "low" || result.mlLabel === "persistent" ? "low" : "typical") : "insufficient";
    const evidence = result.evidence.map((row) => `<tr><td><code>${row.locus.id}</code></td><td>${escapeHtml(row.locus.gene)}</td><td>${escapeHtml(row.source)}</td><td>${row.source === "direct" || row.source === "proxy" ? row.integerContribution : "-"}</td><td>${row.proxy ? `<code>${row.proxy.matched_id}</code> · r² ${row.proxy.r2.toFixed(3)}` : row.genotype || "-"}</td><td>${percent(row.quality)}</td></tr>`).join("");
    return `<article class="trait-result ${tone}"><div class="trait-result-head"><div><small>${escapeHtml(result.evidenceTier)}</small><h3>${escapeHtml(result.name)}</h3></div><div class="score-ring ${tone}"><strong>${result.geneticScore}</strong><span>z ${result.maxScore}</span></div></div><p class="trait-label">${escapeHtml(visibleLabel)}</p><div class="mini-stats"><span><b>${percent(result.coverage)}</b> pokrytie</span><span><b>${percent(result.reliability)}</b> technická spoľahlivosť</span></div>${result.sufficient ? probabilityRows(result.probabilities) : '<div class="notice warning">Trieda sa nezobrazuje, kým vstup nespĺňa minimálne pokrytie modulu.</div>'}<details><summary>Audit markerov</summary><div class="table-wrap"><table><thead><tr><th>Cieľ</th><th>Gén</th><th>Zdroj</th><th>Body</th><th>Genotyp / proxy</th><th>Kvalita</th></tr></thead><tbody>${evidence}</tbody></table></div></details><p class="caption">${escapeHtml(result.limitation)}</p></article>`;
  }).join("")}</div>`;
}

function renderCalculatorResult(result, fileName) {
  const target = document.querySelector("#result");
  target.hidden = false;
  const bandLabels = { low: "znížená", typical: "typická", high: "zvýšená" };
  const visibleBand = result.sufficient ? result.transparentBand : "insufficient";
  const title = result.sufficient ? bandLabels[result.transparentBand] : "nedostatočné pokrytie";
  target.className = `result visible card result-band ${visibleBand}`;
  target.innerHTML = `
    <small>VÝSLEDOK PRE ${escapeHtml(fileName)}</small>
    <h2 style="margin-top:8px">Relatívna predispozícia: ${escapeHtml(title)}</h2>
    <div class="grid">
      <div><small>REFERENČNÉ SKÓRE</small><div class="metric">${result.transparentScore.toFixed(2)}</div></div>
      <div><small>EUR/CEU PERCENTIL</small><div class="metric">${percent(result.percentile)}</div></div>
      <div><small>POKRYTIE</small><div class="metric">${result.counts.direct + result.counts.proxy}/50</div></div>
    </div>
    <p><strong>HLA odhad:</strong> ${escapeHtml(result.hla.key)} · ${result.counts.direct} priamo, ${result.counts.proxy} cez proxy, ${result.counts.population} populačne neistých.</p>
    ${result.sufficient ? "" : '<div class="notice warning"><strong>Výsledok nie je interpretovateľný:</strong> menej ako polovica cieľových markerov bola zistená priamo alebo cez overenú proxy.</div>'}
    <h3>Výskumný ML výstup</h3>
    ${probabilityRows(result.probabilities)}
    <p><strong>ML trieda:</strong> ${escapeHtml(result.mlLabel)}. High-sensitivity flag pri prahu ${result.highRiskThreshold.toFixed(2)}: <strong>${result.highSensitivityFlag ? "áno" : "nie"}</strong>.</p>
    <p class="privacy">Hodnoty sú pravdepodobnosti tried syntetického oracle, nie pravdepodobnosti ochorenia. Výpočet prebehol lokálne v prehliadači.</p>
  `;

  const evidenceBody = document.querySelector("#evidence-body");
  evidenceBody.innerHTML = result.evidence.map((row) => `
    <tr><td><code>${row.id}</code></td><td>${escapeHtml(row.gene)}</td><td>${row.riskAllele}</td>
    <td>${row.observed.toFixed(3)}</td><td><span class="badge ${row.source}">${row.source}</span></td>
    <td>${row.proxy ? `<code>${row.proxy.id}</code> ${escapeHtml(row.proxy.genotype)} · r² ${row.proxy.r2.toFixed(3)}` : row.genotype || "-"}</td>
    <td>${percent(row.quality)}</td></tr>
  `).join("");
  document.querySelector("#evidence-section").hidden = false;

  const download = document.querySelector("#download-result");
  download.onclick = () => {
    const blob = new Blob([JSON.stringify({ ...result, source_file: fileName }, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "alergenrisk-celiac-result.json";
    link.click();
    URL.revokeObjectURL(link.href);
  };
}

async function setupCalculator() {
  const [manifest, proxyCatalog, model, reference, traitBundle, traitModels, traitReferences] = await Promise.all([
    fetchJson("celiac-model.json"),
    fetchJson("proxy-audit.json"),
    fetchJson("structured-model.json"),
    fetchJson("reference-distribution.json"),
    fetchJson("trait-models.json"),
    fetchJson("trait-structured-models.json"),
    fetchJson("trait-references.json"),
  ]);
  const status = document.querySelector("#file-status");
  const analyze = async (text, fileName) => {
    status.textContent = "Počítam lokálne...";
    try {
      renderCalculatorResult(runInference(text, manifest, proxyCatalog, model, reference), fileName);
      renderTraitResults(runTraitBundleInference(text, traitBundle, traitModels, traitReferences));
      status.textContent = "Hotovo. Súbor neopustil tento prehliadač.";
    } catch (error) {
      status.textContent = error.message;
    }
  };
  document.querySelector("#genotype-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 100 * 1024 * 1024) {
      status.textContent = "Súbor je väčší ako 100 MB.";
      return;
    }
    await analyze(await file.text(), file.name);
  });
  document.querySelector("#demo-button").addEventListener("click", async () => {
    const response = await fetch("./downloads/all-traits-demo-genotype.txt");
    await analyze(await response.text(), "all-traits-demo-genotype.txt");
  });
}

function renderPreview(rows, traitId) {
  const celiac = traitId === "celiac";
  const columns = celiac
    ? ["sample_id", "split", "chip_profile", "oracle_label", "oracle_score", "observed_reference_score", "predicted_hla_diplotype", "direct_count", "proxy_count", "population_imputed_count", "coverage_fraction"]
    : ["sample_id", "split", "chip_profile", "oracle_label", "oracle_genetic_score", "oracle_weighted_score", "observed_integer_score", "direct_count", "proxy_count", "population_imputed_count", "missing_count", "coverage_fraction"];
  const labels = celiac
    ? ["Vzorka", "Split", "Profil", "Trieda", "Oracle skóre", "Pozorované skóre", "HLA odhad", "Direct", "Proxy", "Population", "Pokrytie"]
    : ["Vzorka", "Split", "Profil", "Trieda", "Celé skóre", "Vážené skóre", "Pozorované celé skóre", "Direct", "Proxy", "Population", "Missing", "Pokrytie"];
  document.querySelector("#preview-head").innerHTML = `<tr>${labels.map((label) => `<th>${label}</th>`).join("")}</tr>`;
  document.querySelector("#preview-body").innerHTML = rows.map((row) => `<tr>${columns.map((column) => {
    if (column === "sample_id") return `<td><code>${escapeHtml(row[column])}</code></td>`;
    if (column === "coverage_fraction") return `<td>${percent(row[column])}</td>`;
    if (["oracle_score", "observed_reference_score", "oracle_weighted_score"].includes(column)) return `<td>${Number(row[column]).toFixed(2)}</td>`;
    return `<td>${escapeHtml(row[column])}</td>`;
  }).join("")}</tr>`).join("");
  document.querySelector("#preview-count").textContent = `${rows.length} zobrazených ukážkových riadkov`;
}

async function setupData() {
  const [celiacPreview, celiacDictionary, traitPreviews, traitDictionaries] = await Promise.all([
    fetchJson("data-preview.json"), fetchJson("data-dictionary.json"), fetchJson("trait-data-preview.json"), fetchJson("trait-data-dictionaries.json"),
  ]);
  const apply = () => {
    const traitId = document.querySelector("#trait-filter").value;
    const allRows = traitId === "celiac" ? celiacPreview.preview_rows : traitPreviews[traitId].rows;
    const dictionary = traitId === "celiac" ? celiacDictionary : traitDictionaries[traitId];
    const split = document.querySelector("#split-filter").value;
    const label = document.querySelector("#class-filter").value;
    const profile = document.querySelector("#profile-filter").value;
    renderPreview(allRows.filter((row) => (!split || row.split === split) && (!label || row.oracle_label === label) && (!profile || row.chip_profile === profile)), traitId);
    document.querySelector("#dictionary-body").innerHTML = dictionary.map((row) => `
      <tr><td><code>${escapeHtml(row.column)}</code></td><td>${escapeHtml(row.type)}</td><td>${escapeHtml(row.description)}</td></tr>
    `).join("");
  };
  for (const control of document.querySelectorAll("#trait-filter,#split-filter,#class-filter,#profile-filter")) control.addEventListener("change", apply);
  apply();
}

async function setupAudit() {
  const [celiacPayload, traitPayload] = await Promise.all([fetchJson("locus-audit.json"), fetchJson("trait-audit.json")]);
  const allRows = [
    ...celiacPayload.rows.map((row) => ({ ...row, trait_id: "celiac", trait_name: "Celiakia", beta: row.weight, evidence_tier: row.evidence_status, missing_policy: "direct-proxy-population" })),
    ...traitPayload.rows,
  ];
  const render = () => {
    const query = document.querySelector("#audit-search").value.trim().toLowerCase();
    const trait = document.querySelector("#audit-trait").value;
    const proxyFilter = document.querySelector("#audit-proxy").value;
    const rows = allRows.filter((row) => (!trait || row.trait_id === trait)
      && (!proxyFilter || (proxyFilter === "yes" ? row.proxies.length > 0 : row.proxies.length === 0))
      && (!query || `${row.trait_name} ${row.target} ${row.gene} ${row.proxies.map((proxy) => proxy.id).join(" ")}`.toLowerCase().includes(query)));
    document.querySelector("#audit-count").textContent = `${rows.length} z ${allRows.length} záznamov panel-lokus`;
    document.querySelector("#audit-body").innerHTML = rows.map((row) => `
      <tr><td>${escapeHtml(row.trait_name)}</td><td><code>${row.target}</code></td><td>${escapeHtml(row.gene)}</td><td>${row.risk_allele}</td>
      <td>${row.haplotype || (Number.isFinite(Number(row.beta)) ? Number(row.beta).toFixed(3) : "HLA")}</td><td>${row.proxies.length ? row.proxies.map((proxy) => `<div><code>${proxy.id}</code> · r² ${Number(proxy.r2).toFixed(3)} · D′ ${Number(proxy.d_prime).toFixed(3)}</div>`).join("") : "bez automatickej proxy"}</td>
      <td>${escapeHtml(row.evidence_tier)}</td><td>${escapeHtml(row.missing_policy)}</td></tr>
    `).join("");
  };
  document.querySelector("#audit-search").addEventListener("input", render);
  document.querySelector("#audit-trait").addEventListener("change", render);
  document.querySelector("#audit-proxy").addEventListener("change", render);
  render();
}

const page = document.body.dataset.page;
if (page === "calculator") setupCalculator().catch((error) => { document.querySelector("#file-status").textContent = error.message; });
if (page === "data") setupData().catch((error) => { document.querySelector("#preview-count").textContent = error.message; });
if (page === "audit") setupAudit().catch((error) => { document.querySelector("#audit-count").textContent = error.message; });
