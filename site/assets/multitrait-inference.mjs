import { detectProfile, parseGenotypeText } from "./inference.mjs";

function dosage(genotype, allele) {
  return [...genotype].filter((value) => value === allele).length;
}

function proxyExpectedDosage(genotype, proxy) {
  return [...genotype].reduce(
    (total, allele) => total + (allele === proxy.proxy_risk_allele ? proxy.p_target_if_proxy : proxy.p_target_if_other),
    0,
  );
}

function frequency(locus) {
  return locus.eur_frequency ?? locus.simulation_frequency;
}

function findProxyCall(calls, proxies) {
  const ordered = [...proxies].sort((left, right) => right.r2 - left.r2);
  for (const proxy of ordered) {
    const ids = [proxy.id, ...(proxy.aliases || [])];
    const id = ids.find((candidate) => calls.has(candidate.toLowerCase()));
    if (id) return { proxy, genotype: calls.get(id.toLowerCase()), matchedId: id };
  }
  return null;
}

export function buildTraitEvidence(calls, trait) {
  return trait.loci.map((locus) => {
    const direct = locus.required_proxy ? null : calls.get(locus.id.toLowerCase());
    if (direct) {
      const observed = dosage(direct, locus.risk_allele);
      return { locus, observed, integerContribution: observed, quality: 1, source: "direct", genotype: direct, proxy: null };
    }
    const matched = findProxyCall(calls, locus.proxies || []);
    if (matched) {
      const expected = proxyExpectedDosage(matched.genotype, matched.proxy);
      return {
        locus,
        observed: Math.round(expected),
        integerContribution: Math.round(expected),
        quality: matched.proxy.r2,
        source: "proxy",
        genotype: null,
        proxy: { ...matched.proxy, genotype: matched.genotype, matched_id: matched.matchedId, expected_dosage: expected },
      };
    }
    const source = trait.missing_policy === "population-expectation-for-ML-only" ? "population" : "missing";
    return {
      locus,
      observed: 2 * frequency(locus),
      integerContribution: 0,
      quality: 0,
      source,
      genotype: null,
      proxy: null,
    };
  });
}

function softmax(logits) {
  const maximum = Math.max(...logits);
  const values = logits.map((value) => Math.exp(value - maximum));
  const total = values.reduce((sum, value) => sum + value, 0);
  return values.map((value) => value / total);
}

function featureVector(evidence, profile, coverage, trait, model, profileNames) {
  const byId = Object.fromEntries(evidence.map((row) => [row.locus.id, row]));
  const weighted = evidence.reduce((sum, row) => sum + row.observed * row.locus.beta, 0);
  return model.feature_names.map((name) => {
    if (name.startsWith("obs_")) return byId[name.slice(4)].observed;
    if (name.startsWith("quality_")) return byId[name.slice(8)].quality;
    if (name.startsWith("profile_")) return name === `profile_${profile}` ? 1 : 0;
    if (name === "aggregate_weighted_score") return weighted;
    if (name === "interaction_missingness_x_weighted_score") return weighted * (1 - coverage);
    if (name.startsWith("interaction_rs")) {
      const markerIds = name.match(/rs\d+/g);
      if (markerIds?.length === 2) return byId[markerIds[0]].observed * byId[markerIds[1]].observed;
    }
    if (profileNames.some((candidate) => name === `profile_${candidate}`)) return 0;
    throw new Error(`Unknown ${trait.id} model feature: ${name}`);
  });
}

function predict(features, model) {
  const normalized = features.map((value, index) => (value - model.mean[index]) / model.scale[index]);
  const design = [1, ...normalized];
  const classCount = model.weights[0].length;
  const logits = Array.from({ length: classCount }, (_, classIndex) =>
    design.reduce((sum, value, rowIndex) => sum + value * model.weights[rowIndex][classIndex], 0));
  return softmax(logits);
}

function transparentBand(score, trait) {
  if (trait.id === "lactose") return score === 2 ? "nonpersistent" : "persistent";
  return Object.entries(trait.bands).find(([, range]) => score >= range[0] && score <= range[1])?.[0] || "unknown";
}

function percentile(score, distribution) {
  return distribution.reduce((sum, [candidate, probability]) => candidate <= score ? sum + probability : sum, 0);
}

export function runTraitInference(calls, trait, model, reference, profileNames, rawText = "") {
  const evidence = buildTraitEvidence(calls, trait);
  const covered = evidence.filter((row) => row.source === "direct" || row.source === "proxy").length;
  const coverage = covered / evidence.length;
  const profile = detectProfile(rawText, coverage);
  const features = featureVector(evidence, profile, coverage, trait, model, profileNames);
  const probabilities = predict(features, model);
  const geneticScore = evidence.reduce((sum, row) => sum + row.integerContribution, 0);
  const best = probabilities.indexOf(Math.max(...probabilities));
  const counts = Object.fromEntries(["direct", "proxy", "population", "missing"].map((source) => [
    source, evidence.filter((row) => row.source === source).length,
  ]));
  return {
    traitId: trait.id,
    name: trait.name_sk,
    profile,
    evidence,
    counts,
    coverage,
    sufficient: coverage >= trait.minimum_coverage,
    geneticScore,
    maxScore: trait.loci.length * 2,
    transparentBand: transparentBand(geneticScore, trait),
    percentile: coverage === 1 ? percentile(geneticScore, reference.distribution) : null,
    reliability: evidence.reduce((sum, row) => sum + row.quality, 0) / evidence.length,
    mlLabel: trait.classes[best],
    probabilities: Object.fromEntries(trait.classes.map((label, index) => [label, probabilities[index]])),
    highSensitivityFlag: probabilities.at(-1) >= model.metadata.high_risk_threshold,
    highRiskThreshold: model.metadata.high_risk_threshold,
    evidenceTier: trait.evidence_tier,
    limitation: trait.limitations_sk,
  };
}

export function runTraitBundleInference(text, bundle, models, references) {
  const calls = parseGenotypeText(text);
  if (!calls.size) throw new Error("V súbore sa nenašli platné rsID genotypy.");
  const profiles = Object.keys(bundle.synthetic_profiles);
  return bundle.traits.map((trait) => runTraitInference(calls, trait, models[trait.id], references[trait.id], profiles, text));
}
