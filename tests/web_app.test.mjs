import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { buildEvidence, parseGenotypeText, runInference } from "../site/assets/inference.mjs";

const readJson = async (path) => JSON.parse(await readFile(new URL(path, import.meta.url), "utf8"));
const manifest = await readJson("../site/assets/celiac-model.json");
const proxies = await readJson("../site/assets/proxy-audit.json");
const model = await readJson("../site/assets/structured-model.json");
const reference = await readJson("../site/assets/reference-distribution.json");
const demo = await readFile(new URL("./fixtures/synthetic-demo-genotype.txt", import.meta.url), "utf8");

test("synthetic demo produces a deterministic full-coverage result", () => {
  assert.equal(parseGenotypeText(demo).size, 50);
  const result = runInference(demo, manifest, proxies, model, reference);
  assert.deepEqual(result.counts, { direct: 50, proxy: 0, population: 0 });
  assert.equal(result.coverage, 1);
  assert.equal(result.sufficient, true);
  assert.equal(result.transparentScore, 3.98);
  assert.equal(result.transparentBand, "typical");
  assert.equal(result.hla.key, "DQ2.2/DQ2.2");
  assert.ok(["low", "typical", "high"].includes(result.mlLabel));
  assert.ok(Math.abs(Object.values(result.probabilities).reduce((a, b) => a + b, 0) - 1) < 1e-12);
  const repeated = runInference(demo, manifest, proxies, model, reference);
  assert.deepEqual(repeated.probabilities, result.probabilities);
  assert.equal(repeated.mlLabel, result.mlLabel);
});

test("an audited proxy is used only when its direct target is absent", () => {
  const calls = parseGenotypeText("rs2596565 GG\n");
  const evidence = buildEvidence(calls, manifest, proxies);
  const target = evidence.find((row) => row.id === "rs4143332");
  assert.equal(target.source, "proxy");
  assert.equal(target.proxy.id, "rs2596565");
  assert.equal(target.quality, 0.987025);
  assert.equal(target.observed, 2);

  const direct = buildEvidence(parseGenotypeText("rs4143332 AA\nrs2596565 GG\n"), manifest, proxies)
    .find((row) => row.id === "rs4143332");
  assert.equal(direct.source, "direct");
  assert.equal(direct.observed, 0);
});

test("sparse input is explicitly marked insufficient", () => {
  const result = runInference("rs2596565 GG\n", manifest, proxies, model, reference);
  assert.equal(result.sufficient, false);
  assert.equal(result.counts.proxy, 1);
  assert.equal(result.counts.population, 49);
});
