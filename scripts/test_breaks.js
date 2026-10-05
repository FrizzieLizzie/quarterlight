// Checks when the 20-20-20 reminder fires.  Run:  node --test scripts/test_breaks.js
const test = require("node:test");
const assert = require("node:assert");
const Module = require("module");

const load = Module._load;
Module._load = (request, ...rest) => (request === "vscode" ? {} : load(request, ...rest));
const { breakDecision } = require("../extension.js");

const MIN = 60000;

// Plays out one check-in per minute; `focusedAt(minute)` says whether VS Code is in front then.
function simulate(minutes, focusedAt) {
  let state = { lastBreak: 0, lastSeen: 0, snoozeUntil: 0 };
  const shown = [];
  for (let m = 1; m <= minutes; m++) {
    const result = breakDecision(state, m * MIN, 20, focusedAt(m));
    state = result.state;
    if (result.show) shown.push(m);
  }
  return shown;
}

test("reminds every 20 minutes while VS Code stays in front", () => {
  assert.deepStrictEqual(simulate(60, () => true), [20, 40, 60]);
});

test("time in another app still counts (the 1.0.0 bug)", () => {
  // In VS Code for 3 minutes, then a browser for 6, over and over.
  const shown = simulate(60, (m) => m % 9 < 3);
  assert.ok(shown.length >= 2, `expected reminders, got ${shown}`);
});

test("a due reminder waits until you return to VS Code", () => {
  // Due at minute 20, but VS Code isn't in front again until minute 25.
  assert.deepStrictEqual(simulate(25, (m) => m < 18 || m >= 25), [25]);
});

test("VS Code closed or computer asleep for 5+ minutes counts as a break", () => {
  let state = { lastBreak: 0, lastSeen: 0, snoozeUntil: 0 };
  state = breakDecision(state, 15 * MIN, 20, true).state; // working until minute 15
  const after = breakDecision(state, 25 * MIN, 20, true); // no check-ins for 10 minutes
  assert.strictEqual(after.show, false);
  assert.strictEqual(after.state.lastBreak, 25 * MIN);
});
