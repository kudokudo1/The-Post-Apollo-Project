#!/usr/bin/env python3
"""Native/browser notification intake: metadata, safe presentation, and actions."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SERVER=ROOT/"services/notifications/NotificationsService.qml"
CONVERTER=ROOT/"services/notifications/NotificationsConverter.qml"
POPUP=ROOT/"modules/Notifications.qml"
FACETS=ROOT/"services/notifications/NotificationFacets.js"
HUB=ROOT/"widgets/notifications/NotificationsHubW.qml"

server=SERVER.read_text()
convert=CONVERTER.read_text()
popup=POPUP.read_text()
hub=HUB.read_text()
for needle in [
    "NotificationServer {", "bodySupported: true", "actionsSupported: true",
    "persistenceSupported: true", "imageSupported: true", "bodyMarkupSupported: false",
    "onNotification: function (notification)", "notification.tracked = true;",
    "root.pushConverted(converted);", "root.trackExternalNotification(eventId, notification, converted);",
    "function pushConverted(notification)", "appendNotification(notification);",
    "function trackExternalNotification(eventId, nativeNotification, converted)",
    "nativeNotification.closed.connect(function(reason)",
    "function invokeExternalAction(eventId, actionIdentifier)",
    "action.invoke();", "function historySnapshot(", "scheduleHistorySave();"
]:
    assert needle in server, needle
assert popup.count("textFormat: Text.PlainText")>=3
assert "text: notificationCard.sourceId" in popup
assert "text: notificationCard.title" in popup
assert "text: notificationCard.message" in popup
assert "NotificationsService.externalActionsFor(notificationCard.notificationId)" in popup
assert "NotificationsService.invokeExternalAction(" in popup
assert "NotificationsService.notifications" in hub
assert "NotificationFacets.facetsFor(entry)" in hub
assert "notification.summary" in convert and "notification.body" in convert
assert "notification.desktopEntry" in convert
assert "notification.appName" in convert
for banned in ["notifications.append(nativeNotification)", "JSON.stringify(nativeNotification)",
               "nativeNotification.actions.map(", "bodyHyperlinksSupported: true",
               "bodyMarkupSupported: true"]:
    assert banned not in server, banned

NODE=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const conv=fs.readFileSync(process.argv[1],'utf8');
const srv=fs.readFileSync(process.argv[2],'utf8');
const facetSrc=fs.readFileSync(process.argv[3],'utf8')
 .replace(/^\s*\.pragma library\s*$/m,'');
function method(text,name){
 const at=text.indexOf('function '+name+'(');assert(at>=0,'missing '+name);
 const o=text.indexOf('{',at);let depth=0,end=-1;
 for(let i=o;i<text.length;i++){
  if(text[i]==='{')depth++;
  else if(text[i]==='}' && --depth===0){end=i+1;break;}
 }
 assert(end>o);return text.slice(at,end);
}
const C={String,NotificationUrgency:{Critical:2,Normal:1,Low:0},root:{}};
vm.runInNewContext(['categoryFor','severityFor','convert']
 .map(n=>method(conv,n)).join('\n'),C);
C.root.categoryFor=C.categoryFor;C.root.severityFor=C.severityFor;
const F={String,Array,Object};
vm.runInNewContext(facetSrc,F);
const mock=(appName,desktopEntry,category,urgency)=>({
 appName,desktopEntry,hints:category?{category}:{},
 urgency,summary:'<b>Literal title</b>',body:'<script>not HTML</script>',
 appIcon:'discord',image:''
});
let result=C.convert(mock('Discord','discord','im.received',1));
assert.strictEqual(result.source,'Discord');
assert.strictEqual(result.sourceId,'discord');
assert.strictEqual(result.category,'im.received');
assert.strictEqual(result.title,'<b>Literal title</b>');
assert.strictEqual(result.message,'<script>not HTML</script>');
assert.strictEqual(F.facetsFor(result).domain,'social');
let mail=C.convert(mock('Thunderbird','thunderbird','email.arrived',1));
assert.strictEqual(F.facetsFor(mail).domain,'social');
let browser=C.convert(mock('Brave','brave-browser',null,1));
assert.strictEqual(F.facetsFor(browser).domain,'apps',
 'Browser cannot be assumed to be a social website');
let webHint=C.convert(mock('Brave','brave-browser','im.received',2));
assert.strictEqual(F.facetsFor(webHint).domain,'social');
assert.strictEqual(webHint.severity,'critical');
assert.strictEqual(F.facetsFor(webHint).severity,'warning');
assert.strictEqual(C.convert(mock('App','','',0)).severity,'low');
assert.strictEqual(C.convert(mock('App','','',1)).severity,'normal');
assert.strictEqual(C.convert(mock('App','','',2)).severity,'critical');

let now=1000,invokeCount=0;
class Clock extends Date {static now(){return now;}}
const notification={
 actions:[
  {identifier:'default',text:'OPEN',invoke:()=>{invokeCount++;}},
  {identifier:'reply',text:'REPLY',invoke:()=>{invokeCount+=2;}}
 ]
};
const S={
 Date:Clock,String,
 liveExternalNotifications:{
  'event-1':{notification,expiresAt:4000}
 }
};
vm.runInNewContext(['externalActionsFor','invokeExternalAction']
 .map(n=>method(srv,n)).join('\n'),S);
const actions=S.externalActionsFor('event-1');
assert.strictEqual(actions.length,2);
assert.strictEqual(actions[0].identifier,'default');
assert.strictEqual(S.invokeExternalAction('event-1','reply'),true);
assert.strictEqual(invokeCount,2);
assert.strictEqual(S.invokeExternalAction('event-1','unknown'),false);
assert.strictEqual(S.invokeExternalAction('unknown','reply'),false);
now=5000;
assert.strictEqual(S.externalActionsFor('event-1').length,0);
assert.strictEqual(S.invokeExternalAction('event-1','default'),false);
assert.strictEqual(invokeCount,2);
console.log('Synthetic native metadata, classification, live-action routing: PASS');
"""
subprocess.run(["node","-e",NODE,str(CONVERTER),str(SERVER),str(FACETS)],check=True)
print("External native/browser intake contracts: PASS")
