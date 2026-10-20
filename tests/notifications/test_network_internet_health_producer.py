#!/usr/bin/env python3
"""Internet health: bounded real probe transport + QML policy/producer contracts."""
from pathlib import Path
from unittest import mock
import importlib.util
import json
import socket
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PY = ROOT / "scripts/network/internet_health_probe.py"
POLICY = ROOT / "services/notifications/NetworkInternetHealthPolicy.js"
PRODUCER = ROOT / "services/notifications/NetworkInternetHealthNotificationProducer.qml"
LINK = ROOT / "services/notifications/NetworkLinkPolicy.js"
NETWORK = ROOT / "modules/Network.qml"
QM = ROOT / "services/notifications/qmldir"
WORKFLOW = ROOT / ".github/workflows/notification-policy-contracts.yml"
SERVICE = ROOT / "services/notifications/NotificationsService.qml"

spec = importlib.util.spec_from_file_location("pa_internet_probe", PY)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
assert len(probe.TARGETS) == 2
assert len({host for host, _ in probe.TARGETS}) == 2
assert probe.TIMEOUT_SECONDS <= 4
assert probe.snapshot(lambda host, path: "ok")["status"] == "reachable"
assert probe.snapshot(lambda host, path: "dns")["status"] == "dns-failed"
assert probe.snapshot(lambda host, path: "https")["status"] == "https-failed"
assert probe.snapshot(lambda host, path: "unknown")["status"] == "unknown"
assert probe.snapshot(lambda host, path: "ok" if host == probe.TARGETS[0][0] else "https")["status"] == "reachable"
assert probe.snapshot(lambda host, path: "dns" if host == probe.TARGETS[0][0] else "https")["status"] == "https-failed"
assert not any("ip" in result or "detail" in result or "ssid" in result for result in probe.snapshot(lambda h, p: "https")["results"])

with mock.patch.object(probe.socket, "getaddrinfo", side_effect=socket.gaierror("offline")):
    assert probe.probe_target("example.com", "/") == "dns"

class FakeResponse:
    status = 204
    def read(self, limit):
        assert limit <= 128
        return b""
class FakeConnection:
    next_status = 204
    def __init__(self, host, port, timeout, context):
        assert host == "example.com" and port == 443
        assert timeout <= 4
        self.closed = False
    def request(self, method, path, headers):
        assert method == "GET" and path == "/"
        assert "Authorization" not in headers and "Cookie" not in headers
    def getresponse(self):
        class Response(FakeResponse):
            status = FakeConnection.next_status
        return Response()
    def close(self):
        self.closed = True
with mock.patch.object(probe.socket, "getaddrinfo", return_value=[object()]), \
     mock.patch.object(probe.ssl, "create_default_context", return_value=object()), \
     mock.patch.object(probe.http.client, "HTTPSConnection", FakeConnection):
    FakeConnection.next_status = 204
    assert probe.probe_target("example.com", "/") == "ok"
    FakeConnection.next_status = 302
    assert probe.probe_target("example.com", "/") == "http", "redirect is not verified access"

module = NETWORK.read_text()
qml = PRODUCER.read_text()
assert "NetworkLinkNotificationProducer {" in module
assert "NetworkInternetHealthNotificationProducer {" in module
assert "networkInternetHealthProducer.observeDeviceResult(text);" in module
assert "networkLinkProducer.observeDeviceResult(text);" in module
assert 'command: ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]' in module
assert "NetworkInternetHealthNotificationProducer 1.0 NetworkInternetHealthNotificationProducer.qml" in QM.read_text()
assert "test_network_internet_health_producer.py" in WORKFLOW.read_text()
assert "Quickshell.shellPath(\"scripts/network/internet_health_probe.py\")" in qml
assert 'interval: 120000' in qml
assert "producer.localLinkAvailable" in qml and "NotificationsService.historyReady" in qml
assert "producer.pendingEpoch !== producer.linkEpoch" in qml
assert '"sourceId": "apollo-internet-health"' in qml
assert '"origin": "apollo"' in qml and '"domain": "system"' in qml
assert '"severity": restored ? "normal" : "warning"' in qml
assert "NotificationsService.pushRich({" in qml
assert "function pushRich(notification)" in SERVICE.read_text()
for forbidden in ['command: ["nmcli"', "ping(", "iptables", "pkexec", "Quickshell.execDetached",
                  "service.restart", "systemctl", "kill(", "gatewayAddress",
                  '"ssid":', '"password":', "subprocess.run("]:
    assert forbidden not in qml, "Notification producer may not control network: " + forbidden

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8')
  .replace(/^\s*\.pragma library\s*$/m,'');
const links=fs.readFileSync(process.argv[3],'utf8')
  .replace(/^\s*\.pragma library\s*$/m,'');
const P={JSON,Number,String,Array,Object,isFinite};
vm.runInNewContext(source,P,{filename:'NetworkInternetHealthPolicy.js'});
const L={String,Number,isFinite,Array,Object};
vm.runInNewContext(links,L);
function result(a,b) {
 const stages=[a,b],names=['example.com','www.cloudflare.com'];
 const ok=stages.filter(x=>x==='ok').length;
 const dns=stages.filter(x=>x==='dns').length;
 return JSON.stringify({
  schema:1,probeCount:2,successes:ok,dnsFailures:dns,
  status: stages.includes('unknown')?'unknown':
          ok?'reachable':dns===2?'dns-failed':'https-failed',
  results:stages.map((stage,i)=>({target:names[i],stage}))
 });
}
assert.strictEqual(P.parseResult(result('dns','dns')).status,'dns-failed');
assert.strictEqual(P.parseResult(result('https','http')).status,'https-failed');
assert.strictEqual(P.parseResult(result('ok','https')).status,'reachable');
assert.strictEqual(P.parseResult(result('unknown','https')).status,'unknown');
assert.strictEqual(P.parseResult('garbage'),null);
assert.strictEqual(P.parseResult('{"schema":1,"status":"reachable","results":[]}'),null);
assert.strictEqual(P.parseResult(result('dns','dns').replace('dns-failed','reachable')),null);
assert.strictEqual(P.parseResult(result('ok','https').replace('example.com','wrong')),null);
let state=P.initial(), events=[];
function sample(raw,when) {
 const v=P.transition(state,P.parseResult(raw),when);
 state=v.state;events.push(v.event);return v.event;
}
sample(result('ok','https'),1000);
assert.strictEqual(state.stable,'reachable');
assert.strictEqual(events[0],'','healthy startup silent');
sample(result('dns','dns'),121000);
assert.strictEqual(sample(result('dns','dns'),241000),'dns-failed');
assert.strictEqual(state.stable,'impaired');
assert.strictEqual(sample(result('dns','dns'),361000),'','no repeated down spam');
assert.strictEqual(sample(result('ok','https'),481000),'','one endpoint success, recovery pending');
assert.strictEqual(sample(result('ok','http'),601000),'restored');
assert.strictEqual(state.stable,'reachable');
assert.strictEqual(sample(result('dns','dns'),721000),'');
assert.strictEqual(sample(result('https','https'),841000),'','changing diagnosis resets candidate');
assert.strictEqual(sample(result('https','https'),961000),'https-failed');
state=P.initial();
assert.strictEqual(sample(result('dns','dns'),1000),'');
assert.strictEqual(sample(result('dns','dns'),121000),'dns-failed',
 'startup after two correlated failures must notify');
state=P.initial();
assert.strictEqual(sample(result('https','https'),1000),'');
assert.strictEqual(sample(result('unknown','https'),121000),'',
 'uncertain probe can never notify');
assert.strictEqual(sample(result('https','https'),241000),'',
 'unknown interrupts a candidate streak');
assert.strictEqual(sample(result('https','https'),361000),'https-failed');
state=P.initial();
assert.strictEqual(sample(result('dns','dns'),1000),'');
assert.strictEqual(sample(result('dns','dns'),500000),'','stale observation invalidates pending');
assert.strictEqual(sample(result('dns','dns'),620000),'dns-failed');
const before=JSON.stringify(state);
assert.strictEqual(sample(result('dns','dns'),620000),'');
assert.strictEqual(JSON.stringify(state),before);

const qml=fs.readFileSync(process.argv[2],'utf8');
function method(name) {
 const at=qml.indexOf('function '+name+'(');assert(at>=0,'missing '+name);
 const open=qml.indexOf('{',at);let n=0,end=-1;
 for(let i=open;i<qml.length;i++){
  if(qml[i]==='{')n++;
  else if(qml[i]==='}' && --n===0){end=i+1;break;}
 }
 assert(end>open);return qml.slice(at,end);
}
const sent=[];
let t=1000, refreshes=0;
class Clock extends Date {static now(){return t;}}
const runtime={
 Date:Clock, String, InternetPolicy:P, LinkPolicy:L,
 NotificationsService:{historyReady:true,pushRich:x=>sent.push(x)},
 producer:{
  localLinkAvailable:false,linkEpoch:0,pendingEpoch:-1,
  lastProbeAtMs:0,reachabilityState:P.initial(),
  refresh:()=>{refreshes++;}
 },
 probeProcess:{running:false}
};
vm.runInNewContext(['observeDeviceResult','refresh','acceptResponse']
 .map(method).join('\n'),runtime);
runtime.producer.refresh=runtime.refresh;
runtime.observeDeviceResult('wlp3s0:wifi:connected:Home');
assert.strictEqual(runtime.producer.localLinkAvailable,true);
assert.strictEqual(runtime.producer.linkEpoch,1);
assert.strictEqual(runtime.probeProcess.running,true,'probe starts after confirmed link');
assert.strictEqual(runtime.producer.pendingEpoch,1);
runtime.probeProcess.running=false;
runtime.acceptResponse(result('dns','dns'));
assert.strictEqual(sent.length,0);
t=121000;runtime.acceptResponse(result('dns','dns'));
assert.strictEqual(sent.length,1);
assert(sent[0].title.includes('DNS RESOLUTION FAILED'));
assert.strictEqual(sent[0].severity,'warning');
assert.strictEqual(sent[0].context.origin,'apollo');
assert.strictEqual(sent[0].context.domain,'system');
assert.strictEqual(sent[0].context.successCount,0);
assert(!JSON.stringify(sent[0]).includes('Home'),'no SSID leaks');
assert(!JSON.stringify(sent[0]).includes('192.168'),'no IP leaks');
t=241000;runtime.acceptResponse(result('dns','dns'));
assert.strictEqual(sent.length,1,'same outage does not notify repeatedly');
t=361000;runtime.acceptResponse(result('ok','https'));
assert.strictEqual(sent.length,1);
t=481000;runtime.acceptResponse(result('ok','https'));
assert.strictEqual(sent.length,2);
assert.strictEqual(sent[1].severity,'normal');
assert(sent[1].title.includes('REACHABLE AGAIN'));
runtime.observeDeviceResult('wlp3s0:wifi:disconnected:--\neth0:ethernet:disconnected:--');
assert.strictEqual(runtime.producer.localLinkAvailable,false);
const epoch=runtime.producer.linkEpoch;
runtime.acceptResponse(result('dns','dns'));
assert.strictEqual(sent.length,2,'local link down ignores pending external results');
runtime.observeDeviceResult('wlp3s0:wifi:connected:Home');
assert.strictEqual(runtime.producer.linkEpoch,epoch+1);
runtime.producer.pendingEpoch=epoch;
runtime.acceptResponse(result('dns','dns'));
assert.strictEqual(sent.length,2,'stale old-link result ignored');
console.log('Internet reachability debounce, safe QML notification fanout: PASS');
"""
subprocess.run(["node", "-e", NODE, str(POLICY), str(PRODUCER), str(LINK)], check=True)
print("Network Internet-health notification contracts: PASS")
