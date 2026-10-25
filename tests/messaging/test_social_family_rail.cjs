#!/usr/bin/env node
"use strict";
// Exercise real family-policy functions, independent of GUI and live accounts.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const raw = fs.readFileSync(path.join(__dirname,
    "../../services/social/SocialIdentityPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(raw, policy, {filename:"SocialIdentityPolicy.js"});

const base = policy.initialDocument();
const initialRows = policy.view("ready", base, "");
assert.equal(initialRows.railRows.length, 33);
assert.equal(initialRows.railRows[0].kind, "family");
assert.equal(initialRows.railRows[0].title, "ALL APPS");
assert.equal(initialRows.railRows[0].expanded, true);
assert.equal(initialRows.railRows[0].count, 32);
assert.equal(initialRows.visibleAppIndices.join(","), Array.from({length:32},(_,i)=>i).join(","));
assert.equal(initialRows.railRows[1].serviceId, "sessions");
assert.equal(initialRows.railRows[1].serviceIndex, 0);
assert.equal(initialRows.railRows[32].serviceId, "bereal");
assert.equal(initialRows.railRows[32].serviceIndex, 31);

// Collapse only changes the active identity's preference and is immutable.
const closedResult = policy.toggleFamily(base, "family-1");
assert.equal(closedResult.ok, true);
const closed = closedResult.document;
assert.equal(policy.validate(closed).ok, true);
assert.equal(closed.identities[0].layout.families[0].expanded, false);
assert.equal(base.identities[0].layout.families[0].expanded, true);
assert.equal(policy.view("ready", closed, "").railRows.length, 1);
assert.equal(policy.view("ready", closed, "").visibleAppIndices.length, 0);
assert.equal(policy.view("ready", closed, "").railRows[0].expanded, false);
assert.equal(policy.toggleFamily(closed, "unknown").reason, "INVALID_FAMILY");
assert.equal(policy.toggleFamily(closed, 7).reason, "INVALID_FAMILY");

// Copy layout retains collapse state, without binding either identity to
// its original arrays. Toggling the copy leaves the source collapsed.
const copiedResult = policy.create(closed, "Gaming", "copy", "identity-1");
assert.equal(copiedResult.ok, true);
const copied = copiedResult.document;
assert.equal(copied.activeId, "identity-2");
assert.equal(policy.view("ready", copied, "").visibleAppIndices.length, 0);
const expandedCopy = policy.toggleFamily(copied, "family-1").document;
assert.equal(policy.view("ready", expandedCopy, "").visibleAppIndices.length, 32);
assert.equal(expandedCopy.identities[0].layout.families[0].expanded, false);
assert.equal(expandedCopy.identities[1].layout.families[0].expanded, true);
const back = policy.select(expandedCopy, "identity-1").document;
assert.equal(policy.view("ready", back, "").visibleAppIndices.length, 0);

const empty = policy.create(base, "Empty", "empty", "").document;
const emptyView = policy.view("ready", empty, "");
assert.equal(emptyView.railRows.length, 1);
assert.equal(emptyView.railRows[0].kind, "empty");
assert.equal(emptyView.visibleAppIndices.length, 0);
assert.equal(policy.toggleFamily(empty, "family-1").reason, "INVALID_FAMILY");

// A user-specified order must not be mistaken for legacy launcher indices.
const shuffled = policy.initialDocument();
const fam = shuffled.identities[0].layout.families[0];
fam.appIds = ["x", "telegram", "sessions"];
shuffled.identities[0].layout.families.push({
    id:"family-2", name:"B", appIds:["discord"], expanded:true
});
shuffled.identities[0].layout.nextFamilyId = 3;
assert.equal(policy.validate(shuffled).ok, true);
const shuffledView = policy.view("ready", shuffled, "");
assert.equal(shuffledView.visibleAppIndices.join(","), "3,2,0,1");
assert.equal(shuffledView.railRows[1].serviceIndex, 3);
assert.equal(shuffledView.railRows[4].kind, "family");
assert.equal(shuffledView.railRows[5].serviceIndex, 1);

shuffled.identities[0].layout.hiddenAppIds = ["telegram", "discord"];
assert.equal(policy.validate(shuffled).ok, true);
const hiddenView = policy.view("ready", shuffled, "");
assert.equal(hiddenView.visibleAppIndices.join(","), "3,0");
assert.equal(hiddenView.railRows[0].count, 2);
assert.equal(hiddenView.railRows[3].count, 0);

// Storage unavailable means legacy all-apps fallback, never data repair.
const corrupted = {version: 400, identities: []};
const fallback = policy.view("unsupported", corrupted, "UNSUPPORTED_VERSION");
assert.equal(fallback.writable, false);
assert.equal(fallback.error, "UNSUPPORTED_VERSION");
assert.equal(fallback.visibleAppIndices.length, 32);
assert.equal(policy.validate(corrupted).ok, false);
assert.equal(policy.view("saving", closed, "").writable, false);

const allowed = policy.parse(JSON.stringify(closed));
assert.equal(allowed.ok, true);
assert.equal(allowed.document.identities[0].layout.families[0].expanded, false);
console.log("Social collapsible families: visibility, copy isolation, routing and fallback PASS");
