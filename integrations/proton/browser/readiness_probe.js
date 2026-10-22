"use strict";

// Executed ONLY after a click on the companion icon in an exact Proton-origin
// tab, using activeTab + scripting. This is a PAGE-SHAPE PROBE, not mailbox
// authentication or message identity. No mailbox operation is performed.
//
// Read only ARIA/title attributes of button-like controls. Never copy page
// contents, subject, addresses, URLs, message IDs, tokens or form fields.
(() => {
  const empty = {
    kind: "PROTON_READINESS_V1",
    originOk: false,
    markReadCandidates: 0,
    messageIdentityVerified: false,
    canMutate: false
  };
  if (location.origin !== "https://mail.proton.me")
    return empty;

  let count = 0;
  const buttons = document.querySelectorAll("button, [role='button']");
  for (let i = 0; i < buttons.length && i < 500; i++) {
    const element = buttons[i];
    if (!element || typeof element.getAttribute !== "function")
      continue;
    const aria = element.getAttribute("aria-label") || "";
    const title = element.getAttribute("title") || "";
    if ((aria === "Mark as read" || title === "Mark as read")
        && !element.disabled && element.getAttribute("aria-disabled") !== "true")
      count++;
    // Result is intentionally capped, and never identifies a clicked button.
    if (count >= 2)
      break;
  }
  return {
    kind: "PROTON_READINESS_V1",
    originOk: true,
    markReadCandidates: Math.min(2, count),
    messageIdentityVerified: false,
    canMutate: false
  };
})()
