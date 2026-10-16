#!/usr/bin/env python3
"""Solar Report source contracts and deterministic offline NOAA sample tests."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/SolarReportPolicy.js"
PRODUCER = ROOT / "services/notifications/SolarReportNotificationProducer.qml"
SHELL = ROOT / "shell.qml"
QM = ROOT / "services/notifications/qmldir"
SPACE = ROOT / "services/weather/SpaceService.qml"
BACKEND = ROOT / "services/notifications/NotificationsService.qml"

producer = PRODUCER.read_text()
shell = SHELL.read_text()
qmldir = QM.read_text()
space = SPACE.read_text()
backend = BACKEND.read_text()

assert 'SolarReportNotificationProducer {' in shell
assert 'spaceService: spaceService' in shell
assert 'SpaceService {' in shell
assert 'SolarReportNotificationProducer 1.0 SolarReportNotificationProducer.qml' in qmldir
assert '"source": "SOLAR REPORT"' in producer
assert '"sourceId": "weather-space"' in producer
assert '"category": "internal"' in producer
assert '"severity": "normal"' in producer
assert '"id": id' in producer
assert 'if (!NotificationsService.historyReady' in producer
assert 'function historyContains(id)' in producer
assert '"observationTimesUtc": data.observed' in producer
assert 'NotificationsService.pushRich({' in producer
assert 'function onHistoryReadyChanged()' in producer
assert 'function onReadyChanged()' in producer
assert 'function onKpTimeChanged()' in producer
assert 'function onSolarWindTimeChanged()' in producer
assert 'function onMagneticFieldTimeChanged()' in producer
assert 'function onSolarFluxTimeChanged()' in producer
assert 'interval: 600000' in producer
assert 'function refresh()' in space
assert 'interval: 300000' in space
assert 'function pushRich(notification)' in backend
for forbidden in ['Process {', 'Quickshell.execDetached', 'spaceService.refresh(',
                  'spaceService.parseKp(', 'spaceService.parseSolarWind(']:
    assert forbidden not in producer, forbidden

NODE = r"""
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const src = fs.readFileSync(process.argv[1], 'utf8')
  .replace(/^\s*\.pragma library\s*$/m, '');
const ctx = {Date, String, Number, Math, isFinite};
vm.runInNewContext(src, ctx, {filename:'SolarReportPolicy.js'});

const now=Date.parse('2026-10-16T12:00:00Z');
const good = {
    ready:true, kp:4.7, kpLabel:'ACTIVE',
    solarWindSpeed:540.3, magneticFieldBt:7.5,
    magneticFieldBz:-6.4, bzLabel:'SOUTH', solarFlux:173,
    kpTime:'2026-10-16 09:00:00',
    solarWindTime:'2026-10-16T11:50:00Z',
    magneticFieldTime:'2026-10-16 11:45:00',
    solarFluxTime:'2026-10-15 20:00:00'
};
assert.strictEqual(ctx.observationTimeMs('2026-10-16 09:00:00'),
  Date.parse('2026-10-16T09:00:00Z'));
assert.strictEqual(ctx.localDayKey(new Date('2026-10-16T12:00:00Z')),
    '2026-10-16'); // CI runner uses UTC
let record=ctx.snapshot(good,now);
assert(record !== null);
assert.strictEqual(record.kp,4.7);
assert.strictEqual(record.bzNt,-6.4);
assert.strictEqual(record.solarFluxSfu,173);
const message=ctx.summary(record);
for(const token of ['KP 4.7 ACTIVE','WIND 540 KM/S','Bz -6.4 nT SOUTH',
                    'Bt 7.5 nT','F10.7 SOLAR FLUX 173 SFU'])
    assert(message.includes(token), token);

function denied(change) {
    const copy={...good, ...change};
    assert.strictEqual(ctx.snapshot(copy,now),null,JSON.stringify(change));
}
denied({ready:false});
denied({kp:NaN});
denied({solarFlux:NaN});
denied({magneticFieldBz:Infinity});
denied({solarWindSpeed:-1});
denied({kpTime:''});
denied({kpTime:'2026-10-15 02:00:00'});
denied({solarWindTime:'2026-10-16 05:00:00'});
denied({magneticFieldTime:'2026-10-16 15:00:00'});
denied({solarFluxTime:'2026-10-12 20:00:00'});
assert.strictEqual(ctx.snapshot(good, now).kp, 4.7);
console.log('Daily Solar Report policy: PASS');
"""
subprocess.run(["node","-e",NODE,str(POLICY)], check=True)
print("Daily Solar Report producer contracts: PASS")
