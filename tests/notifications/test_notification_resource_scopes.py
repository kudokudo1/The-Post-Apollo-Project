#!/usr/bin/env python3
"""Resource and resource+event rules on actual notification scope/service code."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / "services/notifications/NotificationScopePolicy.js"
SERVICE = ROOT / "services/notifications/NotificationsService.qml"
HUB = ROOT / "widgets/notifications/NotificationsHubW.qml"
PRODUCER = ROOT / "services/notifications/ResourcePressureNotificationProducer.qml"
scope = SCOPE.read_text(encoding="utf-8")
svc = SERVICE.read_text(encoding="utf-8")
hub = HUB.read_text(encoding="utf-8")
producer = PRODUCER.read_text(encoding="utf-8")
for needle in ('"resourceId": kind', '"resourceLabel": label', '"metric": kind'):
    assert needle in producer, needle
for needle in (
    '"resourceId": String((entry.context || {}).resourceId || "")',
    '"resourceLabel": String((entry.context || {}).resourceLabel || "")',
    '"legacyMetric": String((entry.context || {}).metric || "")',
    'resourceId: notificationEntry.resourceId',
    'resourceLabel: notificationEntry.resourceLabel',
    'metric: notificationEntry.legacyMetric',
    '"resource": "RSRC"', '"resourceEvent": "R+E"',
    'NotificationsService.isDndForNotification(scopeEntry)',
    'NotificationsService.isSnoozedForNotification(scopeEntry)',
):
    assert needle in hub, needle
for needle in (
    'function isDndForNotification(entry)',
    'function isSnoozedForNotification(entry)',
    'selected.kind === "resourceEvent"',
    'selected.kind === "resource"',
):
    assert needle in svc, needle
assert "const legacyPressure =" in scope
assert '"resourceEvent", pair' in scope
assert '"resource", resourceId' in scope

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
const scopeSrc=fs.readFileSync(process.argv[2],'utf8');
function extract(code,name) {
 const i=code.indexOf('function '+name+'(');assert(i>=0,name+' missing');
 const start=code.indexOf('{',i);let depth=0;
 for(let j=start;j<code.length;j++) {
  if(code[j]==='{')depth++;
  else if(code[j]==='}' && --depth===0)return code.slice(i,j+1);
 }
 throw Error(name+' unbalanced');
}
class Model {
 constructor(){this.rows=[];}
 get count(){return this.rows.length;}
 get(i){return this.rows[i];}
 append(x){this.rows.push({...x});}
 setProperty(i,k,v){this.rows[i][k]=v;}
 remove(i,n=1){this.rows.splice(i,n);}
 clear(){this.rows=[];}
}
let now=1762711200000;
class Clock extends Date{static now(){return now;}}
const Scope={String,Number,Math,Array,encodeURIComponent};
vm.runInNewContext(scopeSrc,Scope);
const notice=(id,resource,status,legacy=false)=>({
 id,source:'CPU++',sourceId:'cpu-plus-resource-pressure',
 title:'CPU++ '+resource.toUpperCase()+' '+status.toUpperCase(),
 message:'System metric: observable value, not a scope identity',
 websiteHost:'',
 context:{
  eventType:'resource-pressure-'+status,
  origin:'apollo',domain:'system',
  ...(legacy ? {metric:resource} : {resourceId:resource,
      resourceLabel:resource==='storage'?'ROOT STORAGE':'MEMORY',metric:resource})
 }
});
const mw=notice('mw','memory','warning');
const mc=notice('mc','memory','critical');
const mr=notice('mr','memory','recovered');
const sw=notice('sw','storage','warning');
const sc=notice('sc','storage','critical');
const old=notice('old','memory','critical',true);
const opts=e=>Scope.scopeOptionsFor(e,'cpu-plus-resource-pressure','');
const key=(e,kind)=>opts(e).find(x=>x.kind===kind)?.key;
assert.deepStrictEqual(Array.from(opts(mc).slice(0,4),x=>x.kind),
 ['resourceEvent','resource','event','app'],
 'Cards must offer RESOURCE + EVENT, RESOURCE, EVENT, APP in that order');
assert(opts(mc).find(x=>x.kind==='resource').label.includes('MEMORY'));
assert(opts(sc).find(x=>x.kind==='resource').label.includes('ROOT STORAGE'));
assert(opts(mc).find(x=>x.kind==='resourceEvent').label.includes('CRITICAL'));
assert.strictEqual(key(mc,'resource'),key(mw,'resource'));
assert.strictEqual(key(mc,'resource'),key(mr,'resource'));
assert.notStrictEqual(key(mc,'resource'),key(sc,'resource'));
assert.notStrictEqual(key(mc,'resourceEvent'),key(mw,'resourceEvent'));
assert.notStrictEqual(key(mc,'resourceEvent'),key(sc,'resourceEvent'));
assert.strictEqual(key(mc,'resource'),key(old,'resource'),
 'Older CPU++ history carrying metric only must expose same resource key');
assert.strictEqual(key(mc,'resourceEvent'),key(old,'resourceEvent'),
 'Legacy critical notifications must have the same combo rule key');
assert.strictEqual(key(mc,'event'),key(sc,'event'),
 'Old broad event scope continues to cross resources');
assert.strictEqual(key(mc,'event'),
 Scope.scopeKey('cpu-plus-resource-pressure','event','resource-pressure-critical'),
 'Never rewrite a stored event-rule key');
const unknown={...old,sourceId:'unrelated-source'};
assert(!opts({...unknown,context:{metric:'memory',
  eventType:'resource-pressure-critical'}}).some(x=>x.kind==='resource'),
 'Unrelated notification metric fields must not claim verified resource identity');
const explicitOther={source:'GPU widget',sourceId:'gpu-widget',
 title:'GPU CRITICAL',context:{resourceId:'gpu',resourceLabel:'GPU',
 eventType:'heat-critical'}};
assert(opts(explicitOther).some(x=>x.kind==='resourceEvent'),
 'Other producers can use typed resource identities without bespoke code');
assert.notStrictEqual(
 Scope.scopeOptionsFor(explicitOther,'gpu-widget','').find(x=>x.kind==='resource').key,
 key(mc,'resource'), 'resource keys are always app-namespaced');

const S={
 String,Number,Math,Array,Object,Date:Clock,encodeURIComponent,
 BrowserSiteIdentity:{hostnameFor:x=>x||''},NotificationScopePolicy:Scope,
 sourcePolicies:new Model(),activeNotifications:new Model(),
 notifications:new Model(),favoriteSources:new Model(),
 policyVersion:1,policyRevision:0,favoritesRevision:0,
 policyReady:true,policyStatus:'ready',favoritesReady:true,favoritesStatus:'ready',
 defaultSnoozeDurationMs:60000,pendingPolicyIntakeEntries:[],
 normalize:e=>e,timeoutFor:()=>5000,pruneHistory(){},
 schedulePolicySave(){},scheduleHistorySave(){},scheduleFavoritesSave(){},
 markNotificationsChanged(){}
};
S.root=S;
const funcs=['sourceKey','websiteKey','scopeOptionsFor','policyIndex','policyFor',
 'isBlocked','shouldBlockNotification','inheritedBlockOwnerKey',
 'isDnd','isSnoozed','isDndForNotification','isSnoozedForNotification',
 'shouldSuppress','shouldSuppressScoped','inheritedPolicyOwnerKey',
 'ensurePolicy','compactPolicy','markPoliciesChanged','suppressActiveForKey',
 'setBlocked','setDnd','snoozeApp','clearSnooze','favoriteIndex','isFavorite',
 'setFavorite','isFavoriteForNotification','policyDocument',
 'indexOfNotification','replaceModelEntry','appendNotification'];
vm.runInNewContext(funcs.map(n=>extract(source,n)).join('\n'),S);
const scopeKey=(e,kind)=>S.scopeOptionsFor(e).find(x=>x.kind===kind).key;
const event=scopeKey(mc,'event'),mem=scopeKey(mc,'resource');
const combo=scopeKey(mc,'resourceEvent');
// Preserve the user's existing EVENT block: this covers memory AND storage
// until deliberately unblocked in the Manager.
assert.strictEqual(S.setBlocked(event,'cpu-plus-resource-pressure','CPU++ / CRITICAL',true),true);
assert(S.shouldBlockNotification(mc));
assert(S.shouldBlockNotification(sc));
assert(!S.shouldBlockNotification(mw));
assert.strictEqual(S.inheritedBlockOwnerKey(mc,combo),event,
 'R+E must route the first BLOCK click to the existing broad EVENT');
assert.strictEqual(S.inheritedBlockOwnerKey(mc,mem),event,
 'RESOURCE must disclose an overlapping broad EVENT rule');
assert.strictEqual(S.isBlocked(combo),false,
 'Selecting narrow combo must not silently change broad EVENT policy');
assert.strictEqual(S.setBlocked(event,'cpu-plus-resource-pressure','CPU++ / CRITICAL',false),true);
assert(!S.shouldBlockNotification(mc));
assert(!S.shouldBlockNotification(sc));

// Resource-wide BLOCK: all RAM severities blocked, storage left alone.
assert.strictEqual(S.setBlocked(mem,'cpu-plus-resource-pressure','CPU++ / MEMORY',true),true);
for (const e of [mw,mc,mr,old])assert(S.shouldBlockNotification(e));
for (const e of [sw,sc])assert(!S.shouldBlockNotification(e));
assert.strictEqual(S.appendNotification(mc),false);
assert.strictEqual(S.appendNotification(mw),false);
assert.strictEqual(S.notifications.count,0);
S.appendNotification(sc);
assert.strictEqual(S.notifications.count,1);
assert.strictEqual(S.activeNotifications.count,1);
assert.strictEqual(S.setBlocked(mem,'cpu-plus-resource-pressure','CPU++ / MEMORY',false),true);

// One particular combination: memory-critical, not memory-warning or
// recovered, and not storage-critical.
assert.strictEqual(S.setBlocked(combo,'cpu-plus-resource-pressure',
 'CPU++ / MEMORY / CRITICAL',true),true);
assert(S.shouldBlockNotification(mc));
for (const e of [mw,mr,sc,sw])assert(!S.shouldBlockNotification(e));
assert.strictEqual(S.appendNotification(mc),false);
S.appendNotification(mw);
assert.strictEqual(S.notifications.count,2);
assert.strictEqual(S.notifications.rows.some(e=>e.id==='mc'),false);
assert.strictEqual(S.setBlocked(combo,'cpu-plus-resource-pressure',
 'CPU++ / MEMORY / CRITICAL',false),true);

// DND/ZZ and Favorites use exact same independently keyed scopes.
assert.strictEqual(S.setDnd(combo,'cpu-plus-resource-pressure',
 'CPU++ / MEMORY / CRITICAL',true),undefined);
assert(S.shouldSuppressScoped(mc));
assert(S.isDndForNotification(mc));
assert(!S.isDndForNotification(mw));
assert(!S.isDndForNotification(sc));
assert.strictEqual(S.inheritedPolicyOwnerKey(mc,mem),''
 ,'A narrow combo rule must not be presented as global resource inheritance');
S.setDnd(combo,'cpu-plus-resource-pressure','CPU++',false);
S.setDnd(event,'cpu-plus-resource-pressure','CPU++ / CRITICAL',true);
assert.strictEqual(S.inheritedPolicyOwnerKey(mc,combo),event,
 'R+E DND click routes to inherited cross-resource EVENT');
S.setDnd(event,'cpu-plus-resource-pressure','CPU++ / CRITICAL',false);
S.snoozeApp(mem,'cpu-plus-resource-pressure','CPU++ / MEMORY');
assert(S.isSnoozedForNotification(mc));
assert(S.isSnoozedForNotification(mw));
assert(!S.isSnoozedForNotification(sc));
S.clearSnooze(mem);
S.setFavorite(mem,'cpu-plus-resource-pressure','CPU++ / MEMORY',true);
assert(S.isFavoriteForNotification(mc));
assert(S.isFavoriteForNotification(mw));
assert(!S.isFavoriteForNotification(sc));
S.setFavorite(mem,'cpu-plus-resource-pressure','CPU++ / MEMORY',false);

// Composite key encoding must not collide when IDs contain separators.
const a={source:'Other',sourceId:'other',
 context:{resourceId:'a/b',eventType:'c'}};
const b={source:'Other',sourceId:'other',
 context:{resourceId:'a',eventType:'b/c'}};
assert.notStrictEqual(
 Scope.scopeOptionsFor(a,'other','').find(x=>x.kind==='resourceEvent').key,
 Scope.scopeOptionsFor(b,'other','').find(x=>x.kind==='resourceEvent').key);
console.log('CPU++ resource/event: legacy, isolation, old broad rules, DND, ZZ, BLOCK, favorites: PASS');
"""
subprocess.run(["node","-e",NODE,str(SERVICE),str(SCOPE)],check=True)
print("Notification resource scopes: PASS")
