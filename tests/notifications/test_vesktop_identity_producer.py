#!/usr/bin/env python3
"""Opt-in Vencord Discord identity producer: source + actual scoped hint behavior."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
V = ROOT/"integrations/vesktop/postApolloNotificationBridge"
IDENTITY = V/"identity.ts"
NATIVE = V/"native.ts"
PLUGIN = V/"index.ts"
SCOPE = ROOT/"services/notifications/NotificationScopePolicy.js"
CONVERTER = ROOT/"services/notifications/NotificationsConverter.qml"
SVC = ROOT/"services/notifications/NotificationsService.qml"
PLUGIN_TEXT = PLUGIN.read_text(encoding="utf-8")
NATIVE_TEXT = NATIVE.read_text(encoding="utf-8")
SCOPE_TEXT = SCOPE.read_text(encoding="utf-8")

for requirement in (
    'default: false',
    'allowedDiscordChannels(settings.store.channelIds)',
    'allowedDiscordChannels(settings.store.serverIds)',
    'FluxDispatcher.subscribe("MESSAGE_CREATE", onMessage)',
    'FluxDispatcher.unsubscribe("MESSAGE_CREATE", onMessage)',
    'Native.emit(payload)',
    'ChannelStore.getChannel(channelId)',
    'UserStore.getCurrentUser()',
):
    assert requirement in PLUGIN_TEXT, requirement
for requirement in (
    'execFile("notify-send", args',
    'notificationArgs(raw)',
    'const PER_MINUTE = 12',
    'if (minuteCount >= PER_MINUTE || sent.has(messageId))',
    'return { status: "INVALID" }',
):
    assert requirement in NATIVE_TEXT, requirement
for banned in (
    'shell: true', 'exec(', 'spawn(', 'eval(', 'fetch(',
    'client.token', 'getToken(', 'localStorage', 'message.content',
    'message.body', 'event.message.content',
    'http://', 'https://', 'Authorization:',
):
    assert banned not in PLUGIN_TEXT + NATIVE_TEXT, banned
assert '"context": { "notificationScope": scope }' in CONVERTER.read_text()
assert 'function shouldBlockNotification(entry)' in SVC.read_text()
assert '"x-post-apollo-account-id"' in SCOPE_TEXT

NODE = r"""
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {pathToFileURL} from 'node:url';

const id=await import(pathToFileURL(process.argv[1]).href);
const scopeSrc=fs.readFileSync(process.argv[2],'utf8');
const converterSrc=fs.readFileSync(process.argv[3],'utf8');
const Scope={String,Number,Array,Math,encodeURIComponent};
vm.runInNewContext(scopeSrc,Scope);
function extract(code,name) {
 const i=code.indexOf('function '+name+'(');
 assert(i>=0,'missing '+name);
 const b=code.indexOf('{',i);let depth=0;
 for(let j=b;j<code.length;j++) {
  if(code[j]==='{')depth++;
  else if(code[j]==='}'&&--depth===0)return code.slice(i,j+1);
 }
 throw Error('unclosed '+name);
}
const C={
 BrowserSiteIdentity:{fromNotification:()=>({label:'',host:'',icon:''})},
 NotificationScopePolicy:Scope,
 root:{categoryFor:()=> 'im.received',severityFor:()=> 'normal'}
};
vm.runInNewContext(extract(converterSrc,'convert'),C);
const a='111111111111111111', b='222222222222222222',
    guild='333333333333333333', channel='444444444444444444',
    dm='555555555555555555', group='666666666666666666',
    other='777777777777777777', msg='888888888888888888';
const allow=id.allowedDiscordChannels(channel+' , '+dm+' ; '+group);
assert.equal(allow.size,3);
assert.equal(id.allowedDiscordChannels('').size,0);
assert.equal(id.allowedDiscordChannels('ANY').size,0);
assert.equal(id.allowedDiscordChannels('0').size,0);
assert.equal(id.allowedDiscordChannels('9'.repeat(23)).size,0);
assert.equal(id.discordSnowflake(''), '');
const ev=(cid=channel,author=b)=>({
 message:{id:msg,author:{id:author,username:'Name\ninjected'},channel_id:cid,
 content:'PRIVATE BODY NOT TO BE FORWARDED',state:'RECEIVED'},
 channelId:cid, optimistic:false
});
const serverCh={id:channel,type:0,guild_id:guild,name:'general'};
const guildEvent=id.scopedDiscordEvent(ev(),serverCh,a,allow,new Set());
assert.equal(guildEvent.accountId,a);
assert.equal(guildEvent.senderId,b);
assert.equal(guildEvent.guildId,guild);
assert.equal(guildEvent.channelId,channel);
assert.equal(guildEvent.messageId,msg);
assert(!('content' in guildEvent));
assert(!JSON.stringify(guildEvent).includes('PRIVATE BODY'));
assert(!guildEvent.senderName.includes('\n'));
assert.equal(id.scopedDiscordEvent(ev(),serverCh,a,new Set(),new Set()),null);
const byServer=id.scopedDiscordEvent(ev(),serverCh,a,new Set([other]),new Set([guild]));
assert(byServer);
assert.equal(id.scopedDiscordEvent(ev(),serverCh,b,allow,new Set()),null,
 'own message not forwarded');
assert.equal(id.scopedDiscordEvent({...ev(),optimistic:true},serverCh,a,allow,new Set()),null);
assert.equal(id.scopedDiscordEvent(ev(other),serverCh,a,new Set([other]),new Set()),null,
 'mismatched channel identity refused');
assert.equal(id.scopedDiscordEvent(ev(),{...serverCh,id:other},a,allow,new Set()),null);
assert.equal(id.scopedDiscordEvent(ev(),{...serverCh,guild_id:'',type:9},
 allow,new Set()),null);

const dmEvent=id.scopedDiscordEvent(ev(dm),{id:dm,type:1,name:'Direct chat'},
 a,allow,new Set());
const groupEvent=id.scopedDiscordEvent(ev(group),{id:group,type:3,name:'Family'},
 a,allow,new Set());
assert.equal(dmEvent.conversationType,'direct');
assert.equal(dmEvent.conversationId,dm);
assert.equal(groupEvent.conversationType,'group');
assert.equal(groupEvent.groupId,group);
function hints(event) {
 const args=id.notificationArgs(event);
 assert(args);
 assert(args.includes('--app-name=Vesktop'));
 assert.equal(args.at(-2),'Discord // New message');
 assert(!JSON.stringify(args).includes('PRIVATE BODY'));
 const pairs=args.filter(x=>x.startsWith('--hint=string:')).map(x=>{
  const without=x.slice('--hint=string:'.length);
  const i=without.indexOf(':');
  return [without.slice(0,i),without.slice(i+1)];
 });
 return Object.fromEntries(pairs);
}
function scopes(event) {
 const hintsObject=hints(event);
 const converted=C.convert({desktopEntry:'vesktop',appName:'Vesktop',
  summary:'Discord // New message',body:'Generic text',hints:hintsObject});
 const kinds=Scope.scopeOptionsFor(converted,'vesktop','').map(x=>x.kind);
 return {hints:hintsObject,kinds};
}
const g=scopes(guildEvent),d=scopes(dmEvent),gr=scopes(groupEvent);
assert.deepEqual([g.hints['x-post-apollo-account-id'],
 g.hints['x-post-apollo-server-id'],g.hints['x-post-apollo-channel-id'],
 g.hints['x-post-apollo-sender-id']],[a,guild,channel,b]);
assert(g.kinds.includes('server')&&g.kinds.includes('channel')&&g.kinds.includes('sender'));
assert(d.kinds.includes('conversation')&&d.kinds.includes('sender'));
assert(gr.kinds.includes('group')&&gr.kinds.includes('sender'));
assert(!d.kinds.includes('group'));
assert(!gr.kinds.includes('conversation'));
const invalid=id.notificationArgs({ ...groupEvent, senderId:'; rm -rf' });
assert.equal(invalid,null);
assert.equal(id.notificationArgs({...groupEvent, accountId:''}),null);
assert.equal(id.notificationArgs({...groupEvent, conversationId:'wrong'}),null);
assert.equal(id.notificationArgs({...groupEvent, groupId:''}),null);
assert.equal(id.notificationArgs({...groupEvent,conversationType:'direct'}),null);
assert.equal(id.notificationArgs({...groupEvent, guildId:guild}),null);
assert.equal(id.notificationArgs({}),null);
const hostile=id.notificationArgs({...guildEvent,
 senderName:'hello\n--urgency=critical',channelName:'--app-name=evil'});
assert(hostile);
assert.equal(hostile.at(-2),'Discord // New message');
assert(!hostile.some(x=>x==='--urgency=critical'));
assert(hostile.some(x=>x.includes('x-post-apollo-sender-name:hello --urgency=critical')));
assert(hostile.every(x=>x.length<500));
console.log('Vesktop opt-in identity-only FDO producer, actual converter and 3 scopes: PASS');
"""
subprocess.run(
    ["node", "--experimental-strip-types", "--input-type=module", "-e",
     NODE, str(IDENTITY), str(SCOPE), str(CONVERTER)],
    check=True,
)
print("Vesktop identity producer contracts: PASS")
