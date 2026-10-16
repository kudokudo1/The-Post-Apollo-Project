#!/usr/bin/env python3
"""CPU++ fan health: hwmon-backed cautionary events only, no fan controls."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/CpuPlusFanHealthPolicy.js"
PRODUCER = ROOT / "services/notifications/CpuPlusFanHealthNotificationProducer.qml"
SHELL = ROOT / "shell.qml"
QM = ROOT / "services/notifications/qmldir"
SYSTEM = ROOT / "services/system/SystemTelemetry.qml"
SERVICE = ROOT / "services/notifications/NotificationsService.qml"

source = PRODUCER.read_text()
policy = POLICY.read_text()
shell = SHELL.read_text()
system = SYSTEM.read_text()
assert "CpuPlusFanHealthNotificationProducer {" in shell
assert "telemetry: sharedSystemTelemetry" in shell
assert "CpuPlusFanHealthNotificationProducer 1.0 CpuPlusFanHealthNotificationProducer.qml" in QM.read_text()
assert "signal refreshed()" in system
assert r'\"rpmAvailable\": True' in system
assert r'\"minRpm\": minimum' in system
assert r'\"pwmPercent\":' in system
assert 'fan.source || fan.id' in source
assert 'FanPolicy.transition(next[key], fan, now)' in source
assert 'function onRefreshed() { producer.observe(); }' in source
assert '"sourceId": "cpu-plus-fan-health"' in source
assert '"origin": "apollo"' in source
assert '"domain": "system"' in source
assert '"severity": recovered ? "normal" : "warning"' in source
assert '"evidence": "repeated hwmon tachometer and configured minimum"' in source
assert "NotificationsService.pushRich({" in source
assert "function pushRich(notification)" in SERVICE.read_text()
for forbidden in ["Process {", "Timer {", "telemetry.refresh(",
                  "Quickshell.execDetached", "fanControl.", "systemctl",
                  "pkexec", "kill(", "terminate(", "sensor.contributors",
                  "sensor.source,", "fan.source,"]:
    assert forbidden not in source, "fan notification producer must remain passive: " + forbidden

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const body=fs.readFileSync(process.argv[1],'utf8')
    .replace(/^\s*\.pragma library\s*$/m,'');
const p={Number,String,isFinite};
vm.runInNewContext(body,p,{filename:'CpuPlusFanHealthPolicy.js'});
const make=(rpm,extra={})=>({
  sensorKind:'fan',rpmAvailable:true,rpm,minRpm:600,pwmPercent:65,
  id:'fan:board:one',source:'/sys/class/hwmon/hwmon0/fan1_input',
  name:'FAN 1',chip:'BOARD',...extra
});
const r=p.reading,step=p.transition;
assert.strictEqual(r(make(500)).concerning,true);
assert.strictEqual(r(make(600)).concerning,false);
assert.strictEqual(r(make(0)).concerning,true,'zero and strong PWM demand');
assert.strictEqual(r(make(0,{pwmPercent:10})).concerning,false);
assert.strictEqual(r(make(0,{pwmPercent:-1})).concerning,false);
assert.strictEqual(r(make(0,{pwmPercent:undefined})).concerning,false);
assert.strictEqual(r(make(0,{minRpm:0})),null);
assert.strictEqual(r(make(300,{rpmAvailable:false})),null);
assert.strictEqual(r(make(300,{sensorKind:'temperature'})),null);
assert.strictEqual(r(make(300,{minRpm:null})),null);
assert.strictEqual(r(make(NaN)),null);
assert.strictEqual(r(make(-1)),null);
assert.strictEqual(r(make(300,{minRpm:40000})),null);
assert.strictEqual(r(make(300,{pwmPercent:200})),null);

let state=p.initial(),history=[];
function sample(fan,t){
  const d=step(state,fan,t);
  state=d.state;history.push(d.event);return d.event;
}
sample(make(440),1000);
sample(make(610),2900);
assert.strictEqual(history.length,2);
sample(make(450),4800);sample(make(450),6700);
assert.strictEqual(sample(make(450),8600),'warning');
assert.strictEqual(state.active,true);
sample(make(410),10500);sample(make(440),12400);
assert.strictEqual(history.filter(x=>x==='warning').length,1,'no repeat alert storm');
sample(make(620),14300);sample(make(650),16200);
assert.strictEqual(sample(make(650),18100),'recovered');
assert.strictEqual(state.active,false);
sample(make(0,{pwmPercent:0}),20000);
assert.strictEqual(history.filter(x=>x==='warning').length,1,
   'intentional zero RPM with low demand is silent');
state=p.initial();history=[];
sample(make(0,{pwmPercent:0}),1000);
sample(make(0,{pwmPercent:0}),2900);
sample(make(0,{pwmPercent:0}),4800);
assert(!history.some(Boolean),'zero RPM alone not failure');
sample(make(0,{pwmPercent:60}),6700);
sample(make(0,{pwmPercent:60}),8600);
assert.strictEqual(sample(make(0,{pwmPercent:60}),10500),'warning');
sample(make(0,{pwmPercent:0}),12400);
sample(make(0,{pwmPercent:0}),14300);
sample(make(0,{pwmPercent:0}),16200);
assert.strictEqual(state.active,true,'zero with no demand cannot claim recovery');
sample(make(605),18100);sample(make(605),20000);
assert.strictEqual(sample(make(605),21900),'recovered');
state=p.initial();
sample(make(400),1000);sample(make(400),23000);
assert.strictEqual(sample(make(400),24900),'');
assert.strictEqual(sample(make(400),26800),'warning','stale sample resets streak');
const saved=JSON.stringify(state);
assert.strictEqual(sample(make(400),26800),'');
assert.strictEqual(JSON.stringify(state),saved,'duplicate timestamp invalid');
assert.strictEqual(sample(make(400,{rpmAvailable:false}),28900),'');
assert.strictEqual(JSON.stringify(state),saved,'unavailable tach never mutates state');

// Execute real QML observe() and publish() methods under a mocked passive sink.
const qml=fs.readFileSync(process.argv[2],'utf8');
function extract(method){
  const at=qml.indexOf('function '+method+'(');
  assert(at>=0);
  const open=qml.indexOf('{',at);
  let depth=0,end=-1;
  for(let i=open;i<qml.length;i++){
    if(qml[i]==='{')depth++;
    else if(qml[i]==='}' && --depth===0){end=i+1;break;}
  }
  assert(end>open);return qml.slice(at,end);
}
const sent=[], clock={now:1000};
class Clock extends Date {static now(){return clock.now;}}
const rt={
  Date:Clock,Number,String,Object,Array,
  FanPolicy:p,
  NotificationsService:{pushRich:e=>sent.push(e)},
  producer:{telemetry:{errorText:'',fanRows:[]},fanStates:{}}
};
vm.runInNewContext(extract('observe')+'\n'+extract('publish'),rt);
rt.producer.publish=rt.publish;
function scan(rows,t){
  rt.producer.telemetry.fanRows=rows;
  clock.now=t;
  rt.observe();
}
scan([make(480),make(0,{source:'/sys/class/hwmon/hwmon0/fan2_input',
 name:'FAN 2',rpmAvailable:false})],1000);
scan([make(480)],2900);scan([make(450)],4800);
assert.strictEqual(sent.length,1);
assert.strictEqual(sent[0].title,'CPU++ // FAN RPM BELOW MINIMUM');
assert.strictEqual(sent[0].severity,'warning');
assert.strictEqual(sent[0].metrics.hwmonMinimumRpm,600);
assert.strictEqual(sent[0].context.origin,'apollo');
assert.strictEqual(sent[0].context.domain,'system');
assert.strictEqual(sent[0].context.eventType,'fan-rpm-below-hwmon-minimum');
assert(!JSON.stringify(sent[0]).includes('/sys/class/hwmon'));
scan([make(450)],6700);
assert.strictEqual(sent.length,1,'no repeat popup at same low RPM');
scan([make(650)],8600);scan([make(650)],10500);scan([make(650)],12400);
assert.strictEqual(sent.length,2);
assert.strictEqual(sent[1].severity,'normal');
assert.strictEqual(sent[1].context.eventType,'fan-rpm-recovered');
scan([make(0,{minRpm:0})],14300);
assert.strictEqual(sent.length,2,'missing limit is not an alert');
console.log('CPU++ fan-health policy and actual QML producer: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY), str(PRODUCER)], check=True)
print("CPU++ fan-health notification contracts: PASS")
