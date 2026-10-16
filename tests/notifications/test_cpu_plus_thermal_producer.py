#!/usr/bin/env python3
"""CPU++ thermal alert producer: synthetic threshold, recovery and wiring tests."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/CpuPlusThermalPolicy.js"
PRODUCER = ROOT / "services/notifications/CpuPlusThermalNotificationProducer.qml"
SHELL = ROOT / "shell.qml"
QM = ROOT / "services/notifications/qmldir"
SYSTEM = ROOT / "services/system/SystemTelemetry.qml"
CPU = ROOT / "widgets/CpuPlusW.qml"
BASE = ROOT / "services/notifications/NotificationsService.qml"
HUB = ROOT / "widgets/notifications/NotificationsHubW.qml"

producer = PRODUCER.read_text(encoding="utf-8")
shell = SHELL.read_text(encoding="utf-8")
system = SYSTEM.read_text(encoding="utf-8")
cpu = CPU.read_text(encoding="utf-8")
assert 'CpuPlusThermalNotificationProducer {' in shell
assert 'telemetry: sharedSystemTelemetry' in shell
assert 'CpuPlusThermalNotificationProducer 1.0 CpuPlusThermalNotificationProducer.qml' in QM.read_text()
assert 'SystemTelemetry {' in shell
assert 'id: sharedSystemTelemetry' in shell
assert '\\"tempC\\"' in system and '\\"highC\\"' in system and '\\"critC\\"' in system
assert 'signal refreshed()' in system
assert 'interval: 1900' in cpu
assert 'cpuPlusWindow.menuOpen' in cpu
assert 'function onRefreshed() { producer.observe(); }' in producer
assert 'if (!telemetry || telemetry.errorText' in producer
assert 'NotificationsService.pushRich({' in producer
assert '"source": "CPU++"' in producer
assert '"sourceId": "cpu-plus"' in producer
assert '"category": "internal"' in producer
assert 'critical ? "critical" : "warning"' in producer
assert '"eventType": "hardware-thermal-limit"' in producer
assert '"sensorLabels": raised.map(' in producer
assert 'sourceText === "cpu++"' in HUB.read_text()
assert 'function pushRich(notification)' in BASE.read_text()
assert 'raised.sort(' in producer, "Coalesce multiple sensor events into a single batch"
for forbidden in ["Process {", "Timer {", "telemetry.refresh(", "Quickshell.execDetached",
                  "fanControl.", "kill(", "contributors"]:
    assert forbidden not in producer, forbidden

NODE = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8')
  .replace(/^\s*\.pragma library\s*$/m, '');
const ctx = {Math, Number, String, isFinite};
vm.runInNewContext(source,ctx,{filename:'CpuPlusThermalPolicy.js'});
const make=(temp,extra={})=>({
  sensorKind:'temperature',id:'thermal:core:0',name:'Package',
  tempC:temp,highC:82,critC:97,...extra
});
assert.strictEqual(ctx.limits(make(90)).high,82);
assert.strictEqual(ctx.level(ctx.limits(make(82))),1);
assert.strictEqual(ctx.level(ctx.limits(make(97))),2);
assert.strictEqual(ctx.level(ctx.limits(make(81))),0);
assert.strictEqual(ctx.limits(make(90,{highC:0,critC:0})),null);
assert.strictEqual(ctx.limits(make(90,{highC:0,critC:null})),null);
assert.strictEqual(ctx.limits(make(90,{sensorKind:'fan'})),null);
assert.strictEqual(ctx.limits(make(NaN)),null);
assert.strictEqual(ctx.limits(make(900)),null);
assert.strictEqual(ctx.limits(make(40,{tempC:''})),null);
assert.strictEqual(ctx.level(ctx.limits(make(99,{highC:0,critC:98}))),2);

let state=ctx.initial();
function sample(temp, expected, sent, override={}) {
  const result=ctx.transition(state,make(temp,override));
  assert.strictEqual(result.emit,expected,'emit @'+temp);
  assert.strictEqual(result.state.sent,sent,'latched level @'+temp);
  state=result.state;
}
sample(70,0,0);
sample(83,0,0);
sample(81,0,0); // one overheated sample is not a confirmed event
sample(83,0,0);
sample(84,1,1); // two consecutive warning samples
sample(92,0,1); // same high-band must not alert again
sample(98,0,1);
sample(99,2,2); // critical escalation
sample(88,0,2); // improvement in same episode is not a new warning
sample(78,0,2); // one sufficiently cool sample does not rearm
sample(83,0,2); // temperature bounce cancels recovery
sample(78,0,2);
sample(77,0,0); // two samples below high-3 rearm
sample(83,0,0);
sample(84,1,1);
state=ctx.initial();
sample(101,0,0,{highC:0,critC:100});
sample(101,2,2,{highC:0,critC:100}); // crit-only hardware
const before=JSON.stringify(state);
const invalid=ctx.transition(state,make(50,{tempC:null}));
assert.strictEqual(invalid.emit,0);
assert.strictEqual(JSON.stringify(invalid.state),before); // unavailable sensors can't rearm
console.log('CPU++ hardware thermal transition policy: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY)], check=True)
print("CPU++ thermal notification producer contracts: PASS")
