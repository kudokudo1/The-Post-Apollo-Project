#!/usr/bin/env python3
"""Notification retention limits and bounded history projection (synthetic only)."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/notifications/NotificationsService.qml"
HUB = ROOT / "widgets/notifications/NotificationsHubW.qml"
s = SERVICE.read_text(encoding="utf-8")
h = HUB.read_text(encoding="utf-8")

# Capacity survives restart from the history file itself, avoiding async
# preference-load ordering that could prune an existing high-capacity archive.
assert "property int maxHistoryEntries: 300" in s
assert "function normalizeHistoryCapacity(value)" in s
assert "function setMaxHistoryEntries(value)" in s
assert '"maxHistoryEntries": maxHistoryEntries' in s
assert "maxHistoryEntries = normalizeHistoryCapacity(document.maxHistoryEntries)" in s
assert s.index("maxHistoryEntries = normalizeHistoryCapacity(document.maxHistoryEntries)") < s.index("const firstRetainedIndex")
assert "notifications.remove(0, surplus);" in s
assert "JSON.stringify(historyDocument())" in s

# The capacity control previews before Apply, including a pruning warning.
assert "id: historyCapacityControls" in h
assert "id: historyCapacitySlider" in h
assert "function previewHistoryCapacity(pointerX, railWidth)" in h
assert 'label: root.historyCapacityDirty ? "APPLY" : "SAVED"' in h
assert "NotificationsService.setMaxHistoryEntries(" in h
assert "APPLY WILL DELETE OLDEST HISTORY" in h
assert "property int controlBayHeight: 220" in h

# The whole archive is never rebuilt into the QML view at once.
assert "property int filterPageSize: 100" in h
assert "id: filteredScanTimer" in h
assert "id: filteredRenderTimer" in h
assert "filterScanIndex + 64" in h
assert "filteredNotifications.count + 24" in h
assert 'label: "MORE HISTORY"' in h
assert 'trim() !== "0"' in h
assert "filteredNotifications.append(rows[j].data);" in h

NODE = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const service = fs.readFileSync(process.argv[1], 'utf8');
const hub = fs.readFileSync(process.argv[2], 'utf8');
function extract(source, name) {
  const pos = source.indexOf('function ' + name + '(');
  assert(pos >= 0, 'missing function: ' + name);
  const open = source.indexOf('{', pos);
  let depth = 0;
  for (let i = open; i < source.length; i++) {
    if (source[i] === '{') depth++;
    else if (source[i] === '}' && --depth === 0)
      return source.slice(pos, i + 1);
  }
  throw Error('unclosed function: ' + name);
}
const asModel = (arr) => ({
  data: arr,
  get count() { return this.data.length; },
  get(i) { return this.data[i]; },
  remove(i, n) { this.data.splice(i, n === undefined ? 1 : n); },
  clear() { this.data = []; },
  append(entry) { this.data.push(entry); }
});
const retained = asModel(Array.from({length: 1350}, (_, i) => ({id:String(i)})));
const owner = {
  Math, Number, JSON, Date, Array, String, console,
  notifications: retained, maxHistoryEntries: 300, historyVersion: 1,
  historySnapshot: (entry) => entry,
  saves: 0, revisions: 0,
  scheduleHistorySave() { owner.saves++; },
  markNotificationsChanged() { owner.revisions++; }
};
vm.runInNewContext(['normalizeHistoryCapacity','setMaxHistoryEntries',
  'pruneHistory','historyDocument','historyToJson']
  .map(n => extract(service, n)).join('\n'), owner);
assert.strictEqual(owner.normalizeHistoryCapacity(999), 1000);
assert.strictEqual(owner.normalizeHistoryCapacity(90000), 5000);
assert.strictEqual(owner.normalizeHistoryCapacity(-1), 300);
assert.strictEqual(owner.normalizeHistoryCapacity('broken'), 300);
assert.strictEqual(owner.setMaxHistoryEntries(5000), true);
assert.strictEqual(retained.count, 1350, 'raising limit never deletes');
const snapshot = JSON.parse(owner.historyToJson());
assert.strictEqual(snapshot.maxHistoryEntries, 5000);
assert.strictEqual(snapshot.notifications.length, 1350);
assert.strictEqual(owner.setMaxHistoryEntries(900), true);
assert.strictEqual(retained.count, 900, 'lowering prunes oldest in one batch');
assert.strictEqual(retained.get(0).id, '450');
assert.strictEqual(owner.setMaxHistoryEntries(900), false, 'no redundant save');
assert.strictEqual(owner.saves, 2);
assert.strictEqual(owner.revisions, 1);

const history = asModel(Array.from({length: 1250}, (_, i) => ({
  id: String(i), source:'test', sourceId:'test', title:'synthetic',
  message:'synthetic', category:'generic', severity:'normal',
  createdAt:i, updatedAt:0, context:{}, metrics:{}, actions:[]
})));
let scanned = 0;
const instrumented = {
  get count() { return history.count; },
  get(i) { scanned++; return history.get(i); }
};
const rendered = asModel([]);
const projected = {
  Math, Number, JSON, Date, Array, String, console,
  bgLagProbeEnabled:false, filteredNotifications:rendered,
  filteredRows:[], filterScanRows:[], filterScanIndex:0,
  filterBuildInProgress:false, filterVisibleTarget:0,
  filterPageSize:100, activeFilter:'all',
  filteredScanTimer:{ start(){}, stop(){} },
  filteredRenderTimer:{ start(){}, stop(){} },
  NotificationsService:{notifications:instrumented},
  NotificationFacets:{facetsFor(){return {};} },
  classificationFor(){return {group:'apps'};},
  notificationMatches(){return true;},
  reportKindFor(){return '';},
  reportDetailsFor(){return '';}
};
projected.root = projected;
vm.runInNewContext(['rebuildFilteredNotifications','scanFilteredNotificationsChunk',
  'appendNextFilteredPage','appendFilteredPageBatch']
  .map(n => extract(hub, n)).join('\n'), projected);
projected.rebuildFilteredNotifications();
let chunks = 0;
while (projected.filterBuildInProgress) {
  const before = scanned;
  projected.scanFilteredNotificationsChunk();
  assert(scanned - before <= 64, 'a scan must not monopolize the UI thread');
  chunks++;
  assert(chunks < 100, 'bounded scan terminates');
}
assert(scanned === 1250);
assert(projected.filteredRows.length === 1250);
assert.strictEqual(rendered.count, 0, 'scan does not create QML rows');
while (rendered.count < projected.filterVisibleTarget) {
  const before = rendered.count;
  projected.appendFilteredPageBatch();
  assert(rendered.count - before <= 24, 'bounded render batches');
}
assert.strictEqual(rendered.count, 100);
assert.strictEqual(rendered.get(0).notificationId, '1249', 'newest first');
projected.appendNextFilteredPage();
while (rendered.count < projected.filterVisibleTarget)
  projected.appendFilteredPageBatch();
assert.strictEqual(rendered.count, 200);
assert.strictEqual(projected.filteredRows.length, 1250);
console.log('Synthetic 1250-item scan / 100-item paging / capacity persistence: PASS');
"""
subprocess.run(["node", "-e", NODE, str(SERVICE), str(HUB)], check=True)
print("Notifications history capacity and paging contracts: PASS")
