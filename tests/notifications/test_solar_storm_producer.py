#!/usr/bin/env python3
"""Storm thresholds: real NOAA Kp timestamps and producer-level suppression."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/SolarStormPolicy.js"
PRODUCER = ROOT / "services/notifications/SolarStormNotificationProducer.qml"
REPORT = ROOT / "services/notifications/SolarReportPolicy.js"
SHELL = ROOT / "shell.qml"
QM = ROOT / "services/notifications/qmldir"
SPACE = ROOT / "services/weather/SpaceService.qml"

src = PRODUCER.read_text()
shell = SHELL.read_text()
space = SPACE.read_text()
assert "SolarStormNotificationProducer {" in shell
assert "spaceService: spaceService" in shell
assert "SolarStormNotificationProducer 1.0 SolarStormNotificationProducer.qml" in QM.read_text()
assert 'sourceId": "weather-space-storm"' in src
assert '"origin": "apollo"' in src
assert '"domain": "weather"' in src
assert "NotificationsService.historyReady" in src
assert "function onKpTimeChanged()" in src
assert "function onKpReadyChanged()" in src
assert "function onHistoryReadyChanged()" in src
assert "function historyContains(id)" in src
assert "function observe()" in src
assert "StormPolicy.transition(" in src
assert 'id = "apollo-noaa-kp-storm-" + observedMs' in src
assert "interval: 300000" in space
assert "NOAA SWPC" in src
for forbidden in ["Process {", "Timer {", 'command: ["curl"', "spaceService.refresh(",
                  "systemctl", "pkexec", "Quickshell.execDetached", "kill("]:
    assert forbidden not in src, f"storm producer cannot poll/control: {forbidden}"
NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
function load(path, ctx) {
  vm.runInNewContext(fs.readFileSync(path,'utf8')
    .replace(/^\s*\.pragma library\s*$/m,''),ctx,{filename:path});
}
const core={Date,Number,String,isFinite},solar={Date,Number,String,isFinite};
load(process.argv[1],core);
load(process.argv[3],solar);
const initial=core.initial,advance=core.transition;
for(const [v,l] of [[0,0],[4.99,0],[5,1],[5.5,1],[6,2],[7,3],[8,4],[9,5]]) {
  assert.strictEqual(core.stormLevel(v),l);
}
for(const bad of [null,undefined,'',true,-1,9.1,NaN,Infinity])
  assert.strictEqual(core.stormLevel(bad),-1);
const hour=3600000,t0=Date.parse('2026-10-16T10:00:00Z');
let state=initial();
function read(kp,time,now=time+30*60000){
  const outcome=advance(state,kp,time,now);
  state=outcome.state;return outcome;
}
assert.strictEqual(read(4.2,t0).emit,0);
assert.strictEqual(read(5.2,t0).emit,0,'same observation must never be replayed');
let x=read(5.2,t0+3*hour);
assert.strictEqual(x.emit,1);
assert.strictEqual(x.kind,'observed');
assert.strictEqual(read(9,t0+3*hour).emit,0,'same timestamp never renotifies');
x=read(6.2,t0+6*hour);assert.strictEqual(x.emit,2);
assert.strictEqual(x.kind,'escalated');
x=read(7.1,t0+9*hour);assert.strictEqual(x.emit,3);
x=read(7.5,t0+12*hour);assert.strictEqual(x.emit,0);
read(3.9,t0+15*hour);
x=read(5.5,t0+18*hour);assert.strictEqual(x.emit,1);
assert.strictEqual(x.kind,'observed');
const prior=JSON.stringify(state);
assert.strictEqual(read(9,t0+15*hour).emit,0);
assert.strictEqual(JSON.stringify(state),prior,'out-of-order timestamps ignored');
assert.strictEqual(read(9,t0+24*hour,t0+34*hour).emit,0,'stale Kp ignored');
assert.strictEqual(read(9,t0+24*hour,t0+23*hour).emit,0,'future Kp ignored');

const qml=fs.readFileSync(process.argv[2],'utf8');
function extract(name) {
  const at=qml.indexOf('function '+name+'('),open=qml.indexOf('{',at);
  assert(at>=0);
  let depth=0,close=-1;
  for(let i=open;i<qml.length;i++){
    if(qml[i]==='{')depth++;
    else if(qml[i]==='}'){if(--depth===0){close=i+1;break;}}
  }
  assert(close>open);return qml.slice(at,close);
}
const emitted=[],history=[];
let wall=t0+2*hour;
class Clock extends Date{static now(){return wall;}}
const runtime={
 Date:Clock,Number,String,StormPolicy:core,SolarReportPolicy:solar,
 NotificationsService:{
  historyReady:true,
  notifications:{get count(){return history.length;},get:i=>history[i]},
  pushRich:e=>{emitted.push(e);history.push(e);}
 },
 producer:{
  kpState:initial(),spaceService:{kpReady:true,kp:6.3,
    kpTime:'2026-10-16 10:00:00'}
 }
};
vm.runInNewContext(extract('historyContains')+'\n'+extract('observe'),runtime);
runtime.producer.historyContains=runtime.historyContains;
runtime.observe();
assert.strictEqual(emitted.length,1);
assert.strictEqual(emitted[0].severity,'warning');
assert.strictEqual(emitted[0].context.origin,'apollo');
assert.strictEqual(emitted[0].context.domain,'weather');
assert.strictEqual(emitted[0].title,'SPACE WEATHER // G2 STORM OBSERVED');
assert.strictEqual(emitted[0].metrics.kp,6.3);
runtime.observe();
assert.strictEqual(emitted.length,1);
runtime.producer.kpState=initial();
runtime.observe();
assert.strictEqual(emitted.length,1,'history dedupes restart');
runtime.producer.spaceService.kp=7.1;
runtime.producer.spaceService.kpTime='2026-10-16 13:00:00';
wall=t0+5*hour;
runtime.observe();
assert.strictEqual(emitted.length,2);
assert.strictEqual(emitted[1].severity,'critical');
assert.strictEqual(emitted[1].title,'SPACE WEATHER // G3 STORM ESCALATED');
runtime.NotificationsService.historyReady=false;
runtime.producer.spaceService.kp=8.2;
runtime.producer.spaceService.kpTime='2026-10-16 16:00:00';
wall=t0+8*hour;
runtime.observe();
assert.strictEqual(emitted.length,2);
console.log('NOAA observed Kp transition and real producer: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY), str(PRODUCER),
                str(REPORT)], check=True)
print("Solar storm notification contracts: PASS")
