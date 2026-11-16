#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm");
const src=fs.readFileSync(path.join(__dirname,
    "../../services/publisher/PublisherAccessIntentPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const p=vm.createContext({});
vm.runInContext(src,p,{filename:"PublisherAccessIntentPolicy.js"});
let doc=p.emptyDocument();
assert.equal(p.validate(doc).ok,true);
assert.equal(p.view("empty",doc).writable,true);
for(const state of ["loading","saving","error","unsupported"]){
    assert.equal(p.view(state,doc).writable,false);
}
assert.equal(p.view("ready",doc).canPublish,false);
assert.equal(p.view("ready",doc).hostConnected,false);
assert.equal(p.view("ready",doc).grants.length,0);
assert.equal(p.providerIds().includes("youtube"),true);
assert.equal(p.scopes("youtube").join(","),"post.video");
assert.equal(p.scopes("discord").includes("post.video"),false);
const no=p.request(doc,"identity-1","personal","youtube","my-channel","post.video",1000);
assert.equal(no.ok,true);
assert.equal(no.intentId,"r1");
assert.equal(doc.intents.length,0);
assert.equal(no.document.intents[0].status,"requested");
doc=no.document;
const duplicate=p.request(doc,"identity-1","personal","youtube","my-channel","post.video",1001);
assert.equal(duplicate.ok,true);
assert.equal(duplicate.unchanged,true);
assert.equal(duplicate.intentId,"r1");
assert.equal(p.request(doc,"identity-1","personal","youtube","my-channel","post.text",1100).reason,
            "INVALID_ACCOUNT_INTENT");
assert.equal(p.request(doc,"fake-1","personal","youtube","my-channel","post.video",1100).reason,
            "INVALID_ACCOUNT_INTENT");
assert.equal(p.request(doc,"identity-1","organization","unknown","my-channel","post.text",1100).reason,
            "INVALID_ACCOUNT_INTENT");
assert.equal(p.request(doc,"identity-1","organization","youtube","my-channel","post.video",1200).ok,true);
assert.equal(p.request(doc,"identity-2","personal","youtube","my-channel","post.video",1200).ok,true);
assert.equal(p.request(doc,"identity-1","personal","youtube","another-channel","post.video",1200).ok,true);
assert.equal(p.request(doc,"identity-1","personal","youtube","secret\nheader","post.video",1200).reason,
            "INVALID_ACCOUNT_INTENT");
assert.equal(p.request(doc,"identity-1","personal","youtube","x","post.video",-1).reason,
            "INVALID_ACCOUNT_INTENT");
const withdraw=p.withdraw(doc,"r1",2000);
assert.equal(withdraw.ok,true);
assert.equal(withdraw.document.intents[0].status,"withdrawn");
assert.equal(doc.intents[0].status,"requested");
assert.equal(p.withdraw(withdraw.document,"r1",3000).reason,"NOT_ACTIVE");
assert.equal(p.withdraw(doc,"r1",500).reason,"STALE_TIME");
assert.equal(p.withdraw(doc,"r12",5000).reason,"UNKNOWN_INTENT");
const replacement=p.request(withdraw.document,"identity-1","personal","youtube","my-channel","post.video",4000);
assert.equal(replacement.ok,true);
assert.equal(replacement.intentId,"r2");
assert.equal(p.parse(JSON.stringify(replacement.document)).ok,true);
assert.equal(p.parse("{").reason,"MALFORMED_JSON");
assert.equal(p.parse(JSON.stringify({...doc,access_token:"SHOULD_NOT_PERSIST"})).reason,
             "UNKNOWN_FIELDS");
assert.equal(p.parse(JSON.stringify({...doc,version:2})).reason,"UNSUPPORTED_VERSION");
const forged=JSON.parse(JSON.stringify(doc));
forged.intents[0].status="approved";
assert.equal(p.parse(JSON.stringify(forged)).reason,"INVALID_INTENT");
const extra=JSON.parse(JSON.stringify(doc));
extra.intents[0].credential="SECRET";
assert.equal(p.parse(JSON.stringify(extra)).reason,"INVALID_INTENT");
const dup=JSON.parse(JSON.stringify(doc));
dup.intents.push(dup.intents[0]);
assert.equal(p.parse(JSON.stringify(dup)).reason,"DUPLICATE_INTENT_ID");
const rewind=JSON.parse(JSON.stringify(doc));
rewind.nextId=1;
assert.equal(p.parse(JSON.stringify(rewind)).reason,"SEQUENCE_REWIND");
assert.equal(p.parse("x".repeat(200001)).reason,"INVALID_SOURCE");
const attempt={identityId:"identity-1",context:"personal",provider:"youtube",
               accountAlias:"my-channel",scope:"post.video",status:"requested"};
for(const receipt of [
    null,{}, {approved:true}, {verified:true,signature:"signed"},
    {hostConnected:true,allowed:true,role:"owner",consent:true},
    {issuer:"trusted",credential:"abc",notExpired:true,revoked:false}
]){
    const decision=p.evaluate(attempt,receipt);
    assert.equal(decision.allowed,false);
    assert.equal(decision.reason,"TRUSTED_PUBLISHING_BROKER_NOT_CONNECTED");
}
assert.equal(p.evaluate({...attempt,status:"withdrawn"},{approved:true}).allowed,false);
assert.equal(p.evaluate({...attempt,provider:"not-real"},{approved:true}).reason,
             "INVALID_REQUEST");
assert.equal(p.evaluate({},{approved:true}).allowed,false);
assert.equal(p.view("ready",replacement.document).grants.length,0);
assert.equal(p.view("ready",replacement.document).canPublish,false);
console.log("publisher P1.5 deny-only account intents: all assertions passed");
