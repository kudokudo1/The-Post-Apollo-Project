#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const filename = path.join(__dirname, "../../services/time/MachineSelectionPolicy.js");
const code = fs.readFileSync(filename, "utf8").replace(/^\.pragma library\s*/m, "");
const p = vm.createContext({});
vm.runInContext(code, p, {filename: "MachineSelectionPolicy.js"});

const preview = {
  preview_only: true, kind: "sway-layout-metadata-preview",
  outputs: [
    {connector: "DP-5", rect: {x: 0, y: 0, width: 2560, height: 1440}},
    {connector: "HDMI-A-1", rect: {x: 2560, y: 0, width: 1360, height: 768}}
  ],
  workspaces: [{name: "1", output: "DP-5"}, {name: "2", output: "HDMI-A-1"}],
  windows: [
    {app_id: "brave", workspace: "1", floating: false},
    {app_id: "brave", workspace: "1", floating: false},
    {app_id: "kitty", workspace: "2", floating: true}
  ]
};
const original = JSON.stringify(preview);
assert.equal(p.validate(preview, {}).status, "ready");
assert.equal(p.validate(preview, {}).included.windows, 3);
assert.equal(p.validate(null, {}).status, "no_capture");
assert.equal(p.validate(preview, {"windows:1": true}).included.windows, 2);
let result = p.validate(preview, {"outputs:0": true});
assert.equal(result.status, "blocked");
assert.equal(result.issues[0].kind, "workspaces");
assert.equal(result.issues[0].index, 0);
assert.equal(result.issues[0].code, "output_excluded");
result = p.validate(preview, {"workspaces:0": true});
assert.equal(result.status, "blocked");
assert.equal(result.issueCount, 2);
assert.equal(result.issues[0].code, "workspace_excluded");
assert.equal(p.validate(preview, {"outputs:0": true, "workspaces:0": true,
  "windows:0": true, "windows:1": true}).status, "ready");
assert.equal(p.validate(preview, {"outputs:0": true, "outputs:1": true}).status, "blocked");
const missingOutput = JSON.parse(JSON.stringify(preview));
missingOutput.workspaces[1].output = "absent";
assert.equal(p.validate(missingOutput, {}).issues[0].code, "output_missing");
const missingWorkspace = JSON.parse(JSON.stringify(preview));
missingWorkspace.windows[2].workspace = "absent";
assert.equal(p.validate(missingWorkspace, {}).issues[0].code, "workspace_missing");
const duplicateOutput = JSON.parse(JSON.stringify(preview));
duplicateOutput.outputs[1].connector = "DP-5";
assert.equal(p.validate(duplicateOutput, {}).issues[0].code, "duplicate_output");
const duplicateWorkspace = JSON.parse(JSON.stringify(preview));
duplicateWorkspace.workspaces[1].name = "1";
assert.equal(p.validate(duplicateWorkspace, {}).issues[0].code, "duplicate_workspace");
const invalid = JSON.parse(JSON.stringify(preview));
invalid.windows[0].app_id = "private\n";
assert.equal(p.validate(invalid, {}).reason, "INVALID PREVIEW");
assert.equal(p.validate({...preview, kind: "other"}, {}).reason, "INVALID PREVIEW");
assert.equal(p.validate({...preview, outputs: Array(17).fill(preview.outputs[0])}, {}).reason,
             "INVALID PREVIEW");
assert.equal(JSON.stringify(preview), original); // no input mutation
const large = JSON.parse(JSON.stringify(preview));
large.windows = Array.from({length: 50}, () =>
  ({app_id: "kitty", workspace: "absent", floating: false}));
result = p.validate(large, {});
assert.equal(result.issueCount, 50);
assert.equal(result.issues.length, p.MAX_ISSUES);
console.log("TIMEW MACHINE SELECTION POLICY: PASS / NO CASCADE / NO WRITES");
