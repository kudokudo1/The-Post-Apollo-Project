"use strict";
// Real QML capacity expressions are evaluated with synthetic backend values.
// This test never uses a desktop, persistent state or user snapshot bytes.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const test = require("node:test");
const qml = fs.readFileSync(
  path.join(__dirname, "../../modules/Trash.qml"), "utf8"
);

function propertyExpression(name) {
  const line = qml.split("\n").find(s =>
    s.trim().startsWith("readonly property real " + name + ":"));
  assert.ok(line, "Missing real QML binding " + name);
  return line.slice(line.indexOf(":") + 1).trim();
}
const realRatio = new Function(
  "archiveCapacity", "return (" + propertyExpression("archiveCapacityRatio") + ");");

function ratio(used, limit) {
  return realRatio({chargedBytes:used, diskQuotaBytes:limit});
}

test("capacity gauge is located in the Archive header, before the search and filters", () => {
  const start = qml.indexOf("id: archiveRecordsView");
  const capacity = qml.indexOf("id: archiveCapacityGauge", start);
  const heading = qml.indexOf("ARCHIVE // ", start);
  const search = qml.indexOf("id: archiveSearch", start);
  const filters = qml.indexOf("id: archiveFilterRow", start);
  const list = qml.indexOf("id: archiveEntriesBox", start);
  assert.ok(heading > start && capacity > heading);
  assert.ok(capacity < search && search < filters && filters < list);
  assert.ok(qml.includes('id: archiveCapacityTrack'));
  assert.ok(qml.includes('id: archiveCapacityFill'));
  assert.equal(qml.includes('id: archiveCapacityLine'), false);
});

test("real backend usage determines the exact fill fraction and clamps to track", () => {
  const MiB = 1024 * 1024;
  assert.equal(realRatio(null), 0);
  assert.equal(ratio(0,768*MiB),0);
  assert.equal(ratio(384*MiB,768*MiB),0.5);
  assert.equal(ratio(576*MiB,768*MiB),0.75);
  assert.equal(ratio(768*MiB,768*MiB),1);
  assert.equal(ratio(999*MiB,768*MiB),1);
  assert.equal(ratio(123,0),0);
  assert.ok(Math.abs(ratio(123456,768*MiB)
      - 123456/(768*MiB)) < 1e-15);
});

test("fill width is proportional and never adds a fake minimum amount", () => {
  const widthLine = qml.split("\n").find(s =>
    s.trim().startsWith("width: Math.max(0, (parent.width - 2) * trashLauncher.archiveCapacityRatio)"));
  assert.ok(widthLine, "Missing proportionate fill-width binding");
  const widthExpr = widthLine.trim().slice("width:".length);
  const width = new Function("parent","trashLauncher", "return " + widthExpr);
  const parent = {width: 400};
  for (const [fraction,expected] of [[0,0],[0.01,3.98],[0.5,199],[1,398]]) {
    assert.ok(Math.abs(width(parent,{archiveCapacityRatio:fraction})-expected)<1e-9);
  }
  assert.ok(qml.includes('text: !trashLauncher.archiveCapacity'));
  assert.ok(qml.includes('"NOT MEASURED"'));
  assert.ok(qml.includes('"NO DISK INVENTORY"'));
  assert.ok(qml.includes('"UNAVAILABLE"'));
  assert.ok(qml.includes('archiveCapacityPercent < 0.01 ? "<0.01%"'));
  assert.ok(qml.includes('archiveCapacityPercentText + " USED"'));
});

test("capacity updates use read-only backend data and preserve safe permissions", () => {
  assert.ok(qml.includes("archiveCapacity = reply.capacity;"));
  assert.ok(qml.includes("archiveCapacity = null;"));
  assert.ok(qml.includes("reply.capacity.chargedBytes"));
  assert.ok(qml.includes("reply.capacity.diskQuotaBytes"));
  assert.ok(qml.includes("reply.capacity.remainingBytes"));
  assert.ok(qml.includes("archiveCapacityRatio >= 0.80 ? Colors.orange"));
  assert.ok(qml.includes("archiveCapacityRatio >= 1 ? Colors.red"));
  const panel = qml.slice(qml.indexOf("id: archiveCapacityGauge"),
                          qml.indexOf("id: archiveSearch"));
  assert.equal(panel.includes("ActionButton"), false);
  assert.equal(panel.includes("onLeftClicked"), false);
  assert.equal(panel.includes("Process {"), false);
  assert.equal(panel.includes("Quickshell.shellPath("), false);
  assert.ok(qml.includes("trashLauncher.chassisSize === \"compact\" ? 52 : 66"));
  assert.ok(qml.includes('visible: trashLauncher.chassisSize !== "compact"'));
});

test("receipt refreshes the same read-only index that supplies capacity", () => {
  assert.ok(qml.includes('trashLauncher.refreshArchiveV2('));
  assert.ok(qml.includes('snapshotStatus = "SAVED // INDEPENDENT READ-ONLY COPY";'));
  assert.ok(qml.includes('archiveCapacity = reply.capacity;'));
});
