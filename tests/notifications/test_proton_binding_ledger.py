#!/usr/bin/env python3
"""Offline Proton notification/mail lease ledger. No live adapter or mail I/O."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "services/notifications/mail/ProtonMailBindingLedger.js"
POLICY = ROOT / "services/notifications/mail/ProtonMailActionPolicy.js"

source = LEDGER.read_text(encoding="utf8")
for forbidden in ("console.", "FileView", "LocalStorage", "localStorage",
                  "fetch(", "XMLHttpRequest", "WebSocket(", "sendNativeMessage",
                  "NotificationServer", "JSON.stringify", ".click("):
    assert forbidden not in source, f"Forbidden I/O or serialization: {forbidden}"
assert ".pragma library" in source
assert "function createLedger(" in source
assert "transport-not-connected" in source

NODE = r"""
"use strict";
const fs=require("fs"),vm=require("vm"),assert=require("assert");
function moduleAt(path){
  const source=fs.readFileSync(path,"utf8").replace(/^\s*\.pragma library\s*$/m,"");
  const scope={Number,String,Array,Object,Math,RegExp};
  vm.runInNewContext(source,scope,{filename:path});
  return scope;
}
const L=moduleAt(process.argv[1]);
const P=moduleAt(process.argv[2]);
const clone=(x)=>JSON.parse(JSON.stringify(x));
const NOW=1000000, ACC="account.id0001";
const e1="event.20261022.0001",e2="event.20261022.0002";
const readRef=(account=ACC,id="browser.message.0001")=>({
  attested:true, accountKey:account,
  origin:"https://mail.proton.me", messageKey:id
});
const make=(eventId,ref=readRef(),account=ACC,expiresAtMs=NOW+60000)=>({
  eventId,accountKey:account,attested:true,expiresAtMs,
  references:{browser:ref}
});
// No trusted adapter or live event predicate: a forged attested claim cannot
// become active by simply constructing a ledger.
const cold=L.createLedger();
assert.strictEqual(cold.admit(make(e1),NOW),"transport-not-connected");
assert.strictEqual(cold.lookup(e1,NOW),null);
const events=new Set([e1,e2]), grants=new Map();
const auth=key=>grants.get(key)||null;
const live=id=>events.has(id);
const ledger=L.createLedger(auth,live);
const keyA={},keyB={},keyC={};
grants.set(keyA,make(e1));
grants.set(keyB,make(e2,readRef(ACC,"browser.message.0002")));
grants.set(keyC,make(e2)); // same message as e1, must be denied
assert.strictEqual(ledger.admit({eventId:e1,attested:true,references:{
  browser:readRef()}},NOW),"untrusted-binding");
// A callback that simply passes user-controlled fields through cannot mint
// authority, even if it is present and the event is still live.
const unsafeEcho=L.createLedger(claim=>claim,live);
assert.strictEqual(unsafeEcho.admit(make(e1),NOW),"untrusted-binding");
assert.strictEqual(ledger.admit({kind:"PROTON_READINESS_V4",
  selectedMailRows:1,selectedRowStructureOk:true},NOW),"untrusted-binding");
assert.strictEqual(ledger.admit(keyA,-1),"invalid-clock");
assert.strictEqual(ledger.admit(keyA,NOW),"accepted");
assert.strictEqual(ledger.size(NOW),1);
assert.strictEqual(ledger.admit(keyA,NOW),"event-already-bound");
assert.strictEqual(ledger.admit(keyC,NOW),"message-already-bound");
assert.strictEqual(ledger.admit(keyB,NOW),"accepted");
const privateA=clone(ledger.lookup(e1,NOW));
assert.strictEqual(privateA.eventId,e1);
assert.strictEqual(privateA.references.browser.messageKey,"browser.message.0001");
const copy=ledger.lookup(e1,NOW);
copy.references.browser.messageKey="manipulated";
copy.references.browser.accountKey="evil.account.0001";
assert.strictEqual(ledger.lookup(e1,NOW).references.browser.messageKey,
  "browser.message.0001");

// Existing router is reusable ONLY when a separate trusted transport eventually
// yields valid state. None is connected today.
assert.strictEqual(P.routeFor(e1,"mark-read",ledger.lookup(e1,NOW),{
  browser:{ready:false,capabilities:[]}}, {nowMs:NOW}).status,
  "not-connected-or-not-matched");
assert.strictEqual(P.routeFor(e1,"mark-read",ledger.lookup(e1,NOW),{
  browser:{ready:true,attested:true,accountKey:ACC,capabilities:["mark-read"]}},
  {nowMs:NOW}).status,"ready"); // synthetic policy-only test, not live auth
assert.strictEqual(P.routeFor(e2,"mark-read",ledger.lookup(e1,NOW),{
  browser:{ready:true,attested:true,accountKey:ACC,capabilities:["mark-read"]}},
  {nowMs:NOW}).status,"unverified-message");

assert.strictEqual(ledger.revoke(e1),true);
assert.strictEqual(ledger.lookup(e1,NOW),null);
assert.strictEqual(ledger.admit(keyA,NOW),"event-revoked");
assert.strictEqual(ledger.revoke(e1),false);
ledger.reset();
assert.strictEqual(ledger.lookup(e2,NOW),null);
assert.strictEqual(ledger.admit(keyB,NOW),"event-revoked");
assert.strictEqual(ledger.size(NOW),0);

// Closing a native notification invalidates a lease immediately.
const closed=L.createLedger(auth,live);
assert.strictEqual(closed.admit(keyA,NOW),"accepted");
events.delete(e1);
assert.strictEqual(closed.lookup(e1,NOW),null);
assert.strictEqual(closed.size(NOW),0);
events.add(e1);
assert.strictEqual(closed.admit(keyA,NOW),"accepted");
assert.strictEqual(closed.lookup(e1,NOW+60000),null);

// No existing sender, malformed bound ref, wrong account, bad origin, excessive
// or expired TTL, and transport exceptions must all fail.
const absent=L.createLedger(auth,()=>false);
assert.strictEqual(absent.admit(keyA,NOW),"event-not-live");
const bad=new Map(), keyBad={};
const reject=L.createLedger(key=>bad.get(key)||null, live);
function invalid(r){
  bad.set(keyBad,r);
  assert.strictEqual(reject.admit(keyBad,NOW),"untrusted-binding");
}
invalid(make(e1,readRef("other.account.0001")));
invalid(make(e1,{...readRef(),origin:"https://evil.test"}));
invalid(make(e1,readRef(),ACC,NOW+120001));
invalid(make(e1,readRef(),ACC,NOW));
invalid(make(e1,{...readRef(),messageKey:"?"}));
invalid({...make(e1),references:{}});
invalid({...make(e1),references:{browser:readRef(),unexpected:readRef()}});
invalid({...make(e1),accountKey:"me@proton.me"});
invalid({...make(e1),attested:false});
const thrown=L.createLedger(()=>{throw Error("sensitive ignored")},live);
assert.strictEqual(thrown.admit({},NOW),"untrusted-binding");

// Bridge uses independent UIDVALIDITY + UID + mailbox identity. Never assume
// the browser key and the Bridge UID are interchangeable.
const bridgeKey={},bridgeEvent="event.20261022.bridge", bridgeAccount="account.id0002";
events.add(bridgeEvent);
grants.set(bridgeKey,{
 eventId:bridgeEvent,accountKey:bridgeAccount,attested:true,
 expiresAtMs:NOW+60000,references:{bridge:{
  attested:true,accountKey:bridgeAccount,
  mailboxKey:"inbox.opaque.0001",uidValidity:420,uid:32}}
});
const bridge=L.createLedger(auth,live);
assert.strictEqual(bridge.admit(bridgeKey,NOW),"accepted");
assert.strictEqual(bridge.lookup(bridgeEvent,NOW).references.bridge.uid,32);
const bridgeCopy=bridge.lookup(bridgeEvent,NOW);
bridgeCopy.references.bridge.uid=99;
assert.strictEqual(bridge.lookup(bridgeEvent,NOW).references.bridge.uid,32);

// Fixed capacity and expiry, so a stalled process cannot retain unlimited
// opaque mail references.
const capEvents=new Set(),capGrants=new Map();
const capacity=L.createLedger(key=>capGrants.get(key)||null,id=>capEvents.has(id));
for(let i=0;i<64;i++){
 const id="event.capacity."+String(i).padStart(4,"0");
 const key={i};capEvents.add(id);
 capGrants.set(key,make(id,readRef(ACC,"browser.capacity."+i)));
 assert.strictEqual(capacity.admit(key,NOW),"accepted");
}
const overflow={};
const overflowId="event.capacity.9999";capEvents.add(overflowId);
capGrants.set(overflow,make(overflowId,readRef(ACC,"browser.capacity.9999")));
assert.strictEqual(capacity.admit(overflow,NOW),"capacity-exceeded");
assert.strictEqual(capacity.size(NOW),64);
assert.strictEqual(capacity.size(NOW+60001),0);

console.log("Proton memory-only binding leases, trust gate and provider policy: PASS");
"""
subprocess.run(["node", "-e", NODE, str(LEDGER), str(POLICY)], check=True)
print("Proton private binding ledger contracts: PASS")
