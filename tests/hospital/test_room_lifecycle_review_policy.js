#!/usr/bin/env node
// Pure fixtures only; no PX, Quickshell or Trash++ source mutations.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname,
    "../../services/hospital/HospitalRoomTrashReviewPolicy.js"), "utf8");
const policy = vm.createContext({});
vm.runInContext(source, policy);

const rooms = [{ id: "room-1" }, { id: "room-2" }];
const sessions = [
    { id: "s1", roomId: "room-1", status: "WAITING" },
    { id: "s2", roomId: "room-1", status: "FAILED" }
];
function review(override) {
    return policy.inspect(Object.assign({
        pinnedRoomId: "room-1",
        room: { roomId: "room-1", assignmentId: "42",
            assignmentStatus: "ACTIVE" },
        roomsLoaded: true, sessionsLoaded: true,
        allRooms: rooms, allSessions: sessions
    }, override || {}));
}
for (const fixture of [
    review(), review({pinnedRoomId: "room-2"}),
    review({roomsLoaded: false}),
    review({sessionsLoaded: false}),
    review({room: {roomId: "room-1", assignmentId: "",
        assignmentStatus: ""}, allSessions: []})
]) {
    assert.equal(fixture.state, "DENY_ONLY_OWNER_REVIEW");
    for (const capability of [
        "trashAllowed", "restoreAllowed", "burnAllowed",
        "enqueueAllowed", "sourceMutationAllowed"
    ]) assert.equal(fixture[capability], false, capability);
}
const active = review();
assert.equal(active.roomMatched, true);
assert.equal(active.sessionCount, 2);
assert.ok(active.blockers.includes("LINKED_SESSION_HISTORY_PRESERVE"));
assert.ok(active.blockers.includes("ACTIVE_ASSIGNMENT_HOLD"));
const missing = review({pinnedRoomId:"other"});
assert.ok(missing.blockers.includes("EXACT_ROOM_ID_MISMATCH"));
assert.ok(missing.blockers.includes("DURABLE_ROOM_REGISTRY_UNVERIFIED"));
assert.equal(review({sessionsLoaded:false}).sessionSummary, "UNVERIFIED");
assert.equal(review({room:{roomId:"room-1"},allSessions:[]}).sessionCount,0);
console.log("HOSPITAL ROOM TRASH++ REVIEW // PASS // deny-only exact Room and dependencies");
