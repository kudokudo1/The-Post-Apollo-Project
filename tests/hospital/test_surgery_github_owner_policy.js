#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalGitHubOwnerPolicy.js"), "utf8"), ctx);

assert.deepEqual({...ctx.splitRepository("kudokudo1/The-Post-Apollo-Project")},
    {owner:"kudokudo1",repository:"The-Post-Apollo-Project"});
assert.deepEqual({...ctx.splitRepository("someone-else/repo-name")},
    {owner:"someone-else",repository:"repo-name"});
assert.equal(ctx.splitRepository("not-a-repo").owner,"");
assert.equal(ctx.splitRepository("owner/repo/extra").repository,"");
assert.equal(ctx.splitRepository("owner/invalid repo").repository,"");
assert.equal(ctx.part("kudokudo1"),"kudokudo1");
assert.equal(ctx.part("bad/slash"),"");
assert.equal(ctx.part(" "), "");

const myPatient = ctx.suggestion("kudokudo1/The-Post-Apollo-Project", "kudokudo1");
assert.equal(myPatient.source,"CURRENT PATIENT");
assert.equal(myPatient.owner,"kudokudo1");
assert.equal(myPatient.repository,"The-Post-Apollo-Project");
assert.equal(ctx.compose(myPatient.owner,myPatient.repository),
    "kudokudo1/The-Post-Apollo-Project");

const foreign = ctx.suggestion("another-org/shared-project","kudokudo1");
assert.equal(foreign.owner,"another-org");
assert.equal(foreign.repository,"shared-project");
assert.equal(foreign.source,"CURRENT PATIENT");
// Never silently construct kudokudo1/shared-project from a foreign Patient.
assert.notEqual(ctx.compose(foreign.owner,foreign.repository),
    "kudokudo1/shared-project");
const missingPatient = ctx.suggestion("invalid-patient","kudokudo1");
assert.equal(missingPatient.owner,"kudokudo1");
assert.equal(missingPatient.repository,"");
assert.equal(missingPatient.source,"SIGNED-IN GITHUB");
assert.equal(ctx.suggestion("","").owner,"");

const options = Array.from(ctx.ownerOptions(
    [
        {repository:"another-org/shared-project"},
        {repository:"kudokudo1/The-Post-Apollo-Project"},
        {repository:"third-user/demo"},
        {repository:"another-org/second-repo"},
        {repository:"invalid string"}
    ],"kudokudo1/The-Post-Apollo-Project","kudokudo1"));
assert.deepEqual(options.map(x=>x.owner),
    ["kudokudo1","another-org","third-user"]);
assert.equal(options[0].label,"MY GITHUB");
assert.equal(options[1].label,"USED IN HOSPITAL");
assert.equal(ctx.ownerOptions([], "", "").length,0);
console.log("HOSPITAL GITHUB OWNER // PASS // account vs Patient default, foreign owner and existing profile suggestions");
