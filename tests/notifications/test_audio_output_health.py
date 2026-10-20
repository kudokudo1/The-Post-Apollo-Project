#!/usr/bin/env python3
"""Passive default audio sink availability, with synthetic QML transitions."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/AudioOutputHealthPolicy.js"
QML = ROOT / "services/notifications/AudioOutputHealthNotificationProducer.qml"
VOLUME = ROOT / "modules/Volumebar.qml"
QM = ROOT / "services/notifications/qmldir"
WORKFLOW = ROOT / ".github/workflows/notification-policy-contracts.yml"
NOTIFICATIONS = ROOT / "services/notifications/NotificationsService.qml"

qml = QML.read_text()
volume = VOLUME.read_text()
assert "import Quickshell.Services.Pipewire" in volume
assert "import qs.services.notifications" in volume
assert "property var sink: Pipewire.defaultAudioSink" in volume
assert "readonly property bool ready: sink && sink.ready" in volume
assert "AudioOutputHealthNotificationProducer {" in volume
assert "outputReady: root.ready" in volume
assert "AudioOutputHealthNotificationProducer 1.0 AudioOutputHealthNotificationProducer.qml" in QM.read_text()
assert "test_audio_output_health.py" in WORKFLOW.read_text()
assert "required property bool outputReady" in qml
assert "interval: 4000" in qml and "repeat: false" in qml
assert "onOutputReadyChanged" in qml and "onTriggered: producer.observe()" in qml
assert '"sourceId": "audio-default-output-health"' in qml
assert '"origin": "apollo"' in qml and '"domain": "system"' in qml
assert '"observation": "default PipeWire audio sink readiness only"' in qml
assert "function pushRich(notification)" in NOTIFICATIONS.read_text()
for forbidden in ["Process {", "execDetached", "pw-dump", "pactl", "wpctl",
                  "MPD", "setVolume(", "setMuted(", "toggleMute(", "device.name",
                  "bluetoothctl", "systemctl", "audio.muted"]:
    assert forbidden not in qml, "Default audio observer cannot control audio: " + forbidden

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const logic=fs.readFileSync(process.argv[1],'utf8')
 .replace(/^\s*\.pragma library\s*$/m,'');
const P={String,Number,isFinite};
vm.runInNewContext(logic,P,{filename:'AudioOutputHealthPolicy.js'});
let state=P.initial();
function at(ready,t){
 const result=P.transition(state,ready,t);
 state=result.state;return result.event;
}
assert.strictEqual(at(false,1000),'','no output on startup is silent');
assert.strictEqual(at(false,5000),'');
assert.strictEqual(at(true,7000),'','first-ever ready is silent');
assert.strictEqual(state.everReady,true);
assert.strictEqual(at(false,11000),'');
assert.strictEqual(at(true,12000),'','quick sink change cannot warn');
assert.strictEqual(at(false,15000),'');
assert.strictEqual(at(false,19000),'unavailable');
assert.strictEqual(at(false,23000),'');
assert.strictEqual(at(true,24000),'');
assert.strictEqual(at(true,28000),'restored');
assert.strictEqual(at(true,32000),'');
assert.strictEqual(at(false,33000),'');
assert.strictEqual(at(true,34000),'');
assert.strictEqual(at(false,36000),'');
assert.strictEqual(at(false,40000),'unavailable');
const before=JSON.stringify(state);
assert.strictEqual(at(null,42000),'');
assert.strictEqual(JSON.stringify(state),before);
assert.strictEqual(at(false,40000),'','stale same timestamp cannot repeat');

const qml=fs.readFileSync(process.argv[2],'utf8');
function method(name) {
 const start=qml.indexOf('function '+name+'(');assert(start>=0);
 const open=qml.indexOf('{',start);let n=0,end=-1;
 for(let i=open;i<qml.length;i++){
  if(qml[i]==='{')n++;
  else if(qml[i]==='}' && --n===0){end=i+1;break;}
 }
 assert(end>open);return qml.slice(start,end);
}
let clock=1000, timerRestarts=0, timerStops=0;
const sent=[];
class Clock extends Date{static now(){return clock;}}
const timer={
 running:false,
 restart(){timerRestarts++;this.running=true;},
 stop(){timerStops++;this.running=false;}
};
const runtime={
 Date:Clock,OutputPolicy:P,
 NotificationsService:{historyReady:true,pushRich:x=>sent.push(x)},
 producer:{outputReady:true,state:P.initial()},
 confirmChange:timer
};
vm.runInNewContext(method('observe'),runtime);
runtime.observe();
assert.strictEqual(sent.length,0);
runtime.producer.outputReady=false;clock=3000;runtime.observe();
assert.strictEqual(timer.running,true,'change starts bounded confirmation');
clock=7500;runtime.observe();
assert.strictEqual(sent.length,1);
assert(sent[0].title.includes('DEFAULT OUTPUT NOT READY'));
assert.strictEqual(sent[0].severity,'warning');
assert.strictEqual(sent[0].context.origin,'apollo');
assert.strictEqual(sent[0].context.domain,'system');
assert.strictEqual(timer.running,false,'confirmed warning stops timer');
runtime.producer.outputReady=true;clock=9000;runtime.observe();
clock=14000;runtime.observe();
assert.strictEqual(sent.length,2);
assert(sent[1].title.includes('DEFAULT OUTPUT READY AGAIN'));
assert.strictEqual(sent[1].severity,'normal');
runtime.producer.outputReady=false;clock=15000;runtime.observe();
runtime.producer.outputReady=true;clock=16000;runtime.observe();
assert.strictEqual(sent.length,2,'flaps do not create a warning');
assert(timerRestarts>0 && timerStops>0);
assert(sent.every(x=>!JSON.stringify(x).includes('mpd')));
assert(sent.every(x=>!JSON.stringify(x).includes('ALC1220')));
console.log('Default audio-output signal and bounded confirmation QML fanout: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY), str(QML)], check=True)
print("Passive default PipeWire output health: PASS")
