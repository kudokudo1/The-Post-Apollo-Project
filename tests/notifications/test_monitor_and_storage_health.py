#!/usr/bin/env python3
"""CPU++ telemetry and Notifications storage: read-only recorded health."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/CpuPlusTelemetryHealthPolicy.js"
PRODUCER = ROOT / "services/notifications/CpuPlusTelemetryHealthNotificationProducer.qml"
STORAGE_POLICY = ROOT / "services/notifications/NotificationsPersistenceHealthPolicy.js"
STORAGE_PRODUCER = ROOT / "services/notifications/NotificationsPersistenceHealthProducer.qml"
TELEMETRY = ROOT / "services/system/SystemTelemetry.qml"
SHELL = ROOT / "shell.qml"
QM = ROOT / "services/notifications/qmldir"
NOTIFICATIONS = ROOT / "services/notifications/NotificationsService.qml"
WORKFLOW = ROOT / ".github/workflows/notification-policy-contracts.yml"

cpu = PRODUCER.read_text()
storage = STORAGE_PRODUCER.read_text()
telemetry = TELEMETRY.read_text()
shell = SHELL.read_text()
qm = QM.read_text()
assert "signal monitorObservation(bool healthy)" in telemetry
assert "systemTelemetry.monitorObservation(" in telemetry
assert 'systemTelemetry.errorText === ""' in telemetry
assert "systemTelemetry.monitorObservation(false);" in telemetry
assert "CpuPlusTelemetryHealthNotificationProducer {" in shell
assert "NotificationsPersistenceHealthProducer {}" in shell
assert "CpuPlusTelemetryHealthNotificationProducer 1.0 CpuPlusTelemetryHealthNotificationProducer.qml" in qm
assert "NotificationsPersistenceHealthProducer 1.0 NotificationsPersistenceHealthProducer.qml" in qm
assert "test_monitor_and_storage_health.py" in WORKFLOW.read_text()
assert "function onMonitorObservation(healthy)" in cpu
assert "function onHistoryStatusChanged()" in storage
assert "function onHistoryReadyChanged()" in storage
assert "function onPolicyStatusChanged()" in storage
assert "function onFavoritesStatusChanged()" in storage
assert '"sourceId": "cpu-plus-telemetry-health"' in cpu
assert '"sourceId": "notifications-storage-health"' in storage
assert '"origin": "apollo"' in cpu and '"domain": "system"' in cpu
assert '"origin": "apollo"' in storage and '"domain": "system"' in storage
assert "function pushRich(notification)" in NOTIFICATIONS.read_text()
for name, text in [("CPU++", cpu), ("Storage", storage)]:
    for forbidden in ["Process {", "Timer {", "execDetached", "setText(", "open(", "remove(",
                      "systemctl", "pactl", "nmcli", "sudo", "pkexec", "kill("]:
        assert forbidden not in text, (name, forbidden)

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
function logic(path) {
 const text=fs.readFileSync(path,'utf8').replace(/^\s*\.pragma library\s*$/m,'');
 const context={Number,Array,String,Object,isFinite};
 vm.runInNewContext(text,context,{filename:path});
 return context;
}
const P=logic(process.argv[1]);
const S=logic(process.argv[3]);

let state=P.initial();
function sample(ok,at){
 const result=P.transition(state,ok,at);state=result.state;
 return result.event;
}
assert.strictEqual(sample(true,1000),'','normal startup silent');
assert.strictEqual(sample(true,5000),'');
assert.strictEqual(sample(false,10000),'');
assert.strictEqual(sample(true,11000),'','one failed probe is not an outage');
assert.strictEqual(sample(false,16000),'');
assert.strictEqual(sample(false,20000),'unavailable');
assert.strictEqual(state.health,'failed');
assert.strictEqual(sample(false,24000),'','no repeated warnings');
assert.strictEqual(sample(true,28000),'','a request resetting error text cannot by itself establish recovery');
assert.strictEqual(sample(false,30000),'','failed next sample cancels attempted recovery');
assert.strictEqual(sample(true,36000),'');
assert.strictEqual(sample(true,40000),'restored');
assert.strictEqual(sample(true,45000),'');
state=P.initial();
assert.strictEqual(sample(false,1000),'');
assert.strictEqual(sample(false,6000),'unavailable','repeat failures after startup warn');
state=P.initial();
assert.strictEqual(sample(false,1000),'');
assert.strictEqual(sample(false,70000),'','stale gap resets streak');
assert.strictEqual(sample(false,75000),'unavailable');
assert.strictEqual(sample(false,75000),'','same timestamp never repeats');
const before=JSON.stringify(state);
assert.strictEqual(sample(null,80000),'');
assert.strictEqual(JSON.stringify(state),before);

let storageState=S.initial();
function store(area,status) {
 const result=S.transition(storageState,area,status);
 storageState=result.state;
 return result.event;
}
assert.strictEqual(store('history','loading'),'');
assert.strictEqual(store('history','ready'),'');
assert.strictEqual(store('history','saving'),'');
assert.strictEqual(store('history','save-error'),'unavailable');
assert.strictEqual(store('history','save-error'),'','repeat failure cannot spam');
assert.strictEqual(store('history','saving'),'','a retry is not success');
assert.strictEqual(store('history','saved'),'restored','actual save success recovers');
assert.strictEqual(store('history','saved'),'');
assert.strictEqual(store('policy','load-error'),'unavailable');
assert.strictEqual(store('favorites','parse-error'),'unavailable');
assert.strictEqual(store('policy','ready'),'restored');
assert.strictEqual(store('favorites','new'),'','missing new file is not recovered');
assert.strictEqual(store('favorites','saved'),'restored');
assert.strictEqual(store('unknown','save-error'),'');
assert.strictEqual(store('history','clearing'),'');
assert.strictEqual(Object.keys(storageState).length,3);

function extract(qml,name) {
 const at=qml.indexOf('function '+name+'(');
 assert(at>=0,'missing function '+name);
 const brace=qml.indexOf('{',at);
 let depth=0,end=-1;
 for(let i=brace;i<qml.length;i++){
  if(qml[i]==='{')depth++;
  else if(qml[i]==='}' && --depth===0){end=i+1;break;}
 }
 assert(end>brace);return qml.slice(at,end);
}
const cpuSource=fs.readFileSync(process.argv[2],'utf8');
const sent=[];let clock=1000;
class Clock extends Date{static now(){return clock;}}
const runtime={
 Date:Clock,HealthPolicy:P,NotificationsService:{
   historyReady:true,pushRich:x=>sent.push(x)
 },producer:{state:P.initial()}
};
vm.runInNewContext(extract(cpuSource,'receive'),runtime);
function receive(ok,at){clock=at;runtime.receive(ok);}
receive(true,1000);
receive(false,6000);
receive(false,12000);
assert.strictEqual(sent.length,1);
assert(sent[0].title.includes('MONITOR DATA UNAVAILABLE'));
assert.strictEqual(sent[0].severity,'warning');
assert(!JSON.stringify(sent[0]).includes('password'));
assert.strictEqual(sent[0].context.domain,'system');
receive(true,18000);
receive(true,24000);
assert.strictEqual(sent.length,2);
assert(sent[1].title.includes('MONITOR DATA RESTORED'));
assert.strictEqual(sent[1].severity,'normal');

const storageSource=fs.readFileSync(process.argv[4],'utf8');
const history=[];
const storageService={
 historyReady:true,policyReady:true,favoritesReady:true,
 historyStatus:'ready',policyStatus:'ready',favoritesStatus:'ready',
 pushRich:x=>history.push(x)
};
const storageRuntime={
 Date:Clock,StoragePolicy:S,NotificationsService:storageService,
 producer:{state:S.initial()}
};
vm.runInNewContext([extract(storageSource,'observe'),
 extract(storageSource,'scan')].join('\n'),storageRuntime);
storageRuntime.producer.observe=storageRuntime.observe;
storageRuntime.producer.scan=storageRuntime.scan;
storageRuntime.scan();
assert.strictEqual(history.length,0,'normal loaded startup silent');
storageService.historyStatus='save-error';
storageRuntime.scan();
assert.strictEqual(history.length,1);
assert.strictEqual(history[0].source,'NOTIFICATIONS');
assert.strictEqual(history[0].severity,'warning');
assert.strictEqual(history[0].context.store,'history');
storageRuntime.scan();
assert.strictEqual(history.length,1);
storageService.historyStatus='saving';
storageRuntime.scan();
assert.strictEqual(history.length,1);
storageService.historyStatus='saved';
storageRuntime.scan();
assert.strictEqual(history.length,2);
assert.strictEqual(history[1].severity,'normal');
storageService.policyStatus='save-error';
storageRuntime.scan();
assert.strictEqual(history.length,3);
assert(history[2].title.includes('DND / SNOOZE'));
storageService.favoritesStatus='load-error';
storageRuntime.scan();
assert.strictEqual(history.length,4);
assert(history[3].title.includes('FAVORITE'));
assert(history.every(x=>!JSON.stringify(x).includes('/home/')));
assert(history.every(x=>x.context.origin==='apollo'));
console.log('CPU telemetry & Notifications storage actual QML fanout: PASS');
"""
subprocess.run([
    "node", "-e", NODE, str(POLICY), str(PRODUCER),
    str(STORAGE_POLICY), str(STORAGE_PRODUCER)
], check=True)
print("CPU++ monitoring and notification persistence health: PASS")
