#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalWorkforceJobActivationPolicy.js"), "utf8");
const ctx = vm.createContext({});
vm.runInContext(source, ctx);

const draft = {id:"17",roomId:"room-A",status:"DRAFT",title:"Read-only source audit",
    goal:"Inspect selected files",permissions:["READ"]};
const room = {id:"room-A",repository:"owner/repo",assignmentId:""};
const baseline = {
    roomId:"room-A",assignmentId:"17",rooms:[room],
    sessions:[],assignments:[draft],roomsLoaded:true,sessionsLoaded:true,
    assignmentsLoaded:true,assignmentsLoading:false,
    assignmentError:"",registryError:""
};
let checks=0;
function valid(change) {checks++;return ctx.review({...baseline,...change});}
function held(change,message) {
    const r=valid(change);
    assert.equal(r.ready,false);
    assert.equal(r.mutationAuthorized,false);
    assert(r.blockers.some(s=>s.includes(message)),String(message)+" => "+JSON.stringify(r.blockers));
}
const v=valid({});
assert.equal(v.ready,true);
assert.equal(v.assignmentId,"17");
assert.equal(v.roomId,"room-A");
assert.equal(v.status,"DRAFT");
assert.equal(v.launchesProvider,false);
assert.equal(v.createsSession,false);
assert.equal(v.mutationAuthorized,false);
assert.equal(v.authorityVerified,false);
assert.deepEqual(Array.from(v.permissions),["READ"]);
held({roomsLoaded:false},"registry not verified");
held({sessionsLoaded:false},"registry not verified");
held({assignmentsLoaded:false},"list not verified");
held({assignmentsLoading:true},"list not verified");
held({registryError:"PX unavailable"},"reported an error");
held({assignmentError:"PX unavailable"},"reported an error");
held({roomId:"room-B"},"registered Room");
held({rooms:[room,{...room}]},"registered Room");
held({rooms:[{...room,assignmentId:"99"}]},"already has an active Assignment");
held({assignments:[draft,{...draft,id:"18",status:"ACTIVE"}]},"Another ACTIVE Assignment");
held({assignmentId:"18"},"saved Assignment");
held({assignments:[draft,{...draft,id:"17"}]},"saved Assignment");
held({assignments:[{...draft,roomId:"room-B"}]},"Foreign Room Assignment");
held({assignments:[{...draft,status:"READY"}]},"Only a saved DRAFT");
held({assignments:[{...draft,status:"COMPLETE"}]},"Only a saved DRAFT");
held({assignments:[{...draft,title:""}]},"missing its title or goal");
held({assignments:[{...draft,goal:""}]},"missing its title or goal");
held({assignments:[{...draft,permissions:["READ","EDIT"]}]},"requires READ-only");
held({assignments:[{...draft,permissions:["EDIT"]}]},"requires READ-only");
held({assignments:[{...draft,permissions:[]}]},"requires READ-only");
held({sessions:[{roomId:"room-A",status:"WAITING",activePid:0}]},"not explicitly released");
held({sessions:[{roomId:"room-A",status:"COMPLETE",activePid:0}]},"not explicitly released");
held({sessions:[{roomId:"room-A",status:"COMPLETE",endedAt:"today",activePid:16}]},"not explicitly released");
held({sessions:[{roomId:"room-A",status:"COMPLETE",endedAt:"today",activePid:"broken"}]},"not explicitly released");
assert.equal(valid({sessions:[{roomId:"room-A",status:"FAILED",endedAt:"today",activePid:0}]}).ready,true);
console.log("SURGERY FIRST-JOB ACTIVATION // PASS // " + checks + " cases, no AI execution");
