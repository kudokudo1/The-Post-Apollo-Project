#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const dir = path.resolve(__dirname, "../../services/time");
const diffCode = fs.readFileSync(path.join(dir, "MachineLayoutDiffPolicy.js"), "utf8")
                   .replace(/^\.pragma library\s*/m, "");
const Diff = vm.createContext({});
vm.runInContext(diffCode, Diff, {filename:"MachineLayoutDiffPolicy.js"});
const restoreSource = fs.readFileSync(path.join(dir,"MachineRestorePreviewPolicy.js"),"utf8");
assert.match(restoreSource, /\.import "MachineLayoutDiffPolicy.js" as Diff/);
const restoreCode = restoreSource.replace(/^\.(pragma|import).*$/gm, "");
const P = vm.createContext({Diff});
vm.runInContext(restoreCode, P, {filename:"MachineRestorePreviewPolicy.js"});

const saved = {
    kind:"sway-layout-selection-preview",preview_only:true,
    outputs:[{connector:"DP-5",rect:{x:0,y:0,width:2560,height:1440}}],
    workspaces:[{name:"1",output:"DP-5"}],
    windows:[{app_id:"brave",workspace:"1",floating:false},
             {app_id:"kitty",workspace:"1",floating:true}]
};
const live = JSON.parse(JSON.stringify(saved));
live.kind = "sway-layout-metadata-preview";
const snapshot = JSON.stringify(saved);
const liveSnapshot = JSON.stringify(live);
const clone = x => JSON.parse(JSON.stringify(x));
let p=P.plan(saved,live);
assert.equal(p.status,"aligned");
assert.equal(p.executable,false);
assert.equal(p.preview_only,true);
assert.equal(p.kind,"machine-restore-plan-preview");
assert.equal(p.counts.aligned,4);
assert.equal(p.totalItems,0);
assert.equal(p.items.length,0);
assert.equal(P.plan(saved,null).status,"unavailable");
assert.equal(P.plan(null,live).status,"unavailable");

let g=clone(live);
g.outputs[0].rect.width=1920;
p=P.plan(saved,g);
assert.equal(p.status,"review");
assert.equal(p.items[0].code,"geometry_review");
assert.equal(p.items[0].category,"manual");

g=clone(live);
g.outputs=[];g.workspaces=[];g.windows=[];
p=P.plan(saved,g);
assert.equal(p.status,"blocked");
assert.equal(p.counts.blocked,4);
assert.equal(p.items[0].code,"missing_output");
assert.equal(p.items[1].code,"workspace_output_missing");
assert.equal(p.items[2].code,"window_workspace_unavailable");

g=clone(live);
g.workspaces=[];g.windows=[];
p=P.plan(saved,g);
assert.equal(p.status,"review");
assert.ok(p.items.some(x=>x.code==="workspace_absent"));
assert.ok(p.items.some(x=>x.code==="window_not_observed"));

g=clone(live);
g.outputs.push({connector:"HDMI-A-1",rect:{x:2560,y:0,width:1360,height:768}});
g.workspaces[0].output="HDMI-A-1";
p=P.plan(saved,g);
assert.equal(p.status,"review");
assert.equal(p.items[0].code,"workspace_reassignment");

g=clone(live);g.windows=[];
p=P.plan(saved,g);
assert.equal(p.items.filter(x=>x.code==="window_not_observed").length,2);

g=clone(live);
g.windows=[{app_id:"brave",workspace:"1",floating:true}];
p=P.plan(saved,g);
assert.equal(p.status,"review");
assert.equal(p.items[0].code,"possible_window_reuse");
assert.equal(p.items[0].category,"ambiguous");

g=clone(live);
g.windows.push({app_id:"brave",workspace:"1",floating:false});
p=P.plan(saved,g);
assert.equal(p.status,"review");
assert.equal(p.items[0].code,"duplicate_window_candidates");
assert.equal(p.items[0].category,"ambiguous");

const two=clone(saved);
two.windows.push({app_id:"brave",workspace:"1",floating:false});
g=clone(live);
p=P.plan(two,g);
assert.equal(p.counts.ambiguous,2);
assert.equal(p.items[0].code,"duplicate_window_candidates");
assert.equal(p.items[1].code,"possible_window_reuse");

g=clone(live);
g.windows[0].app_id="private\n";
assert.equal(P.plan(saved,g).status,"unavailable");
g=clone(live);
g.workspaces.push({name:"1",output:"DP-5"});
assert.equal(P.plan(saved,g).status,"unavailable");

const lots=clone(saved);
lots.windows=Array.from({length:51},(_,i)=>({app_id:"app"+i,workspace:"1",floating:false}));
g=clone(live);g.windows=[];
p=P.plan(lots,g);
assert.equal(p.counts.manual,51);
assert.equal(p.totalItems,51);
assert.equal(p.items.length,P.MAX_PLAN_ITEMS);
assert.equal(p.truncated,true);
assert.equal(JSON.stringify(saved),snapshot);
assert.equal(JSON.stringify(live),liveSnapshot);
assert.ok(!restoreSource.includes("swaymsg"));
assert.ok(!restoreSource.includes("execDetached"));
assert.ok(!restoreSource.includes("Process {"));
assert.ok(!restoreSource.includes("FileView {"));
console.log("TIMEW MACHINE M1I: RESTORE PREVIEW POLICY PASS / NO APPLY");
