// DOC 3: additive observer contract against the actual existing consumers.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {execFileSync} = require("node:child_process");
const root = path.resolve(__dirname, "../..");
const read = name => fs.readFileSync(path.join(root, name), "utf8");
const policy = vm.createContext({});
vm.runInContext(read("services/diagnostics/CpuPlusDiagnosticsPolicy.js"), policy);
const ui = read("widgets/cpuplus/CpuPlusDiagnosticsPane.qml");
const breakdown = vm.createContext({});
vm.runInContext(ui.slice(ui.indexOf("    function memoryBreakdown("),
    ui.indexOf("    function comparisonLabel(")), breakdown);
// Generate a sample through the real observer with disposable proc fixtures.
const sample = JSON.parse(execFileSync("python3", ["-B", "-c", [
    "import os, sys, tempfile, json",
    "from pathlib import Path",
    "sys.path[:0] = ['scripts', 'tests/cpuplus']",
    "import cpuplus_quickshell_memory_observer as observer",
    "from test_quickshell_memory_observer import stat, rollup, host_info",
    "with tempfile.TemporaryDirectory() as tmp:",
    "    p = Path(tmp) / '123'",
    "    p.mkdir()",
    "    (p / 'stat').write_text(stat())",
    "    (p / 'smaps_rollup').write_text(rollup())",
    "    (p.parent / 'meminfo').write_text(host_info())",
    "    print(json.dumps(observer.observe(p, os.getuid(), 100)))"
].join("\n")], {cwd:root, encoding:"utf8"}));
assert.equal(sample.privateResidentKiB, 110);
assert.equal(sample.hostObservation.beforeKiB.MemAvailable, 6000);
assert.equal(sample.hostObservation.afterKiB.MemAvailable, 6000);
const current = {...sample, cpuPct:null, sampleIntervalMs:null};
const legacy = JSON.parse(JSON.stringify(current));
delete legacy.memoryKiB.Private_Clean;
delete legacy.privateResidentKiB;
delete legacy.hostObservation;
const terminal = {event:"complete",pid:sample.pid,startTicks:sample.startTicks};
// Explicit map callback avoids Array.map passing an index as JSON replacer.
const jsonl = row => [row, terminal].map(x => JSON.stringify(x)).join("\n");
const oldText = jsonl(legacy), newText = jsonl(current);
const oldSummary=policy.summarize("memory", oldText), newSummary=policy.summarize("memory", newText);
assert.ok(newSummary.startsWith(oldSummary+"\nHOST CONTEXT // 1/1 paired samples"));
assert.match(newSummary,/HOST AVAILABLE MIN \x28OBSERVED\x29 \/\/ 5\.9 MiB/);
assert.match(newSummary,/CORRELATION ONLY \/\/ CAUSE NOT ESTABLISHED/);
assert.doesNotMatch(oldSummary,/HOST CONTEXT/);
const after={...current,tsMs:current.tsMs+10000,cpuTicks:current.cpuTicks+10,cpuPct:1,sampleIntervalMs:10000,
    memoryKiB:{...current.memoryKiB,Rss:200+1024,Pss:150+1024,Pss_Anon:100+1024},
    pssPlusSwapPssKiB:180+1024,
    hostObservation:{...current.hostObservation,afterKiB:{...current.hostObservation.afterKiB,MemAvailable:3952}}};
const summaryFor=(rows)=>policy.summarize("memory",[...rows,terminal].map(x=>JSON.stringify(x)).join("\n"));
let summary=summaryFor([current,after]);
assert.match(summary,/HOST CONTEXT \/\/ 2\/2 paired samples/);
assert.match(summary,/HOST AVAILABLE CHANGE \/\/ -2\.0 MiB/);
assert.match(summary,/QS PSS CHANGE \/\/ \+1\.0 MiB/);
for(const unavailable of [null,{...after.hostObservation,afterKiB:null},
    {...after.hostObservation,afterKiB:{...after.hostObservation.afterKiB,MemAvailable:999999}},
    {...after.hostObservation,spanMs:-1}]){
    summary=summaryFor([current,{...after,hostObservation:unavailable}]);
    assert.match(summary,/HOST CONTEXT \/\/ 1\/2 paired samples/);
    assert.match(summary,/HOST TREND \/\/ INCOMPLETE/);
    assert.doesNotMatch(summary,/HOST AVAILABLE CHANGE|QS PSS CHANGE/);
}
summary=summaryFor([{...current,hostObservation:null}]);
assert.match(summary,/HOST CONTEXT \/\/ 0\/1 paired samples \/\/ UNAVAILABLE/);
summary=summaryFor([current,{...after,hostObservation:{...after.hostObservation,
    beforeKiB:{...after.hostObservation.beforeKiB,MemTotal:64000},
    afterKiB:{...after.hostObservation.afterKiB,MemTotal:64000}}}]);
assert.match(summary,/HOST TREND \/\/ INCOMPLETE OR CHANGED CAPACITY/);
assert.doesNotMatch(summary,/HOST AVAILABLE CHANGE/);
const details = text => breakdown.memoryBreakdown("memory", {status:"COMPLETE",text});
assert.ok(details(oldText));
assert.deepEqual(JSON.parse(JSON.stringify(details(oldText))),
    JSON.parse(JSON.stringify(details(newText))));
// Archive validates the unchanged outer record, preserving text byte-for-byte.
const records = [oldText,newText].map((text,i)=>({kind:"memory",id:"session-abc-def-"+(i+1),
    status:"COMPLETE",summary:"fixture",text,finishedAt:"2026-11-24T12:00:00.000Z"}));
const restored = JSON.parse(execFileSync("python3", ["-B", "-c", [
    "import json, sys",
    "sys.path.insert(0, 'scripts')",
    "from cpuplus_diagnostic_archive import validate_record",
    "print(json.dumps([validate_record(r) for r in json.load(sys.stdin)]))"
].join("\n")], {cwd:root, input:JSON.stringify(records),encoding:"utf8"}));
assert.deepEqual(restored,records);
console.log("DOC 3 legacy and extended memory capture consumer compatibility PASS");
