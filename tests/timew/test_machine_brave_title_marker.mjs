import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {
  HOST_NAME, TITLE_PREFIX, REQUEST_KIND, RESPONSE_KIND,
  validChallenge, markerRequest, checkMarkerReply,
} from "../../integrations/machine/brave-topology/marker-protocol.mjs";

const token="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
assert.equal(HOST_NAME,"org.postapollo.machine_brave_title_marker");
assert.equal(TITLE_PREFIX,"MACHINE WINDOW CHECK ");
assert.equal(validChallenge(token),true);
assert.deepEqual(markerRequest(token),{kind:REQUEST_KIND,challenge:token});
const good={
  kind:RESPONSE_KIND,status:"transient_title_marker_observed",
  challenge:token,read_only_host:true,marker_unique_and_stable:true,
  sway_container_id:1031,output:"DP-3",workspace:"1",
  browser_window_id:null,extension_origin_authenticated:false,
  host_private_window_exclusion_verified:false,
  persistent_window_identity_verified:false,
  session_capture_allowed:false,restore_allowed:false,safe_actions:[]
};
assert.deepEqual(checkMarkerReply(token,good),{
  status:good.status,conId:1031,output:"DP-3",workspace:"1",
  sessionRestorable:false,safeActions:[]
});
const no={...good,status:"marker_not_observed",marker_unique_and_stable:false,
  sway_container_id:null,output:null,workspace:null};
assert.deepEqual(checkMarkerReply(token,no),{
  status:"marker_not_observed",conId:null,output:null,workspace:null,
  sessionRestorable:false,safeActions:[]
});
for(const bad of [
  {},null,42,[],{...good,status:"identity_verified"},
  {...good,challenge:"00000000-0000-4000-8000-000000000000"},
  {...good,restore_allowed:true}, {...good,safe_actions:["move"]},
  {...good,extension_origin_authenticated:true},
  {...good,host_private_window_exclusion_verified:true},
  {...good,persistent_window_identity_verified:true},
  {...good,browser_window_id:100},
  {...good,sway_container_id:0}, {...good,output:"DP-3\nSECRET"},
  {...good,workspace:"1\tPRIVATE"},{...good,url:"https://secret.example"},
  {...no,output:"DP-3"},{...no,marker_unique_and_stable:true}
]){
  assert.throws(()=>checkMarkerReply(token,bad),/MARKER REPLY REJECTED/);
}
for(const t of [null,1,true,"",token.toUpperCase(),"not-a-uuid"]){
  assert.equal(validChallenge(t),false);
  assert.throws(()=>markerRequest(t),/INVALID MARKER/);
}

const path="../../integrations/machine/brave-topology/";
const source = name => readFileSync(new URL(path+name,import.meta.url),"utf8");
const open=source("open-marker-ui.mjs");
const marker=source("marker.mjs");
const popup=source("popup.html");
const page=source("marker.html");
const manifest=JSON.parse(source("manifest.json"));

assert.ok(popup.includes('id="open-marker"'));
assert.ok(popup.includes('src="open-marker-ui.mjs"'));
assert.ok(page.includes('id="verify-marker"'));
assert.ok(page.includes('id="close-marker"'));
assert.ok(page.includes('src="marker.mjs"'));
assert.ok(open.includes('openButton.addEventListener("click", openMarker)'));
assert.ok(open.includes('crypto.randomUUID()'));
assert.ok(open.includes('chrome.tabs.create({'));
assert.ok(open.includes('windowId: win.id, active: true, pinned: false'));
assert.ok(open.includes('chrome.runtime.getURL("marker.html#" + token)'));
assert.ok(open.includes('win.incognito !== false'));
assert.ok(marker.includes('document.title = TITLE_PREFIX + token'));
assert.ok(marker.includes('chrome.tabs.getCurrent()'));
assert.ok(marker.includes('chrome.windows.get(tab.windowId'));
assert.ok(marker.includes('!tab.active'));
assert.ok(marker.includes('win.focused !== true'));
assert.ok(marker.includes('chrome.permissions.contains('));
assert.ok(marker.includes('chrome.runtime.sendNativeMessage('));
assert.ok(marker.includes('checkMarkerReply(token, response)'));
assert.ok(marker.includes('chrome.tabs.remove(tab.id)'));
assert.ok(marker.includes('"TITLE MARKER MATCHED // TEMPORARY // NO RESTORE"'));
assert.ok(marker.includes('verify.addEventListener("click", compare)'));
assert.ok(marker.includes('close.addEventListener("click", closeOwn)'));
assert.ok(marker.indexOf("chrome.permissions.contains(")
          < marker.indexOf("chrome.runtime.sendNativeMessage("));
for(const src of [open,marker]){
  for(const forbidden of [
    "chrome.storage.", "chrome.sessions.", "chrome.debugger.",
    "chrome.tabs.update(", "chrome.windows.update(", "chrome.windows.create(",
    "fetch(", "XMLHttpRequest", "WebSocket", "localStorage",
    "sessionStorage", "setTimeout(", "setInterval(", "innerHTML",
    "chrome.tabs.query(", "chrome.tabs.executeScript(",
  ]) assert.equal(src.includes(forbidden),false,forbidden);
}
assert.deepEqual(manifest.permissions,[]);
assert.deepEqual(manifest.host_permissions,[]);
assert.deepEqual(manifest.optional_permissions,["nativeMessaging"]);
assert.equal(manifest.incognito,"not_allowed");
assert.equal(Object.hasOwn(manifest,"background"),false);

console.log("MACHINE title marker // strict protocol and explicit tab create/close PASS");
