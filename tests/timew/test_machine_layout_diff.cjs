#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const filename = path.join(__dirname, "../../services/time/MachineLayoutDiffPolicy.js");
const src = fs.readFileSync(filename, "utf8").replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(src, policy, {filename});
const saved = {
  preview_only: true, kind: "sway-layout-selection-preview",
  outputs: [{connector:"DP-5",rect:{x:0,y:0,width:2560,height:1440}}],
  workspaces:[{name:"1",output:"DP-5"}],
  windows:[
    {app_id:"brave",workspace:"1",floating:false},
    {app_id:"brave",workspace:"1",floating:false},
    {app_id:"kitty",workspace:"1",floating:true}
  ]
};
const current = JSON.parse(JSON.stringify(saved));
current.kind = "sway-layout-metadata-preview";
const srcBefore=JSON.stringify(saved);
const currentBefore=JSON.stringify(current);
let x=policy.compare(saved,current);
assert.equal(x.status,"match");
assert.equal(x.differenceCount,0);
assert.equal(x.differences.length,0);
assert.equal(policy.compare(null,current).status,"unavailable");
assert.equal(policy.compare(saved,null).status,"unavailable");
const missingMonitor=JSON.parse(JSON.stringify(current));
missingMonitor.outputs=[];
assert.equal(policy.compare(saved,missingMonitor).status,"unavailable"); // orphan dependency
const newMonitor=JSON.parse(JSON.stringify(current));
newMonitor.outputs.push({connector:"HDMI-A-1",rect:{x:2560,y:0,width:1360,height:768}});
x=policy.compare(saved,newMonitor);
assert.equal(x.status,"changed");
assert.equal(x.differences[0].label,"NEW MONITOR // HDMI-A-1");
const geometry=JSON.parse(JSON.stringify(current));
geometry.outputs[0].rect.width=1920;
assert.equal(policy.compare(saved,geometry).differences[0].code,"geometry");
const moved=JSON.parse(JSON.stringify(current));
moved.outputs.push({connector:"HDMI-A-1",rect:{x:2560,y:0,width:1360,height:768}});
moved.workspaces[0].output="HDMI-A-1";
assert.equal(policy.compare(saved,moved).differences.filter(t=>t.code==="moved").length,1);
const missingWindow=JSON.parse(JSON.stringify(current));
missingWindow.windows.splice(1,1);
x=policy.compare(saved,missingWindow);
assert.equal(x.counts.windows,1);
assert.match(x.differences[0].label,/MISSING 1 \/\/ brave @ 1/);
const extra=JSON.parse(JSON.stringify(current));
extra.windows.push({app_id:"kitty",workspace:"1",floating:true});
assert.match(policy.compare(saved,extra).differences[0].label,/ADDITIONAL 1 \/\/ kitty/);
const extraWorkspace=JSON.parse(JSON.stringify(current));
extraWorkspace.workspaces.push({name:"2",output:"DP-5"});
assert.equal(policy.compare(saved,extraWorkspace).counts.workspaces,1);
const invalidTitle=JSON.parse(JSON.stringify(current));
invalidTitle.windows[0].app_id="private\n";
assert.equal(policy.compare(saved,invalidTitle).status,"unavailable");
const invalidDuplicate=JSON.parse(JSON.stringify(current));
invalidDuplicate.workspaces.push({name:"1",output:"DP-5"});
assert.equal(policy.compare(saved,invalidDuplicate).status,"unavailable");
const many=JSON.parse(JSON.stringify(current));
many.windows=[];
for (let i=0;i<50;i++) many.windows.push({app_id:"app"+i,workspace:"1",floating:false});
x=policy.compare(saved,many);
assert.equal(x.status,"changed");
assert.ok(x.differenceCount > policy.MAX_DELTAS);
assert.equal(x.differences.length,policy.MAX_DELTAS);
assert.equal(x.truncated,true);
assert.equal(JSON.stringify(saved),srcBefore);
assert.equal(JSON.stringify(current),currentBefore);
const ownerKeys=JSON.parse(JSON.stringify(current));
ownerKeys.outputs[0].connector="__proto__";
ownerKeys.workspaces[0].output="__proto__";
assert.equal(policy.compare(saved,ownerKeys).status,"changed");
console.log("TIMEW MACHINE LAYOUT DIFF: PASS / MULTISET / BOUNDED / READ ONLY");
