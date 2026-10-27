#!/usr/bin/env python3
"""Official NWS alert intake: explicit point, authenticated source, safe lifecycle."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/NwsOfficialAlertPolicy.js"
PRODUCER = ROOT / "services/notifications/NwsOfficialAlertNotificationProducer.qml"
SHELL = ROOT / "shell.qml"
QM = ROOT / "services/notifications/qmldir"
BASE = ROOT / "services/notifications/NotificationsService.qml"

qml = PRODUCER.read_text()
shell_text = SHELL.read_text()
assert "NwsOfficialAlertNotificationProducer {" in shell_text
assert "id: nwsOfficialAlerts" in shell_text
assert "nwsAlertSource: nwsOfficialAlerts" in shell_text
assert "readonly property bool configured:" in qml
assert "readonly property bool loading:" in qml
assert "readonly property bool ready:" in qml
assert "readonly property var alertList:" in qml
assert "readonly property int activeCount:" in qml
assert "property date lastUpdated" in qml
assert 'property string errorText: ""' in qml
assert "NwsOfficialAlertNotificationProducer 1.0 NwsOfficialAlertNotificationProducer.qml" in QM.read_text()
assert "POST_APOLLO_NWS_ALERT_POINT" in qml
assert "Quickshell.env(" in qml
assert "api.weather.gov/alerts/active?point=" in qml
assert '"Accept: application/geo+json"' in qml
assert "Post-Apollo-WeatherStation" in qml
assert "interval: 900000" in qml
assert 'producer.alertPoint !== ""' in qml
assert "NotificationsService.historyReady" in qml
assert "NwsPolicy.parseActive(text, Date.now())" in qml
assert "function historyContains(alertId, revision, kind)" in qml
assert 'vanished ? "normal" : alert.displaySeverity' in qml
assert '"sourceId": "weather-station-nws"' in qml
assert '"origin": "apollo"' in qml and '"domain": "weather"' in qml
assert "NotificationsService.pushRich({" in qml
assert "function pushRich(notification)" in BASE.read_text()
assert "spaceService.latitude" not in qml and "wttr.in" not in qml
for forbidden in ["pkexec", "systemctl", "Quickshell.execDetached",
                  "kill(", "notification.tracked", "setPower", "fanControl."]:
    assert forbidden not in qml, forbidden

NODE=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8')
  .replace(/^\s*\.pragma library\s*$/m,'');
const p={Date,Number,String,isFinite,Array,JSON,Object};
vm.runInNewContext(source,p,{filename:'NwsOfficialAlertPolicy.js'});
const point=p.configuredPoint;
assert.strictEqual(point('38.8894,-77.0352'),'38.8894,-77.0352');
assert.strictEqual(point(' 38.5, -77 '),'38.5,-77');
for(const invalid of ['',null,'Berlin','127.0.0.1','38.555555,-77',
                       '38,-190','90.1,12','38.2,-77.2;rm -rf /']){
  assert.strictEqual(point(invalid),'',String(invalid));
}
assert.strictEqual(p.notificationSeverity('Extreme'),'critical');
assert.strictEqual(p.notificationSeverity('Severe'),'critical');
assert.strictEqual(p.notificationSeverity('Moderate'),'warning');
assert.strictEqual(p.notificationSeverity('Minor'),'normal');
const now=Date.parse('2026-10-20T13:00:00Z');
function alert(id,props={}){
  return {type:'Feature',id,properties:{
    id,event:'Tornado Warning',status:'Actual',severity:'Severe',
    urgency:'Immediate',certainty:'Observed',messageType:'Alert',
    category:'Met',response:'Shelter',
    headline:'Tornado Warning for TEST county',areaDesc:'TEST County',
    senderName:'NWS TEST Office',sent:'2026-10-20T12:00:00Z',
    updated:'2026-10-20T12:05:00Z',
    effective:'2026-10-20T12:00:00Z',onset:'2026-10-20T12:05:00Z',
    expires:'2026-10-20T14:00:00Z',ends:'2026-10-20T14:00:00Z',
    ...props
  }};
}
function feed(arr){return JSON.stringify({type:'FeatureCollection',features:arr});}
assert.strictEqual(p.parseActive('not json',now),null);
assert.strictEqual(p.parseActive('{"type":"FeatureCollection"}',now),null);
assert.strictEqual(p.parseActive('{"features":[]}',now),null);
assert.strictEqual(p.parseActive(feed([]),now).length,0);
assert.strictEqual(p.parseActive(feed([alert('a',{status:'Test'})]),now).length,0);
assert.strictEqual(p.parseActive(feed([alert('a',{expires:'2026-10-20T12:00:00Z'})]),now).length,0);
assert.strictEqual(p.parseActive(feed([alert('a',{severity:'Severe'}),
                                      alert('a',{severity:'Minor'})]),now).length,1);
const one=p.parseActive(feed([alert('abc')]),now);
assert.strictEqual(one.length,1);
assert.strictEqual(one[0].id,'abc');
assert.strictEqual(one[0].displaySeverity,'critical');
assert.strictEqual(one[0].area,'TEST County');
assert.strictEqual(one[0].issuer,'NWS TEST Office');
assert.strictEqual(one[0].urgency,'Immediate');
assert.strictEqual(one[0].certainty,'Observed');
assert.strictEqual(one[0].effective,'2026-10-20T12:00:00.000Z');
assert.strictEqual(one[0].onset,'2026-10-20T12:05:00.000Z');
assert.strictEqual(one[0].ends,'2026-10-20T14:00:00.000Z');
assert.strictEqual(one[0].messageType,'Alert');
assert.strictEqual(one[0].category,'Met');
assert.strictEqual(one[0].response,'Shelter');
let state={};
let result=p.advance(state,one);
state=result.state;
assert.strictEqual(result.changes.length,1);
assert.strictEqual(result.changes[0].kind,'observed');
let visible=p.visibleAlerts(state);
assert.strictEqual(visible.length,1);
assert.strictEqual(visible[0].listingState,'ACTIVE');
result=p.advance(state,one);
state=result.state;
assert.strictEqual(result.changes.length,0);
const revised=p.parseActive(feed([alert('abc',{updated:'2026-10-20T12:10:00Z'})]),now);
result=p.advance(state,revised);state=result.state;
assert.strictEqual(result.changes[0].kind,'updated');
result=p.advance(state,null);
assert.strictEqual(result.changes.length,0,'failed request cannot clear');
result=p.advance(state,[]);
assert.strictEqual(result.changes.length,0,'first absence silent');
state=result.state;
visible=p.visibleAlerts(state);
assert.strictEqual(visible.length,1);
assert.strictEqual(visible[0].listingState,'RECHECK PENDING');
assert.strictEqual(visible[0].absentChecks,1);
result=p.advance(state,[]);
assert.strictEqual(result.changes[0].kind,'not-listed');
state=result.state;
assert.strictEqual(p.visibleAlerts(state).length,0);
assert.strictEqual(p.advance(state,[]).changes.length,0,'single departure event');

const qml=fs.readFileSync(process.argv[2],'utf8');
function method(name){
 const ix=qml.indexOf('function '+name+'(');
 assert(ix>=0,'must expose '+name);
 const start=qml.indexOf('{',ix);
 let depth=0,end=-1;
 for(let i=start;i<qml.length;i++){
   if(qml[i]==='{')depth++;
   else if(qml[i]==='}' && --depth===0){end=i+1;break;}
 }
 assert(end>start);
 return qml.slice(ix,end);
}
const entries=[];
let ms=now;
class Clock extends Date{static now(){return ms;}}
const runtime={
 Date:Clock,Number,String,Object,
 NwsPolicy:p,
 NotificationsService:{
  historyReady:true, notifications:{get count(){return entries.length;},get:i=>entries[i]},
  pushRich:item=>{entries.push(item);}
 },
 producer:{activeAlerts:{}}
};
vm.runInNewContext(
 ['historyContains','publish','acceptResponse'].map(method).join('\n'),runtime);
runtime.producer.historyContains=runtime.historyContains;
runtime.producer.publish=runtime.publish;
runtime.acceptResponse(feed([alert('abc')]));
assert.strictEqual(entries.length,1);
assert.strictEqual(entries[0].context.alertId,'abc');
assert.strictEqual(entries[0].severity,'critical');
assert.strictEqual(entries[0].context.issuer,'NWS TEST Office');
assert.strictEqual(entries[0].context.origin,'apollo');
assert.strictEqual(entries[0].context.domain,'weather');
assert(entries[0].title.includes('ACTIVE'));
runtime.acceptResponse(feed([alert('abc')]));
assert.strictEqual(entries.length,1);
runtime.acceptResponse('bad json');
assert.strictEqual(entries.length,1,'malformed response must not resolve alert');
assert.strictEqual(runtime.producer.errorText,'NWS RESPONSE INVALID');
runtime.acceptResponse(feed([alert('abc',{updated:'2026-10-20T12:10:00Z'})]));
assert.strictEqual(runtime.producer.errorText,'');
assert.strictEqual(runtime.producer.fetchSucceeded,true);
assert(runtime.producer.lastUpdated instanceof Clock);
assert.strictEqual(entries.length,2);
assert(entries[1].title.includes('UPDATED'));
runtime.acceptResponse(feed([]));
assert.strictEqual(entries.length,2);
runtime.acceptResponse(feed([]));
assert.strictEqual(entries.length,3);
assert(entries[2].title.includes('NO LONGER LISTED AS ACTIVE'));
assert(entries[2].message.includes('does not establish cancellation or all-clear'));
runtime.acceptResponse(feed([]));
assert.strictEqual(entries.length,3);
runtime.producer.activeAlerts={};
runtime.acceptResponse(feed([alert('abc')]));
assert.strictEqual(entries.length,3,'history dedupes restart');
runtime.NotificationsService.historyReady=false;
runtime.acceptResponse(feed([alert('new')]));
assert.strictEqual(entries.length,3);
console.log('NWS official alert policy and real QML intake: PASS');
"""
subprocess.run(["node","-e",NODE,str(POLICY),str(PRODUCER)], check=True)
print("NWS official active-alert contracts: PASS")
