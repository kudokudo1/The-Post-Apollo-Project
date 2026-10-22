#!/usr/bin/env python3
"""Live-only email commands: sender actions, not notification-only mutations."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/"services/notifications/EmailNotificationActions.js"
SERVICE=ROOT/"services/notifications/NotificationsService.qml"
HUB=ROOT/"widgets/notifications/NotificationsHubW.qml"
source=SERVICE.read_text()
hub=HUB.read_text()

for token in (
 'function emailActionsFor(eventId)',
 'function hasEmailAction(eventId, operation)',
 'function dispatchEmailAction(eventId, operation)',
 'return invokeExternalAction(eventId, actions[i].identifier);',
 'EmailNotificationActions.availableActions(',
):
    assert token in source, token
for token in (
 'id: mailActionDeck',
 'id: mailActionGrid',
 'id: mailActionStatus',
 'label: "MAIL"',
 'notificationEntry.emailDeckOpen',
 'notificationEntry.isEmailCard',
 'NotificationsService.hasEmailAction(',
 'NotificationsService.dispatchEmailAction(',
 'onNotificationIdChanged:',
 'emailDeckOpen = false;',
):
    assert token in hub,token

assert 'NotificationsService.toggleFavorite(notificationEntry.appKey' in hub
assert 'NotificationsService.snoozeApp(notificationEntry.targetKey' in hub
assert '"kind": "star", "label": "MAIL STAR"' in hub
assert '"kind": "snooze", "label": "SNOOZE"' in hub
assert '"kind": "trash", "label": "TRASH"' in hub
assert 'notificationEntry.emailDeckOpen && notificationEntry.isEmailCard ? 102 : 0' in hub
assert 'opacity: enabled ? 1.0 : 0.38' in hub
# Buttons must not pretend a disconnected/expired sender is editable.
assert 'enabled: NotificationsService.externalActionsRevision >= 0' in hub

NODE=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const script=fs.readFileSync(process.argv[1],'utf8')
 .replace(/^\s*\.pragma library\s*/,'');
const service=fs.readFileSync(process.argv[2],'utf8');
function extract(s,name) {
 const start=s.indexOf('function '+name+'(');assert(start>=0,'missing '+name);
 const brace=s.indexOf('{',start);let level=0;
 for(let i=brace;i<s.length;i++) {
  if(s[i]==='{')level++;
  else if(s[i]==='}'&&--level===0) return s.slice(start,i+1);
 }
 throw new Error('unclosed '+name);
}
const P={String,Math,Number,Array,Object};
vm.runInNewContext(script,P);
const email={source:'Brave',sourceId:'brave-browser',
 websiteHost:'mail.proton.me',category:'generic'};
const spamSite={...email,websiteHost:'mail.proton.me.evil.test'};
const generic={source:'Brave',sourceId:'brave-browser',
 websiteHost:'youtube.com',category:'generic'};
assert.strictEqual(P.isEmail(email),true);
assert.strictEqual(P.isEmail(generic),false);
assert.strictEqual(P.isEmail(spamSite),false);
assert.strictEqual(P.isEmail({source:'Thunderbird',sourceId:'thunderbird.desktop'}),true);
assert.strictEqual(P.isEmail({source:'App',category:'email.arrived'}),true);
assert.strictEqual(P.isEmail({source:'Brave',websiteHost:'example.gmail.com'}),false);
assert.strictEqual(P.isEmail({source:'Brave',websiteHost:'mail.google.com'}),true);
assert.strictEqual(P.operationFor('delete','Delete'),'', 'never treat delete as Trash');
assert.strictEqual(P.operationFor('default','Open Email'),'', 'default is navigation');
assert.strictEqual(P.operationFor('mark_as_read','Mark as Read'),'mark-read');
assert.strictEqual(P.operationFor('archive','Archive'),'archive');
const kinds=P.availableActions(email,[
 {identifier:'default',text:'Open'},
 {identifier:'mark-as-read',text:'Mark as Read'},
 {identifier:'trash',text:'Move to Trash'},
 {identifier:'archive',text:'Archive'},
 {identifier:'snooze',text:'Snooze'},
 {identifier:'spam',text:'Report Spam'},
 {identifier:'star',text:'Add Star'},
 {identifier:'delete',text:'Delete Permanently'},
]).map(a=>a.kind);
assert.deepStrictEqual(JSON.parse(JSON.stringify(kinds)),
 ['mark-read','trash','archive','snooze','spam','star']);
assert.strictEqual(P.availableActions(generic,[{identifier:'archive',text:'Archive'}]).length,0);
assert.strictEqual(P.availableActions(email,[{identifier:'delete',text:'Delete'}]).length,0);
const invoked=[];
let now=1000;
class Clock extends Date {static now(){return now;}}
const model={count:2,get(i){return [email,generic][i];}};
const st={
 String,Number,Date:Clock,notifications:model,
 indexOfNotification(m,id){return id==='email-id'?0:id==='generic-id'?1:-1},
 EmailNotificationActions:P,
 liveExternalNotifications:{
  'email-id':{expiresAt:2000,notification:{actions:[
   {identifier:'mark-as-read',text:'Mark as Read',invoke(){invoked.push('read');}},
   {identifier:'trash',text:'Move to Trash',invoke(){invoked.push('trash');}}
  ]}},
  'generic-id':{expiresAt:2000,notification:{actions:[
   {identifier:'archive',text:'Archive',invoke(){invoked.push('other');}}
  ]}}
 }
};
vm.runInNewContext(
 ['invokeExternalAction','emailActionsFor','hasEmailAction','dispatchEmailAction']
 .map(n=>extract(service,n)).join('\n'),st);
assert.strictEqual(st.hasEmailAction('email-id','mark-read'),true);
assert.strictEqual(st.hasEmailAction('email-id','archive'),false);
assert.strictEqual(st.dispatchEmailAction('email-id','mark-read'),true);
assert.deepStrictEqual(invoked,['read']);
assert.strictEqual(st.dispatchEmailAction('email-id','archive'),false);
assert.strictEqual(st.dispatchEmailAction('email-id','default'),false);
assert.strictEqual(st.dispatchEmailAction('generic-id','archive'),false);
assert.strictEqual(st.dispatchEmailAction('missing-id','trash'),false);
assert.deepStrictEqual(invoked,['read']);
now=3000;
assert.strictEqual(st.hasEmailAction('email-id','mark-read'),false);
assert.strictEqual(st.dispatchEmailAction('email-id','trash'),false);
assert.deepStrictEqual(invoked,['read'],'expired callbacks may never mutate mail');
console.log('Email sender-action mapping, live identity and expiry: PASS');
"""
subprocess.run(["node","-e",NODE,str(SCRIPT),str(SERVICE)],check=True)
print("Notifications email action contracts: PASS")
