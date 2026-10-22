#!/usr/bin/env python3
"""Event-specific notification routing without fabricated notification URLs.

The JS harness runs the real QML destination function. Browser/site fallback
is intentional and only opens a validated site origin; only a live native
"default" action can open the exact notification target.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HUB = ROOT / "widgets/notifications/NotificationsHubW.qml"
POPUP = ROOT / "modules/Notifications.qml"
SERVICE = ROOT / "services/notifications/NotificationsService.qml"
IDENTITY = ROOT / "services/notifications/BrowserSiteIdentity.js"

hub = HUB.read_text(encoding="utf-8")
popup = POPUP.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")

assert "function invokeExternalDefaultAction(eventId)" in service
assert 'return invokeExternalAction(eventId, "default");' in service
assert "function hasExternalDefaultAction(eventId)" in service
assert "root.openNotificationDestination(" in hub
assert "row.notificationId, row.sourceId, row.source, row.websiteHost" in hub
assert "notificationEntry.notificationId," in hub
assert "notificationEntry.websiteHost);" in hub
assert 'root.bringAppHere(notificationEntry.sourceId, notificationEntry.source)' in hub, (
    "Bring Here arrow should remain a distinct workspace action"
)
assert "id: nativeDefaultClickArea" in popup
assert "NotificationsService.invokeExternalDefaultAction(" in popup
assert "NotificationsService.hasExternalDefaultAction(" in popup
assert "id: externalActionRow" in popup
assert "NotificationsService.invokeExternalAction(" in popup, (
    "Explicit native action buttons must still work"
)
assert '"xdg-open", "https://" + hostname + "/"' in hub
assert 'eval(' not in hub and "exec(" not in hub

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
function method(text,name) {
  const at=text.indexOf('function '+name+'(');assert(at>=0,'missing '+name);
  const start=text.indexOf('{',at);let depth=0,end=-1;
  for (let i=start;i<text.length;i++) {
    if (text[i]==='{')depth++;
    else if (text[i]==='}' && --depth===0) {end=i+1;break;}
  }
  assert(end>start,'unclosed '+name);return text.slice(at,end);
}
const hub=fs.readFileSync(process.argv[1],'utf8');
const sites=fs.readFileSync(process.argv[2],'utf8');
const Site={String};
vm.runInNewContext(['token','chromiumFamily','hostnameFor']
 .map(n=>method(sites,n)).join('\n'),Site);
const actions=[];
let nativeResult=false;
const root={
  takeMeToApp(sourceId,source) {actions.push({kind:'app',sourceId,source});}
};
const Q={
  execDetached(argv) {actions.push({kind:'exec',argv:[...argv]});}
};
const H={
  String,Quickshell:Q,root,
  BrowserSiteIdentity:{
    hostnameFor:Site.hostnameFor,
    chromiumFamily:Site.chromiumFamily
  },
  NotificationsService:{
    invokeExternalDefaultAction(id) {
      actions.push({kind:'native-attempt',id});
      return nativeResult;
    },
    // Browser notifications have no registered Apollo event route. Apollo
    // routing itself is exercised in test_apollo_destination_routing.py.
    requestApolloDestination(id) { return false; }
  }
};
vm.runInNewContext(method(hub,'openNotificationDestination'),H);
function check(route, expectedKinds) {
  assert.strictEqual(route, expectedKinds[0].route);
  assert.deepStrictEqual(actions.map(x=>x.kind),expectedKinds[0].actions);
  actions.length=0;
}
nativeResult=true;
check(H.openNotificationDestination('event-1','brave-browser','Brave','mail.proton.me'),[
 {route:'native-default', actions:['native-attempt']}
]);
nativeResult=false;
check(H.openNotificationDestination('expired','brave-browser','Brave','mail.proton.me'),[
 {route:'site-home', actions:['native-attempt','exec']}
]);
const siteHome=Q.execDetached; // verification captured below with separate run
const route=H.openNotificationDestination('expired2','brave-browser','Brave','www.youtube.com');
assert.strictEqual(route,'site-home');
assert.deepStrictEqual(actions[1].argv,['xdg-open','https://www.youtube.com/']);
actions.length=0;
const badHosts=[
 'https://youtube.com;touch /tmp/untrusted', 'javascript:alert(1)',
 'https://youtube.com@evil.test', 'not a domain',
 'youtube.com" --danger', 'http://localhost:9999'
];
for (const host of badHosts) {
  check(H.openNotificationDestination('bad','brave-browser','Brave',host),[
   {route:'application',actions:['native-attempt','app']}
  ]);
}
check(H.openNotificationDestination('empty','brave-browser','Brave',''),[
 {route:'application',actions:['native-attempt','app']}
]);
check(H.openNotificationDestination('other','discord','Discord','youtube.com'),[
 {route:'application',actions:['native-attempt','app']}
]);
assert.strictEqual(
 H.openNotificationDestination('unknown','brave-browser','Brave','youtube.com.evil.test'),
 'site-home');
assert.deepStrictEqual(actions.map(x=>x.kind),['native-attempt','exec']);
assert.deepStrictEqual(actions[1].argv,['xdg-open','https://youtube.com.evil.test/'],
 'exact sender-supplied host, not a guessed YouTube location');
actions.length=0;
console.log('Native destination, website origin and application fallback: PASS');
"""
subprocess.run(
    ["node", "-e", NODE, str(HUB), str(IDENTITY)],
    check=True,
)
print("Notification destination routing contracts: PASS")
