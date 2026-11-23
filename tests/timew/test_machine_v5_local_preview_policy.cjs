#!/usr/bin/env node
"use strict";
// TimeW M5 non-authorizing display decoder: adversarial QML JS regression.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.join(__dirname, "../..");
const file = path.join(ROOT, "services/time/MachineV3LocalPreviewPolicy.js");
const source = fs.readFileSync(file, "utf8").replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(source, policy, {filename: "MachineV3LocalPreviewPolicy.js"});
let checks = 0;
function check(condition, label) {
  assert.ok(condition, label);
  checks += 1;
}
function clone(value) { return JSON.parse(JSON.stringify(value)); }

const cid = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const windowId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const captureId = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const axis = (decimal, binary64_hex) => ({decimal, binary64_hex});
const geometry = {
  x: axis("259.0", "0x1.0300000000000p+8"),
  y: axis("92.5", "0x1.7200000000000p+6"),
  width: axis("1402.0", "0x1.5e80000000000p+10"),
  height: axis("872.0", "0x1.b400000000000p+9")
};
const entry = {
  capture_id: captureId,
  checkpoint_window_key: windowId,
  app_id: "kitty", output_id: "DP-1", workspace_id: "3",
  saved_at_utc: "2026-11-23T10:20:00+00:00",
  geometry, observed_phase: "CURRENT_VALUE_ONLY",
  local_data_untrusted: true,
  selected_window_identity_verified: false,
  source_authenticated: false,
  settled_frame_verified: false,
  action_allowed: false
};
const data = {
  kind: "timew-v3-local-exact-capture-preview-v1",
  checkpoint_id: cid, status: "LOCAL_CAPTURES_UNTRUSTED_HOLD",
  count: 1, entries: [entry],
  read_only: true, data_origin: "CALLER_SUPPLIED_LOCAL_UNTRUSTED",
  source_authenticated: false, operator_selection_verified: false,
  c5_spent_verified: false, native_receipt_verified: false,
  exact_restore_verified: false, restore_allowed: false,
  native_action_allowed: false, retry_allowed: false,
  undo_allowed: false, safe_actions: []
};
const untouched = JSON.stringify(data);
const result = policy.accept(clone(data), cid);
check(result.valid === true && result.count === 1, "legitimate local preview");
check(result.status === "LOCAL_CAPTURES_UNTRUSTED_HOLD", "HOLD still");
check(result.entries[0].app_id === "kitty", "sanitized app");
check(result.entries[0].geometry.y.decimal === "92.5", "exact decimal");
check(result.entries[0].geometry.y.binary64_hex === geometry.y.binary64_hex,
      "exact display bits");
check(result.safe_actions === undefined && result.restore_allowed === undefined
      && result.native_action_allowed === undefined,
      "no authority field survives into display object");
check(JSON.stringify(data) === untouched, "validator never edits input");

const empty = clone(data);
empty.status = "NO_LOCAL_CAPTURES";
empty.count = 0;
empty.entries = [];
const emptyResult = policy.accept(empty, cid);
check(emptyResult.valid && emptyResult.entries.length === 0,
      "absent local captures are valid empty screen");

function deny(modify, label) {
  const altered = clone(data);
  modify(altered);
  const outcome = policy.accept(altered, cid);
  check(outcome.valid === false && outcome.entries.length === 0
        && outcome.count === 0, label);
}
const rootDenials = [
  "source_authenticated", "operator_selection_verified",
  "c5_spent_verified", "native_receipt_verified",
  "exact_restore_verified", "restore_allowed",
  "native_action_allowed", "retry_allowed", "undo_allowed"
];
for (const flag of rootDenials)
  deny(x => { x[flag] = true; }, "privilege flag " + flag);
for (const flag of [
  "selected_window_identity_verified", "source_authenticated",
  "settled_frame_verified", "action_allowed"
])
  deny(x => { x.entries[0][flag] = true; }, "native entry claim " + flag);

deny(x => { x.kind = "signed-receipt"; }, "wrong kind");
deny(x => { x.checkpoint_id = windowId; }, "stale checkpoint");
deny(x => { x.read_only = false; }, "read only claim");
deny(x => { x.data_origin = "TRUSTED"; }, "source origin");
deny(x => { x.safe_actions = ["move"]; }, "actions never admitted");
deny(x => { x.status = "RESTORE_ALLOWED"; }, "status allowlist");
deny(x => { x.status = "UNAVAILABLE_HOLD"; }, "error is not a valid screen");
deny(x => { x.count = 2; }, "count mismatch");
deny(x => { x.count = -1; }, "negative count");
deny(x => { x.entries = new Array(513).fill(x.entries[0]); x.count = 513; },
     "oversize list");
deny(x => { x.entries[0].geometry.y = {decimal:"92.5",binary64_hex:"bad"}; },
     "invalid hex");
deny(x => { x.entries[0].geometry.y.decimal = "92.5\nRESTORE"; },
     "multiline coordinates");
deny(x => { x.entries[0].geometry.x.decimal = "NaN"; }, "nonfinite decimal");
deny(x => { x.entries[0].geometry.x.decimal = "Infinity"; }, "infinity");
deny(x => { x.entries[0].geometry.x.extra = "permission"; },
     "extra geometry field");
deny(x => { delete x.entries[0].geometry.width; }, "missing axis");
deny(x => { x.entries[0].geometry.extra = axis("1", "0x1.0p+0"); },
     "extra axis");
deny(x => { x.entries[0].app_id = "<script>\n"; }, "text injection");
deny(x => { x.entries[0].output_id = ""; }, "empty output");
deny(x => { x.entries[0].workspace_id = "A".repeat(129); },
     "oversized workspace");
deny(x => { x.entries[0].capture_id = "bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb"; }, "capture uuid wrong version");
deny(x => { x.entries[0].checkpoint_window_key = "abc"; }, "invalid window id");
deny(x => { x.entries[0].saved_at_utc = "\n"; }, "bad timestamp display");
deny(x => { x.entries[0].local_data_untrusted = false; },
     "local source becomes trusted");
deny(x => { x.entries[0].observed_phase = "SETTLED"; },
     "CURRENT cannot be final receipt");
deny(x => { x.entries[0].new_permission = true; },
     "unknown entry privilege");
deny(x => { x.permission = true; }, "unknown root privilege");
deny(x => { x.entries = [x.entries[0], x.entries[0]]; x.count = 2; },
     "duplicate capture");
deny(x => { x.entries = "not-an-array"; }, "not array");
deny(x => { x.entries[0].geometry.y.decimal = 92.5; }, "no numeric coercion");
deny(x => { x.entries[0].geometry.x.binary64_hex = true; }, "no boolean hex");
deny(x => { x.entries[0].geometry = null; }, "no missing geometry");

check(policy.accept(data, windowId).valid === false,
      "caller-selected checkpoint cannot be substituted");
check(policy.accept(data, "NOT-UUID").valid === false,
      "invalid request ID");
check(policy.accept(null, cid).valid === false, "missing result");

for (let i = 1; i <= 256; i++) {
  const sample = clone(data);
  sample.entries[0].geometry.y.decimal = String(92 + i / 4096);
  sample.entries[0].geometry.y.binary64_hex =
    "0x1." + i.toString(16).padStart(13, "0") + "p+6";
  const readable = policy.accept(sample, cid);
  check(readable.valid === true
        && readable.entries[0].geometry.y.binary64_hex
           === sample.entries[0].geometry.y.binary64_hex,
        "untrusted numeric data preserved " + i);
  check(readable.entries[0].source_authenticated === undefined,
        "numeric exactness grants no authority " + i);
}

// Verify the actual QML surface uses only the isolated read-only process.
// A true UI runtime test is still separately required for native acceptance.
const ui = fs.readFileSync(path.join(ROOT, "widgets/TimeW.qml"), "utf8");
for (const marker of [
  "MachineV3LocalPreviewPolicy.js",
  "MachineV3LocalPreviewPolicy.accept(",
  "MachineV3LocalPreviewUiRead.py",
  "id: machineM5PreviewProcess",
  "function machineRequestM5Preview()",
  "function machineInvalidateM5Preview()",
  "function machineStepM5PreviewItem(delta)",
  "onMachineSavedItemChanged: machineInvalidateM5Preview()",
  "onMachineStoredViewOpenChanged: machineInvalidateM5Preview()",
  "LOCAL FRACTIONAL CAPTURES // READ ONLY",
  "LOCAL DATA ONLY // NOT A NATIVE RECEIPT"
])
  check(ui.includes(marker), "M5 UI marker: " + marker);
const request = ui.split("function machineRequestM5Preview()")[1]
                  .split("function machineStepM5PreviewItem(delta)")[0];
for (const forbidden of [
  "machineRestoreSelectedCheckpoint(", "machineStoreRequest(",
  "machineApplyOneProcess.exec(", "machineSaveBridgeProcess.exec(",
  "machineAutoRestoreProcess.exec(", "machineRestoreOneWindow("
])
  check(!request.includes(forbidden), "button never writes or restores: " + forbidden);

console.log("TIMEW M5 PREVIEW DISPLAY POLICY // " + checks
            + " deny-only checks PASS; NO NATIVE RESTORE AUTHORITY");
