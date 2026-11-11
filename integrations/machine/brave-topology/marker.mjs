import {
  HOST_NAME, TITLE_PREFIX, validChallenge, markerRequest, checkMarkerReply
} from "./marker-protocol.mjs";
import {MarkerCandidateLifecycle} from "./marker-lifecycle.mjs";

const status = document.getElementById("status");
const verify = document.getElementById("verify-marker");
const close = document.getElementById("close-marker");
const token = location.hash.slice(1);
let busy = false;
const association = new MarkerCandidateLifecycle();

function revokeCandidate(reason) {
  association.revoke();
  status.textContent = reason;
}

// Browser focus and page visibility can change independently of a native
// reply. Invalidate outstanding reads; never carry a match across tab switches.
window.addEventListener("blur", () => revokeCandidate(
  "WINDOW FOCUS LOST // CANDIDATE EXPIRED // COMPARE AGAIN"));
document.addEventListener("visibilitychange", () => {
  if (document.hidden) revokeCandidate(
    "TEST TAB HIDDEN // CANDIDATE EXPIRED // COMPARE AGAIN");
});
window.addEventListener("pagehide", () => association.revoke());

if (validChallenge(token)) {
  // The marker must actually be the active browser window's title, not a
  // guess based on focus timing or tab count. Never use a real tab title.
  document.title = TITLE_PREFIX + token;
} else {
  verify.disabled = true;
  status.textContent = "INVALID TEMPORARY MARKER // REFUSED";
}

async function ownTab() {
  const tab = await chrome.tabs.getCurrent();
  if (!tab || tab.incognito !== false || !tab.active
      || !Number.isSafeInteger(tab.id) || tab.id <= 0
      || !Number.isSafeInteger(tab.windowId) || tab.windowId <= 0) {
    throw new Error("invalid own tab");
  }
  const win = await chrome.windows.get(tab.windowId, {populate:false});
  if (!win || win.type !== "normal" || win.incognito !== false
      || win.focused !== true) throw new Error("not focused normal window");
  return tab;
}

async function compare() {
  if (busy || !validChallenge(token)) return;
  busy = true;
  verify.disabled = true;
  status.textContent = "READING SWAY TITLE MARKER // NO RESTORE";
  let ticket = null;
  try {
    const tab = await ownTab();
    if (document.hidden) throw new Error("hidden page");
    ticket = association.begin({
      tabId: tab.id, windowId: tab.windowId, token
    });
    if (ticket === null) throw new Error("invalid tab identity");
    const allowed = await chrome.permissions.contains({
      permissions: ["nativeMessaging"],
    });
    if (!association.isCurrent(ticket)) return;
    if (!allowed) {
      revokeCandidate("LOCAL CONNECTION PERMISSION REQUIRED // NO MATCH");
      return;
    }
    const response = await chrome.runtime.sendNativeMessage(
      HOST_NAME, markerRequest(token));
    if (!association.isCurrent(ticket)) return;
    const result = checkMarkerReply(token, response);
    if (result.status !== "transient_title_marker_observed") {
      revokeCandidate("MARKER NOT OBSERVED // CANDIDATE REVOKED");
      return;
    }
    // The user could change tabs or windows while native messaging runs.
    const after = await ownTab();
    if (!association.isCurrent(ticket)) return;
    if (document.hidden) throw new Error("hidden after host reply");
    const accepted = association.accept(ticket, {
      tabId: after.id, windowId: after.windowId, token,
      conId: result.conId, output: result.output,
      workspace: result.workspace
    });
    if (accepted.status === "candidate") {
      status.textContent = "BRAVE TEMP " + after.windowId
        + " // SWAY CON " + result.conId
        + " // " + result.output + " / " + result.workspace
        + "\nTITLE MARKER MATCHED // TEMPORARY // NO RESTORE"
        + "\nIN MEMORY ONLY // INVALIDATED ON FOCUS LOSS";
    } else if (accepted.status !== "stale") {
      status.textContent = "WINDOW ASSOCIATION CHANGED // REVOKED // COMPARE AGAIN";
    }
  } catch {
    if (ticket === null || association.isCurrent(ticket)) {
      revokeCandidate("MARKER CHECK REFUSED // CANDIDATE REVOKED");
    }
  } finally {
    busy = false;
    verify.disabled = false;
  }
}

async function closeOwn() {
  association.revoke();
  try {
    const tab = await chrome.tabs.getCurrent();
    if (!tab || tab.incognito !== false || !Number.isSafeInteger(tab.id)
        || tab.id <= 0) throw new Error("not own tab");
    await chrome.tabs.remove(tab.id);
  } catch {
    status.textContent = "COULD NOT CLOSE TEST TAB // CLOSE MANUALLY";
  }
}

verify.addEventListener("click", compare);
close.addEventListener("click", closeOwn);
