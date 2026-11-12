#!/usr/bin/env node
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const code = fs.readFileSync(path.join(__dirname,
    "../../services/publisher/PublisherMediaPolicy.js"), "utf8")
    .replace(/^\.pragma library\s*/m, "");
const p = vm.createContext({});
vm.runInContext(code, p, {filename:"PublisherMediaPolicy.js"});
let doc = p.emptyDocument();
assert.equal(p.validate(doc).ok, true);
assert.equal(p.view("empty", doc).writable, true);
for (const state of ["loading","saving","error","unsupported"])
    assert.equal(p.view(state, doc).writable, false);
const sourceUrl = "file:///home/demo/Pictures/Photo%20%231.png";
const info = {sourceUrl, title:"Photo #1.png", kind:"image",
    mime:"image/png", sizeBytes:1234, stamp:"a".repeat(64)};
const created = p.register(doc, info, 10000);
assert.equal(created.ok, true);
assert.equal(created.assetId, "m1");
assert.equal(created.document.nextId, 2);
assert.equal(doc.assets.length, 0);
doc = created.document;
assert.equal(doc.assets[0].sourceUrl, sourceUrl);
assert.equal(p.view("ready", doc).assets.length, 1);
const dupe = p.register(doc, info, 10001);
assert.equal(dupe.ok, true);
assert.equal(dupe.unchanged, true);
assert.equal(dupe.assetId, "m1");
assert.equal(p.register(doc, {...info, stamp:"b".repeat(64)}, 10002).reason,
             "SOURCE_CHANGED_REVIEW_REQUIRED");
assert.equal(p.register(doc, {...info, sourceUrl:"https://example.com/"}, 10002).reason,
             "INVALID_PROBE_RECEIPT");
assert.equal(p.register(doc, {...info, mime:"application/javascript"}, 10002).reason,
             "INVALID_PROBE_RECEIPT");
assert.equal(p.register(doc, {...info, token:"secret"}, 10002).reason,
             "INVALID_PROBE_RECEIPT");
assert.equal(p.register(doc, {...info, sizeBytes:33554433}, 10002).reason,
             "INVALID_PROBE_RECEIPT");

const linked = p.attach(doc, "d1", "m1");
assert.equal(linked.ok, true);
assert.equal(linked.document.links.length, 1);
assert.equal(doc.links.length, 0);
assert.equal(p.attach(doc, "", "m1").reason, "DRAFT_MUST_BE_SAVED");
assert.equal(p.attach(doc, "d1", "m99").reason, "UNKNOWN_MEDIA");
doc = linked.document;
assert.equal(p.attach(doc, "d1", "m1").reason, "ALREADY_ATTACHED");
const removed = p.detach(doc, "d1", "m1");
assert.equal(removed.ok, true);
assert.equal(removed.document.links.length, 0);
assert.equal(removed.document.assets.length, 1);
assert.equal(doc.links.length, 1);
assert.equal(p.detach(removed.document, "d1", "m1").reason, "NO_ATTACHMENT");
assert.equal(p.parse(JSON.stringify(doc)).ok, true);
assert.equal(p.parse("{").reason, "MALFORMED_JSON");
assert.equal(p.parse(JSON.stringify({version:2,nextId:1,assets:[],links:[]})).reason,
             "UNSUPPORTED_VERSION");
assert.equal(p.parse(JSON.stringify({...doc,credentials:"secret"})).reason, "UNKNOWN_FIELDS");
const duplicates = JSON.parse(JSON.stringify(doc));
duplicates.assets.push(duplicates.assets[0]);
assert.equal(p.parse(JSON.stringify(duplicates)).reason, "DUPLICATE_MEDIA_ID");
const rewind = JSON.parse(JSON.stringify(doc));
rewind.nextId = 1;
assert.equal(p.parse(JSON.stringify(rewind)).reason, "SEQUENCE_REWIND");
const forged = JSON.parse(JSON.stringify(doc));
forged.assets[0].sourceUrl = "https://bad.example/";
assert.equal(p.parse(JSON.stringify(forged)).reason, "INVALID_MEDIA_RECORD");
const brokenLink = JSON.parse(JSON.stringify(doc));
brokenLink.links[0].assetId = "m22";
assert.equal(p.parse(JSON.stringify(brokenLink)).reason, "INVALID_MEDIA_LINK");
assert.equal(p.parse("x".repeat(1048577)).reason, "INVALID_SOURCE");
console.log("publisher P1.2 media policy: all assertions passed");
