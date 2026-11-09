import assert from "node:assert/strict";
import {
  MAX_NORMAL_WINDOWS, MAX_TABS_PER_WINDOW, MAX_TOTAL_TABS,
  projectBraveTopology, TOPOLOGY_KIND
} from "../../integrations/machine/brave-topology/topology.mjs";

function tab(index, extras = {}) {
  return { index, pinned: index === 0, active: index === 1, ...extras };
}
function windowFixture(id, tabCount = 3, extras = {}) {
  return {
    id, type: "normal", incognito: false,
    tabs: Array.from({ length: tabCount }, (_, i) => tab(i)),
    ...extras,
  };
}
function refuses(input, current = null) {
  assert.throws(
    () => projectBraveTopology(input, current),
    /BROWSER WINDOW INVENTORY UNAVAILABLE/
  );
}

// Twenty-one Brave windows with independent tab counts, including a case
// with the same number of tabs in every window. Do not infer identity from
// the tab-count/order multiset.
const source = Array.from({ length: 17 }, (_, i) =>
  windowFixture(101 + i, 6)
);
const before = structuredClone(source);
const result = projectBraveTopology(source, 107);
assert.equal(result.kind, TOPOLOGY_KIND);
assert.equal(result.status, "ready");
assert.equal(result.read_only, true);
assert.deepEqual(result.counts, {
  browser_windows: 17, tabs: 102, pinned_tabs: 17
});
assert.deepEqual(source, before, "Read-only projection mutated Brave API input");
assert.equal(result.windows.length, 17);
assert.equal(result.windows[0].temporary_browser_window_id, 107);
assert.equal(result.windows[0].current_browser_window, true);
assert.equal(result.windows[1].current_browser_window, false);
assert.equal(new Set(result.windows.map(w => w.temporary_browser_window_id)).size, 17);
for (const w of result.windows) {
  assert.equal(w.tab_count, 6);
  assert.equal(w.pinned_tab_count, 1);
  assert.equal(w.active_tab_index, 1);
  assert.deepEqual(Object.keys(w).sort(), [
    "active_tab_index", "current_browser_window", "pinned_tab_count",
    "tab_count", "temporary_browser_window_id"
  ]);
}
for (const flag of [
  "private_windows_included", "title_url_contents_included",
  "sway_window_binding_verified", "restart_session_identity_verified",
  "tabs_restorable"
]) {
  assert.equal(result[flag], false, flag);
}
assert.equal(result.temporary_ids_only, true);
assert.deepEqual(result.safe_restore_actions, []);

// Protected/private metadata is never accessed even when supplied by the
// browser API object. A strict field-picking implementation must ignore
// accessors for URL/title/secret/profile/content information.
const nastyTab = tab(0, { active: true });
const nastyWindow = windowFixture(1001, 1, { tabs: [nastyTab] });
for (const key of [
  "url", "pendingUrl", "title", "favIconUrl", "cookie", "profile",
  "profilePath", "sessionId", "description", "processId"
]) {
  Object.defineProperty(nastyTab, key, { get() {
    throw new Error("UNSAFE TAB DATA READ: " + key);
  } });
  Object.defineProperty(nastyWindow, key, { get() {
    throw new Error("UNSAFE WINDOW DATA READ: " + key);
  } });
}
const redacted = projectBraveTopology([nastyWindow], 1001);
assert.equal(redacted.counts.tabs, 1);
const encoded = JSON.stringify(redacted);
for (const key of [
  "url", "title", "cookie", "profilePath", "processId", "sessionId",
  "favIconUrl", "pendingUrl", "description"
]) {
  assert.equal(encoded.includes('"' + key + '"'), false, key);
}

// Even if Brave exposes an incognito window to a privileged test harness,
// skip it before reading its tabs or counts. Also ignore non-normal windows.
const privateWindow = {
  id: 777, type: "normal", incognito: true,
  get tabs() { throw new Error("PRIVATE TAB READ"); }
};
const popupWindow = {
  id: 778, type: "popup", incognito: false,
  get tabs() { throw new Error("POPUP READ"); }
};
const redactedPrivate = projectBraveTopology(
  [privateWindow, popupWindow, windowFixture(199, 0)], 777
);
assert.equal(redactedPrivate.counts.browser_windows, 1);
assert.equal(redactedPrivate.counts.tabs, 0);
assert.equal(redactedPrivate.windows[0].current_browser_window, false);

const noActive = windowFixture(12, 2, {
  tabs: [{ index: 0, pinned: false, active: false },
         { index: 1, pinned: true, active: false }]
});
assert.equal(projectBraveTopology([noActive]).windows[0].active_tab_index, null);

// All errors fail closed with a generic message. Rejected reports cannot
// silently become supported browser-session or host identities.
refuses(null);
refuses({});
refuses([null]);
refuses([windowFixture(2), windowFixture(2)]);
refuses([windowFixture(-1)]);
refuses([windowFixture(0)]);
refuses([windowFixture(1, 0, { incognito: undefined })]);
refuses([windowFixture(1, 0, { tabs: null })]);
refuses([windowFixture(1, 1, { tabs: [tab(2)] })]);
refuses([windowFixture(1, 2, { tabs: [tab(0), tab(0)] })]);
refuses([windowFixture(1, 2, { tabs: [tab(0, {active:true}), tab(1, {active:true})] })]);
refuses([windowFixture(1, 1, { tabs: [tab(0, {pinned:"yes"})] })]);
refuses([windowFixture(1, 1, { tabs: [tab(0, {incognito:true})] })]);
refuses([windowFixture(1, 1, { tabs: [tab(0, {active:undefined})] })]);
refuses([windowFixture(1, MAX_TABS_PER_WINDOW + 1)]);
refuses(Array.from({ length: MAX_NORMAL_WINDOWS + 1 }, (_, i) =>
  windowFixture(i + 1, 0)));
refuses(Array.from({ length: 5 }, (_, i) =>
  windowFixture(i + 1, MAX_TABS_PER_WINDOW))); // exceeds total tab limit
refuses([windowFixture(1)], -2);
refuses([windowFixture(1)], 0);
refuses([windowFixture(1)], "1");

// The API window ID is deliberately not equivalent to a stable identity.
// Changing it after restart must change the transient label, with no
// "session verified" or safe action inferred from the same tab structure.
const beforeRestart = projectBraveTopology([windowFixture(10)]);
const afterRestart = projectBraveTopology([windowFixture(90)]);
assert.notEqual(
  beforeRestart.windows[0].temporary_browser_window_id,
  afterRestart.windows[0].temporary_browser_window_id
);
assert.equal(afterRestart.restart_session_identity_verified, false);
assert.deepEqual(afterRestart.safe_restore_actions, []);

console.log("MACHINE Brave topology // 17 independent windows, redaction and no identity claims PASS");
