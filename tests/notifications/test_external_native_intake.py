#!/usr/bin/env python3
"""Native/browser notification intake: metadata, safe presentation, and actions."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SERVER=ROOT/"services/notifications/NotificationsService.qml"
CONVERTER=ROOT/"services/notifications/NotificationsConverter.qml"
SITES=ROOT/"services/notifications/BrowserSiteIdentity.js"
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
assert 'notificationCard.source + " // " + notificationCard.website' in popup
assert 'notificationCard.source + "  [" + notificationCard.sourceId + "]"' in popup
assert "text: notificationCard.title" in popup
assert "text: notificationCard.message" in popup
assert "NotificationsService.externalActionsFor(notificationCard.notificationId)" in popup
assert "NotificationsService.invokeExternalAction(" in popup
assert "NotificationsService.notifications" in hub
assert "NotificationFacets.facetsFor(entry)" in hub
assert "notification.summary" in convert and "notification.body" in convert
assert "notification.desktopEntry" in convert
assert "notification.appName" in convert
assert 'BrowserSiteIdentity.fromNotification(notification)' in convert
assert '"website": website.label' in convert
assert '"websiteIcon": website.icon' in convert
assert 'readonly property url resolvedAppIcon: root.resolveNotificationIcon(' in hub
assert 'assets/notifications/youtube.svg' in hub
assert 'assets/notifications/youtube.svg' in popup
assert 'assets/notifications/proton-mail.svg' in hub
assert 'assets/notifications/proton-mail.svg' in popup
assert 'BrowserSiteIdentity.iconKindFor(websiteHost)' in hub
assert 'BrowserSiteIdentity.iconKindFor(host)' in popup
assert 'BrowserSiteIdentity.initialsFor(notificationCard.website,' in popup
assert 'websiteIcon !== ""' not in popup, "do not use notification artwork as site icon"
assert '"website": notification.website || ""' in server
assert '"website": String(notification.website || "")' in server
assert (ROOT/"assets/notifications/youtube.svg").is_file()
assert (ROOT/"assets/notifications/proton-mail.svg").is_file()
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
const siteSrc=fs.readFileSync(process.argv[4],'utf8')
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
const Sites={String,Array,Object};
vm.runInNewContext(siteSrc,Sites);
const C={
 String,NotificationUrgency:{Critical:2,Normal:1,Low:0},root:{},
 BrowserSiteIdentity:{fromNotification:Sites.fromNotification}
};
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
const siteNotice=mock('Brave','brave-browser',null,1);
siteNotice.body='www.youtube.com\n\nNew channel video';
siteNotice.image='file:///tmp/native-site-logo.png';
let youtube=C.convert(siteNotice);
assert.strictEqual(youtube.source,'Brave','source identity remains the browser');
assert.strictEqual(youtube.sourceId,'brave-browser','DND/FAVS/action policy key stable');
assert.strictEqual(youtube.website,'YouTube');
assert.strictEqual(youtube.websiteHost,'www.youtube.com');
assert.strictEqual(youtube.websiteIcon,'',
 'associated notification image is not a verified site favicon');
assert.strictEqual(youtube.image,'file:///tmp/native-site-logo.png',
 'native content image remains available separately');
assert.strictEqual(Sites.iconKindFor('www.youtube.com'),'youtube');
assert.strictEqual(Sites.iconKindFor('mail.proton.me'),'proton-mail');
assert.strictEqual(Sites.iconKindFor('mail.protonmail.com'),'proton-mail');
assert.strictEqual(Sites.iconKindFor('mail.proton.me.attacker.test'),'',
 'do not map attacker suffix to Proton icon');
assert.strictEqual(Sites.iconKindFor('github.com'),'');
assert.strictEqual(Sites.initialsFor('GitHub','github.com'),'GH');
assert.strictEqual(Sites.initialsFor('Reddit','reddit.com'),'RD');
const maliciousRemote=mock('Brave','brave-browser',null,1);
maliciousRemote.body='youtube.com\n\nNew video';
maliciousRemote.image='https://tracker.example/favicon.png';
assert.strictEqual(C.convert(maliciousRemote).website,'YouTube');
assert.strictEqual(C.convert(maliciousRemote).websiteIcon,'',
 'do not turn a native notice into a remote favicon request');
assert.strictEqual(youtube.message,'www.youtube.com\n\nNew channel video');
assert.strictEqual(F.facetsFor(youtube).domain,'apps','site label never changes classification');
const kdeNotice=mock('Brave','brave-browser',null,1);
kdeNotice.body='Message with no embedded origin';
kdeNotice.hints={'x-kde-origin-name':'https://github.com/',category:'generic'};
assert.strictEqual(C.convert(kdeNotice).website,'GitHub');
assert.strictEqual(C.convert(mock('Brave','brave-browser',null,1)).website,'');
const passingMention=mock('Brave','brave-browser',null,1);
passingMention.body='Check out https://youtube.com in my message';
assert.strictEqual(C.convert(passingMention).website,'','do not guess from text');
const spoof=mock('Brave','brave-browser',null,1);
spoof.body='youtube.com.attacker.test\n\nFake YouTube post';
assert.strictEqual(C.convert(spoof).website,'youtube.com.attacker.test');
const nonBrowser=mock('Discord','discord',null,1);
nonBrowser.body='youtube.com\n\nMessage';
assert.strictEqual(C.convert(nonBrowser).website,'','app bodies are not browser origins');
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
vm.runInNewContext(['externalActionsFor','invokeExternalAction',
 'hasExternalDefaultAction','invokeExternalDefaultAction']
 .map(n=>method(srv,n)).join('\n'),S);
const actions=S.externalActionsFor('event-1');
assert.strictEqual(actions.length,2);
assert.strictEqual(actions[0].identifier,'default');
assert.strictEqual(S.hasExternalDefaultAction('event-1'),true);
assert.strictEqual(S.invokeExternalDefaultAction('event-1'),true);
assert.strictEqual(invokeCount,1);
assert.strictEqual(S.invokeExternalAction('event-1','reply'),true);
assert.strictEqual(invokeCount,3);
assert.strictEqual(S.invokeExternalAction('event-1','unknown'),false);
assert.strictEqual(S.invokeExternalAction('unknown','reply'),false);
assert.strictEqual(S.hasExternalDefaultAction('unknown'),false);
S.liveExternalNotifications['event-without-default']={
 notification:{actions:[{identifier:'reply',text:'REPLY',invoke:()=>{invokeCount+=10;}}]},
 expiresAt:4000
};
assert.strictEqual(S.hasExternalDefaultAction('event-without-default'),false);
assert.strictEqual(S.invokeExternalDefaultAction('event-without-default'),false);
assert.strictEqual(invokeCount,3,'never invoke a nondefault action by guess');
now=5000;
assert.strictEqual(S.externalActionsFor('event-1').length,0);
assert.strictEqual(S.invokeExternalAction('event-1','default'),false);
assert.strictEqual(S.hasExternalDefaultAction('event-1'),false);
assert.strictEqual(S.invokeExternalDefaultAction('event-1'),false);
assert.strictEqual(invokeCount,3);
console.log('Synthetic native metadata, classification, live-action routing: PASS');
"""
subprocess.run(["node","-e",NODE,str(CONVERTER),str(SERVER),str(FACETS),str(SITES)],check=True)
print("External native/browser intake contracts: PASS")
