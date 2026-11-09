import {
  NATIVE_HOST_NAME, makeProbeRequest, checkProbeResponse
} from "./native-probe-protocol.mjs";

// The popup can display inventory without a host. All native messaging
// actions require a separate explicit click. No background connection,
// timers, site access, clipboard use or persisted permission cache.
const allow = document.getElementById("allow-local");
const test = document.getElementById("test-local");
const revoke = document.getElementById("revoke-local");
const status = document.getElementById("local-status");
let busy = false;

async function run(action) {
  if (busy) return;
  busy = true;
  for (const button of [allow, test, revoke]) button.disabled = true;
  try {
    if (!chrome.permissions || !chrome.runtime) {
      status.textContent = "LOCAL CONNECTION UNAVAILABLE";
      return;
    }
    const permission = {permissions: ["nativeMessaging"]};
    if (action === "allow") {
      const granted = await chrome.permissions.request(permission);
      status.textContent = granted
        ? "LOCAL PERMISSION GRANTED // NO HOST CONTACTED"
        : "LOCAL PERMISSION DECLINED";
    } else if (action === "revoke") {
      const removed = await chrome.permissions.remove(permission);
      status.textContent = removed
        ? "LOCAL PERMISSION REMOVED"
        : "PERMISSION NOT REMOVED // REVIEW BRAVE SETTINGS";
    } else if (action === "test") {
      if (!(await chrome.permissions.contains(permission))) {
        status.textContent = "LOCAL PERMISSION REQUIRED // ENABLE FIRST";
        return;
      }
      // Browser-window inventory and URLs are deliberately NOT sent.
      const challenge = crypto.randomUUID();
      const request = makeProbeRequest(challenge);
      const response = await chrome.runtime.sendNativeMessage(
        NATIVE_HOST_NAME, request);
      checkProbeResponse(challenge, response);
      status.textContent =
        "LOCAL TRANSPORT OBSERVED // WINDOW IDENTITY NOT VERIFIED";
    }
  } catch {
    // No host path, browser API error, origin or private payload in UI.
    status.textContent =
      "LOCAL CONNECTION FAILED // HOST MAY BE UNINSTALLED";
  } finally {
    busy = false;
    for (const button of [allow, test, revoke]) button.disabled = false;
  }
}

allow.addEventListener("click", () => run("allow"));
test.addEventListener("click", () => run("test"));
revoke.addEventListener("click", () => run("revoke"));
