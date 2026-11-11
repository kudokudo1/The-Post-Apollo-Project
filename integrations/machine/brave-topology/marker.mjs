import {
  HOST_NAME, TITLE_PREFIX, validChallenge, markerRequest, checkMarkerReply
} from "./marker-protocol.mjs";

const status = document.getElementById("status");
const verify = document.getElementById("verify-marker");
const close = document.getElementById("close-marker");
const token = location.hash.slice(1);
let busy = false;

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
  try {
    const tab = await ownTab();
    const allowed = await chrome.permissions.contains({
      permissions: ["nativeMessaging"],
    });
    if (!allowed) {
      status.textContent = "LOCAL CONNECTION PERMISSION REQUIRED // REFUSED";
      return;
    }
    const response = await chrome.runtime.sendNativeMessage(
      HOST_NAME, markerRequest(token));
    const result = checkMarkerReply(token, response);
    if (result.status === "transient_title_marker_observed") {
      status.textContent = "BRAVE TEMP " + tab.windowId
        + " // SWAY CON " + result.conId
        + " // " + result.output + " / " + result.workspace
        + "\nTITLE MARKER MATCHED // TEMPORARY // NO RESTORE";
    } else {
      status.textContent = "MARKER NOT OBSERVED // NO WINDOW MATCH";
    }
  } catch {
    status.textContent = "MARKER CHECK REFUSED // REVIEW DISPOSABLE HOST";
  } finally {
    busy = false;
    verify.disabled = false;
  }
}

async function closeOwn() {
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
