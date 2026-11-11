import {
  FOCUS_HOST_NAME, makeFocusObserveRequest, checkFocusObserveResponse
} from "./focus-observe-protocol.mjs";

// Separate one-click diagnostic, not the transport probe. Browser-local IDs
// never leave the extension and host-side Sway IDs never leave the host.
// No automatic permission request, background task, state or browser action.
const trigger = document.getElementById("observe-focus");
const status = document.getElementById("focus-status");
let busy = false;

async function observeOnce() {
  if (busy) return;
  busy = true;
  trigger.disabled = true;
  status.textContent = "READING FOCUS // NOT YET LINKED";
  try {
    if (!chrome.permissions || !chrome.runtime || !chrome.windows
        || typeof chrome.windows.getCurrent !== "function") {
      throw new Error("unavailable");
    }
    const granted = await chrome.permissions.contains({
      permissions: ["nativeMessaging"],
    });
    if (!granted) {
      status.textContent = "ALLOW LOCAL CONNECTION FIRST // NO HOST CONTACT";
      return;
    }
    const current = await chrome.windows.getCurrent({populate: false});
    if (!current || current.type !== "normal" || current.incognito !== false
        || !Number.isSafeInteger(current.id) || current.id <= 0) {
      status.textContent = "NORMAL NON-PRIVATE BRAVE WINDOW REQUIRED";
      return;
    }
    const browserWindowId = current.id;
    const challenge = crypto.randomUUID();
    const response = await chrome.runtime.sendNativeMessage(
      FOCUS_HOST_NAME, makeFocusObserveRequest(challenge));
    const witness = checkFocusObserveResponse(challenge, response);
    if (witness.status === "host_brave_focus_observed_unverified") {
      // Same-click timing is not an authenticated Chromium/Wayland identity.
      status.textContent = "BRAVE TEMP " + browserWindowId
        + " // SWAY " + witness.output + " / " + witness.workspace
        + " // CO-OBSERVED // UNLINKED // NO RESTORE";
    } else {
      status.textContent = "NO STABLE BRAVE HOST FOCUS // NOT LINKED";
    }
  } catch {
    // Do not disclose host error, paths, browser state or Sway payloads.
    status.textContent = "FOCUS TEST UNAVAILABLE // CHECK ISOLATED HOST";
  } finally {
    busy = false;
    trigger.disabled = false;
  }
}

trigger.addEventListener("click", observeOnce);
