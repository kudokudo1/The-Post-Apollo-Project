/* MACHINE // Explicit current-window tab-eligibility preview.
 *
 * The optional 'tabs' permission is broad browser-wide address access.
 * Never auto-request. Only a separately clicked preview uses it, and only
 * for the current NORMAL non-private browser window. Addresses stay in
 * function-local memory and only URL-free classification reaches the DOM.
 * No storage, logging, native host, network, window changes or restoration.
 */
import {planSyntheticBraveSession} from "./session-recovery-plan.mjs";

const grantButton = document.getElementById("grant-tabs");
const previewButton = document.getElementById("preview-tabs");
const revokeButton = document.getElementById("revoke-tabs");
const status = document.getElementById("tab-preview-status");
const summary = document.getElementById("tab-preview-summary");
const list = document.getElementById("tab-preview-list");
const ACCESS = {permissions: ["tabs"]};
let busy = false;
let epoch = 0;
let closed = false;

function clearPreview() {
  summary.textContent = "";
  list.replaceChildren();
}

function setBusy(value) {
  busy = value;
  grantButton.disabled = value;
  previewButton.disabled = value;
  revokeButton.disabled = value;
}

function active(ticket) {
  return !closed && epoch === ticket;
}

function rowText(value) {
  const item = document.createElement("li");
  item.textContent = value;
  return item;
}

async function refreshPermission() {
  // This reads only the permission bit. No browser tabs or URLs are read.
  try {
    const granted = await chrome.permissions.contains(ACCESS);
    if (!closed && !busy) {
      status.textContent = granted
        ? "TAB ACCESS GRANTED // NO ADDRESSES READ YET"
        : "TAB ACCESS NOT GRANTED // NO ADDRESSES READ";
    }
  } catch {
    if (!closed && !busy) status.textContent = "PERMISSION STATE UNAVAILABLE";
  }
}

async function grantAccess() {
  if (busy || closed) return;
  const ticket = ++epoch;
  clearPreview();
  setBusy(true);
  status.textContent = "REQUESTING BROAD TAB ADDRESS ACCESS // NO PREVIEW YET";
  try {
    // Mandatory direct user gesture; no await before request().
    const granted = await chrome.permissions.request(ACCESS);
    if (!active(ticket)) return;
    status.textContent = granted
      ? "TAB ACCESS GRANTED // CLICK PREVIEW SEPARATELY"
      : "TAB ACCESS DECLINED // NO ADDRESSES READ";
  } catch {
    if (active(ticket)) status.textContent = "TAB PERMISSION REQUEST REFUSED";
  } finally {
    if (active(ticket)) setBusy(false);
  }
}

async function revokeAccess() {
  if (busy || closed) return;
  const ticket = ++epoch;
  clearPreview();
  setBusy(true);
  status.textContent = "REVOKING ACTIVE TAB ACCESS";
  try {
    const removed = await chrome.permissions.remove(ACCESS);
    const stillGranted = await chrome.permissions.contains(ACCESS);
    if (!active(ticket)) return;
    status.textContent = removed && !stillGranted
      ? "ACTIVE TAB ACCESS REVOKED // PREVIEW CLEARED"
      : "REVOCATION NOT CONFIRMED // NO PREVIEW";
  } catch {
    if (active(ticket)) status.textContent = "REVOCATION NOT CONFIRMED // NO PREVIEW";
  } finally {
    if (active(ticket)) setBusy(false);
  }
}

async function previewOnce() {
  if (busy || closed) return;
  const ticket = ++epoch;
  clearPreview();
  setBusy(true);
  status.textContent = "CHECKING TAB ACCESS // NO OUTPUT YET";
  try {
    if (await chrome.permissions.contains(ACCESS) !== true || !active(ticket)) {
      if (active(ticket)) status.textContent = "TAB ACCESS REQUIRED // NO PREVIEW";
      return;
    }
    // Check window type/privacy BEFORE requesting tab metadata.
    const selected = await chrome.windows.getCurrent({populate:false});
    if (!active(ticket)) return;
    if (!selected || selected.type !== "normal"
        || selected.incognito !== false
        || !Number.isSafeInteger(selected.id) || selected.id <= 0) {
      throw new Error("unsupported window");
    }
    const current = await chrome.windows.get(selected.id, {populate:true});
    if (!active(ticket)) return;
    if (!current || current.id !== selected.id || current.type !== "normal"
        || current.incognito !== false || !Array.isArray(current.tabs)) {
      throw new Error("window changed");
    }
    // The raw tab URL strings are examined only inside this call. The
    // projector returns no URL, title, tab ID, process or profile data.
    const plan = planSyntheticBraveSession([{
      operator_label: "CURRENT WINDOW",
      incognito: current.incognito, type: current.type,
      tabs: current.tabs,
    }]);
    const latest = await chrome.windows.getCurrent({populate:false});
    const allowed = await chrome.permissions.contains(ACCESS);
    if (!active(ticket)) return;
    if (!latest || latest.id !== selected.id || latest.type !== "normal"
        || latest.incognito !== false || allowed !== true) {
      throw new Error("window or permission changed");
    }
    const only = plan.windows[0];
    if (!only || plan.windows.length !== 1 || plan.restore_allowed !== false
        || plan.persisted !== false || plan.user_tab_urls_exported !== false) {
      throw new Error("unexpected projection");
    }
    // Render only the redacted summary. Never display actual URL/title.
    summary.textContent = only.tab_count + " TABS // "
      + plan.counts.candidate_only + " CANDIDATE // "
      + plan.counts.requires_sensitive_review + " REVIEW // "
      + plan.counts.not_eligible + " EXCLUDED";
    list.replaceChildren(...only.tab_eligibility.map(entry =>
      rowText("TAB " + (entry.position + 1) + " // "
        + entry.eligibility.replaceAll("_"," ").toUpperCase())));
    status.textContent =
      "CURRENT WINDOW REVIEWED ONCE // MEMORY ONLY // NOTHING SAVED";
  } catch {
    if (active(ticket)) {
      clearPreview();
      status.textContent = "TAB PREVIEW REFUSED // NO DATA SAVED";
    }
  } finally {
    if (active(ticket)) setBusy(false);
  }
}

grantButton.addEventListener("click", grantAccess);
previewButton.addEventListener("click", previewOnce);
revokeButton.addEventListener("click", revokeAccess);
window.addEventListener("pagehide", () => {
  closed = true;
  epoch++;
  clearPreview();
});
window.addEventListener("blur", () => {
  epoch++;
  clearPreview();
  // Invalidate any in-flight permission/preview response, but leave the
  // popup controls usable should Brave keep the popup open after a prompt.
  if (!closed) {
    setBusy(false);
    status.textContent = "PREVIEW CLEARED ON FOCUS LOSS";
  }
});
refreshPermission();
