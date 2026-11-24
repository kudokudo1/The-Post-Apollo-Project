// Run with: node tests/cpuplus_memory_snapshot_test.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const base = path.join(__dirname, "..");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(base, "widgets/cpuplus/CpuPlusMemorySnapshot.js"), "utf8"), ctx);
const parse = ctx.parseSnapshot;
const fixture = "MemTotal: 32768000 kB\nMemAvailable: 9437184 kB\nSwapTotal: 8388608 kB\nSwapFree: 8388608 kB\nFilename Type Size Used Priority\n/dev/zram0 partition 8388608 0 100\nsome avg10=0.00 avg60=0.00 avg300=0.00 total=0\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=0\n60\n";
assert.equal(parse(fixture).rows[0].kind, "ZRAM");
assert.equal(parse(fixture).available, 9437184);
assert.equal(parse(fixture.replace("SwapFree: 8388608","SwapFree: 9999999")), null);
assert.equal(parse(fixture.replace("MemAvailable: 9437184 kB\n","")), null);
assert.equal(parse(fixture.replace("full avg10=0.00","full avg10=101.00")), null);
assert.equal(parse(fixture.replace("/dev/zram0 partition 8388608 0 100","/var/swapfile file 8388608 100 10")).rows[0].kind, "OTHER SWAP");
assert.equal(parse(fixture.replace("/dev/zram0 partition 8388608 0 100\n","").replace("SwapTotal: 8388608","SwapTotal: 0").replace("SwapFree: 8388608","SwapFree: 0")).rows.length, 0);
const plan = ctx.capacityPlan;
const activeFixture = fixture.replace("SwapTotal: 8388608", "SwapTotal: 25165820")
    .replace("SwapFree: 8388608", "SwapFree: 25165820")
    .replace("some avg10=", "/var/lib/post-apollo-memory-swap/swapfile file 16777212 0 10\nsome avg10=");
const activeSample = parse(activeFixture);
assert.equal(plan(activeSample,16).direction,"unchanged");
assert.equal(plan(activeSample,16).projectedKiB,25165820);
assert.equal(plan(activeSample,24).direction,"expand");
assert.equal(plan(activeSample,24).projectedKiB,33554432);
assert.equal(plan(activeSample,8).direction,"reduce");
assert.equal(plan(activeSample,8).projectedKiB,16777216);
assert.equal(plan(parse(fixture),16).direction,"add");
assert.equal(plan(parse(fixture),16).projectedKiB,25165824);
assert.equal(plan(activeSample,17),null);
const expandedFixture = activeFixture.replace("SwapTotal: 25165820", "SwapTotal: 33554424")
    .replace("SwapFree: 25165820", "SwapFree: 33554424")
    .replace("some avg10=", "/var/lib/post-apollo-memory-extension/swapfile file 8388604 0 9\nsome avg10=");
const expandedSample = parse(expandedFixture);
assert.equal(plan(expandedSample,24).direction,"unchanged");
assert.equal(plan(expandedSample,24).actualKiB,25165816);
assert.equal(plan(expandedSample,16).direction,"reduce");
assert.equal(plan(expandedSample,16).projectedKiB,25165824);
const compose = ctx.swapComposition;
const current = compose(activeSample);
assert.equal(current.groups[0].size,8388608);
assert.equal(current.groups[1].size,16777212);
assert.equal(current.groups[2].size,0);
assert.equal(current.total,25165820);
assert.equal(current.used,0);
assert.equal(current.capacityMatches,true);
const usedSample = parse(expandedFixture.replace("8388608 0 100","8388608 17203 100")
    .replace("16777212 0 10","16777212 4096 10")
    .replace("8388604 0 9","8388604 2048 9"));
const usedComposition = compose(usedSample);
assert.equal(usedComposition.groups[0].used,17203);
assert.equal(usedComposition.groups[1].used,4096);
assert.equal(usedComposition.groups[2].used,2048);
assert.equal(usedComposition.used,23347);
assert.equal(usedComposition.total,33554424);
assert.equal(compose({...activeSample, rows:[...activeSample.rows,{name:"/other",size:1024,used:512}]}).groups[3].used,512);
assert.equal(compose({...activeSample, rows:[...activeSample.rows,activeSample.rows[0]]}),null);
assert.equal(compose({...activeSample,swap:0}).capacityMatches,false);
assert.equal(compose(null),null);
const bar = fs.readFileSync(path.join(base,"widgets/cpuplus/CpuPlusSwapComposition.qml"),"utf8");
assert.match(bar,/height: 24/);
assert.match(bar,/segment.modelData.used \/ segment.modelData.size/);
assert.match(bar,/LIVE BAR UNCHANGED/);
assert.doesNotMatch(bar,/\b(?:Process|pkexec|sudo|execDetached)\b/);
const pane = fs.readFileSync(path.join(base,"widgets/cpuplus/CpuPlusMemoryActuatorPane.qml"),"utf8");
assert.match(pane, /command: \["\/usr\/bin\/cat"/);
assert.doesNotMatch(pane, /\b(?:sudo|pkexec|swapon|swapoff|mkswap|sysctl)\b/);
assert.match(pane, /PREVIEW ONLY \/\/ RESIZE NOT AVAILABLE YET/);
assert.match(pane, /root.capacity.projectedKiB/);
assert.match(pane, /CpuPlusSwapComposition\s*\{/);
const widget = fs.readFileSync(path.join(base,"widgets/CpuPlusW.qml"),"utf8");
assert.match(widget, /active: cpuPlusWindow\.menuOpen && cpuPlusWindow\.selectedModeIndex === 3[\s\S]{0,650}sourceComponent: CpuPlusMemoryActuatorPane/);
console.log("CPU++ memory snapshot and read-only scope PASS");
