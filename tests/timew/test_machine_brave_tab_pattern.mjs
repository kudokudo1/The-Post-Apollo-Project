import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { projectBraveTopology } from "../../integrations/machine/brave-topology/topology.mjs";

// Exercise the parser used by the QML input against actual JS syntax.
// This is a source-derived unit test, not a Sway/Brave runtime bridge.
const qml = readFileSync(new URL("../../widgets/TimeW.qml", import.meta.url), "utf8");
const m = qml.match(
  /function machineParseBraveTabCounts\(text\) \{([\s\S]*?)\n    \}\n\n    \/\/ MACHINE v2/
);
assert.ok(m, "MACHINE live QML parser must remain present");
const parse = new Function("text", m[1]);

assert.deepEqual(parse(""), []);
assert.deepEqual(parse("   "), []);
assert.deepEqual(parse("2//5//6"), [2, 5, 6]);
assert.deepEqual(parse("2 // 5 // 6"), [2, 5, 6]);
assert.deepEqual(parse(" 0 // 1 // 2048 "), [0, 1, 2048]);
assert.deepEqual(parse("1"), [1]);

for (const wrong of [
  undefined, null, 123, "TABS // 2 // 5 // 6", "1 / 2",
  "1 //", "// 2", "1 //// 2", "0x2 // 5",
  "0002", "-1", "2.5", "nan", "http://host/path",
  "2 // <script>", "2 // 2049", "9".repeat(257),
]) assert.equal(parse(wrong), null, String(wrong));

assert.equal(parse(Array.from({ length: 65 }, () => "1").join(" // ")), null);
assert.equal(parse(Array.from({ length: 5 }, () => "2048").join(" // ")), null);
assert.equal(parse(Array.from({ length: 4 }, () => "2048").join(" // ")).length, 4);

// Production Brave projection has no URLs/titles, and preserves the visible
// list order used by the live tab-count signature, not a trusted Sway order.
const windows = [
  {id: 15, incognito: false, type: "normal",
   tabs: Array.from({length: 2}, (_,i)=>({index:i,pinned:false,active:i===0}))},
  {id: 20, incognito: false, type: "normal",
   tabs: Array.from({length: 5}, (_,i)=>({index:i,pinned:false,active:i===0}))},
  {id: 30, incognito: false, type: "normal",
   tabs: Array.from({length: 6}, (_,i)=>({index:i,pinned:false,active:i===0}))},
  {id: 99, incognito: true, type: "normal",
   get tabs() { throw new Error("Private tab access"); }},
];
const report = projectBraveTopology(windows, 15);
assert.deepEqual(report.windows.map(w=>w.tab_count), [2,5,6]);
assert.equal(report.private_windows_included, false);
assert.equal(report.sway_window_binding_verified, false);
assert.equal(report.tabs_restorable, false);
assert.deepEqual(report.safe_restore_actions, []);

console.log("MACHINE Brave tab signature parser & 2 // 5 // 6 privacy tests PASS");
