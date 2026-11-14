"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const {test} = require("node:test");
const file=path.join(__dirname,"../../widgets/messanger/PhonePersonalSaveFeedbackP45.js");
const ctx=vm.createContext({});
vm.runInContext(fs.readFileSync(file,"utf8"),ctx,{filename:file});
const clone=(o)=>JSON.parse(JSON.stringify(o));

test("all known denied and partial states stay unsaved and non-authorizing",()=>{
  for(const status of [
    "HOST_UNAVAILABLE","KEY_LOCKED","CONSENT_REVOKED","CONTACT_STALE",
    "PARTIAL_UNCONFIRMED","COMMIT_UNCERTAIN","INVALID_EDIT"
  ]){
    const v=clone(ctx.classify({status}));
    assert.equal(v.status,status);
    assert.equal(v.saved,false);
    assert.equal(v.retryAuthorized,false);
    assert.equal(v.productionEnabled,false);
    assert.ok(!/\bSAVED\b/.test(v.text) || /NOT SAVED/.test(v.text));
  }
});

test("forged success or injected personal details never become saved",()=>{
  for(const result of [
    {status:"SAVED"}, {status:"SEALED"}, {status:"VERIFIED_SAVED"},
    {status:"HOST_UNAVAILABLE",note:"private contact note"},
    {status:"KEY_LOCKED",productionEnabled:true},
    null, false, true, "SAVED", {}, [], {status:7},
    {status:"COMMIT_UNCERTAIN",retryAuthorized:true}
  ]){
    const v=clone(ctx.classify(result));
    assert.equal(v.status,"HOST_UNAVAILABLE");
    assert.equal(v.saved,false);
    assert.equal(v.retryAuthorized,false);
    assert.equal(v.productionEnabled,false);
    assert.ok(!JSON.stringify(v).includes("private contact note"));
  }
});

test("no IO, permission minting, or secret debug prints",()=>{
  const source=fs.readFileSync(file,"utf8");
  for(const forbidden of [
    "XMLHttpRequest","LocalStorage","secret-tool","FileView",
    "fetch(","Vault.commit(","console.log(","print(",
    "savePersonalApproval(","sessionStorage"
  ])assert.equal(source.includes(forbidden),false,forbidden);
});
