const BASES = /^[ACGT]{1,2}$/i;

export function detectProfile(text, coverageFraction = 1) {
  const head = text.slice(0, 16000).toLowerCase();
  if (head.includes("23andme")) return "23andme_like";
  if (head.includes("myheritage")) return "myheritage_like";
  if (head.includes("dnaera") || head.includes("dna era")) return "dnaera_like";
  return coverageFraction < 0.65 ? "sparse_stress" : "complete";
}

export function parseGenotypeText(text) {
  const calls = new Map();
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const tokens = line.replaceAll('"', "").split(/[\s,;]+/).filter(Boolean);
    const rsIndex = tokens.findIndex((token) => /^rs\d+$/i.test(token));
    if (rsIndex < 0) continue;
    const marker = tokens[rsIndex].toLowerCase();
    const genotypeToken = tokens.slice(rsIndex + 1).reverse().find((token) => BASES.test(token));
    if (!genotypeToken || calls.has(marker)) continue;
    const genotype = genotypeToken.toUpperCase();
    if (genotype.length === 2) calls.set(marker, genotype);
  }
  return calls;
}

function dosage(genotype, riskAllele) {
  return [...genotype].filter((allele) => allele === riskAllele).length;
}

function proxyExpectedDosage(genotype, proxy) {
  return [...genotype].reduce(
    (sum, allele) => sum + (allele === proxy.proxy_risk_allele ? proxy.p_target_if_proxy : proxy.p_target_if_other),
    0,
  );
}

function markerRows(manifest) {
  return [
    ...manifest.additive_loci.map((row) => ({ ...row, kind: "additive" })),
    ...manifest.hla.tag_markers.map((row) => ({ ...row, kind: "hla" })),
  ];
}

export function buildEvidence(calls, manifest, proxyCatalog) {
  const evidence = [];
  for (const marker of markerRows(manifest)) {
    const direct = calls.get(marker.id.toLowerCase());
    if (direct) {
      evidence.push({
        id: marker.id,
        kind: marker.kind,
        gene: marker.gene,
        riskAllele: marker.risk_allele,
        genotype: direct,
        observed: dosage(direct, marker.risk_allele),
        quality: 1,
        source: "direct",
        proxy: null,
      });
      continue;
    }
    const candidates = [...(proxyCatalog.proxies[marker.id] || [])].sort((a, b) => b.r2 - a.r2);
    const matched = candidates.find((proxy) => calls.has(proxy.id.toLowerCase()));
    if (matched) {
      const proxyGenotype = calls.get(matched.id.toLowerCase());
      evidence.push({
        id: marker.id,
        kind: marker.kind,
        gene: marker.gene,
        riskAllele: marker.risk_allele,
        genotype: null,
        observed: proxyExpectedDosage(proxyGenotype, matched),
        quality: matched.r2,
        source: "proxy",
        proxy: { ...matched, genotype: proxyGenotype },
      });
      continue;
    }
    const expectation = marker.kind === "additive"
      ? 2 * marker.eur_frequency
      : 2 * manifest.hla.haplotype_frequencies[marker.haplotype];
    evidence.push({
      id: marker.id,
      kind: marker.kind,
      gene: marker.gene,
      riskAllele: marker.risk_allele,
      genotype: null,
      observed: expectation,
      quality: 0,
      source: "population",
      proxy: null,
    });
  }
  return evidence;
}

function inferHla(evidence, manifest) {
  const grouped = new Map();
  for (const marker of manifest.hla.tag_markers) {
    if (!grouped.has(marker.haplotype)) grouped.set(marker.haplotype, []);
    grouped.get(marker.haplotype).push(evidence.find((row) => row.id === marker.id).observed);
  }
  const ranked = [...grouped.entries()]
    .map(([haplotype, values]) => ({ haplotype, value: values.reduce((a, b) => a + b, 0) / values.length }))
    .sort((a, b) => b.value - a.value);
  const copies = [];
  for (const row of ranked) {
    const count = Math.max(0, Math.min(2, Math.round(row.value)));
    for (let index = 0; index < count && copies.length < 2; index += 1) copies.push(row.haplotype);
  }
  while (copies.length < 2) copies.push("X");
  copies.sort((a, b) => manifest.hla.haplotype_order.indexOf(a) - manifest.hla.haplotype_order.indexOf(b));
  const key = copies.join("/");
  return { key, weight: manifest.hla.diplotype_weights[key] ?? 0, ranked };
}

function featureVector(evidence, profile, hla, manifest, model) {
  const byId = Object.fromEntries(evidence.map((row) => [row.id, row]));
  const observedCoreScore = manifest.additive_loci.reduce(
    (sum, marker) => sum + byId[marker.id].observed * marker.beta,
    0,
  );
  const covered = evidence.filter((row) => row.source !== "population").length;
  const coverage = covered / evidence.length;
  const haplotypeMarkers = {};
  for (const marker of manifest.hla.tag_markers) {
    (haplotypeMarkers[marker.haplotype] ||= []).push(marker.id);
  }
  const interactions = {};
  for (const [haplotype, markers] of Object.entries(haplotypeMarkers)) {
    if (markers.length === 2) {
      interactions[`interaction_${haplotype.replaceAll(".", "_")}_tag_pair`] =
        byId[markers[0]].observed * byId[markers[1]].observed;
    }
  }
  interactions.interaction_hla_weight_x_core_score = observedCoreScore * hla.weight;
  interactions.interaction_missingness_x_core_score = observedCoreScore * (1 - coverage);

  return model.feature_names.map((name) => {
    if (name.startsWith("obs_")) return byId[name.slice(4)].observed;
    if (name.startsWith("quality_")) return byId[name.slice(8)].quality;
    if (name.startsWith("profile_")) return name === `profile_${profile}` ? 1 : 0;
    if (Object.hasOwn(interactions, name)) return interactions[name];
    throw new Error(`Unknown model feature: ${name}`);
  });
}

function softmax(logits) {
  const maximum = Math.max(...logits);
  const values = logits.map((value) => Math.exp(value - maximum));
  const total = values.reduce((a, b) => a + b, 0);
  return values.map((value) => value / total);
}

export function predictStructured(features, model) {
  const normalized = features.map((value, index) => (value - model.mean[index]) / model.scale[index]);
  const design = [1, ...normalized];
  const logits = [0, 1, 2].map((classIndex) =>
    design.reduce((sum, value, rowIndex) => sum + value * model.weights[rowIndex][classIndex], 0),
  );
  return softmax(logits);
}

function bandForScore(score, reference) {
  if (score <= reference.low_cut) return "low";
  if (score <= reference.high_cut) return "typical";
  return "high";
}

function percentileForScore(score, distribution) {
  let cumulative = 0;
  for (const [candidate, probability] of distribution) {
    if (candidate > score) break;
    cumulative += probability;
  }
  return Math.max(0, Math.min(1, cumulative));
}

export function runInference(text, manifest, proxyCatalog, model, reference) {
  const calls = parseGenotypeText(text);
  if (calls.size === 0) throw new Error("V súbore sa nenašli platné rsID genotypy.");
  let evidence = buildEvidence(calls, manifest, proxyCatalog);
  const covered = evidence.filter((row) => row.source !== "population").length;
  const coverage = covered / evidence.length;
  const profile = detectProfile(text, coverage);
  const hla = inferHla(evidence, manifest);
  const transparentScore = Math.round((hla.weight + manifest.additive_loci.reduce(
    (sum, marker) => sum + evidence.find((row) => row.id === marker.id).observed * marker.beta,
    0,
  )) * 50) / 50;
  const features = featureVector(evidence, profile, hla, manifest, model);
  const probabilities = predictStructured(features, model);
  const labels = ["low", "typical", "high"];
  const mlClass = probabilities.indexOf(Math.max(...probabilities));
  const counts = {
    direct: evidence.filter((row) => row.source === "direct").length,
    proxy: evidence.filter((row) => row.source === "proxy").length,
    population: evidence.filter((row) => row.source === "population").length,
  };
  return {
    profile,
    hla,
    evidence,
    counts,
    coverage,
    sufficient: coverage >= 0.5,
    transparentScore,
    transparentBand: bandForScore(transparentScore, reference),
    percentile: percentileForScore(transparentScore, reference.distribution),
    mlLabel: labels[mlClass],
    probabilities: Object.fromEntries(labels.map((label, index) => [label, probabilities[index]])),
    highSensitivityFlag: probabilities[2] >= model.metadata.high_risk_threshold,
    highRiskThreshold: model.metadata.high_risk_threshold,
  };
}
