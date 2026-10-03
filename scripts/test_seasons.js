// Checks that each date lands in the right season.  Run:  node --test scripts/test_seasons.js
const test = require("node:test");
const assert = require("node:assert");
const Module = require("module");

// extension.js loads the "vscode" module, which only exists inside VS Code; an empty stand-in is enough here.
const load = Module._load;
Module._load = (request, ...rest) => (request === "vscode" ? {} : load(request, ...rest));
const { seasonFor } = require("../extension.js");

const STARTS = { spring: "03-20", summer: "06-21", autumn: "09-22", winter: "12-21" };
const CASES = {
  "2026-12-20": "Autumn", "2026-12-21": "Winter", "2027-01-15": "Winter", "2027-03-19": "Winter",
  "2027-03-20": "Spring", "2027-06-20": "Spring", "2027-06-21": "Summer", "2027-09-21": "Summer",
  "2027-09-22": "Autumn", "2027-12-31": "Winter",
};

for (const [day, season] of Object.entries(CASES)) {
  test(`${day} is ${season}`, () => assert.strictEqual(seasonFor(new Date(`${day}T12:00:00`), STARTS), season));
}
