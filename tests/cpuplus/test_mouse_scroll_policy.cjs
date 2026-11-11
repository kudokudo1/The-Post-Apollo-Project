"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(
    path.join(__dirname,"../../services/input/MouseScrollPolicy.js"),"utf8")
    .replace(/^\.pragma library\s*/m,"");
const policy={};
vm.runInNewContext(source,policy);
let doc=policy.initialDocument();
assert.deepEqual(JSON.parse(JSON.stringify(doc)),{version:1,devices:[]});
for (const n of [0.25,0.5,1,1.25,1.5,2,3,4,5,6])
    assert.equal(policy.validFactor(n),true);
for (const n of [-1,0,0.1,1.1,NaN,Infinity,100,"2"])
    assert.equal(policy.validFactor(n),false);
doc=policy.withFactor(doc,"1234:5678:Mouse",2).document;
assert.equal(policy.get(doc,"1234:5678:Mouse"),2);
doc=policy.withFactor(doc,"1234:5678:Mouse",1).document;
assert.equal(policy.get(doc,"1234:5678:Mouse"),1);
assert.equal(doc.devices.length,1);
assert.equal(policy.withFactor(doc,"type:pointer;reload",2).ok,false);
assert.equal(policy.parse(JSON.stringify(doc)).ok,true);
assert.equal(policy.parse('{"version":1,"devices":[{"identifier":"x","factor":1},{"identifier":"x","factor":2}]}').ok,false);
assert.equal(policy.parse("{}").ok,false);
assert.equal(policy.parse("bad").ok,false);
console.log("MOUSE_SCROLL_POLICY_PASS // NO_AUTOMATIC_REAPPLY");
