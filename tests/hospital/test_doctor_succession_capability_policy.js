#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalDoctorSuccessionCapabilityPolicy.js"), "utf8"),
    context);

const goodHelp = "usage: px agent session-succeed [-h] " + [
    "--room-id", "--previous-session-id", "--new-session-id",
    "--previous-doctor-id", "--previous-provider-id",
    "--successor-doctor-id", "--successor-provider-id",
    "--assignment-id", "--repository", "--branch", "--working-directory",
    "--confirm", "--json"
].join(" ");
const present = context.evaluate(0, goodHelp, "");
assert.equal(present.supported, true);
assert.equal(present.authorityVerified, false);
assert.equal(present.replacementAuthorized, false);
assert.match(present.reason, /NOT VERIFIED/);
assert.match(present.source, /NO SESSION MUTATION/);
assert.equal(present.detail, "");

assert.equal(context.evaluate(127, "", "No PX installed").supported, false);
assert.equal(context.evaluate("0", goodHelp, "").supported, false);
assert.equal(context.evaluate(1, goodHelp, "").supported, false);
assert.equal(context.evaluate(0, goodHelp.replace("session-succeed", "session-attach"), "").supported, false);
for (const flag of ["--previous-session-id", "--new-session-id",
    "--previous-provider-id", "--successor-provider-id",
    "--assignment-id", "--working-directory", "--confirm", "--json"]) {
    assert.equal(context.evaluate(0, goodHelp.replace(flag, ""), "").supported,
        false, "Missing " + flag + " must refuse");
}
assert.equal(context.evaluate(0, "unexpected usage", "").replacementAuthorized, false);
assert.equal(context.evaluate(0, "unexpected usage", "").authorityVerified, false);
assert.equal(context.evaluate(0, goodHelp.replace("--json", ""),
    "z".repeat(1000)).detail.length, 180);
console.log("HOSPITAL DOCTOR SUCCESSION CAPABILITY // PASS // help only, no authentication or mutation claim");
