#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalRoomSuccessorPreviewPolicy.js"), "utf8"), ctx);

const room = {id:"room-map",patientId:"patient-main",
    repository:"org/main",branch:"feature/map",bedPath:"/tmp/map-bed",
    doctorId:"doctor-old",providerId:"mock",assignmentId:"42"};
const assignment = {id:"42",roomId:"room-map",status:"ACTIVE",title:"Map integration",
    phase:"VERIFICATION",goal:"Ship map",openQuestions:"Approve map clipping"};
const overview = {
    verified:true,roomId:"room-map",repository:"org/main",
    assignment,checkpoint:{id:"5",body:"Verified map startup"},
    handoff:{id:"6",kind:"HANDOFF",body:"Preserve layout and current branch"},
    decisions:[{id:"10",title:"Retain vector map",body:"Operator approved"}],
    next:{body:"Verify overlay"}};
const doctors=[{id:"doctor-old",status:"ACTIVE",name:"Original"},
    {id:"doctor-new",status:"ACTIVE",name:"Replacement"}];
const providers=[{id:"mock",available:true,name:"Mock"},
    {id:"hermes",available:true,name:"Hermes"}];
const snap = {room};
const base = {
    roomId:"room-map",overview,snapshot:snap,roomData:{roomDoctorId:"doctor-old"},
    doctors,providers,rooms:[room],sessions:[],
    doctorId:"doctor-new",providerId:"hermes",
    doctorsLoaded:true,providersLoaded:true,roomsLoaded:true,sessionsLoaded:true,
    sourceError:""
};
const run = changes=>ctx.preview({...base,...changes});
const good=run({});
assert.equal(good.contextAvailable,true);
assert.equal(good.previewable,true);
assert.equal(good.mutationAuthorized,false);
assert.equal(good.operatorApprovalRequired,true);
assert.equal(good.previousDoctorId,"doctor-old");
assert.equal(good.successorDoctorId,"doctor-new");
assert.equal(good.assignmentId,"42");
assert.match(good.status,/TRANSFER PENDING/);
assert(good.actions.some(x=>x.includes("Atomically create a fresh Session")));
assert(good.actions.some(x=>x.includes("Doctor/Session release")));
assert.match(good.disclaimer,/NO NEW SESSION/);
const brief=ctx.briefing(base);
assert.match(brief,/ROOM \/\/ room-map/);
assert.match(brief,/ASSIGNMENT \/\/ #42/);
assert.match(brief,/LAST HANDOFF \/\/ #6/);
assert.match(brief,/APPROVED DECISIONS \/\/ 1/);
assert.match(brief,/FULL CONTEXT MUST BE REBUILT/);
assert(!brief.includes("HOSPITAL-CONNECTED"));
function denied(changes,phrase) {
    const p=run(changes);
    assert.equal(p.previewable,false,JSON.stringify(changes));
    assert.equal(p.mutationAuthorized,false);
    assert(p.blockers.some(b=>b.includes(phrase)),
        JSON.stringify(p.blockers)+" expected "+phrase);
    return p;
}
denied({roomId:"other"},"pinned persistent Room");
denied({overview:{...overview,verified:false}},"pinned persistent Room");
denied({snapshot:{room:{...room,doctorId:"doctor-other"}}},"identity differs");
denied({snapshot:{room:{...room,patientId:""}}},"Room Patient");
denied({snapshot:{room:{...room,bedPath:""}}},"Room Patient");
denied({snapshot:{room:{...room,assignmentId:"99"}}},"linked ACTIVE Assignment");
denied({overview:{...overview,assignment:{...assignment,status:"PAUSED"}}},"linked ACTIVE Assignment");
denied({sessionsLoaded:false},"Session registry");
denied({roomsLoaded:false},"Room registry");
denied({doctorsLoaded:false},"directories");
denied({providersLoaded:false},"directories");
denied({sourceError:"PX unavailable"},"source error");
denied({doctorId:"missing"},"existing registered successor");
denied({doctorId:"doctor-old"},"different Doctor");
denied({doctors:[{...doctors[1],status:"INACTIVE"}]},"not ACTIVE");
denied({providerId:"missing"},"registered PX Provider");
denied({providers:[{...providers[1],available:false}]},"not listed as available");
denied({providerId:"int1-fake"},"Synthetic-only");
denied({sessions:[{id:"px-room",roomId:"room-map",status:"IDLE"}]},"still claims this Room");
denied({sessions:[{id:"px-room",roomId:"room-map",status:"OPERATING",activePid:555}]},"active/operating");
denied({sessions:[{id:"one",roomId:"room-map",status:"WAITING"},
                  {id:"two",roomId:"room-map",status:"PAUSED"}]},"Multiple nonterminal");
denied({rooms:[room,{id:"other-room",bedPath:"/tmp/map-bed"}],
    sessions:[{id:"x",roomId:"other-room",status:"IDLE"}]},"same recorded Bed");
denied({sessions:[{id:"x",roomId:"other-room",status:"IDLE",doctorId:"doctor-new"}]},
    "open Session in another Room");
const terminal=run({sessions:[{id:"former",roomId:"room-map",
    status:"FAILED",endedAt:"2026-11-08",activePid:0}]});
assert.equal(terminal.previewable,true);
denied({sessions:[{id:"former",roomId:"room-map",
    status:"FAILED",endedAt:"2026-11-08",activePid:121}]},"active/operating");
const missingHandoff=run({overview:{...overview,handoff:null}});
assert.equal(missingHandoff.previewable,true);
assert(missingHandoff.warnings.some(x=>x.includes("no explicit HANDOFF")));
assert.match(ctx.briefing({...base,overview:{...overview,handoff:null}}),/MISSING/);
denied({overview:{...overview,handoff:null,checkpoint:null}},
    "No checkpoint or HANDOFF");
assert.match(ctx.briefing({...base,overview:{...overview,verified:false}}),
    /BRIEFING UNAVAILABLE/);
assert.equal(run({sourceError:"outdated"}).mutationAuthorized,false);
console.log("HOSPITAL SUCCESSOR PREFLIGHT // PASS // scoped work and ownership, no auto-succession, blocked collisions and read-only handoff context");
