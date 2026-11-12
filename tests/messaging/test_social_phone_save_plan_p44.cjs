"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const {test} = require("node:test");
const file = path.join(__dirname, "../../widgets/messanger/PhonePersonalSavePlanP44.js");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(file,"utf8"),ctx,{filename:file});
const toJS = (v) => JSON.parse(JSON.stringify(v));
const sel = "profile-id:epoch-11:row-2";
const draft = (favorite=null,note=null) => ({
  changed:true,contactId:sel,favorite,note
});

test("staged Favorite and Note become exactly TWO separate operations",()=>{
 const p = toJS(ctx.planDraft(draft(true,"Synthetic secret note"),sel));
 assert.equal(p.status,"UNTRUSTED_REVIEW_ONLY");
 assert.equal(p.operations.length,2);
 assert.deepEqual(p.operations.map(x=>x.action),["FAVORITE","NOTE"]);
 assert.deepEqual(p.operations.map(x=>Object.keys(x).sort()),[
   ["action","favorite","schema","selectedContactId"],
   ["action","note","schema","selectedContactId"]
 ]);
 assert.equal(p.operations[0].favorite,true);
 assert.equal(p.operations[1].note,"Synthetic secret note");
 assert.ok(!JSON.stringify(p).includes("approved"));
 assert.ok(!JSON.stringify(p).includes("nonce"));
});

test("one-action edit, unset favorite and empty note are distinct",()=>{
 const star=toJS(ctx.planDraft(draft(false,null),sel));
 const clear=toJS(ctx.planDraft(draft(null,""),sel));
 assert.equal(star.operations.length,1);
 assert.equal(star.operations[0].favorite,false);
 assert.equal(clear.operations.length,1);
 assert.equal(clear.operations[0].action,"NOTE");
 assert.equal(clear.operations[0].note,"");
});

test("different contact, invalid or no edit fails closed",()=>{
 const cases=[
 draft(null,null),
 {...draft(true,"private"),contactId:"different"},
 {...draft(true,null),changed:false},
 {...draft(null,"too long".repeat(1024))},
 {...draft(null,"bad\u0000")},
 {...draft(null,"\ud800")},
 {...draft(true,"private"),productionEnabled:true},
 {...draft(true,"private"),expectedRevision:1},
 {...draft(true,"private"),requestNonce:"a".repeat(32)},
 {...draft(true,null),favorite:"true"},
 {...draft(null,null),note:42},
 null,
 ];
 for(const input of cases){
   const p=toJS(ctx.planDraft(input,sel));
   assert.equal(p.status,"REFUSED");
   assert.deepEqual(p.operations,[]);
 }
 assert.equal(ctx.planDraft(draft(true,null),"../bad").status,"REFUSED");
});

test("JS planner never saves, signs, requests trust, or persists data",()=>{
 const source=fs.readFileSync(file,"utf8");
 for(const forbidden of ["XMLHttpRequest","LocalStorage","secret-tool",
  "FileView","fetch(","Vault.commit","console.log(","print(",
  "Qt.openUrlExternally","savePersonalApproval("])
   assert.equal(source.includes(forbidden),false,forbidden);
});
