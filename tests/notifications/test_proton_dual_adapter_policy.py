#!/usr/bin/env python3
"""Proton dual mail adapter policy contracts. No live mailbox connections."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MAIL = ROOT / "services/notifications/mail"
POLICY = MAIL / "ProtonMailActionPolicy.js"
BROWSER = MAIL / "ProtonBrowserCompanionPolicy.js"
BRIDGE = MAIL / "ProtonBridgeAdapterPolicy.js"

for path in (POLICY, BROWSER, BRIDGE):
    assert path.is_file()
    assert "eval(" not in path.read_text()
    assert "fetch(" not in path.read_text()

NODE = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
function moduleAt(path) {
 const source=fs.readFileSync(path,'utf8').replace(/^\s*\.pragma library\s*$/m,'');
 const scope={Date,Number,String,Array,Object,Math,RegExp};
 vm.runInNewContext(source,scope,{filename:path});
 return scope;
}
const P=moduleAt(process.argv[1]);
const B=moduleAt(process.argv[2]);
const I=moduleAt(process.argv[3]);
const clone=x=>JSON.parse(JSON.stringify(x));
const EVENT='event.20261022.0001', ACCOUNT='account.id0001';
const browserRef={attested:true,accountKey:ACCOUNT,
 origin:'https://mail.proton.me',messageKey:'browser.message.0001'};
const bridgeRef={attested:true,accountKey:ACCOUNT,
 mailboxKey:'mailbox.inbox.001',uidValidity:238,uid:818};
const binding={eventId:EVENT,accountKey:ACCOUNT,attested:true,
 expiresAtMs:99999,references:{browser:browserRef,bridge:bridgeRef}};
const states={
 browser:{ready:true,attested:true,accountKey:ACCOUNT,
  capabilities:['mark-read','trash','archive','snooze','spam','star']},
 bridge:{ready:true,attested:true,accountKey:ACCOUNT,
  capabilities:['mark-read','trash','archive','spam','star']}
};
const opts={nowMs:1000,confirmed:true};
const plan=(op,bind=binding,st=states,options=opts,id=EVENT)=>
 clone(P.routeFor(id,op,bind,st,options));

assert.deepStrictEqual(clone(P.operations),
 ['mark-read','trash','archive','snooze','spam','star']);
assert.strictEqual(plan('mark-read').adapter,'bridge');
assert.strictEqual(plan('archive').adapter,'bridge');
assert.strictEqual(plan('star').adapter,'bridge');
assert.strictEqual(plan('snooze').adapter,'browser');
assert.strictEqual(plan('trash',{...binding,references:{browser:browserRef,bridge:bridgeRef}},
 states,{nowMs:1000}).status,'confirmation-required');
assert.strictEqual(plan('spam',binding,states,{nowMs:1000}).status,'confirmation-required');
assert.strictEqual(plan('archive',binding,
 {browser:states.browser,bridge:I.dormant()}).adapter,'browser');
assert.strictEqual(plan('snooze',binding,{browser:B.dormant(),bridge:states.bridge}).status,
 'not-connected-or-not-matched');
assert.strictEqual(plan('archive',null).status,'unverified-message');
assert.strictEqual(plan('archive',{...binding,eventId:'other.event.0001'}).status,'unverified-message');
assert.strictEqual(plan('archive',{...binding,accountKey:'test@proton.me'}).status,'unverified-message');
assert.strictEqual(plan('archive',{...binding,expiresAtMs:50}).status,'expired-binding');
assert.strictEqual(plan('archive',{...binding,references:{browser:{...browserRef,origin:'https://evil.test'},
 bridge:{...bridgeRef,accountKey:'wrong.account.0001'}}}).status,'not-connected-or-not-matched');
assert.strictEqual(plan('archive',{...binding,references:{browser:browserRef,
 bridge:{...bridgeRef,uid:0}}}).adapter,'browser');
assert.strictEqual(plan('archive',binding,{bridge:states.bridge,browser:states.browser},
 opts,'another.notification.id').status,'unverified-message');
assert.strictEqual(plan('delete-forever').status,'unsupported-operation');
assert.strictEqual(plan('archive',binding,{bridge:{...states.bridge,accountKey:'wrong.account.0001'},
 browser:B.dormant()}).status,'not-connected-or-not-matched');
assert.strictEqual(P.receiptStatus(plan('archive'),'request.id.0001',null),'not-confirmed');
assert.strictEqual(P.receiptStatus(plan('archive'),'request.id.0001',
 {requestId:'request.id.0001',adapter:'bridge',accountKey:ACCOUNT,operation:'archive',
 eventId:EVENT,mailboxKey:bridgeRef.mailboxKey,
 uidValidity:bridgeRef.uidValidity,uid:bridgeRef.uid,status:'accepted'}),'pending-provider');
assert.strictEqual(P.receiptStatus(plan('archive'),'request.id.0001',
 {requestId:'request.id.0001',adapter:'bridge',accountKey:ACCOUNT,operation:'archive',
 eventId:EVENT,mailboxKey:bridgeRef.mailboxKey,
 uidValidity:bridgeRef.uidValidity,uid:bridgeRef.uid,status:'applied',verified:false}),'not-confirmed');
assert.strictEqual(P.receiptStatus(plan('archive'),'request.id.0001',
 {requestId:'request.id.0001',adapter:'browser',accountKey:ACCOUNT,operation:'archive',
 eventId:EVENT,mailboxKey:bridgeRef.mailboxKey,
 uidValidity:bridgeRef.uidValidity,uid:bridgeRef.uid,status:'applied',verified:true}),'not-confirmed');
assert.strictEqual(P.receiptStatus(plan('archive'),'request.id.0001',
 {requestId:'request.id.0001',adapter:'bridge',accountKey:ACCOUNT,operation:'archive',
 eventId:EVENT,mailboxKey:'different.mailbox.001',
 uidValidity:bridgeRef.uidValidity,uid:bridgeRef.uid,status:'applied',verified:true}),
 'not-confirmed');
assert.strictEqual(P.receiptStatus(plan('archive'),'request.id.0001',
 {requestId:'request.id.0001',adapter:'bridge',accountKey:ACCOUNT,operation:'archive',
 eventId:EVENT,mailboxKey:bridgeRef.mailboxKey,
 uidValidity:bridgeRef.uidValidity,uid:bridgeRef.uid,status:'applied',verified:true}),'confirmed');

assert.strictEqual(B.validOrigin('https://mail.proton.me'),true);
assert.strictEqual(B.validOrigin('https://mail.proton.me.evil.test'),false);
assert.deepStrictEqual(clone(B.stateFromHandshake({protocol:1,kind:'PONG',
 origin:'https://mail.proton.me',mailboxAccess:false,messageIdentityVerified:false,
 accountKey:ACCOUNT,capabilities:['star']})),{ready:false,capabilities:[]});
assert.strictEqual(B.stateFromHandshake({protocol:1,kind:'PONG',
 origin:'https://mail.proton.me',mailboxAccess:true,messageIdentityVerified:true,
 accountKey:ACCOUNT,capabilities:['star','fake-op']}).capabilities.length,1);

assert.strictEqual(I.safeEndpoint({host:'127.0.0.1',port:1143,
 tlsMode:'starttls',bridgeCertificateVerified:true}),true);
assert.strictEqual(I.safeEndpoint({host:'localhost',port:1143,
 tlsMode:'starttls',bridgeCertificateVerified:true}),false);
assert.strictEqual(I.safeEndpoint({host:'0.0.0.0',port:1143,
 tlsMode:'starttls',bridgeCertificateVerified:true}),false);
assert.strictEqual(I.safeEndpoint({host:'127.0.0.1',port:1143,
 tlsMode:'starttls',bridgeCertificateVerified:false}),false);
assert.strictEqual(I.safeEndpoint({host:'127.0.0.1',port:1143,
 tlsMode:'none',bridgeCertificateVerified:true}),false);
const bridge=I.stateFromSession({authenticated:true,messageIdentityVerified:true,
 accountKey:ACCOUNT,capabilities:['mark-read','archive','snooze','star']},
 {host:'127.0.0.1',port:1143,tlsMode:'starttls',bridgeCertificateVerified:true});
assert.strictEqual(bridge.ready,true);
assert.strictEqual(bridge.capabilities.includes('snooze'),false);
assert.strictEqual(bridge.capabilities.includes('archive'),true);
console.log('Dual provider policy, account binding, confirmation and receipts: PASS');
"""
subprocess.run(["node","-e",NODE,str(POLICY),str(BROWSER),str(BRIDGE)],check=True)
print("Proton dual-adapter policy contracts: PASS")
