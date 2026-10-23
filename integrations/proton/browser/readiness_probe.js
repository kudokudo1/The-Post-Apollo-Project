"use strict";

// Runs only following an explicit companion click on the exact Proton origin.
// Read-only count telemetry: never export DOM, labels, subjects, addresses,
// message IDs, URLs, session data or credentials. No action is dispatched.
(() => {
  const empty = {
    kind: "PROTON_READINESS_V4",
    originOk: false,
    inspectedControls: 0,
    scanTruncated: false,
    exactReadEnabled: 0,
    exactReadDisabled: 0,
    otherReadLabels: 0,
    toolbarReadEnabled: 0,
    toolbarReadDisabled: 0,
    toolbarUnreadEnabled: 0,
    toolbarUnreadDisabled: 0,
    unlabeledControls: 0,
    checkedControls: 0,
    selectedMailRows: 0,
    selectedRowStructureOk: false,
    messageIdentityVerified: false,
    canMutate: false
  };
  if (location.origin !== "https://mail.proton.me")
    return empty;

  const buttons = document.querySelectorAll("button, [role='button']");
  const count = Math.min(500, buttons.length);
  let enabled = 0, disabled = 0, other = 0, unlabeled = 0;
  let toolbarReadEnabled = 0, toolbarReadDisabled = 0;
  let toolbarUnreadEnabled = 0, toolbarUnreadDisabled = 0;
  function normalize(value) {
    return (typeof value === "string" ? value : "")
      .trim().toLowerCase().replace(/\s+/g, " ");
  }
  for (let i = 0; i < count; ++i) {
    const element = buttons[i];
    if (!element || typeof element.getAttribute !== "function")
      continue;
    // Proton WebClients uses explicit test IDs for the toolbar buttons,
    // while the accessible help text can live in a separate tooltip.
    // Compare only these two documented constants; do not export arbitrary IDs.
    const toolbarID = element.getAttribute("data-testid");
    const isDisabled = Boolean(element.disabled)
      || element.getAttribute("aria-disabled") === "true";
    if (toolbarID === "toolbar:read") {
      if (isDisabled) toolbarReadDisabled++;
      else toolbarReadEnabled++;
    } else if (toolbarID === "toolbar:unread") {
      if (isDisabled) toolbarUnreadDisabled++;
      else toolbarUnreadEnabled++;
    }
    const aria = normalize(element.getAttribute("aria-label"));
    const title = normalize(element.getAttribute("title"));
    if (!aria && !title)
      unlabeled++;
    const isExactRead = aria === "mark as read" || title === "mark as read";
    if (isExactRead) {
      if (isDisabled)
        disabled++;
      else
        enabled++;
    } else if (/\bmark\s+(?:as\s+)?(?:un)?read\b/.test(aria)
               || /\bmark\s+(?:as\s+)?(?:un)?read\b/.test(title)) {
      // Counts potentially relevant English labels without exposing them.
      other++;
    }
  }
  // Checked controls are only an observation, NOT proof that an email is
  // selected. A page may have unrelated checkboxes or custom row widgets.
  const checked = document.querySelectorAll(
    "input[type='checkbox']:checked, [role='checkbox'][aria-checked='true']"
  ).length;

  // Proton's public Item.tsx and ItemCheckbox.tsx use matching
  // data-element-id on a mail-list row and data-item-id on its checkbox.
  // Compare them privately in-page; NEVER export either value. Note that
  // a list element can be a conversation, not necessarily one message.
  const mailCheckboxes = document.querySelectorAll(
    "input[type='checkbox'][data-testid='item-checkbox']:checked"
  );
  let coherentRows = 0;
  const mailCount = mailCheckboxes.length;
  const rowScan = Math.min(500, mailCount);
  for (let i = 0; i < rowScan; ++i) {
    const checkbox = mailCheckboxes[i];
    if (!checkbox || typeof checkbox.getAttribute !== "function"
        || typeof checkbox.closest !== "function")
      continue;
    const selectedID = checkbox.getAttribute("data-item-id");
    const row = checkbox.closest("[data-element-id]");
    if (!row || typeof row.getAttribute !== "function")
      continue;
    const rowID = row.getAttribute("data-element-id");
    if (typeof selectedID === "string" && selectedID.length > 0
        && selectedID.length <= 256 && rowID === selectedID)
      coherentRows++;
  }

  return {
    kind: "PROTON_READINESS_V4",
    originOk: true,
    inspectedControls: count,
    scanTruncated: buttons.length > 500,
    exactReadEnabled: Math.min(500, enabled),
    exactReadDisabled: Math.min(500, disabled),
    otherReadLabels: Math.min(500, other),
    toolbarReadEnabled: Math.min(500, toolbarReadEnabled),
    toolbarReadDisabled: Math.min(500, toolbarReadDisabled),
    toolbarUnreadEnabled: Math.min(500, toolbarUnreadEnabled),
    toolbarUnreadDisabled: Math.min(500, toolbarUnreadDisabled),
    unlabeledControls: Math.min(500, unlabeled),
    checkedControls: Math.min(20, checked),
    selectedMailRows: Math.min(20, mailCount),
    selectedRowStructureOk: mailCount === 1 && coherentRows === 1,
    messageIdentityVerified: false,
    canMutate: false
  };
})()
