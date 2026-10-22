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

function inspectHandshake(response) {
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
  const request = { protocol: 1, kind: "PING" };
  if (firefoxApi) {
    // Firefox WebExtensions return a Promise from sendNativeMessage.
    browser.runtime.sendNativeMessage(NATIVE_HOST, request)
      .then(inspectHandshake, reportUnavailable);
  } else if (chromiumApi) {
    // Chrome/Brave/Edge/Opera callback-style native messaging.
    chrome.runtime.sendNativeMessage(NATIVE_HOST, request, (response) => {
      if (chrome.runtime.lastError) {
        reportUnavailable();
        return;
      }
      inspectHandshake(response);
    });
  }
}

if (firefoxApi)
  browser.action.onClicked.addListener(onCompanionClicked);
else if (chromiumApi)
  chrome.action.onClicked.addListener(onCompanionClicked);
