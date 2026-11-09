#!/usr/bin/env python3
"""Synthetic app-scoped sender/server/DM rules and popup policy readiness."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / "services/notifications/NotificationScopePolicy.js"
SERVICE = ROOT / "services/notifications/NotificationsService.qml"
HUB = ROOT / "widgets/notifications/NotificationsHubW.qml"
CONVERTER = ROOT / "services/notifications/NotificationsConverter.qml"
s = SERVICE.read_text(encoding="utf-8")
h = HUB.read_text(encoding="utf-8")
c = CONVERTER.read_text(encoding="utf-8")

assert 'import "NotificationScopePolicy.js" as NotificationScopePolicy' in s
assert 'import "NotificationScopePolicy.js" as NotificationScopePolicy' in c
assert 'const scope = NotificationScopePolicy.scopeFromHints(notification.hints || {});' in c
assert '"context": { "notificationScope": scope }' in c
assert "property var pendingPolicyDeliveryIds: []" in s
assert 'const suppressed = !policyReady' in s
assert 'root.reconcilePendingPolicyDeliveries();' in s
assert "function inheritedSuppressionFor(entry, selectedKey)" in s
assert "function shouldSuppressScoped(entry)" in s
assert "function isFavoriteForNotification(entry)" in s

assert "scopeInfoJson" in h
assert "targetScopeIndex" in h
assert "function cycleTargetScope()" in h
assert "TITLE EXACT, NOT VERIFIED SENDER" in h
assert "NotificationsService.toggleFavorite(notificationEntry.targetKey" in h
assert "NotificationsService.toggleDnd(notificationEntry.targetKey" in h
assert "NotificationsService.snoozeApp(notificationEntry.targetKey" in h
assert 'id: managerRuleTabs' in h
assert 'model: managerVisiblePolicies' in h
assert '"DO NOT DISTURB // " + managerVisiblePolicies.count' in h
assert '"SNOOZED // " + managerVisiblePolicies.count' in h
assert 'visible: root.managerPolicyMode === "favorites"' in h
assert 'label: dndRule.dnd ? "ALLOW" : "WAKE"' in h

NODE = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8');
const scopeSource = fs.readFileSync(process.argv[2], 'utf8');
function extract(code, name) {
 const i=code.indexOf('function '+name+'(');
 assert(i>=0, 'missing '+name);
 const start=code.indexOf('{',i); let n=0;
 for(let j=start;j<code.length;j++){
  if(code[j]==='{')n++;
  else if(code[j]==='}' && --n===0)return code.slice(i,j+1);
 }
 throw Error('unbalanced '+name);
}
class Model {
 constructor(){this.rows=[];}
 get count(){return this.rows.length;}
 get(i){return this.rows[i];}
 append(e){this.rows.push({...e});}
 setProperty(i,k,v){this.rows[i][k]=v;}
 remove(i,n=1){this.rows.splice(i,n);}
 clear(){this.rows=[];}
}
let now=1700000000000;
class Clock extends Date { static now(){return now;} }
const Scope={String,Number,Math,Array,encodeURIComponent};
vm.runInNewContext(scopeSource,Scope);
const entry = (server,channel,sender,conversation,title='Message')=>({
 source:'Vesktop', sourceId:'vesktop', websiteHost:'', title, message:'body never parsed',
 context:{notificationScope:{
  serverId:server, serverName:server, channelId:channel, channelName:channel,
  senderId:sender, senderName:sender,
  conversationId:conversation,conversationName:conversation
 }}
});
const sA=entry('guild-a','general','alice','');
const sB=entry('guild-b','general','bob','');
const sAOther=entry('guild-a','offtopic','carol','');
const dmA=entry('','','alice','dm-alice');
const dmB=entry('','','bob','dm-bob');
const declared=Scope.scopeFromHints({
 'x-post-apollo-sender-id':'alice',
 'x-post-apollo-server-id':'guild-a',
 'x-post-apollo-channel-id':'general',
 'x-post-apollo-conversation-id':'dm-alice'
});
assert.strictEqual(declared.senderId,'alice');
assert.strictEqual(declared.channelId,'general');
assert.strictEqual(Scope.scopeFromHints({summary:'alice'}).senderId,undefined,
    'title text alone must not manufacture structured identity');
const options=Scope.scopeOptionsFor(sA,'vesktop','');
const find=(list,kind)=>list.find(x=>x.kind===kind);
assert(find(options,'server')&&find(options,'channel')&&find(options,'sender'));
assert.notStrictEqual(find(options,'channel').key,
 Scope.scopeOptionsFor(sB,'vesktop','').find(x=>x.kind==='channel').key,
 'same channel name in different servers must not collide');
assert.notStrictEqual(Scope.scopeKey('vesktop','sender','Alice'),
 Scope.scopeKey('vesktop','sender','alice'),
 'case-sensitive sender IDs must never collapse');
const fallback=Scope.scopeOptionsFor(entry('','','','', 'Mom'),'vesktop','');
assert.strictEqual(fallback[0].kind,'title');
assert.strictEqual(fallback[0].verified,false);
assert.strictEqual(fallback[1].kind,'app');
assert.notStrictEqual(fallback[0].key,
 Scope.scopeOptionsFor(entry('','','','', 'Mom!'),'vesktop','')[0].key);
assert.strictEqual(Scope.scopeOptionsFor(entry('','','','','Mom'),'another-app','')[0].key===fallback[0].key,false);

const S={String,Number,Math,Array,Date:Clock,encodeURIComponent,
 BrowserSiteIdentity:{hostnameFor:x=>x||''}, NotificationScopePolicy:Scope,
 sourcePolicies:new Model(),activeNotifications:new Model(),favoriteSources:new Model(),
 policyRevision:0,favoritesRevision:0,defaultSnoozeDurationMs:60000,
 policyVersion:1,policyReady:true,policyStatus:'ready',
 favoritesReady:true,favoritesStatus:'ready',
 schedulePolicySave(){},scheduleFavoritesSave(){},
};
const names=['sourceKey','websiteKey','scopeOptionsFor','favoriteIndex','isFavorite',
 'setFavorite','toggleFavorite','isFavoriteForNotification','policyIndex','policyFor',
 'isDnd','isSnoozed','shouldSuppress','shouldSuppressScoped','inheritedSuppressionFor',
 'ensurePolicy','markPoliciesChanged','suppressActiveForKey','compactPolicy',
 'setDnd','toggleDnd','snoozeApp','clearSnooze'];
vm.runInNewContext(names.map(n=>extract(source,n)).join('\n'),S);
const opt=e=>S.scopeOptionsFor(e);
const key=(e,kind)=>opt(e).find(x=>x.kind===kind).key;
assert.strictEqual(S.shouldSuppressScoped(sA),false);
S.activeNotifications.append({...sA,id:'a'});
S.activeNotifications.append({...sB,id:'b'});
S.activeNotifications.append({...sAOther,id:'a2'});
S.activeNotifications.append({...dmA,id:'d1'});
S.setDnd(key(sA,'server'),'vesktop','Vesktop // SERVER guild-a',true);
assert.strictEqual(S.shouldSuppressScoped(sA),true);
assert.strictEqual(S.shouldSuppressScoped(sAOther),true);
assert.strictEqual(S.shouldSuppressScoped(sB),false);
assert.strictEqual(S.shouldSuppressScoped(dmA),false);
assert.deepStrictEqual(S.activeNotifications.rows.map(x=>x.id),['b','d1']);
assert.strictEqual(S.inheritedSuppressionFor(sA,key(sA,'channel')),true);
assert.strictEqual(S.inheritedSuppressionFor(sA,key(sA,'app')),false);
S.setDnd(key(sA,'server'),'vesktop','Vesktop // SERVER guild-a',false);
S.snoozeApp(key(dmA,'conversation'),'vesktop','Vesktop // DM alice');
assert.strictEqual(S.shouldSuppressScoped(dmA),true);
assert.strictEqual(S.shouldSuppressScoped(dmB),false);
assert.strictEqual(S.shouldSuppressScoped(sB),false);
now+=60001;
assert.strictEqual(S.shouldSuppressScoped(dmA),false,'ZZ expiry must release only its scope');
S.setFavorite(key(dmA,'sender'),'vesktop','Vesktop // SENDER Alice',true);
assert.strictEqual(S.isFavoriteForNotification(dmA),true);
assert.strictEqual(S.isFavoriteForNotification(dmB),false);
assert.strictEqual(S.shouldSuppressScoped(dmA),false,'Favorite is not a mute');
S.setFavorite(key(dmA,'sender'),'vesktop','Vesktop // SENDER Alice',false);
assert.strictEqual(S.isFavoriteForNotification(dmA),false);
S.setFavorite(fallback[0].key,'vesktop','Vesktop // TITLE EXACT Mom',true);
assert.strictEqual(S.isFavoriteForNotification(entry('','','','','Mom')),true);
assert.strictEqual(S.isFavoriteForNotification(entry('','','','','Mom!')),false);

// Policy file not ready: retain history, withhold popup. After successful
// load, admit only nonexpired events which are not suppressed.
const Q={String,Number,Math,Array,Date:Clock,
 notifications:new Model(), activeNotifications:new Model(),
 pendingPolicyDeliveryIds:[], policyReady:false, policyStatus:'loading',
 normalize:e=>e,timeoutFor:()=>5000,pruneHistory(){},
 shouldSuppress:()=>false,shouldSuppressScoped:e=>e.source==='Muted App',
 markNotificationsChanged(){},scheduleHistorySave(){},
 indexOfNotification(model,id){return model.rows.findIndex(x=>x.id===id);},
 replaceModelEntry(model,i,e){model.rows[i]={...e};},
};
Q.root=Q;
vm.runInNewContext(['appendNotification','reconcilePendingPolicyDeliveries']
 .map(n=>extract(source,n)).join('\n'),Q);
Q.appendNotification({id:'pending-visible',source:'Allowed App',sourceId:'allowed'});
Q.appendNotification({id:'pending-muted',source:'Muted App',sourceId:'muted'});
assert.strictEqual(Q.notifications.count,2);
assert.strictEqual(Q.activeNotifications.count,0);
Q.policyReady=true;Q.policyStatus='ready';
Q.reconcilePendingPolicyDeliveries();
assert.deepStrictEqual(Q.activeNotifications.rows.map(x=>x.id),['pending-visible']);
Q.policyReady=false;Q.policyStatus='loading';
Q.appendNotification({id:'corrupt-policy',source:'Allowed App',sourceId:'allowed'});
Q.policyReady=true;Q.policyStatus='parse-error';
Q.reconcilePendingPolicyDeliveries();
assert.strictEqual(Q.activeNotifications.count,1,'bad policy should not release queued popup');
console.log('Scoped sender/server/channel/DM, TITLE, favorites, and startup gate: PASS');
"""
subprocess.run(["node", "-e", NODE, str(SERVICE), str(SCOPE)], check=True)
print("Notification scoped policy contracts: PASS")
