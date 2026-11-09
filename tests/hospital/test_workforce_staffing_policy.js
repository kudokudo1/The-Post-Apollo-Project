#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalWorkforceStaffingPolicy.js"), "utf8"), ctx);

let n = 0;
const room = {
    id:"room-a",patientId:"patient-a",repository:"owner/project",
    branch:"test/isolated",bedPath:"/tmp/px-disposable-a",
    assignmentId:"5",doctorId:"",providerId:""
};
const job = {
    id:"5",roomId:"room-a",patientId:"patient-a",
    status:"ACTIVE",title:"Inspect fixture",goal:"Read-only code search",
    permissions:["READ"]
};
const doctor = {id:"worker-a",name:"First Intern",role:"INT",status:"ACTIVE"};
const provider = {id:"codex",name:"Codex",available:true};
const base = {
    roomId:"room-a",doctorId:"worker-a",providerId:"codex",
    rooms:[room],sessions:[],doctors:[doctor],providers:[provider],
    assignments:[job],roomsLoaded:true,sessionsLoaded:true,
    doctorsLoaded:true,providersLoaded:true,assignmentsLoaded:true,
    assignmentsLoading:false,sourceError:""
};
function run(change) {n++;return ctx.plan({...base,...change});}
function held(change,fragment) {
    const result = run(change);
    assert.equal(result.readyForReview,false);
    assert.equal(result.authorizationVerified,false);
    assert.equal(result.mutationAuthorized,false);
    assert(result.blockers.some(s => s.includes(fragment)),
        "Expected " + fragment + " in " + JSON.stringify(result.blockers));
}
const initial=run({});
assert.equal(initial.readyForReview,true);
assert.equal(initial.needsStaffingWrite,true);
assert.equal(initial.readyForAttachmentReview,false);
assert.equal(initial.roomId,"room-a");
assert.equal(initial.assignmentId,"5");
assert.equal(initial.doctorName,"First Intern");
assert.equal(initial.doctorRole,"INT");
assert.equal(initial.providerName,"Codex");
assert.equal(initial.authorizationVerified,false);
assert.equal(initial.mutationAuthorized,false);
assert.equal(initial.providerLaunched,false);
assert.equal(initial.sessionCreated,false);
assert.match(initial.headline,/ATOMIC PX AUTHORITY REQUIRED/);
const matched=run({rooms:[{...room,doctorId:"worker-a",providerId:"codex"}]});
assert.equal(matched.readyForReview,true);
assert.equal(matched.needsStaffingWrite,false);
assert.equal(matched.readyForAttachmentReview,true);
assert.match(matched.headline,/ATTACHMENT PREVIEW REQUIRED/);

held({roomsLoaded:false},"registry not verified");
held({sessionsLoaded:false},"registry not verified");
held({doctorsLoaded:false},"directory not verified");
held({providersLoaded:false},"directory not verified");
held({assignmentsLoaded:false},"list not verified");
held({assignmentsLoading:true},"list not verified");
held({sourceError:"PX failed"},"PX registry error");
held({roomId:"room-other"},"Select one registered Room");
held({rooms:[room,{...room}]},"Select one registered Room");
held({rooms:[{...room,patientId:""}]},"Patient / repository identity missing");
held({rooms:[{...room,repository:""}]},"Patient / repository identity missing");
held({rooms:[{...room,branch:""}]},"Git branch or working Bed missing");
held({rooms:[{...room,bedPath:""}]},"Git branch or working Bed missing");
held({rooms:[{...room,assignmentId:""}]},"no ACTIVE Assignment");
held({assignments:[]},"has not been verified");
held({assignments:[job,{...job}]},"has not been verified");
held({assignments:[{...job,roomId:"room-b"}]},"another Room");
held({assignments:[{...job,patientId:"patient-b"}]},"Room / Patient ownership");
held({assignments:[{...job,status:"DRAFT"}]},"not ACTIVE");
held({assignments:[{...job,title:""}]},"lacks a title or goal");
held({assignments:[{...job,goal:""}]},"lacks a title or goal");
held({assignments:[{...job,permissions:["READ","EDIT"]}]},"requires an ACTIVE READ-only");
held({assignments:[{...job,permissions:["EDIT"]}]},"requires an ACTIVE READ-only");
held({assignments:[{...job,permissions:[]}]},"requires an ACTIVE READ-only");
held({doctorId:"missing"},"Select one registered Doctor");
held({doctors:[{...doctor,status:"RELEASED"}]},"not ACTIVE");
held({doctors:[doctor,{...doctor}]},"Select one registered Doctor");
held({providerId:"missing"},"Select one registered AI Provider");
held({providers:[{...provider,available:false}]},"not available");
held({providerId:"int1-fake",providers:[{...provider,id:"int1-fake"}]},
    "Fake-only Provider");
held({rooms:[{...room,doctorId:"someone-else"}]},"another Doctor");
held({rooms:[{...room,providerId:"hermes"}]},"different Provider");
held({rooms:[room,{...room,id:"room-b",doctorId:"worker-a",bedPath:"/tmp/other"}]},
    "already owns another");
held({rooms:[room,{...room,id:"room-b",doctorId:"",bedPath:room.bedPath}]},
    "already assigned to another Room");
held({sessions:[{roomId:"room-a",status:"IDLE",activePid:0}]},"not explicitly released");
held({sessions:[{roomId:"room-a",status:"FAILED",activePid:0}]},"not explicitly released");
held({sessions:[{roomId:"room-a",status:"ENDED",endedAt:"today",activePid:12}]},
    "not explicitly released");
held({sessions:[{roomId:"room-a",status:"ENDED",endedAt:"today",activePid:"invalid"}]},
    "not explicitly released");
held({sessions:[{roomId:"room-b",doctorId:"worker-a",status:"IDLE"}]},
    "unreleased Session elsewhere");
assert.equal(run({sessions:[{roomId:"room-a",status:"COMPLETE",
    endedAt:"today",activePid:0}]}).readyForReview,true);

console.log("HOSPITAL STAFFING READINESS // PASS // " + n
    + " fixture scenarios, all writes and provider launch disabled");
