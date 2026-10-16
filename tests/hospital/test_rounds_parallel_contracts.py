#!/usr/bin/env python3
"""Rounds concurrency contract: bounded, independent audit slots."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
s = (root / "services/hospital/HospitalRoundsService.qml").read_text()
for token in (
    "HospitalAuditService { id: auditProbeA }",
    "HospitalAuditService { id: auditProbeB }",
    "HospitalAuditService { id: auditProbeC }",
    "function scanNext()",
    "function finishSlot(slot)",
    "Object.keys(inFlightFloors).length === 0",
    "completedFloors += 1",
    "captureCurrentFloor(floor, probe)",
    "Qt.callLater(scanNext)",
    'status: "AUDIT_ERROR"',
    'status: "LOCAL_ONLY"',
):
    assert token in s, f"missing Rounds concurrency safeguard: {token}"
for legacy in ("scanInFlight", "finishCurrentFloor", "currentFloor", "auditProbe.runAudit"):
    assert legacy not in s, f"stale sequential audit code: {legacy}"
assert s.count("HospitalAuditService { id: auditProbe") == 3
assert "probe.runAudit(true)" in s
assert s.count("onRunningChanged()") == 3
print("HOSPITAL ROUNDS // BOUNDED PARALLEL AUDIT CONTRACT PASS")


# Execute the actual scheduling functions with synthetic probe slots.
# This catches duplicate Floor dispatch, missing completion, and failure
# isolation without requiring a live PX/GitHub installation.
import json
import subprocess
start = s.index("    function scanNext() {")
mid = s.index("    function finishSlot(slot) {", start)
end = s.index("    function captureCurrentFloor(floor, probe) {", mid)
js = s[start:end]
node = r"""
const vm = require("node:vm");
const probes = Array.from({length: 3}, (_, id) => ({
    id, running: false, available: true, lastError: "",
    resetResult(){},
    runAudit(){ this.running = true; }
}));
const queue = [];
const ctx = {
    scanQueue: Array.from({length: 8}, (_, i) => ({
        floorId: String(i), floorLabel: "Floor "+i,
        repository: i===4 ? "" : "kudokudo1/fixture-"+i,
        floorIndex:i, bedCount:0
    })),
    scanIndex: -1, completedFloors: 0, inFlightFloors: {},
    floors: [], rooms: [], running: true, finished:0,
    auditors(){return probes;},
    Qt:{callLater(fn){queue.push(fn);}},
    rebuildMetrics(){},
    captureCurrentFloor(floor, probe){
        ctx.floors.push({floorId:floor.floorId,auditAvailable:true});
    },
    finishRounds(){this.running=false;this.finished+=1;}
};
vm.createContext(ctx);
vm.runInContext(process.argv[1],ctx);
ctx.scanNext();
let count=0, maxConcurrent=0;
while (ctx.running && count++<100){
    maxConcurrent=Math.max(maxConcurrent,
        probes.filter(p=>p.running).length);
    const active = Object.keys(ctx.inFlightFloors);
    if(active.length){
        const slot=Number(active[0]);
        const floor=ctx.inFlightFloors[active[0]];
        const probe=probes[slot];
        probe.available=floor.floorId!=="2";
        probe.lastError="synthetic error";
        probe.running=false;
        ctx.finishSlot(slot);
    }
    while(queue.length)queue.shift()();
}
if(ctx.running || ctx.finished!==1 || ctx.completedFloors!==8 ||
   ctx.floors.length!==8 || maxConcurrent!==3)
    throw Error(JSON.stringify({running:ctx.running,done:ctx.completedFloors,
        floors:ctx.floors,maximum:maxConcurrent,finish:ctx.finished}));
const seen=new Set(ctx.floors.map(f=>f.floorId));
if(seen.size!==8) throw Error("duplicate Floor dispatch");
if(!ctx.floors.some(f=>f.floorId==="2" && f.status==="AUDIT_ERROR"))
    throw Error("failing Floor was not preserved");
if(!ctx.floors.some(f=>f.floorId==="4" && f.status==="LOCAL_ONLY"))
    throw Error("local-only Floor was not preserved");
console.log("ROUNDS THREE-SLOT FAKE AUDIT SCHEDULER PASS");
"""
result = subprocess.run(["node", "-e", node, js],
                        capture_output=True, text=True)
assert result.returncode == 0, (result.stdout, result.stderr)
print(result.stdout.strip())
