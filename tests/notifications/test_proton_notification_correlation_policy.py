#!/usr/bin/env python3
"""Synthetic dual-witness Proton notification correlation. No live mailbox I/O."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "services/notifications/mail/ProtonNotificationCorrelationPolicy.js"
LEDGER = ROOT / "services/notifications/mail/ProtonMailBindingLedger.js"
ROUTER = ROOT / "services/notifications/mail/ProtonMailActionPolicy.js"
SOURCE = POLICY.read_text(encoding="utf8")

assert ".pragma library" in SOURCE
assert "function makeVerifier(" in SOURCE
assert "TRUSTED_PROTON_DELIVERY_V1" in SOURCE
assert "TRUSTED_PROTON_MESSAGE_V1" in SOURCE
for forbidden in ("localStorage", "XMLHttpRequest", "fetch(", "WebSocket",
                  "sendNativeMessage", ".click(", "textContent", "innerHTML",
                  "NotificationServer", "JSON.stringify", "console."):
    assert forbidden not in SOURCE, forbidden

NODE = r"""
"use strict";
const fs=require("fs"),vm=require("vm"),assert=require("assert");
function load(file) {
 const source=fs.readFileSync(file,"utf8").replace(/^\s*\.pragma library\s*$/m,"");
 const scope={Number,String,Array,Object,Math,RegExp};
 vm.runInNewContext(source,scope,{filename:file});
 return scope;
}
const C=load(process.argv[1]),L=load(process.argv[2]),P=load(process.argv[3]);
const clone=x=>JSON.parse(JSON.stringify(x));
const N=5000000;
let t=N;
const E="event.proton.20261023.001",T="adapter.ticket.0001";
const K="event.source.verified001",A="account.proton.0001",M="message.proton.0001";
const ORIGIN="https://mail.proton.me";
const native=()=>{
 return {kind:"TRUSTED_PROTON_DELIVERY_V1",eventId:E,
   provider:"proton-mail",origin:ORIGIN,grouped:false,
   sourceEventKey:K,accountKey:A,messageKey:M,deliveredAtMs:N-10000};
};
const adapter=()=>{
 return {kind:"TRUSTED_PROTON_MESSAGE_V1",provider:"proton-mail",
   origin:ORIGIN,messageKind:"message",sourceEventKey:K,
   accountKey:A,messageKey:M,observedAtMs:N-5000};
};
const deliveries=new Map([[E,native()]]);
const messages=new Map([[T,adapter()]]);
const active=new Set([E]);
const lookupDelivery=id=>deliveries.get(id)||null;
const lookupMessage=ticket=>messages.get(ticket)||null;
const live=id=>active.has(id);
const tick=()=>t;
const verify=C.makeVerifier(lookupDelivery,lookupMessage,live,tick);
const proposal={eventId:E,adapterTicket:T};
const valid=clone(verify(proposal));
assert.deepStrictEqual(Object.keys(valid).sort(),
 ["accountKey","attested","eventId","expiresAtMs","references"].sort());
assert.strictEqual(valid.attested,true);
assert.strictEqual(valid.eventId,E);
assert.strictEqual(valid.accountKey,A);
assert.strictEqual(valid.references.browser.messageKey,M);
assert.strictEqual(valid.expiresAtMs,N+110000);
assert.ok(!JSON.stringify(valid).includes(K));
assert.ok(!JSON.stringify(valid).includes(T));

// The preexisting ledger can consume a VERIFIED record, but is never given
// native delivery registration authority by an arbitrary incoming packet.
const ledger=L.createLedger(verify,live);
assert.strictEqual(ledger.admit({kind:"PROTON_READINESS_V4",
 selectedRowStructureOk:true,toolbarReadEnabled:1},t),"untrusted-binding");
assert.strictEqual(ledger.admit({...proposal,attested:true},t),"untrusted-binding");
assert.strictEqual(ledger.admit(proposal,t),"accepted");
assert.strictEqual(ledger.size(t),1);
assert.strictEqual(ledger.admit(proposal,t),"event-already-bound");
assert.strictEqual(P.routeFor(E,"mark-read",ledger.lookup(E,t),{
 browser:{ready:false,capabilities:[]}}, {nowMs:t}).status,
 "not-connected-or-not-matched");
const altered=ledger.lookup(E,t);
altered.references.browser.messageKey="other.message.0001";
assert.strictEqual(ledger.lookup(E,t).references.browser.messageKey,M);

// Nothing from a desktop card (title, sender, notification ID alone,
// hostname or arbitrary browser tag) may unlock correlation.
const badInputs=[
 null,{}, {eventId:E}, {adapterTicket:T},
 {eventId:E,adapterTicket:T,title:"New email"},
 {eventId:E,adapterTicket:T,tag:M},
 {eventId:E,adapterTicket:"unknown.ticket"},
 {eventId:"another.event.0001",adapterTicket:T},
 {eventId:E,adapterTicket:T,source:"proton",subject:"private"},
 {eventId:E,adapterTicket:T,selectedRowStructureOk:true},
 {eventId:"?",adapterTicket:T}
];
for(const input of badInputs) assert.strictEqual(verify(input),null);
assert.strictEqual(C.makeVerifier()(proposal),null);
assert.strictEqual(C.makeVerifier(()=>{throw Error("secret")},lookupMessage,live,tick)(proposal),null);
assert.strictEqual(C.makeVerifier(lookupDelivery,()=>{throw Error("secret")},live,tick)(proposal),null);
assert.strictEqual(C.makeVerifier(lookupDelivery,lookupMessage,()=>{throw Error("secret")},tick)(proposal),null);
assert.strictEqual(C.makeVerifier(lookupDelivery,lookupMessage,live,()=>NaN)(proposal),null);
assert.strictEqual(C.makeVerifier(x=>x,lookupMessage,live,tick)(proposal),null);

// Synthetic witness tampering must not pass.
function alteredWitness(nativeDelta={},providerDelta={}) {
 const n=new Map([[E,{...native(),...nativeDelta}]]);
 const m=new Map([[T,{...adapter(),...providerDelta}]]);
 return C.makeVerifier(id=>n.get(id)||null,
    ticket=>m.get(ticket)||null,live,tick)(proposal);
}
const badNative=[
 {kind:"PROTON_READINESS_V4"},
 {eventId:"other.event.0001"},
 {provider:"other"},
 {origin:"https://mail.proton.me.evil.test"},
 {grouped:true},
 {sourceEventKey:"different.event.0001"},
 {accountKey:"other.account.0001"},
 {messageKey:"other.message.0001"},
 {deliveredAtMs:N+1},
 {deliveredAtMs:N-120001},
 {deliveredAtMs:"not-int"}
];
for(const bad of badNative)assert.strictEqual(alteredWitness(bad),null);
const badAdapter=[
 {kind:"PROTON_READINESS_V4"},
 {provider:"other"},
 {origin:"https://evil.test"},
 {messageKind:"conversation"},
 {sourceEventKey:"different.event.0001"},
 {accountKey:"other.account.0001"},
 {messageKey:"other.message.0001"},
 {observedAtMs:N+1},
 {observedAtMs:N-120001},
 {observedAtMs:null}
];
for(const bad of badAdapter)assert.strictEqual(alteredWitness({},bad),null);

active.delete(E);
assert.strictEqual(verify(proposal),null);
assert.strictEqual(ledger.lookup(E,t),null);
active.add(E);
t=N+120000;
assert.strictEqual(verify(proposal),null);
t=N;

// Replay must fail after revocation, even while synthetic witnesses remain.
assert.strictEqual(ledger.admit(proposal,t),"accepted");
assert.strictEqual(ledger.revoke(E),true);
assert.strictEqual(ledger.admit(proposal,t),"event-revoked");

// Multiple native events must not claim the same mailbox reference.
const E2="event.proton.20261023.002";
const T2="adapter.ticket.0002";
const K2="event.source.verified002";
active.add(E2);
deliveries.set(E2,{...native(),eventId:E2,sourceEventKey:K2});
messages.set(T2,{...adapter(),sourceEventKey:K2});
const freshLedger=L.createLedger(verify,live);
assert.strictEqual(freshLedger.admit(proposal,t),"accepted");
assert.strictEqual(freshLedger.admit({eventId:E2,adapterTicket:T2},t),
 "message-already-bound");

// A different authenticated message, even from the same account, is allowed.
const M2="message.proton.0002";
deliveries.set(E2,{...native(),eventId:E2,sourceEventKey:K2,messageKey:M2});
messages.set(T2,{...adapter(),sourceEventKey:K2,messageKey:M2});
assert.strictEqual(freshLedger.admit({eventId:E2,adapterTicket:T2},t),"accepted");

// No implicit treatment of Proton web tag as a verified desktop source event.
deliveries.set(E2,{...native(),eventId:E2,sourceEventKey:undefined,
 messageKey:M2});
assert.strictEqual(verify({eventId:E2,adapterTicket:T2}),null);
console.log("Proton dual-source notification correlation policy: PASS");
"""
subprocess.run(
    ["node", "-e", NODE, str(POLICY), str(LEDGER), str(ROUTER)],
    check=True,
)
print("Proton notification correlation policy contracts: PASS")
