// ANGEL recovery sidecar policy: pure validation, no live files or writes.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "../..");
const source = fs.readFileSync(
    path.join(root, "services/time/AngelNoteDraftPolicy.js"), "utf8"
).replace(/^\.pragma library\s*$/m, "");
const policy = {};
vm.runInNewContext(source, policy, {filename: "AngelNoteDraftPolicy.js"});
const clone = v => JSON.parse(JSON.stringify(v));

const observation = {
    id: "a189", digits: "624", observedAtMs: 1794280906000,
    note: "older note"
};
const result = policy.create(observation, "changed note", 1794281106000);
assert.equal(result.ok, true);
assert.equal(result.document.version, 1);
const draft = result.document.draft;
assert.equal(draft.id, observation.id);
assert.equal(draft.digits, observation.digits);
assert.equal(draft.before, "older note");
assert.equal(draft.after, "changed note");
assert.equal(observation.note, "older note", "staging cannot mutate original");
assert.equal(policy.parse(JSON.stringify(result.document)).ok, true);
assert.deepEqual(clone(policy.emptyDocument()), {version: 1, draft: null});
assert.equal(policy.parse(JSON.stringify(policy.emptyDocument())).ok, true);

assert.equal(policy.disposition(draft, [observation]), "recoverable");
assert.equal(policy.disposition(draft, [{...observation, note: "changed note"}]),
    "already-saved", "missed acknowledgement is not a retry");
assert.equal(policy.disposition(draft, [{...observation, note: "newer edit"}]),
    "conflict", "do not overwrite a newer note");
assert.equal(policy.disposition(draft, [{...observation, digits: "222"}]),
    "identity-conflict");
assert.equal(policy.disposition(draft, [{...observation, observedAtMs: 9}]),
    "identity-conflict");
assert.equal(policy.disposition(draft, [{...observation, id: "a147"}]),
    "missing");
assert.equal(policy.disposition(null, [observation]), "none");
assert.equal(policy.disposition(draft, null), "invalid");
assert.equal(policy.disposition({...draft, after: "\u0000"}, [observation]),
    "invalid");

const clearing = policy.create(
    {...observation, note: "newer"}, "", 1794281106000
);
assert.equal(clearing.ok, true);
assert.equal(clearing.document.draft.after, "");
assert.equal(policy.disposition(clearing.document.draft,
    [{...observation, note: "newer"}]), "recoverable");
assert.equal(policy.disposition(clearing.document.draft,
    [{...observation, note: ""}]), "already-saved");

for (const candidate of [
    "{}", "garbage", "[]",
    JSON.stringify({version: 2, draft: null}),
    JSON.stringify({version: 1, draft: "note"}),
    JSON.stringify({version: 1, draft: {...draft, id: "a/../1"}}),
    JSON.stringify({version: 1, draft: {...draft, digits: "12:34"}}),
    JSON.stringify({version: 1, draft: {...draft, before: "x".repeat(281)}}),
    JSON.stringify({version: 1, draft: {...draft, after: "x".repeat(281)}}),
    "x".repeat(5000)
]) {
    assert.equal(policy.parse(candidate).ok, false, candidate.slice(0, 40));
}
assert.equal(policy.create(observation, "x".repeat(281), 1794281106000).ok,
    false);
assert.equal(policy.create(observation, "note", NaN).ok, false);
console.log("ANGEL_DURABLE_NOTE_DRAFT_POLICY_PASS");
