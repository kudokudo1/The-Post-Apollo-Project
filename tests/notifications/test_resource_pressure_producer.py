#!/usr/bin/env python3
"""CPU++ resource-pressure notifications: read-only policy and QML execution."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/ResourcePressurePolicy.js"
PRODUCER = ROOT / "services/notifications/ResourcePressureNotificationProducer.qml"
SHELL = ROOT / "shell.qml"
QM = ROOT / "services/notifications/qmldir"
SERVICE = ROOT / "services/notifications/NotificationsService.qml"
SYSTEM = ROOT / "services/system/SystemTelemetry.qml"

src = PRODUCER.read_text(encoding="utf-8")
shell = SHELL.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")
telemetry = SYSTEM.read_text(encoding="utf-8")
assert "ResourcePressureNotificationProducer {" in shell
assert "telemetry: sharedSystemTelemetry" in shell
assert "ResourcePressureNotificationProducer 1.0 ResourcePressureNotificationProducer.qml" in QM.read_text()
assert "signal refreshed()" in telemetry
assert "function onRefreshed() { producer.observe(); }" in src
assert "NotificationsService.historyReady" in src
assert 'NotificationsService.pushRich({' in src
assert "function pushRich(notification)" in service
assert '"source": "CPU++"' in src
assert '"sourceId": "cpu-plus-resource-pressure"' in src
assert '"origin": "apollo"' in src
assert '"domain": "system"' in src
assert '"severity": recovered ? "normal"' in src
assert '"sampling": "existing active monitoring only"' in src
assert "process control" not in src.lower()
for forbidden in ["Process {", "Timer {", "telemetry.refresh(", "Quickshell.execDetached",
                  "pkexec", "systemctl", "kill(", "terminate(", "fanControl.",
                  "contributors", "controlTarget", "sensor.source"]:
    assert forbidden not in src, f"Producer must remain passive: {forbidden}"

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const code=fs.readFileSync(process.argv[1],'utf8')
  .replace(/^\s*\.pragma library\s*$/m,'');
const policy={Date,String,Number,isFinite,Array};
vm.runInNewContext(code,policy,{filename:'ResourcePressurePolicy.js'});
const p=policy.percent,obs=policy.observation,step=policy.transition;
const row=(id,usage,extra={})=>({_systemRecord:true,id,usage,...extra});
assert.strictEqual(p(null),null);
assert.strictEqual(p(false),null);
assert.strictEqual(p(''),null);
assert.strictEqual(p(-1),null);
assert.strictEqual(p(102),null);
assert.strictEqual(p(97.5),97.5);
assert.strictEqual(obs(null),null);
assert.strictEqual(obs([]),null);
assert.strictEqual(obs([row('system:cpu',98)]),null);
assert.strictEqual(obs([row('system:memory',97,{_systemRecord:false})]),null);
assert.strictEqual(obs([row('system:memory',null),row('system:rootfs',-1)]),null);
const metrics=obs([
  row('system:memory',91.5),row('system:rootfs',97.9),
  row('system:swap',99),row('system:cpu',97)
]);
assert.strictEqual(metrics.memory,91.5);
assert.strictEqual(metrics.storage,97.9);
assert.strictEqual(metrics.swap,99);
assert.strictEqual(policy.level('memory',89.9),0);
assert.strictEqual(policy.level('memory',90),1);
assert.strictEqual(policy.level('memory',97),2);
assert.strictEqual(policy.level('storage',97),2);
assert.strictEqual(policy.thresholds('swap'),null,
  'high swap usage alone must not trigger notifications');

let state=policy.initial(), events=[];
function reading(kind,value,ms){
  const d=step(state,kind,value,ms);
  state=d.state;events.push(d.event);return d.event;
}
reading('memory',95,1000);
reading('memory',95,2900);
assert.strictEqual(reading('memory',95,4800),'warning');
assert.strictEqual(state.sent,1);
reading('memory',95,6700);
reading('memory',95,8600);
assert.strictEqual(events.filter(e=>e==='warning').length,1,
  'unchanged high RAM must not storm');
reading('memory',98,10500);reading('memory',98,12400);
assert.strictEqual(reading('memory',98,14300),'critical');
assert.strictEqual(state.sent,2);
reading('memory',95,16200);reading('memory',95,18100);
reading('memory',95,20000);
assert.strictEqual(state.sent,2,
  'falling below critical is not proof of complete recovery');
reading('memory',86,21900);reading('memory',86,23800);
assert.strictEqual(reading('memory',86,25700),'recovered');
assert.strictEqual(state.sent,0);
reading('memory',94,27600);reading('memory',94,29500);
assert.strictEqual(reading('memory',94,31400),'warning',
  'a confirmed new rise after recovery can report again');
state=policy.initial();events=[];
reading('storage',96,1000);
reading('storage',96,2900);
assert.strictEqual(reading('storage',88,4800),'');
assert.strictEqual(state.sent,0,'short pressure spike must be ignored');
reading('storage',97.5,6700);reading('storage',97.5,8600);
assert.strictEqual(reading('storage',97.5,10500),'critical',
  'critical directly from normal must work');
const frozen=JSON.stringify(state);
assert.strictEqual(reading('storage',101,12400),'');
assert.strictEqual(JSON.stringify(state),frozen,'invalid samples do not mutate');
state=policy.initial();
reading('memory',91,1000);reading('memory',91,25000);
assert.strictEqual(reading('memory',91,26900),'');
assert.strictEqual(reading('memory',91,28800),'warning',
  'stale gap must reset streak');
state=policy.initial();reading('memory',95,1000);
reading('memory',95,2900);
assert.strictEqual(reading('memory',95,2900),'',
  'duplicate timestamps cannot count as separate samples');

// Execute QML method bodies through a synthetic actual service sink.
const qml=fs.readFileSync(process.argv[2],'utf8');
function extract(name) {
  const at=qml.indexOf('function '+name+'(');
  assert(at>=0, name+' QML method exists');
  const open=qml.indexOf('{',at);
  let braces=0,close=-1;
  for(let i=open;i<qml.length;i++){
    if(qml[i]==='{')braces++;
    else if(qml[i]==='}'){
      braces--;
      if(braces===0){close=i+1;break;}
    }
  }
  assert(close>open);
  return qml.slice(at,close);
}
const sent=[];
let clock=1000;
class Clock extends Date{static now(){return clock;}}
const runtime={
  Date:Clock,PressurePolicy:policy,
  NotificationsService:{historyReady:true,pushRich:e=>sent.push(e)},
  producer:{
    telemetry:{systemRows:[],errorText:''},
    metricStates:{memory:policy.initial(),storage:policy.initial()}
  }
};
vm.runInNewContext(extract('publish')+'\n'+extract('observe'),runtime);
runtime.producer.publish=runtime.publish;
function snapshot(memory,storage,swap,ms){
  clock=ms;
  runtime.producer.telemetry.systemRows=[
    row('system:memory',memory),row('system:rootfs',storage),
    row('system:swap',swap)
  ];
  runtime.observe();
}
snapshot(91,60,95,1000);
snapshot(91,60,95,2900);
snapshot(91,60,95,4800);
assert.strictEqual(sent.length,1);
assert.strictEqual(sent[0].title,'CPU++ // MEMORY PRESSURE');
assert.strictEqual(sent[0].severity,'warning');
assert.strictEqual(sent[0].context.metric,'memory');
assert.strictEqual(sent[0].context.origin,'apollo');
assert.strictEqual(sent[0].context.domain,'system');
assert.strictEqual(sent[0].metrics.swapPercent,95);
snapshot(97.2,98,98,6700);
snapshot(97.2,98,98,8600);
snapshot(97.2,98,98,10500);
assert.strictEqual(sent.filter(x=>x.severity==='critical').length,2,
  'both memory and storage can escalate independently');
assert(sent.some(x=>x.title==='CPU++ // ROOT STORAGE CRITICAL'));
runtime.NotificationsService.historyReady=false;
snapshot(86,86,40,12400);
assert.strictEqual(sent.length,3,'history loading must not send');
runtime.NotificationsService.historyReady=true;
snapshot(86,86,40,14300);
snapshot(86,86,40,16200);
snapshot(86,86,40,18100);
assert.strictEqual(sent.filter(x=>x.title.includes('RECOVERED')).length,2);
assert(sent.every(x=>x.sourceId==='cpu-plus-resource-pressure'));
assert(sent.every(x=>x.context.eventType.startsWith('resource-pressure-')));
assert(!sent.some(x=>JSON.stringify(x).includes('processId')));
console.log('CPU++ resource-pressure policy and producer: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY), str(PRODUCER)], check=True)
print("CPU++ resource-pressure contracts: PASS")
