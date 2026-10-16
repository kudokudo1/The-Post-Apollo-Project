#!/usr/bin/env python3
"""CPU++ SYSTEM observations: synthetic data policy and safe source wiring."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/CpuPlusSystemReportPolicy.js"
PRODUCER = ROOT / "services/notifications/CpuPlusSystemNotificationProducer.qml"
SHELL = ROOT / "shell.qml"
QM = ROOT / "services/notifications/qmldir"
SYSTEM = ROOT / "services/system/SystemTelemetry.qml"
SERVICE = ROOT / "services/notifications/NotificationsService.qml"

src = PRODUCER.read_text(encoding="utf-8")
assert "CpuPlusSystemNotificationProducer {" in SHELL.read_text()
assert "telemetry: sharedSystemTelemetry" in SHELL.read_text()
assert "CpuPlusSystemNotificationProducer 1.0 CpuPlusSystemNotificationProducer.qml" in QM.read_text()
assert "signal refreshed()" in SYSTEM.read_text()
assert "function onRefreshed()" in src
assert "NotificationsService.historyReady" in src
assert "function historyContains(id)" in src
assert '"source": "CPU++"' in src
assert '"sourceId": "cpu-plus-system"' in src
assert '"category": "internal"' in src
assert '"severity": "normal"' in src
assert '"origin": "apollo"' in src
assert '"domain": "system"' in src
assert '"eventType": "system-observation-report"' in src
assert "lastObservedAtMs > 15000" in src
assert "NotificationsService.pushRich({" in src
assert "function pushRich(notification)" in SERVICE.read_text()
for forbidden in ["Process {", "Timer {", "telemetry.refresh(", "Quickshell.execDetached",
                  "systemctl", "pkexec", "kill(", "terminate", "fanControl.",
                  "contributors", "controlTarget", "sensor.source"]:
    assert forbidden not in src, forbidden

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const code=fs.readFileSync(process.argv[1],'utf8')
  .replace(/^\s*\.pragma library\s*$/m,'');
const ctx={Date,String,Number,isFinite,Array};
vm.runInNewContext(code,ctx,{filename:'CpuPlusSystemReportPolicy.js'});
const row=(id,usage,extra={})=>({_systemRecord:true,id,usage,...extra});
const at=Date.parse('2026-10-16T13:00:00Z');
const items=[
  row('system:cpu',78.4),row('system:memory',67.5),
  row('system:swap',4.7),row('system:rootfs',71.2),
  row('system:gpu:CARD0',-1),row('system:gpu:CARD1',42),
  row('system:net:eth0',-1,{secondary:'UP'}),
  row('system:net:wlan0',-1,{secondary:'DOWN'}),
  row('system:net:tun0',-1,{secondary:'UNKNOWN'}),
  row('system:disk:sda',30),row('system:cpu',44,{_systemRecord:false})
];
const snapshot=ctx.observation(items,at);
assert(snapshot);
assert.strictEqual(snapshot.cpuPercent,78.4);
assert.strictEqual(snapshot.memoryPercent,67.5);
assert.strictEqual(snapshot.swapPercent,4.7);
assert.strictEqual(snapshot.rootStoragePercent,71.2);
assert.strictEqual(snapshot.gpuPercent,42);
assert.strictEqual(snapshot.networkUp,1);
assert.strictEqual(snapshot.networkDown,1);
assert.strictEqual(snapshot.networkUnknown,1);
assert.strictEqual(snapshot.observedAtUtc,'2026-10-16T13:00:00.000Z');
const summary=ctx.summary(snapshot);
for(const part of ['CPU // 78.4%', 'RAM // 67.5%', 'ROOT STORAGE // 71.2%',
                   'GPU // 42.0%', 'NETWORK // 1 UP'])
  assert(summary.includes(part),part);
assert.strictEqual(ctx.localDayKey(new Date(2026,9,16,8)),'2026-10-16');
assert.strictEqual(ctx.percent(-1),null);
assert.strictEqual(ctx.percent('not available'),null);
assert.strictEqual(ctx.percent(101),null);
assert.strictEqual(ctx.percent(''),null);
assert.strictEqual(ctx.observation([],at),null);
assert.strictEqual(ctx.observation([row('system:cpu',-1)],at),null);
const missing=ctx.observation([row('system:memory',58)],at);
assert(missing && missing.cpuPercent===null);
assert(ctx.summary(missing).includes('CPU // N/A'));
console.log('CPU++ SYSTEM observational report policy: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY)], check=True)
print("CPU++ SYSTEM report contracts: PASS")
