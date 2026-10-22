"use strict";

// User-initiated pilot only. This extension has no content script, never
// reads email DOM/text, does not request network access, and has no mailbox
// mutation commands. Native messaging setup is a separate operator action.
const PROTON_ORIGIN = "https://mail.proton.me";
const NATIVE_HOST = "org.postapollo.proton_mail";

function isProtonTab(tab) {
  try {
    return Boolean(tab && tab.url
        && new URL(tab.url).origin === PROTON_ORIGIN);
  } catch (_) {
    return false;
  }
}

chrome.action.onClicked.addListener((tab) => {
  if (!isProtonTab(tab))
    return;

  chrome.runtime.sendNativeMessage(
    NATIVE_HOST,
    { protocol: 1, kind: "PING" },
    (response) => {
      if (chrome.runtime.lastError) {
        console.warn("Post-Apollo Proton: native host not connected");
        return;
      }
      if (!response || response.protocol !== 1
          || response.kind !== "PONG"
          || response.mailboxAccess !== false) {
        console.warn("Post-Apollo Proton: unexpected handshake response");
        return;
      }
      console.info("Post-Apollo Proton: read-only native handshake OK");
    }
  );
});
