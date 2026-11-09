#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const js = fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalWorkforceManagerPolicy.js"), "utf8");
const ctx = vm.createContext({});
vm.runInContext(js, ctx);

const original = {
    doctorsLoaded:true, roomsLoaded:true, sessionsLoaded:true,
    registryError:"", doctors:[{id:"existing",status:"ACTIVE"}],
    rooms:[{id:"room-old",doctorId:"existing",repository:"owner/repo"}],
    sessions:[]
};
function plan(fn, extra) { return ctx[fn]({...original,...extra}); }
function rejected(fn, extra, match) {
    const p = plan(fn, extra);
    assert.equal(p.ready, false, JSON.stringify(extra));
    assert.equal(p.mutationAuthorized, false);
    assert(p.blockers.some(x => x.includes(match)),
        "Expected blocker " + match + " in " + JSON.stringify(p.blockers));
}
const w = plan("worker",{id:"worker-abcd1234",name:"Finance Intern",role:"INT"});
assert.equal(w.ready,true);
assert.equal(w.mutationAuthorized,false);
assert.equal(w.createsSession,false);
assert.equal(w.launchesProvider,false);
assert.equal(w.role,"INT");
rejected("worker",{id:"existing",name:"Finance Intern",role:"DOC"},"ID already exists");
rejected("worker",{id:"worker-abcd1234",name:"",role:"INT"},"name is required");
rejected("worker",{id:"worker-abcd1234",name:"Finance",role:"HSG"},"INTERN, NURSE or DOCTOR");
rejected("worker",{id:"worker-abcd1234",name:"Finance",role:"DOC",doctorsLoaded:false},
    "directory has not loaded");
rejected("worker",{id:"worker-abcd1234",name:"Finance",role:"DOC",registryError:"PX error"},
    "registry returned an error");
rejected("worker",{id:"worker-abcd1234",name:"Finance",role:"DOC",sessionsLoaded:false},
    "registry not verified");

const room = plan("room",{id:"room-abcdef1234",name:"Finance Test Room",
    repository:"owner/repo"});
assert.equal(room.ready,true);
assert.equal(room.mutationAuthorized,false);
assert.equal(room.createsSession,false);
assert.equal(room.assignsDoctor,false);
assert.equal(room.branch,"");
assert.equal(room.bedPath,"");
assert.equal(room.patientId,"owner/repo");
assert.equal(room.patientLabel,"owner/repo");
const reusedPatient = plan("room",{
    id:"room-abcdef1234", name:"Another room", repository:"owner/repo",
    rooms:[{id:"room-old",repository:"owner/repo",
            patientId:"patient-keep",patientLabel:"Existing Patient"}]
});
assert.equal(reusedPatient.ready,true);
assert.equal(reusedPatient.patientId,"patient-keep");
assert.equal(reusedPatient.patientLabel,"Existing Patient");
rejected("room",{
    id:"room-abcdef1234",name:"Test",repository:"owner/repo",
    rooms:[
        {id:"r1",repository:"owner/repo",patientId:"patient-A"},
        {id:"r2",repository:"owner/repo",patientId:"patient-B"}
    ]
},"Patient ID ambiguous");
rejected("room",{id:"room-old",name:"Test",repository:"owner/repo"},"ID already exists");
rejected("room",{id:"room-abcdef1234",name:"Test",repository:"not-a-repository"},
    "owner/name");
rejected("room",{id:"room-abcdef1234",name:"",repository:"owner/repo"},
    "Room name");
rejected("room",{id:"room-abcdef1234",name:"Test",repository:"owner/repo",
    roomsLoaded:false},"registry not verified");

const retire = plan("retirement",{doctorId:"unassigned",
    doctors:[{id:"unassigned",status:"ACTIVE"}]});
assert.equal(retire.ready,true);
assert.equal(retire.mutationAuthorized,false);
assert.equal(retire.deletesHistory,false);
rejected("retirement",{doctorId:"existing"},"still owns a Room");
rejected("retirement",{doctorId:"unassigned",doctors:[{id:"unassigned",status:"ACTIVE"}],
    sessions:[{id:"s1",doctorId:"unassigned",status:"OPERATING",activePid:51}]},
    "unreleased Session");
rejected("retirement",{doctorId:"unassigned",
    doctors:[{id:"unassigned",status:"ACTIVE"}],
    sessions:[{id:"s1",doctorId:"unassigned",status:"COMPLETE",
        endedAt:"2026-11-08",activePid:123}]}, "recorded active process");
rejected("retirement",{doctorId:"unassigned",
    doctors:[{id:"unassigned",status:"ACTIVE"}],
    sessions:[{id:"s1",doctorId:"unassigned",status:"COMPLETE",
        activePid:0}]}, "unreleased Session");
rejected("retirement",{doctorId:"unassigned",doctors:[{id:"unassigned",status:"RELEASED"}]},
    "already released");
rejected("retirement",{doctorId:"no-such-doctor"},"Select a registered worker");

const job = plan("assignment",{roomId:"room-old",title:"Investigate",goal:"Find failures",
    permissions:"READ, TEST, TEST"});
assert.equal(job.ready,true);
assert.equal(job.mutationAuthorized,false);
assert.equal(job.activatesAssignment,false);
assert.deepEqual(Array.from(job.permissions),["READ","TEST"]);
rejected("assignment",{roomId:"unknown",title:"T",goal:"G",permissions:"READ"},
    "Choose a registered Room");
rejected("assignment",{roomId:"room-old",title:"T",goal:"",permissions:"READ"},
    "goal is required");
rejected("assignment",{roomId:"room-old",title:"T",goal:"G",permissions:"READ, GODMODE"},
    "Unknown permission");
assert.equal(plan("assignment",{roomId:"room-old",title:"A",goal:"B",
    permissions:"READ, OPEN_PR"}).ready,true);
console.log("SURGERY WORKFORCE PREFLIGHT // PASS // fail closed; no Session or implicit authority");
