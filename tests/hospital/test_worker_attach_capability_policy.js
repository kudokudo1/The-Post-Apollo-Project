#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const policy = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalWorkerAttachmentCapabilityPolicy.js"), "utf8"), policy);

const help = `usage: px agent session-attach [-h] --room-id ROOM_ID --session-id SESSION_ID
                      --assignment-id ASSIGNMENT_ID --doctor-id DOCTOR_ID
                      --provider-id PROVIDER_ID --repository REPOSITORY
                      --branch BRANCH --working-directory WORKING_DIRECTORY
                      --mode {create,reuse} [--confirm] [--json]
options:
  --confirm
`;
const ok = policy.evaluate(0, help, "");
assert.equal(ok.supported, true);
assert.equal(ok.errorDetail, "");
assert.match(ok.reason, /AVAILABLE/); // Need an actual separate authority check.
assert.match(ok.source, /NOT PROVIDER REACHABILITY/);

const missing = policy.evaluate(2, "", "px agent: invalid choice 'session-attach'");
assert.equal(missing.supported, false);
assert.match(missing.reason, /INSTALL MATCHING PX PR #123/);
assert.match(missing.errorDetail, /invalid choice/);

const noBinary = policy.evaluate(127, "", "bash: px: No such file or directory");
assert.equal(noBinary.supported, false);
assert.match(noBinary.reason, /UNAVAILABLE/);

const oldHelp = `usage: px agent session-create [-h] --room-id ROOM_ID
   --doctor-id DOCTOR_ID --provider-id PROVIDER_ID
   --working-directory WORKING_DIRECTORY`;
assert.equal(policy.evaluate(0, oldHelp, "").supported, false);
assert.equal(policy.evaluate(0, help.replace("--confirm", "--skip-confirm"), "").supported, false);
assert.equal(policy.evaluate(0, help.replace("--assignment-id", "--task-id"), "").supported, false);
assert.equal(policy.evaluate(0, help.replace("session-attach", "session-create"), "").supported, false);
assert.equal(policy.evaluate(1, help, "").supported, false);
assert.equal(policy.evaluate(null, help, "").supported, false);
assert.equal(policy.evaluate(undefined, help, "").supported, false);
assert.equal(policy.evaluate(0, "", "").supported, false);

console.log("HOSPITAL PX ATTACH CAPABILITY // PASS // exact help probe, old/missing CLI refused, no authority claims");
