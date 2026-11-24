const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, "../services/memory/MemoryQueueNotificationAdapter.js"), "utf8"), ctx);
const offer = ctx.offer;
const id = "c23683a9-b2ab-4a2c-87ce-31bdf27a3012";
const packet = {
    version: 1, can_execute: false, delivery_state: "ATTEMPT_RESERVED",
    request_id: id, kind: "READY_ADVISORY", code: "FRESH_AUTH_AND_ROOT_CHECK_REQUIRED",
    event_id: "apollo-cpu-memory-" + id + "-ready-advisory",
    target_gib: 16, original_actual_kib: 25165816, observed_at: 110,
    checked_at_ms: 110100, valid_before_wall_ms: 111000
};
const rows = [];
let pushes = 0;
const hub = {
    historyReady: true, policyReady: true, historyStatus: "ready", policyStatus: "ready",
    notifications: { get count() { return rows.length; }, get(i) { return rows[i]; } },
    normalize: x => x, shouldBlockNotification: () => false,
    pushRich: x => { pushes++; rows.push(x); }
};
assert.equal(offer(hub, packet, 111000), "STALE_PACKET");
assert.equal(offer(hub, {...packet, can_execute: true}, 110100), "INVALID_PACKET");
assert.equal(offer(hub, {...packet, kind: "COMPLETED"}, 110100), "INVALID_PACKET");
assert.equal(offer(hub, {...packet, event_id: "fake"}, 110100), "INVALID_PACKET");
hub.policyReady = false;
assert.equal(offer(hub, packet, 110100), "HUB_NOT_READY");
hub.policyReady = true;
hub.historyStatus = "parse-error";
assert.equal(offer(hub, packet, 110100), "HUB_NOT_READY");
hub.historyStatus = "ready";
hub.shouldBlockNotification = () => true;
assert.equal(offer(hub, packet, 110100), "BLOCKED");
assert.equal(pushes, 0);
hub.shouldBlockNotification = () => false;
assert.equal(offer(hub, packet, 110100), "HISTORY_OBSERVED");
assert.equal(rows[0].sourceId, "cpu-plus-memory-queue");
assert.match(rows[0].message, /recheck and authorize/);
assert.equal(rows[0].context.advisoryOnly, true);
assert.equal(offer(hub, packet, 110100), "HISTORY_PRESENT");
assert.equal(pushes, 1);
rows.length = 0;
hub.pushRich = () => { pushes++; };
assert.equal(offer(hub, packet, 110100), "OFFER_OUTCOME_UNKNOWN");
console.log("CPU++ memory queue Hub adapter fixture PASS");
