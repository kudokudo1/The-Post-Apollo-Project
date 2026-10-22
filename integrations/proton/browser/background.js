"use strict";

// Shared Proton read-only companion for Chromium-family MV3 and Firefox MV3.
// Browser-family manifests differ, but neither changes the wire protocol.
// User click only; no content scripts, DOM, mail, credentials or mutations.
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
  if (!state || state.kind !== "PROTON_READINESS_V1"
      || state.originOk !== true
      || state.messageIdentityVerified !== false
      || state.canMutate !== false
      || !Number.isInteger(state.markReadCandidates)
      || state.markReadCandidates < 0 || state.markReadCandidates > 2) {
    console.warn("Post-Apollo Proton: readiness probe unavailable");
    return;
  }
  // We cannot derive an authenticated email identity from a button's label.
  // Zero/two candidates mean unrecognised or ambiguous UI; one is just a hint.
  console.info(state.markReadCandidates === 1
    ? "Post-Apollo Proton: one read-control candidate; identity NOT verified"
    : "Post-Apollo Proton: no unambiguous read-control candidate");
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
