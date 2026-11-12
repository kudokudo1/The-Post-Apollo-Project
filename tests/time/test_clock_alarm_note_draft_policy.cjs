// Exercise Clock's actual note draft parser and conflict rules.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const file = path.resolve(__dirname, "../../services/time/AlarmNoteDraftPolicy.js");
const source = fs.readFileSync(file, "utf8").replace(".pragma library", "");
const Draft = vm.createContext({});
vm.runInContext(source, Draft);

const row = {
    id: 23, name: "New Alarm 23", hour: 7, minute: 45,
    mode: "weekly", weekdays: [1, 3], date: "",
    armedAtMs: 1794400400000, note: "original"
};
const good = Draft.create(row, "new note", 1794400600000);
assert.equal(good.ok, true);
assert.equal(good.document.draft.id, 23);
assert.equal(good.document.draft.before, "original");
assert.equal(good.document.draft.after, "new note");
assert.equal(Draft.validDraft(good.document.draft), true);
assert.equal(Draft.parse(JSON.stringify(good.document)).ok, true);
assert.equal(Draft.parse(JSON.stringify(Draft.emptyDocument())).ok, true);
assert.equal(Draft.create(row, "original", 1794400600000).ok, false);
assert.equal(Draft.create(row, "n".repeat(257), 1794400600000).ok, false);
assert.equal(Draft.create(row, "bad\nnote", 1794400600000).ok, false);
assert.equal(Draft.parse("{bad").ok, false);
assert.equal(Draft.parse("x".repeat(4097)).ok, false);
assert.equal(Draft.parse(JSON.stringify({version:1,draft:{...good.document.draft,
    extra:"injection"}})).ok,false);

const doc = rowNote => ({version:2,alarms:[rowNote]});
const d = good.document.draft;
assert.equal(Draft.disposition(d, doc({...row})), "recoverable");
assert.equal(Draft.disposition(d, doc({...row, note:"new note"})), "already-saved");
assert.equal(Draft.disposition(d, doc({...row, note:"changed elsewhere"})), "conflict");
assert.equal(Draft.disposition(d, doc({...row, hour: 9})), "identity-conflict");
assert.equal(Draft.disposition(d, doc({...row, id:24})), "missing");
assert.equal(Draft.disposition(d, {alarms:[]}), "missing");
assert.equal(Draft.disposition(d, doc({...row, hour:9, note:"new note"})),
    "already-saved");
assert.equal(Draft.disposition(null, doc({...row})), "none");
console.log("CLOCK_ALARM_NOTE_DRAFT_POLICY_PASS");
