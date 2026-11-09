#!/usr/bin/env python3
"""Scoped messaging identity: account/contact/DM/group/thread across providers.

Source-only: does not create a live provider bridge, read messages, or enable
messaging permissions. All identities below are invented synthetic fixtures.
"""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SCOPE=ROOT/"services/notifications/NotificationScopePolicy.js"
PROVIDERS=ROOT/"services/notifications/NotificationMessagingIdentity.js"
SERVICE=ROOT/"services/notifications/NotificationsService.qml"
CONVERTER=ROOT/"services/notifications/NotificationsConverter.qml"
HUB=ROOT/"widgets/notifications/NotificationsHubW.qml"
for needle in (
    '["accountId", "x-post-apollo-account-id"]',
    '["contactId", "x-post-apollo-contact-id"]',
    '["conversationType", "x-post-apollo-conversation-type"]',
    '["groupId", "x-post-apollo-group-id"]',
    '["threadId", "x-post-apollo-thread-id"]',
    'add("group"', 'add("thread"', 'add("sender"', 'add("account"',
):
    assert needle in SCOPE.read_text(), needle
hub=HUB.read_text()
assert '"group": "GROUP"' in hub and '"thread": "THREAD"' in hub
assert '"account": "ACCT"' in hub
assert 'return String(detailLabel || "").indexOf("DM // ") === 0' in hub
assert 'function selectInheritedPolicyScope()' in hub
assert 'function selectInheritedBlockScope()' in hub
assert 'const scope = NotificationScopePolicy.scopeFromHints(notification.hints || {});' in CONVERTER.read_text()
assert '["group", "thread", "conversation", "channel", "server", "account", "app"]' in SERVICE.read_text()
assert 'function shouldBlockNotification(entry)' in SERVICE.read_text()

NODE=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
const scopeSrc=fs.readFileSync(process.argv[2],'utf8');
const providerSrc=fs.readFileSync(process.argv[3],'utf8');
function extract(code,name) {
 const start=code.indexOf('function '+name+'(');
 assert(start>=0, name+' function missing');
 const open=code.indexOf('{',start);let depth=0;
 for(let i=open;i<code.length;i++) {
  if(code[i]==='{')depth++;
  else if(code[i]==='}'&&--depth===0)return code.slice(start,i+1);
 }
 throw Error(name+' unbalanced');
}
class Model {
 constructor(){this.rows=[];}
 get count(){return this.rows.length;}
 get(i){return this.rows[i];}
 append(v){this.rows.push({...v});}
 setProperty(i,k,v){this.rows[i][k]=v;}
 remove(i,n=1){this.rows.splice(i,n);}
 clear(){this.rows=[];}
}
const Scope={String,Number,Math,Array,encodeURIComponent};
vm.runInNewContext(scopeSrc,Scope);
const Providers={String,Array,Object,Number,Math};
vm.runInNewContext(providerSrc,Providers);
const entry=(app,sourceId,ctx,title='Message')=>({
 source:app,sourceId,websiteHost:'',
 title,originalTitle:title,context:{notificationScope:ctx}
});
const key=(e,kind)=>Scope.scopeOptionsFor(e,e.sourceId,'').find(x=>x.kind===kind)?.key;
const kinds=e=>Scope.scopeOptionsFor(e,e.sourceId,'').map(x=>x.kind);

// FDO hints for a group, an email thread, a contact and an account: all
// declared identity fields, never parsed from title/body.
const hinted=Scope.scopeFromHints({
 'x-post-apollo-account-id':'account-1',
 'x-post-apollo-contact-id':'+15551234567',
 'x-post-apollo-conversation-id':'group-123',
 'x-post-apollo-conversation-name':'Lunch Group',
 'x-post-apollo-conversation-type':'group',
 'x-post-apollo-sender-name':'Pat'
});
assert.strictEqual(hinted.accountId,'account-1');
assert.strictEqual(hinted.contactId,'+15551234567');
assert.strictEqual(hinted.conversationType,'group');
const hintedEntry=entry('Messenger','messenger',hinted);
assert(kinds(hintedEntry).includes('group'));
assert(kinds(hintedEntry).includes('sender'));
assert(kinds(hintedEntry).includes('account'));
assert(!kinds(hintedEntry).includes('conversation'),
 'group must not masquerade as a DM');
assert(Scope.scopeOptionsFor(hintedEntry,'messenger','')
 .find(x=>x.kind==='sender').label.startsWith('CONTACT // '));
assert(!kinds(entry('Messenger','messenger',
 Scope.scopeFromHints({'x-post-apollo-group-name':'Friends'}))).includes('group'),
 'group names alone cannot manufacture identities');

// Discord metadata must be explicit. An asserted guild/channel/group/DM
// is translated only when a provider producer actually supplies native IDs.
const discordA=Providers.discordScope({
 accountId:'discord-account-a',guildId:'guild-11',channelId:'channel-1',
 guildName:'School',channelName:'general',userId:'member-1',userName:'Pat'
});
const discordB=Providers.discordScope({
 accountId:'discord-account-a',guildId:'guild-22',channelId:'channel-1',
 guildName:'Work',channelName:'general',userId:'member-2'
});
const discordOtherAccount=Providers.discordScope({
 accountId:'discord-account-b',guildId:'guild-11',channelId:'channel-1',
 userId:'member-1'
});
const dA=entry('Vesktop','vesktop',discordA),dB=entry('Vesktop','vesktop',discordB);
const dA2=entry('Vesktop','vesktop',discordOtherAccount);
assert.notStrictEqual(key(dA,'server'),key(dB,'server'));
assert.notStrictEqual(key(dA,'channel'),key(dB,'channel'));
assert.notStrictEqual(key(dA,'server'),key(dA2,'server'),
 'two Discord accounts must not share the same server rule');
assert.notStrictEqual(key(dA,'sender'),key(dA2,'sender'),
 'a sender rule in one Discord account must not bleed into another');
assert(!kinds(entry('Vesktop','vesktop',
 Providers.discordScope({guildName:'Work',userName:'Pat'}))).includes('sender'));
const direct=entry('Vesktop','vesktop',Providers.discordScope({
 accountId:'discord-account-a',dmId:'direct-55',userId:'member-1'}));
const group=entry('Vesktop','vesktop',Providers.discordScope({
 accountId:'discord-account-a',groupDmId:'group-99',userId:'member-1'}));
assert(kinds(direct).includes('conversation'));
assert(!kinds(direct).includes('group'));
assert(kinds(group).includes('group'));
assert(!kinds(group).includes('conversation'));
assert.notStrictEqual(key(direct,'sender'),key(group,'group'),
 'contact rules and group rules must be independently selectable');

// BlueFerry adapter uses the actual read-only projection shape, but its
// snapshot is not a live notification source. Direct chats cannot assume
// that a display name is a verified person/contact ID.
const blueProfile='d7498fd9-1122-4433-9abc-3214abcd1234';
const blueGroup={id:blueProfile+':group-a',serviceId:'blueferry',type:'group',
 displayNameInProfile:'Family'};
const blueDirect={id:blueProfile+':direct-b',serviceId:'blueferry',type:'direct',
 displayNameInProfile:'Mom'};
const blueGroupScope=Providers.blueFerryScope(blueGroup,
 {conversationId:blueGroup.id,direction:'incoming',senderId:'+15551234567'},
 blueProfile);
const blueDirectScope=Providers.blueFerryScope(blueDirect,
 {conversationId:blueDirect.id,direction:'incoming'},blueProfile);
const bg=entry('BlueFerry','blueferry',blueGroupScope);
const bd=entry('BlueFerry','blueferry',blueDirectScope);
assert(kinds(bg).includes('group')&&kinds(bg).includes('sender'));
assert(kinds(bd).includes('conversation')&&!kinds(bd).includes('sender'));
assert.deepStrictEqual(Object.keys(Providers.blueFerryScope(blueDirect,
 {conversationId:blueDirect.id,direction:'outgoing'},blueProfile)),[]);
assert.deepStrictEqual(Object.keys(Providers.blueFerryScope(blueDirect,
 {conversationId:'wrong',direction:'incoming'},blueProfile)),[]);
assert.notStrictEqual(key(bg,'group'),key(group,'group'),
 'BlueFerry and Discord group IDs cannot collide');

// Telegram bridge's type values: private, group, channel. A private dialog
// peer is known, but group message sender IDs are not supplied by this bridge.
const telegramPrivate={id:'12345',type:'private',serviceId:'telegram',
 displayNameInProfile:'Chat contact'};
const telegramGroup={id:'-20000',type:'group',serviceId:'telegram',
 displayNameInProfile:'Neighborhood'};
const telegramChannel={id:'-30000',type:'channel',serviceId:'telegram',
 displayNameInProfile:'Local news'};
const tp=entry('Telegram','telegram',
 Providers.telegramScope(telegramPrivate,{conversationId:'12345',direction:'incoming'},
 'identity-1'));
const tg=entry('Telegram','telegram',
 Providers.telegramScope(telegramGroup,{conversationId:'-20000',direction:'incoming'},
 'identity-1'));
const tc=entry('Telegram','telegram',
 Providers.telegramScope(telegramChannel,{conversationId:'-30000',direction:'incoming'},
 'identity-1'));
assert(kinds(tp).includes('conversation')&&kinds(tp).includes('sender'));
assert(kinds(tg).includes('group')&&!kinds(tg).includes('sender'));
assert(kinds(tc).includes('channel'));
assert.deepStrictEqual(Object.keys(Providers.telegramScope(telegramGroup,
 {conversationId:'wrong',direction:'incoming'},'identity-1')),[]);

// Email account + From address + thread ID, but NOT the current Proton
// count-only pilot. No mailbox or sender is inferred from the title.
const emailA=entry('Proton Mail','proton-mail',Providers.emailScope({
 accountId:'mail-account-a',senderAddress:'mom+family@example.com',
 senderName:'Mom',threadId:'thread-1'}));
const emailSameSenderNewThread=entry('Proton Mail','proton-mail',Providers.emailScope({
 accountId:'mail-account-a',senderAddress:'mom+family@example.com',
 senderName:'Mom',threadId:'thread-2'}));
const emailOtherAccount=entry('Proton Mail','proton-mail',Providers.emailScope({
 accountId:'mail-account-b',senderAddress:'mom+family@example.com',
 threadId:'thread-1'}));
assert(kinds(emailA).includes('thread')&&kinds(emailA).includes('sender'));
assert.strictEqual(key(emailA,'sender'),key(emailSameSenderNewThread,'sender'));
assert.notStrictEqual(key(emailA,'thread'),key(emailSameSenderNewThread,'thread'));
assert.notStrictEqual(key(emailA,'sender'),key(emailOtherAccount,'sender'));
assert.notStrictEqual(key(emailA,'thread'),key(emailOtherAccount,'thread'));
assert(!kinds(entry('Proton Mail','proton-mail',
 Providers.emailScope({senderName:'Mom',threadName:'Inbox'}))).includes('sender'));

// Preserve existing rule keys for older notifications lacking account/type
// metadata. Old APP, SITE, resource, and TITLE rules are unaffected.
const legacy=entry('Vesktop','vesktop',{senderId:'alice',conversationId:'legacy-chat'});
assert.strictEqual(key(legacy,'sender'),Scope.scopeKey('vesktop','sender','alice'));
assert.strictEqual(key(legacy,'conversation'),
 Scope.scopeKey('vesktop','conversation','legacy-chat'));
assert(Scope.scopeOptionsFor(legacy,'vesktop','')
 .find(x=>x.kind==='conversation').label.startsWith('CHAT // '));

let now=1762722000000;
class Clock extends Date {static now(){return now;}}
const S={
 String,Number,Math,Array,Date:Clock,Object,encodeURIComponent,
 BrowserSiteIdentity:{hostnameFor:x=>x||''},NotificationScopePolicy:Scope,
 sourcePolicies:new Model(),activeNotifications:new Model(),notifications:new Model(),
 favoriteSources:new Model(),policyReady:true,policyStatus:'ready',
 favoritesReady:true,favoritesStatus:'ready',policyRevision:0,favoritesRevision:0,
 policyVersion:1,defaultSnoozeDurationMs:60000,
 normalize:e=>e,timeoutFor:()=>5000,pruneHistory(){},
 pendingPolicyIntakeEntries:[],pendingPolicyDeliveryIds:[],
 markNotificationsChanged(){},scheduleHistorySave(){},schedulePolicySave(){},
 scheduleFavoritesSave(){}
};
S.root=S;
const methods=['sourceKey','websiteKey','scopeOptionsFor','policyIndex','policyFor',
 'isBlocked','shouldBlockNotification','inheritedBlockOwnerKey',
 'isDnd','isSnoozed','isDndForNotification','isSnoozedForNotification',
 'shouldSuppress','shouldSuppressScoped','inheritedPolicyOwnerKey',
 'ensurePolicy','markPoliciesChanged','suppressActiveForKey',
 'compactPolicy','setBlocked','toggleBlocked','setDnd','snoozeApp','clearSnooze',
 'favoriteIndex','isFavorite','setFavorite','isFavoriteForNotification',
 'indexOfNotification','appendNotification'];
vm.runInNewContext(methods.map(n=>extract(source,n)).join('\n'),S);
const SKey=(e,k)=>S.scopeOptionsFor(e).find(x=>x.kind===k).key;

// DND a group DM while same contact's ordinary DM stays available.
const groupKey=SKey(group,'group');
assert.strictEqual(S.setDnd(groupKey,'vesktop','Family group',true),undefined);
assert(S.shouldSuppressScoped(group));
assert(!S.shouldSuppressScoped(direct));
assert.strictEqual(S.inheritedPolicyOwnerKey(group,SKey(group,'sender')),groupKey,
 'sender button must route to an already muting group before widening');

// BLOCK sender across their messages, independently of group identity.
S.setDnd(groupKey,'vesktop','Family group',false);
const personKey=SKey(group,'sender');
S.setBlocked(personKey,'vesktop','One person',true);
assert(S.shouldBlockNotification(group));
assert(S.shouldBlockNotification(direct));
assert(!S.shouldBlockNotification(dB));
assert.strictEqual(S.inheritedBlockOwnerKey(group,groupKey),personKey,
 'group button must identify pre-existing sender block');
assert.strictEqual(S.appendNotification(group),false);
S.appendNotification(dB);
assert.strictEqual(S.notifications.count,1);

// Blocking one email thread must not affect the same sender's other thread.
S.setBlocked(personKey,'vesktop','One person',false);
const threadKey=SKey(emailA,'thread');
S.setBlocked(threadKey,'proton-mail','One thread',true);
assert(S.shouldBlockNotification(emailA));
assert(!S.shouldBlockNotification(emailSameSenderNewThread));
assert(!S.shouldBlockNotification(emailOtherAccount));
S.setBlocked(threadKey,'proton-mail','One thread',false);

// DND mail sender affects all their threads in only this account.
S.setDnd(SKey(emailA,'sender'),'proton-mail','One sender',true);
assert(S.shouldSuppressScoped(emailA));
assert(S.shouldSuppressScoped(emailSameSenderNewThread));
assert(!S.shouldSuppressScoped(emailOtherAccount));
S.setDnd(SKey(emailA,'sender'),'proton-mail','One sender',false);

// ZZ only one BlueFerry group; Favorites one Telegram conversation.
S.snoozeApp(SKey(bg,'group'),'blueferry','Family');
assert(S.isSnoozedForNotification(bg));
assert(!S.isSnoozedForNotification(bd));
S.setFavorite(SKey(tg,'group'),'telegram','Neighborhood',true);
assert(S.isFavoriteForNotification(tg));
assert(!S.isFavoriteForNotification(tp));
console.log('Messaging account/contact/DM/group/thread provider scope isolation: PASS');
"""
subprocess.run(["node","-e",NODE,str(SERVICE),str(SCOPE),str(PROVIDERS)],check=True)
print("Notification messaging identity contracts: PASS")
