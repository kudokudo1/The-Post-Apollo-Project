#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ctx = vm.createContext({});
const source = fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalRoomContinuityPolicy.js"),"utf8");
vm.runInContext(source, ctx);

const room = {id:"ROOM-A",patientId:"PAT-A",repository:"org/project",
    branch:"feature/a",assignmentId:"41"};
const assignment = {id:"41",roomId:"ROOM-A",title:"Map work",
    status:"ACTIVE",phase:"TEST",goal:"Finish map",
    checklist:"- [x] Implement\n- [ ] Test\n* [X] Review\ntext only",
    openQuestions:"Do we accept zoom 18?"};
const handoff = {id:"1",roomId:"ROOM-A",kind:"HANDOFF",body:"Last safe checkpoint"};
const note = {id:"2",roomId:"ROOM-A",kind:"DOCTOR_NOTE",body:"Later ordinary report"};
const snapshot = {
    room,assignments:[assignment],checkpoints:[
        {id:"1",roomId:"ROOM-A",kind:"PROGRESS",body:"Initial"},
        {id:"2",roomId:"ROOM-A",kind:"VERIFY",body:"Verified terminal rendering"}],
    reports:[handoff,note],
    roomChart:[
        {id:"3",roomId:"ROOM-A",scope:"ROOM",authorRole:"operator",
         status:"ACTIVE",kind:"DECISION",title:"Use vector map",body:"Approval"},
        {id:"4",roomId:"ROOM-A",scope:"ROOM",authorRole:"doctor",
         status:"ACTIVE",kind:"DRAFT",title:"Not approved"}],
    patientChart:[{id:"8",patientId:"PAT-A",scope:"PATIENT",
        authorRole:"operator",status:"ACTIVE",kind:"DECISION",title:"Brand palette"}]
};
const base = {roomId:"ROOM-A",loaded:true,snapshot,sessionsLoaded:true,sessions:[]};
const p = ctx.project(base);
assert.equal(p.verified,true);
assert.equal(p.repository,"org/project");
assert.equal(p.assignment.id,"41");
assert.equal(p.progress.total,3);
assert.equal(p.progress.done,2);
assert.equal(p.progress.percent,67);
assert.match(p.progress.evidence,/NOT VERIFIED COMPLETION/);
assert.equal(p.checkpoint.id,"2");
assert.equal(p.handoff.id,"1");
assert.equal(p.report.id,"2");
assert.deepEqual(Array.from(p.decisions,v=>v.id),["3","8"]);
assert.equal(p.next.source,"ASSIGNMENT // OPEN QUESTIONS");
assert.equal(p.next.body,"Do we accept zoom 18?");
assert.match(p.recovery.label,/ROOM PERSISTS/);
assert.match(p.claim,/NO PROVIDER HEARTBEAT/);
assert.equal(ctx.project({...base,loaded:false}).verified,false);
assert.equal(ctx.project({...base,roomId:"ROOM-B"}).verified,false);
assert.equal(ctx.project({...base,loaded:true,snapshot:{...snapshot,room:{...room,id:"WRONG"}}}).verified,false);
assert.equal(ctx.project({...base,sessionsLoaded:false}).recovery.label,"SESSION DATA UNVERIFIED");
assert.equal(ctx.project({...base,snapshot:{...snapshot,room:{...room,assignmentId:"42"}}}).assignment,null);
const checklistOnly={...assignment,openQuestions:""};
const unchecked=ctx.project({...base,snapshot:{...snapshot,assignments:[checklistOnly]}});
assert.match(unchecked.next.source,/UNCHECKED/);
assert.equal(unchecked.next.body,"Test");
const handoffNext=ctx.project({...base,snapshot:{...snapshot,
    assignments:[{...checklistOnly,checklist:"- [x] Done"}]}});
assert.match(handoffNext.next.source,/HANDOFF/);
assert.equal(handoffNext.next.body,"Last safe checkpoint");
assert.equal(ctx.checklist("No structured work").percent,null);
assert.equal(ctx.checklist("").total,0);
assert.match(ctx.excerpt("Z".repeat(110),60),/PREVIEW TRUNCATED/);
function checkRecovery(sessions, label) {
    const plan=ctx.project({...base,sessions});
    assert.match(plan.recovery.label,label);
}
checkRecovery([{roomId:"ROOM-A",status:"FAILED",lastError:"timeout",
    endedAt:"2026-11-08"}],/LAST SESSION FAILED/);
checkRecovery([{roomId:"ROOM-A",status:"IDLE"}],/SESSION REGISTERED/);
checkRecovery([{roomId:"ROOM-A",status:"WAITING",lastExitCode:0}],/PRIOR TURN COMPLETE/);
checkRecovery([{roomId:"ROOM-A",status:"WAITING",lastExitCode:3}],/OUTCOME UNVERIFIED/);
checkRecovery([{roomId:"ROOM-A",status:"PAUSED"}],/PAUSED/);
checkRecovery([{roomId:"ROOM-A",status:"REVIEW"}],/REVIEW/);
checkRecovery([{roomId:"ROOM-A",status:"OPERATING",activePid:991}],/OPERATING RECORDED/);
checkRecovery([{roomId:"ROOM-A",status:"IDLE"},{roomId:"ROOM-A",status:"WAITING"}],/COLLISION/);
checkRecovery([{roomId:"ROOM-A",status:"FAILED",endedAt:"yesterday",activePid:99}],/OPERATING RECORDED/);
checkRecovery([{roomId:"FOREIGN",status:"FAILED"}],/ROOM PERSISTS/);
assert.equal(ctx.project({...base,snapshot:{...snapshot,assignments:[],
    reports:[],checkpoints:[],roomChart:[],patientChart:[]}}).next.source,
    "NO RECORDED NEXT ACTION");
console.log("HOSPITAL ROOM CONTINUITY POLICY // PASS // durable work evidence, no fabricated progress, cautious recovery and isolated Patient/Room decisions");
