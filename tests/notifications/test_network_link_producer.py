#!/usr/bin/env python3
"""Network link notifications: synthetic state transitions and QML wiring."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/NetworkLinkPolicy.js"
PRODUCER = ROOT / "services/notifications/NetworkLinkNotificationProducer.qml"
NETWORK = ROOT / "modules/Network.qml"
QM = ROOT / "services/notifications/qmldir"
FACETS = ROOT / "services/notifications/NotificationFacets.js"
SERVICE = ROOT / "services/notifications/NotificationsService.qml"

src = PRODUCER.read_text(encoding="utf-8")
module = NETWORK.read_text(encoding="utf-8")
assert 'NetworkLinkNotificationProducer {' in module
assert 'networkLinkProducer.observeDeviceResult(text);' in module
assert 'command: ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]' in module
assert "NetworkLinkNotificationProducer 1.0 NetworkLinkNotificationProducer.qml" in QM.read_text()
assert 'function observeDeviceResult(output)' in src
assert 'NetworkLinkPolicy.parseDeviceStatus(output)' in src
assert 'NetworkLinkPolicy.transition(' in src
assert '"source": "NETWORK"' in src
assert '"sourceId": "apollo-network-link"' in src
assert '"severity": disconnected ? "warning" : "normal"' in src
assert '"origin": "apollo"' in src
assert '"domain": "system"' in src
assert 'NotificationsService.pushRich({' in src
assert 'function pushRich(notification)' in SERVICE.read_text()
assert 'function facetsFor(event)' in FACETS.read_text()
for forbidden in ["Process {", "Timer {", "Quickshell.execDetached", "nmcli", "networkDock.",
                  "telemetry.refresh(", "kill(", "limit(", "fanControl."]:
    assert forbidden not in src, "producer cannot poll or control: " + forbidden

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8').replace(/^\s*\.pragma library\s*$/m,'');
const ctx={String,Number,isFinite};vm.runInNewContext(source,ctx,{filename:'NetworkLinkPolicy.js'});
const parse=ctx.parseDeviceStatus,step=ctx.transition;
const up='wlp3s0:wifi:connected:Home\neth0:ethernet:disconnected:--';
const down='wlp3s0:wifi:disconnected:--\neth0:ethernet:unavailable:--';
const dual='wlp3s0:wifi:disconnected:--\neth0:ethernet:connected:LAN';
const trying='wlp3s0:wifi:connecting (getting IP configuration):Home\neth0:ethernet:disconnected:--';
const other='lo:loopback:connected (externally):lo\nwg0:wireguard:connected:wg0';
assert.strictEqual(parse(up).connected,true);
assert.strictEqual(parse(down).connected,false);
assert.strictEqual(parse(dual).connected,true,"Wi-Fi loss with Ethernet connected is not an outage");
assert.strictEqual(parse('wlp3s0:wifi:connected (externally):Home').connected,true);
assert.strictEqual(parse(trying),null,"transitional states cannot confirm loss");
assert.strictEqual(parse(other),null,"VPN and loopback are not network links in this policy");
assert.strictEqual(parse('Error: NetworkManager not running'),null);
assert.strictEqual(parse(''),null);
assert.strictEqual(parse('wlp3s0:wifi:unmanaged:--'),null);
let state=ctx.initial(),events=[];
function observed(raw,when){const result=step(state,parse(raw),when);state=result.state;events.push(result.event);return result.event;}
observed(up,1000);observed(up,2000);observed(up,3100);
assert.strictEqual(state.stable,'up');
assert.deepStrictEqual(events,['','',''],"startup baseline must stay quiet");
observed(down,4000);
observed(up,4300); // brief Wi-Fi interruption cancels a pending outage
assert.strictEqual(state.stable,'up');
observed(down,5000); observed(down,6000);
assert.strictEqual(observed(down,7100),'disconnected');
assert.strictEqual(state.stable,'down');
observed(down,8000);observed(down,9000);
assert.strictEqual(events.filter(x=>x==='disconnected').length,1,"no storm");
observed(trying,9500); // unknown must not claim restoration
observed(dual,10000);observed(dual,11000);
assert.strictEqual(observed(dual,12100),'restored');
assert.strictEqual(state.stable,'up');
assert.strictEqual(events.filter(x=>x==='restored').length,1);
observed(up,13000);
observed(down,14000);observed(down,15000);
observed(down,16100);
assert.strictEqual(events.filter(x=>x==='disconnected').length,2,"re-arm after recovery");
const last=JSON.stringify(state);
assert.strictEqual(observed('not parseable',17000),'');
assert.strictEqual(JSON.stringify(state),last,"invalid observations cannot fabricate transitions");
state=ctx.initial();observed(down,1000);observed(down,2000);
assert.strictEqual(observed(down,3100),'');
assert.strictEqual(state.stable,'down');
assert.strictEqual(observed(up,4000),'');
assert.strictEqual(observed(up,5000),'');
assert.strictEqual(observed(up,6100),'restored',"offline startup is silent; subsequent restoration reports");
state=ctx.initial();
observed(up,1000);observed(up,2000);observed(up,3100);
observed(down,4000);observed(down,18000);
assert.strictEqual(observed(down,18500),'',"stale gap resets the pending candidate");
assert.strictEqual(observed(down,20100),'disconnected');
console.log('Network link state transition policy: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY)], check=True)
print("Network link producer contracts: PASS")
