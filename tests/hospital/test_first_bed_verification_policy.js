#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalFirstBedVerificationPolicy.js"), "utf8"), ctx);

let checks = 0;
const room = {id:"room-first",repository:"owner/repo",branch:"",bedPath:"",
    doctorId:"",providerId:""};
const bed = {label:"Test worktree",path:"/tmp/px-fixture",branch:"feature/one",
    origin:"git@github.com:owner/repo.git",head:"abc123",worktree:"CLEAN",isLive:false};
const evidence = {path:bed.path,topLevel:bed.path,branch:bed.branch,
    origin:"https://github.com/owner/repo.git",head:"a".repeat(40),clean:true};
const base = {room,rooms:[room],roomsLoaded:true,beds:[bed],sessions:[],
    bedsDiscovering:false,selectedPath:bed.path,evidence,
    evidenceChecked:true,evidenceBusy:false};
function plan(changes) {checks++;return ctx.assess({...base,...changes})}
function held(changes,needle) {
    const p = plan(changes);
    assert.equal(p.verifiedForReview,false);
    assert.equal(p.authorityVerified,false);
    assert.equal(p.registrationAuthorized,false);
    assert(p.blockers.some(x=>x.includes(needle)),JSON.stringify(p.blockers));
}
const good = plan({});
assert.equal(good.verifiedForReview,true);
assert.equal(good.candidateSelectable,true);
assert.equal(good.branch,"feature/one");
assert.equal(good.repository,"owner/repo");
assert.equal(good.head,evidence.head);
assert.equal(good.providerLaunched,false);
assert.equal(good.sessionCreated,false);
assert.equal(good.registrationAuthorized,false);
assert.deepEqual(Array.from(good.wouldChange),["Room.branch","Room.bedPath"]);
assert.equal(ctx.repository("git@github.com:owner/repo.git"),"owner/repo");
assert.equal(ctx.repository("https://github.com/owner/repo"),"owner/repo");
assert.equal(ctx.repository("ssh://git@github.com/owner/repo.git"),"owner/repo");
assert.equal(ctx.repository("https://evil.example.com/owner/repo"),"");
assert.equal(ctx.repository("https://github.com.evil.com/owner/repo"),"");
assert.equal(ctx.repository("bad/path/third"),"");
held({evidenceChecked:false},"Fresh local Git verification");
held({evidenceBusy:true},"Fresh local Git verification");
held({evidence:{...evidence,path:"/tmp/other"}},"Fresh local Git verification");
held({evidence:{...evidence,topLevel:"/tmp/other"}},"Fresh local Git verification");
held({evidence:{...evidence,origin:"git@github.com:other/repo.git"}},"Fresh local Git verification");
held({evidence:{...evidence,branch:"other"}},"Fresh local Git verification");
held({evidence:{...evidence,head:"not-a-sha"}},"Fresh local Git verification");
held({evidence:{...evidence,clean:false}},"Fresh local Git verification");
held({bedsDiscovering:true},"discovery still running");
held({roomsLoaded:false},"registry not verified");
held({rooms:[room,{...room}]},"exactly one registered Room");
held({room:{...room,repository:"other/repo"}},"clean Bed from this Patient");
held({room:{...room,branch:"other"}},"already has a registered Git Bed");
held({room:{...room,bedPath:"/old"}},"already has a registered Git Bed");
held({room:{...room,doctorId:"worker-a"}},"already staffed");
held({room:{...room,providerId:"codex"}},"already staffed");
held({sessions:[{id:"s1",roomId:"room-first",status:"COMPLETE"}]},"Session history");
held({beds:[{...bed,isLive:true}]},"clean Bed from this Patient");
held({beds:[{...bed,worktree:"DIRTY • 2 CHANGES"}]},"clean Bed from this Patient");
held({beds:[{...bed,origin:"git@github.com:other/repo.git"}]},"clean Bed from this Patient");
held({beds:[{...bed,branch:"DETACHED"}]},"clean Bed from this Patient");
held({rooms:[room,{id:"other",bedPath:bed.path}]},"clean Bed from this Patient");
held({selectedPath:"/other"},"clean Bed from this Patient");
assert.equal(plan({beds:[bed,{...bed}]}).verifiedForReview,true);
assert.equal(ctx.candidateRows({...base,beds:[bed,{...bed}]}).length,1);
console.log("HOSPITAL FIRST BED VERIFICATION // PASS // "+checks+" fixture scenarios, no registration authority");
