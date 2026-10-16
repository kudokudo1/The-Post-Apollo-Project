#!/usr/bin/env python3
"""Regression: Wi-Fi link changes notify even if Ethernet stays connected."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/NetworkLinkPolicy.js"
PRODUCER = ROOT / "services/notifications/NetworkLinkNotificationProducer.qml"
NETWORK = ROOT / "modules/Network.qml"
QM = ROOT / "services/notifications/qmldir"
FACETS = ROOT / "services/notifications/NotificationFacets.js"
SERVICE = ROOT / "services/notifications/NotificationsService.qml"

source = PRODUCER.read_text(encoding="utf-8")
module = NETWORK.read_text(encoding="utf-8")
assert 'NetworkLinkNotificationProducer {' in module
assert 'networkLinkProducer.observeDeviceResult(text);' in module
assert 'command: ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]' in module
assert "NetworkLinkNotificationProducer 1.0 NetworkLinkNotificationProducer.qml" in QM.read_text()
assert 'function observeDeviceResult(output)' in source
assert 'NetworkLinkPolicy.parseDeviceStatus(output)' in source
assert 'NetworkLinkPolicy.transition(' in source
assert '"source": "NETWORK"' in source
assert '"sourceId": "apollo-network-link"' in source
assert '"severity": disconnected ? "warning" : "normal"' in source
assert '"origin": "apollo"' in source
assert '"domain": "system"' in source
assert '"linkType": change.kind' in source
assert 'NotificationsService.pushRich({' in source
assert 'function pushRich(notification)' in SERVICE.read_text()
assert 'function facetsFor(event)' in FACETS.read_text()
for forbidden in ["Process {", "Timer {", "Quickshell.execDetached",
                  'command: ["nmcli"', "networkDock.", "telemetry.refresh(",
                  "kill(", "limit(", "fanControl."]:
    assert forbidden not in source, "producer cannot poll or control: " + forbidden

NODE = r"""
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const policy=fs.readFileSync(process.argv[1],'utf8')
    .replace(/^\s*\.pragma library\s*$/m,'');
const logic={String,Number,isFinite};
vm.runInNewContext(policy,logic,{filename:'NetworkLinkPolicy.js'});
const parse=logic.parseDeviceStatus,step=logic.transition;
const up='wlp3s0:wifi:connected:Home\neth0:ethernet:connected:LAN';
const wifiDown='wlp3s0:wifi:disconnected:--\neth0:ethernet:connected:LAN';
const allDown='wlp3s0:wifi:unavailable:--\neth0:ethernet:disconnected:--';
const ethDown='wlp3s0:wifi:connected:Home\neth0:ethernet:disconnected:--';
const connecting='wlp3s0:wifi:connecting (getting IP configuration):Home\neth0:ethernet:connected:LAN';
const other='lo:loopback:connected (externally):lo\nwg0:wireguard:connected:wg0';
assert.strictEqual(parse(up).wifi,true);
assert.strictEqual(parse(up).ethernet,true);
assert.strictEqual(parse(wifiDown).wifi,false,
    'Wi-Fi down must be seen even while Ethernet remains connected');
assert.strictEqual(parse(wifiDown).ethernet,true);
assert.strictEqual(parse(allDown).wifi,false);
assert.strictEqual(parse(allDown).ethernet,false);
assert.strictEqual(parse(ethDown).ethernet,false);
assert.strictEqual(parse(connecting).wifi,null);
assert.strictEqual(parse(other),null);
assert.strictEqual(parse('Error: NetworkManager not running'),null);
assert.strictEqual(parse('wlp3s0:wifi:unmanaged:--').wifi,null);
assert.strictEqual(parse('wlp3s0:wifi:connected').wifi,true,
    'Unpopulated CONNECTION column cannot discard valid status');

let state=logic.initial(),history=[];
function observed(raw,when){
    const result=step(state,parse(raw),when);
    state=result.state; history.push(...result.events);
    return result.events.map(x=>x.kind+':'+x.event).join(',');
}
observed(up,1000);observed(up,1600);observed(up,2100);
assert.strictEqual(state.wifi.stable,'up');
assert.strictEqual(state.ethernet.stable,'up');
assert.strictEqual(history.length,0,'startup baseline silent');
observed(wifiDown,3000);
observed(up,3300);
assert.strictEqual(history.length,0,'flap must not announce');
observed(wifiDown,4000); observed(wifiDown,4600);
assert.strictEqual(observed(wifiDown,5100),'wifi:disconnected',
    'Wi-Fi loss must notify with Ethernet still online');
observed(wifiDown,6100);observed(wifiDown,7100);
assert.strictEqual(history.length,1,'steady down cannot spam');
observed(connecting,7400);
assert.strictEqual(history.length,1,'connecting is not recovery');
observed(up,8000); observed(up,8600);
assert.strictEqual(observed(up,9100),'wifi:restored');
assert.strictEqual(history.length,2);
observed(ethDown,10000);observed(ethDown,10600);
assert.strictEqual(observed(ethDown,11100),'ethernet:disconnected');
assert.strictEqual(history.length,3);
assert.strictEqual(observed('not parseable',12000),'');
assert.strictEqual(history.length,3);
state=logic.initial();history=[];
observed(allDown,1000);observed(allDown,1500);observed(allDown,2100);
assert.strictEqual(history.length,0,'offline startup must also be quiet');
observed(up,3000);observed(up,3500);
assert.strictEqual(observed(up,4100),'wifi:restored,ethernet:restored');
state=logic.initial();history=[];
observed(up,1000);observed(up,1500);observed(up,2100);
observed(wifiDown,3000);observed(wifiDown,14000);
assert.strictEqual(observed(wifiDown,14500),'');
assert.strictEqual(observed(wifiDown,15100),'wifi:disconnected',
    'gap resets stale candidate rather than manufacturing alert');

// Exercise the ACTUAL QML producer function with mocked event sink and time.
// This catches producer-loop wiring/payload regressions which policy-only tests miss.
const qml=fs.readFileSync(process.argv[2],'utf8');
const methodStart=qml.indexOf('function observeDeviceResult(output)');
assert(methodStart>=0);
const open=qml.indexOf('{',methodStart);
let depth=0,end=-1;
for(let i=open;i<qml.length;i++){
    if(qml[i]==='{')depth++;
    else if(qml[i]==='}'){
        depth--;
        if(depth===0){end=i+1;break;}
    }
}
assert(end>open);
const pushed=[];
let clock=1000;
class Clock extends Date{static now(){return clock;}}
const runtime={
    NetworkLinkPolicy:logic,NotificationsService:{pushRich:e=>pushed.push(e)},
    Date:Clock,linkState:logic.initial()
};
const emit=vm.runInNewContext('('+qml.slice(methodStart,end)+')',runtime);
function sample(raw,ms){clock=ms;emit(raw);}
sample(up,1000);sample(up,1600);sample(up,2100);
sample(wifiDown,3000);sample(wifiDown,3600);sample(wifiDown,4100);
assert.strictEqual(pushed.length,1);
assert.strictEqual(pushed[0].context.linkType,'wifi');
assert.strictEqual(pushed[0].context.origin,'apollo');
assert.strictEqual(pushed[0].context.domain,'system');
assert.strictEqual(pushed[0].severity,'warning');
assert(pushed[0].title.includes('WI-FI LINK DISCONNECTED'));
assert(!pushed[0].message.includes('No Wi-Fi or Ethernet'));
sample(up,5000);sample(up,5600);sample(up,6100);
assert.strictEqual(pushed.length,2);
assert.strictEqual(pushed[1].severity,'normal');
assert(pushed[1].title.includes('WI-FI LINK RESTORED'));
assert(pushed.every(x=>!JSON.stringify(x).includes('Home')),
       'SSID must not be stored in a notification');
console.log('Wi-Fi / Ethernet independent producer execution: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY), str(PRODUCER)], check=True)
print("Network link producer contracts: PASS")
