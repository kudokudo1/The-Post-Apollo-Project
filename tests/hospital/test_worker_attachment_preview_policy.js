#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,
  "../../services/hospital/HospitalWorkerAttachmentPreviewPolicy.js"), "utf8");
const policy = vm.createContext({});
vm.runInContext(source, policy);

const room = {
  roomId:"room-map", patientId:"patient-company",
  repository:"owner/company", branch:"work/map",
  bedPath:"/synthetic/map-bed",
  roomDoctorId:"doc-7", roomProviderId:"codex",
  assignmentId:"43"
};
const assignment = {
  id:"43", roomId:"room-map", patientId:"patient-company",
  title:"Build Company Map", goal:"Integrate map", status:"ACTIVE"
};
const doctor = {id:"doc-7", name:"Map Doctor", status:"ACTIVE"};
const provider = {id:"codex", name:"Codex", available:true};
const base = {
  room, assignments:[assignment], doctors:[doctor],
  providers:[provider], sessions:[], rooms:[{id:"room-map",bedPath:room.bedPath}],
  assignmentId:"43", doctorId:"doc-7", providerId:"codex",
  roomsLoaded:true, sessionsLoaded:true, assignmentsLoaded:true,
  doctorsLoaded:true, providersLoaded:true, loadError:""
};
const run = overrides => policy.plan({...base,...overrides});
function blocked(overrides, expected) {
  const p = run(overrides);
  assert.equal(p.reviewable,false);
  assert.equal(p.mutationAuthorized,false);
  assert(p.blockers.some(x => x.includes(expected)), JSON.stringify(p.blockers));
  return p;
}
const good = run({});
assert.equal(good.reviewable,true);
assert.equal(good.sessionMode,"NEW_SESSION_REVIEW");
assert.equal(good.mutationAuthorized,false);
assert.equal(good.source,"READ-ONLY PX REGISTRY PREVIEW");
assert.equal(good.headline,"PREVIEW CONSISTENT // NOT ATTACHED");
assert.equal(good.roomId,"room-map");
assert.equal(good.facts.length,8);
blocked({room:{...room,roomId:""}}, "No registered Room");
blocked({room:{...room,patientId:""}}, "Patient identity");
blocked({room:{...room,branch:""}}, "branch");
blocked({room:{...room,bedPath:""}}, "Bed");
blocked({roomsLoaded:false}, "snapshot");
blocked({sessionsLoaded:false}, "snapshot");
blocked({assignmentsLoaded:false}, "not been verified");
blocked({doctorsLoaded:false}, "directory");
blocked({providersLoaded:false}, "directory");
blocked({loadError:"PX FAIL"}, "PX read failed");
blocked({assignmentId:"unknown"}, "existing Assignment");
blocked({assignments:[{...assignment,roomId:"different-room"}]}, "another Room");
blocked({assignments:[{...assignment,patientId:"other"}]}, "Patient differs");
blocked({assignments:[{...assignment,status:"READY"}]}, "not ACTIVE");
blocked({room:{...room,assignmentId:"44"}}, "links another Assignment");
blocked({doctorId:"other"}, "existing Doctor");
blocked({doctors:[{...doctor,status:"INACTIVE"}]}, "not ACTIVE");
blocked({room:{...room,roomDoctorId:"another-doctor"}}, "staffing approval");
blocked({providers:[{...provider,available:false}]}, "not reported available");
blocked({providerId:"not-registered"}, "registered PX Provider");
blocked({room:{...room,roomProviderId:"hermes"}}, "staffing approval");
blocked({providers:[{id:"int1-fake",available:true}],
  providerId:"int1-fake"}, "Fake-only");
const session = {
  id:"px-1",roomId:"room-map",doctorId:"doc-7",providerId:"codex",
  workingDirectory:"/synthetic/map-bed",status:"IDLE",activePid:0
};
const reuse=run({sessions:[session]});
assert.equal(reuse.reviewable,true);
assert.equal(reuse.sessionMode,"REUSE_SESSION_REVIEW");
assert.equal(reuse.sessionId,"px-1");
blocked({sessions:[session,{...session,id:"px-2"}]}, "Multiple nonterminal");
blocked({sessions:[{...session,doctorId:"other"}]}, "Session Doctor");
blocked({sessions:[{...session,providerId:"hermes"}]}, "Session Provider");
blocked({sessions:[{...session,workingDirectory:"/another"}]}, "working directory");
blocked({sessions:[{...session,status:"REVIEW"}]}, "not IDLE");
blocked({sessions:[{...session,activePid:45}]}, "active process");
const historical=run({sessions:[{...session,status:"COMPLETE",endedAt:"yesterday"}]});
assert.equal(historical.sessionMode,"NEW_SESSION_REVIEW");
assert.equal(historical.reviewable,true);
const terminalPid = run({sessions:[{
  ...session,status:"FAILED",endedAt:"yesterday",activePid:12345
}]});
assert.equal(terminalPid.reviewable,false);
assert.equal(terminalPid.sessionMode,"REUSE_SESSION_REVIEW");
assert(terminalPid.blockers.some(x => x.includes("not IDLE")));
const terminalPidOtherRoom = run({
  rooms:[{id:"room-map",bedPath:room.bedPath},
         {id:"room-other",bedPath:room.bedPath}],
  sessions:[{...session,id:"old-pid",roomId:"room-other",
             status:"FAILED",endedAt:"yesterday",activePid:12345}]
});
assert.equal(terminalPidOtherRoom.reviewable,false);
assert(terminalPidOtherRoom.blockers.some(x => x.includes("Another Room")));

blocked({
  rooms:[{id:"room-map",bedPath:room.bedPath},{id:"room-other",bedPath:room.bedPath}],
  sessions:[{...session,id:"foreign",roomId:"room-other"}]
},"Another Room has an open Session");
const independent=run({
  rooms:[{id:"room-map",bedPath:room.bedPath},{id:"room-other",bedPath:"/other"}],
  sessions:[{...session,id:"foreign",roomId:"room-other"}]
});
assert.equal(independent.reviewable,true);
assert.equal(policy.plan({}).mutationAuthorized,false);
console.log("HOSPITAL ATTACHMENT PREVIEW // PASS // exact identities, provider registry, Assignment ownership, concurrent Sessions and Beds, no writes");
