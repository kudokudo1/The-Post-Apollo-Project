#!/usr/bin/env python3
"""Hard-block: no new history, no popup, independently scoped, reversible."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SERVICE=ROOT/"services/notifications/NotificationsService.qml"
SCOPE=ROOT/"services/notifications/NotificationScopePolicy.js"
HUB=ROOT/"widgets/notifications/NotificationsHubW.qml"
s=SERVICE.read_text(encoding="utf-8")
h=HUB.read_text(encoding="utf-8")
for needle in (
    "function shouldBlockNotification(entry)",
    "function setBlocked(appKey, sourceId, source, enabled)",
    "function inheritedBlockOwnerKey(entry, selectedKey)",
    "property var pendingPolicyIntakeEntries: []",
    'if (policy.blocked !== true && policy.dnd !== true',
    'if (!blocked && !dnd && snoozeUntil <= now)',
    '"blocked": policy.blocked === true',
    '"blocked": blocked',
):
    assert needle in s, needle
for needle in (
    'label: "✞"',
    'symbolFontFamily: "Noto Sans Symbols 2"',
    "NotificationsService.toggleBlocked(notificationEntry.targetKey",
    'label: "BLOCK"',
    'label: root.managerPolicyMode === "block"',
    'NotificationsService.setBlocked(dndRule.appKey',
    '"BLOCKED // " + managerVisiblePolicies.count',
    'function selectInheritedBlockScope()',
):
    assert needle in h, needle

# The selected BLOCK state uses the shared MiniButton's yellow fill,
# orange border/text and orange text/frame glow. It must NOT inherit the
# red-danger override used by CLEAR ALL and X.
block_button = h.split("label: \"✞\"", 1)[1].split("onTriggered:", 1)[0]
assert "active: notificationEntry.blocked" in block_button
assert "activeColor: Colors.orange" in block_button
assert "danger:" not in block_button
mini = h.split("component MiniButton: Rectangle {", 1)[1].split(
    "// ===== LOCAL VISUAL TYPE: FILTER BUTTON", 1
)[0]
assert 'property string symbolFontFamily: ""' in mini
assert 'font.family: miniButton.symbolFontFamily !== ""' in mini
assert "return Colors.yellow;" in mini
assert "return Colors.orange;" in mini
assert "miniButton.active ? Colors.orange : miniButton.stateColor" in mini

NODE=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
const script=fs.readFileSync(process.argv[2],'utf8');
const hub=fs.readFileSync(process.argv[3],'utf8');
function extract(code,name) {
 const idx=code.indexOf('function '+name+'(');
 assert(idx>=0,'missing '+name);
 const start=code.indexOf('{',idx);let depth=0;
 for(let i=start;i<code.length;i++){
  if(code[i]==='{')depth++;
  else if(code[i]==='}' && --depth===0)return code.slice(idx,i+1);
 }
 throw Error('Unclosed '+name);
}
class Model{
 constructor(){this.rows=[];}
 get count(){return this.rows.length;}
 get(i){return this.rows[i];}
 append(x){this.rows.push({...x});}
 setProperty(i,k,v){this.rows[i][k]=v;}
 remove(i,n=1){this.rows.splice(i,n);}
 clear(){this.rows=[];}
}
let now=1762711200000;
class Clock extends Date {static now(){return now;}}
const scope={String,Number,Array,Math,encodeURIComponent};
vm.runInNewContext(script,scope);
const S={
 String,Number,Array,Object,Math,Date:Clock,encodeURIComponent,
 sourcePolicies:new Model(),notifications:new Model(),activeNotifications:new Model(),
 BrowserSiteIdentity:{hostnameFor:host=>host||''},
 NotificationScopePolicy:scope,policyReady:true,policyStatus:'ready',
 pendingPolicyIntakeEntries:[],pendingPolicyDeliveryIds:[],
 policyVersion:1,defaultSnoozeDurationMs:86400000,
 historyEnabled:true,historyReady:true,revisions:0,saves:0,
 normalize:x=>x,timeoutFor:()=>5000,pruneHistory(){},
 scheduleHistorySave(){},schedulePolicySave(){this.saves++;},
 markNotificationsChanged(){this.revisions++;},
};
S.root=S;
vm.runInNewContext([
 'sourceKey','websiteKey','scopeOptionsFor','policyIndex','policyFor',
 'isBlocked','shouldBlockNotification','inheritedBlockOwnerKey',
 'shouldSuppress','shouldSuppressScoped',
 'ensurePolicy','markPoliciesChanged','suppressActiveForKey',
 'compactPolicy','setBlocked','toggleBlocked','expireSnoozes','policyDocument','loadPolicies',
 'indexOfNotification','replaceModelEntry','updateModelNotification',
 'appendNotification','updateNotification','reconcilePendingPolicyDeliveries'
].map(n=>extract(source,n)).join('\n'),S);
const entry=(id,server,channel,conversation,sender,title)=>({
 id,source:'Vesktop',sourceId:'vesktop',websiteHost:'',
 title:title||'Message from person',message:'initial',
 context:{notificationScope:{
  serverId:server,channelId:channel,
  conversationId:conversation,senderId:sender
 }}
});
const guildA=entry('a','guild-a','general','','alice','Guild A');
const guildB=entry('b','guild-b','general','','bob','Guild B');
const guildA2=entry('a2','guild-a','offtopic','','bob','Guild A other');
const dmMom=entry('m','','','dm-mom','mom','Mom');
const dmFriend=entry('f','','','dm-friend','friend','Friend');
const key=(e,kind)=>S.scopeOptionsFor(e).find(x=>x.kind===kind).key;
assert.notStrictEqual(key(guildA,'server'),key(guildB,'server'));
assert.notStrictEqual(key(dmMom,'conversation'),key(dmFriend,'conversation'));
const serverA=key(guildA,'server');
assert.strictEqual(S.setBlocked(serverA,'vesktop','Vesktop // guild-a',true),true);
assert.strictEqual(S.isBlocked(serverA),true);
assert.strictEqual(S.shouldBlockNotification(guildA),true);
assert.strictEqual(S.shouldBlockNotification(guildA2),true);
assert.strictEqual(S.shouldBlockNotification(guildB),false);
assert.strictEqual(S.inheritedBlockOwnerKey(guildA,key(guildA,'channel')),serverA);
assert.strictEqual(S.appendNotification(guildA),false,'blocked server must not enter history');
assert.strictEqual(S.appendNotification(guildA2),false);
assert.strictEqual(S.notifications.count,0,'blocked items cannot touch ListModel');
assert.strictEqual(S.activeNotifications.count,0,'blocked items cannot popup');
assert.notStrictEqual(S.appendNotification(guildB),false);
assert.strictEqual(S.notifications.count,1);
assert.strictEqual(S.activeNotifications.count,1);
assert.strictEqual(S.setBlocked(serverA,'vesktop','Vesktop // guild-a',false),true);
assert.strictEqual(S.shouldBlockNotification(guildA),false);
assert.strictEqual(S.appendNotification(guildA),undefined);
assert.strictEqual(S.notifications.count,2,'unblocked future event may enter history');

// Blocking after an event is retained removes only its popup, not the past.
assert.strictEqual(S.setBlocked(key(guildA,'title'),'vesktop','Vesktop // Guild A',true),true);
assert.strictEqual(S.notifications.count,2,'BLOCK does not silently erase prior records');
assert.strictEqual(S.activeNotifications.rows.some(x=>x.id==='a'),false);
const retained=S.notifications.get(1).message;
assert.strictEqual(S.updateNotification('a',{message:'updated while blocked'}),false);
assert.strictEqual(S.notifications.get(1).message,retained,
 'mutating a blocked event cannot modify saved history');
assert.strictEqual(S.appendNotification({...guildA,id:'next-a'}),false);
assert.strictEqual(S.notifications.count,2);

// BLOCK remains independent of DND and ZZ, with user-visible UNBLOCK.
const momKey=key(dmMom,'sender');
assert.strictEqual(S.setBlocked(momKey,'vesktop','Vesktop // Mom',true),true);
assert.strictEqual(S.shouldBlockNotification(dmMom),true);
assert.strictEqual(S.shouldBlockNotification(dmFriend),false);
assert.strictEqual(S.appendNotification(dmMom),false);
assert.notStrictEqual(S.appendNotification(dmFriend),false);
assert.strictEqual(S.notifications.count,3);

// Expiring a timed ZZ must not garbage-collect an independent BLOCK.
const momIndex=S.policyIndex(momKey);
S.sourcePolicies.setProperty(momIndex,'snoozeUntil',now-1);
S.expireSnoozes();
assert.strictEqual(S.isBlocked(momKey),true);
assert.strictEqual(S.policyFor(momKey).snoozeUntil,0);

// Old raw policies lacking BLOCK must still restore normally.
const doc=S.policyDocument();
assert(doc.policies.some(x=>x.appKey===momKey&&x.blocked===true));
assert(doc.policies.some(x=>x.appKey===momKey&&x.dnd===false));
const persisted=JSON.stringify(doc);
S.sourcePolicies.clear();
S.policyFile={text:()=>persisted};
S.loadPolicies();
assert.strictEqual(S.isBlocked(momKey),true,'hard BLOCK survives load');
assert.strictEqual(S.isBlocked(serverA),false);
S.sourcePolicies.clear();
S.policyFile={text:()=>JSON.stringify({policies:[{
 appKey:'legacy-app',source:'Legacy',sourceId:'legacy-app',dnd:true,snoozeUntil:0
}]})};
S.loadPolicies();
assert.strictEqual(S.isBlocked('legacy-app'),false);
assert.strictEqual(S.policyFor('legacy-app').dnd,true);

// During async policy load, hold bounded events in memory, but do not write
// either notification model until the saved blocks have been evaluated.
S.sourcePolicies.clear();S.notifications.clear();S.activeNotifications.clear();
S.policyReady=false;S.policyStatus='loading';
const early=entry('early','guild-a','general','','alice','Guild A');
const fine=entry('fine','guild-b','general','','bob','Guild B');
assert.strictEqual(S.appendNotification(early),false);
assert.strictEqual(S.appendNotification(fine),false);
assert.strictEqual(S.notifications.count,0);
assert.strictEqual(S.pendingPolicyIntakeEntries.length,2);
S.policyReady=true;S.policyStatus='ready';
S.setBlocked(serverA,'vesktop','Guild A',true);
S.reconcilePendingPolicyDeliveries();
assert.deepStrictEqual(S.notifications.rows.map(x=>x.id),['fine']);
assert.deepStrictEqual(S.activeNotifications.rows.map(x=>x.id),['fine']);
assert.strictEqual(S.pendingPolicyIntakeEntries.length,0);

// Corrupt policy may never leak history, and the queue is bounded.
S.policyReady=false;S.policyStatus='loading';
for(let i=0;i<40;i++)S.appendNotification(entry('p'+i,'guild-z','','','','Other'));
assert.strictEqual(S.pendingPolicyIntakeEntries.length,32);
S.policyReady=true;S.policyStatus='parse-error';
S.reconcilePendingPolicyDeliveries();
assert.strictEqual(S.pendingPolicyIntakeEntries.length,0);
assert.strictEqual(S.activeNotifications.count,0);
assert.deepStrictEqual(S.notifications.rows.map(x=>x.id),['fine']);
assert.strictEqual(S.setBlocked(serverA,'vesktop','Guild A',false),false,
 'blocked policy file must never be overwritten blindly');

// A blocked app cannot be mistaken for a per-message mute.
const vis={scopeOptions:S.scopeOptionsFor(guildA),inheritedBlockKey:serverA,
 targetScopeIndex:0};
vm.runInNewContext(extract(hub,'selectInheritedBlockScope'),vis);
assert.strictEqual(vis.selectInheritedBlockScope(),true);
assert.strictEqual(vis.scopeOptions[vis.targetScopeIndex].key,serverA);
console.log('Hard BLOCK: scoped identity, no history, no popup, startup, updates, persistence, UNBLOCK: PASS');
"""
subprocess.run(["node","-e",NODE,str(SERVICE),str(SCOPE),str(HUB)],check=True)
print("Notification hard-block contracts: PASS")
