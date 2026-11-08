import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { indexCatalog, search } from "../src/catalog.mjs";
import { diagram } from "../src/runway-diagram.mjs";

const assets = process.argv[2] || "assets";
const read = name => JSON.parse(readFileSync(join(assets, name), "utf8"));
const index = indexCatalog(read("catalog.json"));
assert.equal(search(index, "  ").length, 0);
assert.equal(search(index, "London").length, 3);
for (const [query, kind, name] of [
  ["krst", "Airport", "Rochester"], ["B6", "Airline", "JetBlue"], ["738", "Aircraft", "737-800"],
]) {
  const matches = search(index, query);
  const row = matches.find(r => r.kind === kind && r.name.includes(name));
  assert.ok(row && matches.length <= 3, `Check the known lookup for ${query}`);
  if (kind === "Airport") {
    const field = read(`airfields/${row.code[0]}.json`)[row.id];
    assert.ok(field.radios.length && diagram(field.runways, field.lat, field.lon));
  } else if (kind === "Airline") {
    assert.ok(read("airline-profiles.json")[row.id].callsign);
  } else {
    assert.ok(read("aircraft-profiles.json")[row.id].faa.span);
  }
}
console.log("Verified offline searches, profiles and the three-result limit");
