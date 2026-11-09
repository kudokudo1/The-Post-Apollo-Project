# MACHINE // Brave window topology: opt-in read-only pilot

**Patient:** `The-Post-Apollo-Project`  
**Room:** TimeW MACHINE / per-application session recovery  
**Role:** External Hospital-compatible DOC worker, not registered in live Hospital  
**Assignment:** Establish the first actual browser API inspection seam without
activating host, tab/session access, restore actions or production collection  
**Parent:** M2b session identity sidecar; M2c adapter schema; M2d synthetic
correlation; M2d2 synthetic one-shot challenge, all already merged  
**State:** GitHub draft / no browser extension installed or enabled

## Mechanism and proof boundaries

The existing MACHINE geometry checkpoint saves individual window UUIDs,
output and workspace, rectangles and tiling shape. It has **no stable Brave
session identity**; its window UUIDs are checkpoint-local, while the
compositor's container IDs are process-lifetime. Matching 17 windows of
the same browser by app ID, coordinates or tab count would be a guess.

Chrome/Brave's Manifest V3 `chrome.windows.getAll({populate: true,
windowTypes: ["normal"]})` API can return each normal browser window
and its tab objects. Chromium's documented API exposes tab structural
fields without the sensitive `tabs` permission. URLs, titles,
pending URLs and favicons require additional permissions; **this pilot
requests none**.

Official references:
- https://developer.chrome.com/docs/extensions/reference/api/windows
- https://developer.chrome.com/docs/extensions/reference/api/tabs
- https://brave.com/learn/using-chrome-extensions-in-brave/

The new optional directory is:
`integrations/machine/brave-topology/`

- `manifest.json`: MV3, **zero extension and host permissions**,
  `incognito: not_allowed`, no service worker, content script, externally
  connectable origin or native messaging.
- `popup.html` + `popup.css`: a tiny Post-Apollo-style, explicitly
  user-opened browser action panel with a REFRESH WINDOWS button.
- `popup.mjs`: calls browser `getAll` and `getCurrent` only while the
  user has the popup open. No polling, timers, persistent storage, logs,
  background startup or network requests.
- `topology.mjs`: pure strict projection into per-window temporary
  **browser** ID, local-current-window indicator, tab count, pinned count
  and active tab *index*. No tab IDs, titles, URLs, profile paths,
  session files, groups, cookies, process IDs or browsing content.

The popup is **not** the intended final Post-Apollo interface. It is a
separate, opt-in observation pilot to confirm Brave can report the correct
window structure under its actual extension API before a host link is
designed. It does not transmit its report to MACHINE or create a
checkpoint.

## Explicit capability limits

- `temporary_browser_window_id` is a **run-local browser handle**.
  Chrome documents window IDs as unique only within a browser session.
  This is not a durable Brave restore identity and not a Sway `con_id`.
- The popup highlights THIS BRAVE WINDOW by comparing the extension
  popup's current browser window with the enumerated browser windows.
  It does **not** authenticate a mapping to any compositor/OS window.
- Tab counts and pin counts are inventory, not tab restoration data.
  Without URLs or browser-supported session descriptors, MACHINE cannot
  reopen those tabs. The pilot cannot report that it can.
- The projection rejects malformed, duplicated, over-limit or
  contradictory input, skips private/incognito windows before examining
  their tabs, and never copies sensitive fields from browser objects.
- Manifest V3 and Brave's support for Chrome extensions are documented
  independently, but this PR does **not** claim installation, live
  Brave API success, native Wayland SwayPX correspondence or saved
  browser state.
- The existing saved v1 and v2 records, annotations, MARK NOW, RESTORE,
  Quickshell widgets, and old adapter registry remain unchanged.

## Verification

`tests/timew/test_machine_brave_topology.mjs` is a Node test with 17
fictional Brave windows, equal/unequal tab counts, current-window
highlighting, temporary ID changes, private windows, injected URL/title
getters that throw if touched, malformed data, duplicate IDs, tab index
conflicts, invalid active/pinned flags, and input mutation checks.

`tests/timew/test_machine_brave_topology_contract.py` inspects
the *actual* manifest and JS/HTML source: no extension permissions,
no native host/network/storage/browser modification code, private
window exclusion, strict output flags, no added TimeW process, and
preserved v1 schema. Existing M2b/M2c/M2d/M2d2 identity tests run in
the dedicated CI workflow.

These are source and synthetic tests. They do **not** demonstrate that
a Brave instance on the user's Fedora desktop reports those counts;
that needs an explicitly operator-authorized install and visual test.

## Before any production connection

1. Operator approves opt-in extension installation separately and tests
   only the counts in a real Brave profile. No local install in this PR.
2. Define a **trusted, authenticated** browser-to-host transport.
   A browser-claimed UUID or tab count is not host identity proof.
3. Define how the selected Brave browser window maps to one fresh Sway
   window without title, PID, position, ordering or app ID guessing.
   Otherwise leave the window unbound and do not move/reopen it.
4. Provide separate permission requests for session descriptors
   (potentially sensitive URLs and browser state), local encrypted
   storage, retention and revocation. Never read incognito.
5. Verify that Brave actually provides restart-stable recovery of
   selected windows and tabs before allowing RESTORE actions.
6. Existing REVIVE and RESTORE conflicts remain fail-closed; no
   automated launches, window moves or duplicate tabs on uncertainty.

**No merge, browser installation, local file modifications, Quickshell
restart, network service, or real profile access performed.**
