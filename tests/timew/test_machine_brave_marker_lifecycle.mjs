import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {MarkerCandidateLifecycle} from
  "../../integrations/machine/brave-topology/marker-lifecycle.mjs";

const token="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const base={tabId:17,windowId:201,token};
const observation={...base,conId:701,output:"DP-3",workspace:"1"};
const lifecycle=new MarkerCandidateLifecycle();

assert.equal(lifecycle.candidate,null);
let ticket=lifecycle.begin(base);
assert.ok(ticket);
assert.deepEqual(lifecycle.accept(ticket,observation),{
  status:"candidate",candidate:observation
});
assert.deepEqual(lifecycle.candidate,observation);
assert.ok(Object.isFrozen(lifecycle.candidate));

// Rechecking the *same* live browser/Sway candidate is allowed.
ticket=lifecycle.begin(base);
assert.equal(lifecycle.accept(ticket,observation).status,"candidate");

// Never silently substitute a different Sway container/monitor/workspace.
for(const modified of [
  {conId:702},{output:"DP-4"},{workspace:"2"},
  {tabId:18},{windowId:202},{token:"bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"},
]){
  // Each scenario first establishes the same original correlation.
  lifecycle.revoke();
  ticket=lifecycle.begin(base);
  assert.equal(lifecycle.accept(ticket,observation).status,"candidate");
  ticket=lifecycle.begin(base);
  const status=lifecycle.accept(ticket,{...observation,...modified}).status;
  assert.equal(status,modified.tabId||modified.windowId||modified.token
                     ?"invalid":"changed");
  assert.equal(lifecycle.candidate,null);
}

// Revocation invalidates even an in-flight native host response.
ticket=lifecycle.begin(base);
lifecycle.revoke();
assert.equal(lifecycle.isCurrent(ticket),false);
assert.equal(lifecycle.accept(ticket,observation).status,"stale");
assert.equal(lifecycle.candidate,null);

// Reentry must require a *new* explicit comparison, never restore a cache.
ticket=lifecycle.begin(base);
assert.equal(lifecycle.accept(ticket,observation).status,"candidate");
lifecycle.revoke();
assert.equal(lifecycle.candidate,null);
const fresh=new MarkerCandidateLifecycle();
assert.equal(fresh.candidate,null);
const latest=fresh.begin(base);
assert.equal(fresh.accept(latest,observation).status,"candidate");

for(const bad of [
  {...base,tabId:0},{...base,windowId:-1},
  {...base,tabId:"17"},{...base,token:"not-a-uuid"}
]){
  assert.equal(lifecycle.begin(bad),null);
  assert.equal(lifecycle.candidate,null);
}
ticket=lifecycle.begin(base);
for(const bad of [
  {...observation,conId:0},{...observation,conId:1.1},
  {...observation,output:"DP-3\nsecret"},
  {...observation,workspace:""}, {...observation,workspace:"x".repeat(129)}
]){
  assert.equal(lifecycle.accept(ticket,bad).status,"invalid");
  assert.equal(lifecycle.candidate,null);
  ticket=lifecycle.begin(base);
}

// No storage, polling, window movement or restore authorization.
const ext="../../integrations/machine/brave-topology/";
const js=name=>readFileSync(new URL(ext+name,import.meta.url),"utf8");
const source=js("marker.mjs");
const core=js("marker-lifecycle.mjs");
const popup=js("marker.html");
assert.ok(source.includes('import {MarkerCandidateLifecycle} from "./marker-lifecycle.mjs"'));
assert.ok(source.includes('window.addEventListener("blur"'));
assert.ok(source.includes('document.addEventListener("visibilitychange"'));
assert.ok(source.includes('window.addEventListener("pagehide"'));
assert.ok(source.includes('if (document.hidden) revokeCandidate('));
assert.ok(source.includes('const after = await ownTab()'));
assert.ok(source.includes('association.isCurrent(ticket)'));
assert.ok(source.includes('association.accept(ticket, {'));
assert.ok(source.includes('association.revoke();\n  try {'));
assert.ok(source.includes("IN MEMORY ONLY // INVALIDATED ON FOCUS LOSS"));
assert.ok(popup.includes("COMPARE THIS WINDOW WITH SWAY ONCE"));
assert.ok(popup.includes("CLOSE THIS TEST TAB"));
for(const file of [source,core]){
  for(const banned of [
    "chrome.storage.", "chrome.sessions.", "chrome.tabs.update(",
    "chrome.windows.update(", "chrome.windows.create(",
    "setInterval(", "setTimeout(", "fetch(", "WebSocket",
    "localStorage", "sessionStorage", "IndexedDB",
    "swaymsg move", "swaymsg focus", "restore_allowed: true"
  ]) assert.equal(file.includes(banned),false,banned);
}
console.log("MACHINE marker candidate: revalidate/revoke/stale/changed // PASS");
