import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { parseGenotypeText } from "../site/assets/inference.mjs";
import { buildTraitEvidence, runTraitBundleInference } from "../site/assets/multitrait-inference.mjs";

const json = async (path) => JSON.parse(await readFile(new URL(path, import.meta.url), "utf8"));
const bundle = await json("../site/assets/trait-models.json");
const models = await json("../site/assets/trait-structured-models.json");
const references = await json("../site/assets/trait-references.json");
const demo = await readFile(new URL("../site/downloads/multitrait-demo-genotype.txt", import.meta.url), "utf8");

test("multi-trait demo returns all six non-coeliac modules", () => {
  const results = runTraitBundleInference(demo, bundle, models, references);
  assert.deepEqual(results.map((row) => row.traitId), ["egg", "peanut", "milk", "shared", "lactose", "histamine"]);
  for (const row of results) {
    assert.equal(row.sufficient, true);
    assert.equal(row.coverage, 1);
    assert.equal(Number.isInteger(row.geneticScore), true);
    assert.ok(Math.abs(Object.values(row.probabilities).reduce((a, b) => a + b, 0) - 1) < 1e-12);
  }
  assert.equal(results.find((row) => row.traitId === "milk").counts.proxy, 3);
  assert.equal(results.find((row) => row.traitId === "lactose").transparentBand, "persistent");
});

test("histamine and lactose never invent a population genotype", () => {
  const calls = parseGenotypeText("rs2052129 TT\n");
  const histamine = bundle.traits.find((row) => row.id === "histamine");
  const evidence = buildTraitEvidence(calls, histamine);
  assert.equal(evidence[0].source, "direct");
  assert.equal(evidence[1].source, "missing");
  assert.equal(evidence[2].source, "missing");
  assert.equal(evidence.filter((row) => row.source === "population").length, 0);
});

test("milk proxy contributes an integer while keeping proxy reliability separate", () => {
  const milk = bundle.traits.find((row) => row.id === "milk");
  const evidence = buildTraitEvidence(parseGenotypeText("rs115288876 AG\n"), milk);
  const target = evidence.find((row) => row.locus.id === "rs12123821");
  assert.equal(target.source, "proxy");
  assert.equal(target.integerContribution, 1);
  assert.equal(target.quality, 0.698182);
  assert.ok(target.proxy.expected_dosage > 0 && target.proxy.expected_dosage < 2);
});
