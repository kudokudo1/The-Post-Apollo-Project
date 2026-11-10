import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  FOCUS_HOST_NAME, FOCUS_REQUEST_KIND, FOCUS_RESPONSE_KIND,
  makeFocusObserveRequest, checkFocusObserveResponse,
} from "../../integrations/machine/brave-topology/focus-observe-protocol.mjs";

const nonce = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
assert.equal(FOCUS_HOST_NAME, "org.postapollo.machine_brave_focus_observe");
assert.deepEqual(makeFocusObserveRequest(nonce), {
  kind: FOCUS_REQUEST_KIND, challenge: nonce
});
const good = {
  kind: FOCUS_RESPONSE_KIND,
  status: "host_brave_focus_observed_unverified",
  challenge: nonce, read_only: true,
  host_brave_focus_observed: true, host_focus_stable_two_reads: true,
  observed_output: "DP-3", observed_workspace: "1",
  browser_window_id: null,
  extension_origin_argument_observed: true,
  extension_origin_authenticated: false,
  browser_to_sway_identity_verified: false,
  private_window_exclusion_verified_by_host: false,
  restart_session_identity_verified: false,
  session_capture_allowed: false,
  restore_allowed: false, safe_actions: [],
};
assert.deepEqual(checkFocusObserveResponse(nonce, good), {
  status: good.status, output: "DP-3", workspace: "1",
  browser_to_sway_identity_verified: false,
  restore_allowed: false, safe_actions: [],
});
const missing = {...good, status:"no_host_focus_candidate",
  host_brave_focus_observed:false, host_focus_stable_two_reads:false,
  observed_output:null, observed_workspace:null,
};
assert.deepEqual(checkFocusObserveResponse(nonce, missing), {
  status:missing.status, output:null, workspace:null,
  browser_to_sway_identity_verified:false, restore_allowed:false,
  safe_actions:[],
});

for (const bad of [null, 1, {}, [], "x",
  {...good, status:"verified"},
  {...good, status:"no_host_focus_candidate"},
  {...good, challenge:"00000000-0000-4000-8000-000000000124"},
  {...good, browser_window_id:12},
  {...good, extension_origin_authenticated:true},
  {...good, browser_to_sway_identity_verified:true},
  {...good, private_window_exclusion_verified_by_host:true},
  {...good, session_capture_allowed:true},
  {...good, restore_allowed:true},
  {...good, safe_actions:["move"]},
  {...good, observed_output:"DP-3\nsecret"},
  {...good, observed_workspace:"\tprivate"},
  {...good, title:"SECRET"}, {...good, url:"https://secret.test"},
  {...missing, observed_output:"DP-3"},
  {...missing, host_brave_focus_observed:true},
]) {
  assert.throws(() => checkFocusObserveResponse(nonce, bad),
                /FOCUS OBSERVATION REJECTED/);
}
for (const bad of [undefined,null,"",123,nonce.toUpperCase(),
                    "00000000-0000-4000", "a".repeat(64)]) {
  assert.throws(() => makeFocusObserveRequest(bad),
                /INVALID FOCUS CHALLENGE/);
}

const ui = readFileSync(
  new URL("../../integrations/machine/brave-topology/focus-observe-ui.mjs",
    import.meta.url), "utf8");
const html = readFileSync(
  new URL("../../integrations/machine/brave-topology/popup.html",
    import.meta.url), "utf8");
const manifest = JSON.parse(readFileSync(
  new URL("../../integrations/machine/brave-topology/manifest.json",
    import.meta.url), "utf8"));
assert.ok(html.includes('id="observe-focus"'));
assert.ok(html.includes('src="focus-observe-ui.mjs"'));
assert.ok(ui.includes('trigger.addEventListener("click", observeOnce)'));
assert.ok(ui.includes('chrome.permissions.contains('));
assert.ok(ui.includes('current.incognito !== false'));
assert.ok(ui.includes('current.type !== "normal"'));
assert.ok(ui.includes('chrome.windows.getCurrent({populate: false})'));
assert.ok(ui.includes('FOCUS_HOST_NAME, makeFocusObserveRequest(challenge)'));
assert.ok(ui.includes("browserWindowId = current.id"));
assert.ok(ui.includes(" // UNLINKED // NO RESTORE"));
assert.ok(ui.indexOf("chrome.permissions.contains(")
          < ui.indexOf("chrome.runtime.sendNativeMessage("));
for (const forbidden of [
  "chrome.permissions.request", "chrome.windows.update",
  "chrome.windows.create", "chrome.tabs.", "chrome.sessions.",
  "chrome.storage.", "chrome.debugger.", "localStorage",
  "sessionStorage", "fetch(", "WebSocket", "XMLHttpRequest",
  "setInterval(", "setTimeout(", "console.log(", "window.location",
]) assert.equal(ui.includes(forbidden), false, forbidden);
assert.deepEqual(manifest.permissions, []);
assert.deepEqual(manifest.host_permissions, []);
assert.deepEqual(manifest.optional_permissions, ["nativeMessaging"]);
assert.equal(manifest.incognito, "not_allowed");

console.log("MACHINE Brave one-click co-observation protocol + no-authority UI PASS");
