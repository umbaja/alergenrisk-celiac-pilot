import { runInference } from "./inference.mjs";

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
  const labels = { low: "znížená", typical: "typická", high: "zvýšená" };
  return Object.entries(probabilities).map(([key, value]) => `
    <div class="probability"><strong>${labels[key]}</strong><div class="bar"><span style="width:${Math.max(0, Math.min(100, value * 100))}%"></span></div><span>${percent(value)}</span></div>
  `).join("");
}

function renderCalculatorResult(result, fileName) {
  const target = document.querySelector("#result");
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
  const [manifest, proxyCatalog, model, reference] = await Promise.all([
    fetchJson("celiac-model.json"),
    fetchJson("proxy-audit.json"),
    fetchJson("structured-model.json"),
    fetchJson("reference-distribution.json"),
  ]);
  const status = document.querySelector("#file-status");
  const analyze = async (text, fileName) => {
    status.textContent = "Počítam lokálne...";
    try {
      renderCalculatorResult(runInference(text, manifest, proxyCatalog, model, reference), fileName);
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
    const response = await fetch("./downloads/synthetic-demo-genotype.txt");
    await analyze(await response.text(), "synthetic-demo-genotype.txt");
  });
}

function renderPreview(rows) {
  const columns = ["sample_id", "split", "chip_profile", "oracle_label", "oracle_score", "observed_reference_score", "predicted_hla_diplotype", "direct_count", "proxy_count", "population_imputed_count", "coverage_fraction"];
  const labels = ["Vzorka", "Split", "Profil", "Trieda", "Oracle skóre", "Pozorované skóre", "HLA odhad", "Direct", "Proxy", "Population", "Pokrytie"];
  document.querySelector("#preview-head").innerHTML = `<tr>${labels.map((label) => `<th>${label}</th>`).join("")}</tr>`;
  document.querySelector("#preview-body").innerHTML = rows.map((row) => `<tr>${columns.map((column) => {
    if (column === "sample_id") return `<td><code>${escapeHtml(row[column])}</code></td>`;
    if (column === "coverage_fraction") return `<td>${percent(row[column])}</td>`;
    if (["oracle_score", "observed_reference_score"].includes(column)) return `<td>${Number(row[column]).toFixed(2)}</td>`;
    return `<td>${escapeHtml(row[column])}</td>`;
  }).join("")}</tr>`).join("");
  document.querySelector("#preview-count").textContent = `${rows.length} zobrazených ukážkových riadkov`;
}

async function setupData() {
  const [previewAsset, dictionary] = await Promise.all([fetchJson("data-preview.json"), fetchJson("data-dictionary.json")]);
  const allRows = previewAsset.preview_rows;
  const apply = () => {
    const split = document.querySelector("#split-filter").value;
    const label = document.querySelector("#class-filter").value;
    const profile = document.querySelector("#profile-filter").value;
    renderPreview(allRows.filter((row) => (!split || row.split === split) && (!label || row.oracle_label === label) && (!profile || row.chip_profile === profile)));
  };
  for (const control of document.querySelectorAll("#split-filter,#class-filter,#profile-filter")) control.addEventListener("change", apply);
  renderPreview(allRows);
  document.querySelector("#dictionary-body").innerHTML = dictionary.map((row) => `
    <tr><td><code>${escapeHtml(row.column)}</code></td><td>${escapeHtml(row.type)}</td><td>${escapeHtml(row.description)}</td></tr>
  `).join("");
}

async function setupAudit() {
  const payload = await fetchJson("locus-audit.json");
  const allRows = payload.rows;
  const render = () => {
    const query = document.querySelector("#audit-search").value.trim().toLowerCase();
    const group = document.querySelector("#audit-group").value;
    const proxyFilter = document.querySelector("#audit-proxy").value;
    const rows = allRows.filter((row) => (!group || row.group === group)
      && (!proxyFilter || (proxyFilter === "yes" ? row.proxies.length > 0 : row.proxies.length === 0))
      && (!query || `${row.target} ${row.gene} ${row.proxies.map((proxy) => proxy.id).join(" ")}`.toLowerCase().includes(query)));
    document.querySelector("#audit-count").textContent = `${rows.length} z 50 cieľových markerov`;
    document.querySelector("#audit-body").innerHTML = rows.map((row) => `
      <tr><td><code>${row.target}</code></td><td>${escapeHtml(row.group)}</td><td>${escapeHtml(row.gene)}</td><td>${row.risk_allele}</td>
      <td>${row.haplotype || Number(row.weight).toFixed(3)}</td><td>${row.proxies.length ? row.proxies.map((proxy) => `<div><code>${proxy.id}</code> · r² ${proxy.r2.toFixed(3)} · D′ ${proxy.d_prime.toFixed(3)}</div>`).join("") : "bez automatickej proxy"}</td>
      <td>${escapeHtml(row.evidence_status)}</td></tr>
    `).join("");
  };
  document.querySelector("#audit-search").addEventListener("input", render);
  document.querySelector("#audit-group").addEventListener("change", render);
  document.querySelector("#audit-proxy").addEventListener("change", render);
  render();
}

const page = document.body.dataset.page;
if (page === "calculator") setupCalculator().catch((error) => { document.querySelector("#file-status").textContent = error.message; });
if (page === "data") setupData().catch((error) => { document.querySelector("#preview-count").textContent = error.message; });
if (page === "audit") setupAudit().catch((error) => { document.querySelector("#audit-count").textContent = error.message; });
