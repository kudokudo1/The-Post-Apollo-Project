#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname,
    "../../services/publisher/PublisherDraftPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const policy = vm.createContext({});
vm.runInContext(source, policy, {filename:"PublisherDraftPolicy.js"});
function reasonFor(raw) { return policy.parse(raw).reason; }

let doc = policy.emptyDocument();
assert.equal(policy.validate(doc).ok, true);
assert.equal(policy.view("empty", doc).writable, true);
assert.equal(policy.view("loading", doc).writable, false);
assert.equal(policy.view("saving", doc).writable, false);
assert.equal(policy.view("error", doc).writable, false);
assert.equal(policy.view("unsupported", doc).writable, false);
const one = policy.saveDraft(doc, "", "  Example role  ", "Line 1\nLine 2", 1000);
assert.equal(one.ok, true);
assert.equal(one.draftId, "d1");
assert.equal(one.document.drafts[0].title, "Example role");
assert.equal(one.document.drafts[0].body, "Line 1\nLine 2");
assert.equal(doc.drafts.length, 0); // immutable until explicit FileView receipt
assert.equal(one.document.nextId, 2);
doc = one.document;
const two = policy.saveDraft(doc, "", "Second", "", 2000);
assert.equal(two.ok, true);
doc = two.document;
assert.equal(doc.drafts.length, 2);
assert.equal(doc.drafts[1].id, "d2");
assert.equal(policy.view("ready", doc).drafts.length, 2);

const edited = policy.saveDraft(doc, "d1", "Changed", "new body", 3000);
assert.equal(edited.ok, true);
assert.equal(edited.document.drafts[0].title, "Changed");
assert.equal(edited.document.drafts[0].createdAtMs, 1000);
assert.equal(edited.document.drafts[0].updatedAtMs, 3000);
assert.equal(edited.document.nextId, 3);
assert.equal(doc.drafts[0].title, "Example role");
assert.equal(policy.saveDraft(doc, "d9", "Unknown", "x", 3000).reason, "UNKNOWN_DRAFT");
assert.equal(policy.saveDraft(doc, "d1", "Old", "x", 999).reason, "STALE_CLOCK");
assert.equal(policy.saveDraft(doc, "", "   ", "x", 3000).reason, "INVALID_INPUT");
assert.equal(policy.saveDraft(doc, "", "a".repeat(121), "x", 3000).reason, "INVALID_INPUT");
assert.equal(policy.saveDraft(doc, "", "title", "x".repeat(10001), 3000).reason, "INVALID_INPUT");
assert.equal(policy.saveDraft(doc, "", "bad\nname", "x", 3000).reason, "INVALID_INPUT");
assert.equal(policy.saveDraft(doc, "", "title", "\u0000", 3000).reason, "INVALID_INPUT");
assert.equal(policy.saveDraft(doc, "", "title", "x", -1).reason, "INVALID_TIME");
assert.equal(policy.saveDraft(doc, null, "title", "x", 3000).reason, "INVALID_DRAFT_ID");

const roundtrip = policy.parse(JSON.stringify(edited.document));
assert.equal(roundtrip.ok, true);
assert.equal(roundtrip.document.drafts[0].title, "Changed");
assert.equal(reasonFor("{"), "MALFORMED_JSON");
assert.equal(reasonFor(JSON.stringify({version:2,nextId:1,drafts:[]})), "UNSUPPORTED_VERSION");
assert.equal(reasonFor(JSON.stringify({version:1,nextId:1,drafts:[],secrets:{}})), "UNKNOWN_FIELDS");
assert.equal(reasonFor(JSON.stringify({version:1,nextId:1,drafts:[],token:"abc"})), "UNKNOWN_FIELDS");
const duplicate = JSON.parse(JSON.stringify(doc));
duplicate.drafts.push(duplicate.drafts[0]);
assert.equal(reasonFor(JSON.stringify(duplicate)), "DUPLICATE_DRAFT_ID");
const rewind = JSON.parse(JSON.stringify(doc));
rewind.nextId = 2;
assert.equal(reasonFor(JSON.stringify(rewind)), "SEQUENCE_REWIND");
const unknownDraftField = JSON.parse(JSON.stringify(doc));
unknownDraftField.drafts[0].providerToken = "do-not-store";
assert.equal(reasonFor(JSON.stringify(unknownDraftField)), "INVALID_DRAFT");
assert.equal(reasonFor("x".repeat(1500001)), "INVALID_SOURCE");
console.log("publisher P1 draft policy: all assertions passed");
