"use strict";

// Shared Proton read-only companion for Chromium-family MV3 and Firefox MV3.
// Browser-family manifests differ, but neither changes the wire protocol.
// User-click only. No persistent content scripts or mail actions.
// Optional MAIN-world notification-constructor counter is untrusted telemetry.
const PROTON_ORIGIN = "https://mail.proton.me";
const NATIVE_HOST = "org.postapollo.proton_mail";
const firefoxApi = typeof browser !== "undefined" && browser.runtime && browser.action ? browser : null;
const chromiumApi = typeof chrome !== "undefined" && chrome.runtime && chrome.action ? chrome : null;

function isProtonTab(tab) {
  try {
    return Boolean(tab && typeof tab.url === "string"
        && new URL(tab.url).origin === PROTON_ORIGIN);
  } catch (_) {
    return false;
  }
}

function reportReadiness(results) {
  const state = Array.isArray(results) && results.length === 1
    ? results[0].result : null;
  const counters = [
    "inspectedControls", "exactReadEnabled", "exactReadDisabled",
    "otherReadLabels", "unlabeledControls", "checkedControls",
    "toolbarReadEnabled", "toolbarReadDisabled",
    "toolbarUnreadEnabled", "toolbarUnreadDisabled", "selectedMailRows"
  ];
  if (!state || state.kind !== "PROTON_READINESS_V4"
      || state.originOk !== true
      || state.messageIdentityVerified !== false
      || state.canMutate !== false
      || typeof state.scanTruncated !== "boolean"
      || Object.keys(state).length !== 17
      || typeof state.selectedRowStructureOk !== "boolean"
      || (state.selectedRowStructureOk && state.selectedMailRows !== 1)
      || state.selectedMailRows > state.checkedControls
      || !counters.every((key) => Number.isInteger(state[key])
         && state[key] >= 0 && state[key] <= 500)
      || state.exactReadEnabled + state.exactReadDisabled
         + state.otherReadLabels > state.inspectedControls
      || state.toolbarReadEnabled + state.toolbarReadDisabled
         + state.toolbarUnreadEnabled + state.toolbarUnreadDisabled
         > state.inspectedControls
      || state.unlabeledControls > state.inspectedControls
      || state.checkedControls > 20) {
    console.warn("Post-Apollo Proton: readiness probe unavailable");
    return;
  }
  // Numeric, bounded counts only. No raw labels, page state, or mailbox data.
  // An exact match (even just one) is never a verified message identity.
  console.info("Post-Apollo Proton: read-only UI counts"
    + " exactEnabled=" + state.exactReadEnabled
    + " exactDisabled=" + state.exactReadDisabled
    + " otherEnglishReadLabels=" + state.otherReadLabels
    + " unlabeledControls=" + state.unlabeledControls
    + " checkedControls=" + state.checkedControls
    + " selectedMailRows=" + state.selectedMailRows
    + " selectedRowStructureOk=" + state.selectedRowStructureOk
    + " toolbarReadEnabled=" + state.toolbarReadEnabled
    + " toolbarReadDisabled=" + state.toolbarReadDisabled
    + " toolbarUnreadEnabled=" + state.toolbarUnreadEnabled
    + " toolbarUnreadDisabled=" + state.toolbarUnreadDisabled
    + " inspected=" + state.inspectedControls
    + " truncated=" + state.scanTruncated
    + "; identity NOT verified");
}

// This result is page-realm telemetry, NEVER proof of message identity.
// The page could forge or interfere with it. No page-provided value is logged.
function reportEventPilot(results) {
  const data = Array.isArray(results) && results.length === 1
    ? results[0].result : null;
  const stages = ["started", "stopped", "expired", "unavailable", "wrong-origin"];
  if (!data || typeof data !== "object"
      || Object.keys(data).length !== 8
      || data.kind !== "PROTON_EVENT_PILOT_V1"
      || !stages.includes(data.stage)
      || typeof data.originOk !== "boolean"
      || (data.stage === "wrong-origin") !== (data.originOk === false)
      || !Number.isInteger(data.attempts)
      || data.attempts < 0 || data.attempts > 20
      || typeof data.capped !== "boolean"
      || data.windowMs !== 90000
      || data.messageIdentityVerified !== false
      || data.canMutate !== false
      || (data.stage === "started" &&
          (data.attempts !== 0 || data.capped))) {
    console.warn("Post-Apollo Proton: event pilot unavailable");
    return;
  }
  // Fixed schema only. No Notification tag, title, body, ID or page URL.
  console.info("Post-Apollo Proton: event pilot stage=" + data.stage
    + " attempts=" + data.attempts
    + " capped=" + data.capped
    + "; page observation only; identity NOT verified");
}

function inspectNotificationEventPilot(tab) {
  if (!tab || !Number.isSafeInteger(tab.id) || tab.id < 0)
    return;
  const api = firefoxApi || chromiumApi;
  if (!api || !api.scripting
      || typeof api.scripting.executeScript !== "function")
    return;

  const details = {
    target: {tabId: tab.id},
    files: ["notification_event_pilot.js"],
    world: "MAIN"
  };
  if (firefoxApi) {
    browser.scripting.executeScript(details)
      .then(reportEventPilot,
        () => console.warn("Post-Apollo Proton: event pilot unavailable"));
  } else {
    chrome.scripting.executeScript(details, (results) => {
      if (chrome.runtime.lastError) {
        console.warn("Post-Apollo Proton: event pilot unavailable");
        return;
      }
      reportEventPilot(results);
    });
  }
}

function inspectReadiness(tab) {
  if (!tab || !Number.isSafeInteger(tab.id) || tab.id < 0)
    return;
  const api = firefoxApi || chromiumApi;
  if (!api || !api.scripting || typeof api.scripting.executeScript !== "function")
    return;
  const details = {
    target: {tabId: tab.id},
    files: ["readiness_probe.js"]
  };
  if (firefoxApi) {
    browser.scripting.executeScript(details)
      .then(reportReadiness, () => console.warn(
        "Post-Apollo Proton: readiness probe unavailable"));
  } else {
    chrome.scripting.executeScript(details, (results) => {
      if (chrome.runtime.lastError) {
        console.warn("Post-Apollo Proton: readiness probe unavailable");
        return;
      }
      reportReadiness(results);
    });
  }
}

function inspectHandshake(response, tab) {
  // The read-only host MUST never claim it can identify or mutate mail.
  if (!response || response.protocol !== 1
      || response.kind !== "PONG"
      || response.origin !== PROTON_ORIGIN
      || response.mailboxAccess !== false
      || response.messageIdentityVerified !== false
      || !Array.isArray(response.capabilities)
      || response.capabilities.length !== 0) {
    console.warn("Post-Apollo Proton: unexpected handshake response");
    return;
  }
  console.info("Post-Apollo Proton: read-only native handshake OK");
}

function reportUnavailable() {
  // Deliberately do not log a browser URL, native error or mailbox data.
  console.warn("Post-Apollo Proton: native host not connected");
}

function onCompanionClicked(tab) {
  if (!isProtonTab(tab))
    return;
  // This observation is read-only and does not need native-host privileges.
  // It can be manually inspected before a host is installed/authorized.
  inspectReadiness(tab);
  inspectNotificationEventPilot(tab);
  const request = { protocol: 1, kind: "PING" };
  if (firefoxApi) {
    // Firefox WebExtensions return a Promise from sendNativeMessage.
    browser.runtime.sendNativeMessage(NATIVE_HOST, request)
      .then((response) => inspectHandshake(response, tab), reportUnavailable);
  } else if (chromiumApi) {
    // Chrome/Brave/Edge/Opera callback-style native messaging.
    chrome.runtime.sendNativeMessage(NATIVE_HOST, request, (response) => {
      if (chrome.runtime.lastError) {
        reportUnavailable();
        return;
      }
      inspectHandshake(response, tab);
    });
  }
}

if (firefoxApi)
  browser.action.onClicked.addListener(onCompanionClicked);
else if (chromiumApi)
  chrome.action.onClicked.addListener(onCompanionClicked);
