# TimeW MACHINE // Disposable Brave title-marker window correlation

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / Brave-to-Sway individual window identification  
**STAFF ROLE:** External Hospital-compatible DOC; live Hospital attachment not established  
**ASSIGNMENT:** Continue beyond co-observed focus toward a transient individual-window link  
**STATE:** Repository-only proof of concept. No local installation, merge or production activation.

## IMPLEMENTATION

The previous live test produced:
`BRAVE TEMP … // SWAY DP-3 / 1 // CO-OBSERVED // UNLINKED // NO RESTORE`.
It proved both independent systems observed a focused Brave application.
It did not identify the same *specific* top-level window.

An opt-in experiment now attaches a unique marker to a temporary tab
in the selected Brave window:

1. In the disposable Brave extension popup, the operator clicks
   **OPEN TEMPORARY WINDOW CHECK TAB**.
2. The extension first requires a normal, non-private browser window.
   It creates **one new active extension-only tab** in that same window
   using `chrome.tabs.create`. Existing tabs are not read, navigated,
   pinned, moved, closed, or copied. Opening the tab changes which tab
   is active, and closing it returns control to the other tab(s).
3. The new tab sets its title to `MACHINE WINDOW CHECK <random UUID>`.
   The visible page offers an explicit **COMPARE THIS WINDOW WITH SWAY
   ONCE** button. Nothing runs in the background.
4. Only after that second click, and only after confirming the test tab
   is active, its window is normal/non-private/focused, and the separate
   optional `nativeMessaging` permission is already granted, does the
   page send the UUID to an **independently registered native host**:
   `org.postapollo.machine_brave_title_marker`.
5. That host reads the Sway window tree twice. It requires a unique
   focused Brave-class client with exactly the expected marker title,
   optionally followed by a small allowlisted Brave suffix. It rejects
   duplicates (even in nonfocused windows), focus changes, foreign apps,
   malformed names and unsynchronized output/workspace information.
6. A successful reply exposes a **transient Sway container ID** and
   output/workspace. The browser page locally associates them with its
   own `chrome.tabs.getCurrent().windowId` for display:
   `BRAVE TEMP N // SWAY CON M // DP-3 / 1` and
   `TITLE MARKER MATCHED // TEMPORARY // NO RESTORE`.
7. The operator clicks **CLOSE THIS TEST TAB**. The tab is not deleted
   by any automated timer. The association is intentionally not stored
   or passed to TimeW.

This avoids using tab counts or focus *timing alone* to select a window.
It does not require permission to read existing tab titles, URLs,
cookies, page data or browsing history. Chromium's extension API
supports creating a tab without the broad `tabs` permission; the
Sway IPC tree reports window titles.

## HOW TO USE (only after independent review and separate local authorization)

The local test requires the same isolated test profile used for the
prior native transport/focus experiments. Do not use a normal Brave
instance. The existing marked trial must already pass both
`MachineBraveDisposableTrial.py verify ROOT` and
`MachineBraveFocusTrial.py verify ROOT`.

After the operator specifically authorizes local registration:

```sh
python3 -B -I services/time/MachineBraveTitleTrial.py register \
  /tmp/YOUR_EXISTING_VERIFIED_TRIAL YOUR_TEST_EXTENSION_ID
python3 -B -I services/time/MachineBraveTitleTrial.py verify \
  /tmp/YOUR_EXISTING_VERIFIED_TRIAL
```

The installer refuses ordinary Brave paths, unmarked directories,
incorrect extension origins, existing/colliding registration files,
source tampering, symlinks and unsafe modes. It creates only two new
source files and one exact-origin host manifest inside the trial's
`xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts/`.
The separate already-registered transport and focus hosts are not
overwritten. On a failed write, it removes only files created by that
attempt.

The operator then reloads the test extension in
`brave://extensions`, opens it, chooses **OPEN TEMPORARY WINDOW CHECK
TAB**, clicks **COMPARE THIS WINDOW WITH SWAY ONCE** inside the new
tab, notes the result and clicks **CLOSE THIS TEST TAB**.

If the test fails, leave the older tabs untouched; close the
temporary marker tab manually. If the tab is still visible, it can be
closed with the ordinary browser tab X. No cleanup script or overwrite
of real browser data is part of the trial.

## VERIFY

CI tests pure title extraction from six synthetic Sway tree snapshots,
unique vs duplicate marker, same focused compositor client, changed
focus, unsupported app, invalid title suffix, private title redaction
and strict framing/nonce challenges.

Further tests register and verify the new host in a real private /tmp
fixture, refuse duplicate/wrong-origin/user-home/unsafe/symlinked paths,
verify source bytes/modes, and assert rollback on injected failure.
Extension tests check explicit click gates, unchanged required
permissions, new-tab-only creation and self-close control, strict
no-restore result schema, and unchanged legacy focus/probe behavior.

**These tests cannot establish live Wayland title behavior on Fedora.**
The operator's live trial and independent review remain uncompleted.

## WATCH OUT FOR

- Creating a test tab **changes the browser's active tab** in the
  selected disposable window. It is not a passive observation.
- The challenge is visible in the disposable tab title, and a separate
  local client could imitate it. A matching title is strong
  *correlation evidence*, not cryptographic/OS-attested ownership.
- The host's extension-origin argument is not authenticated against all
  local processes. Host-side private/incognito exclusion remains
  unproven; only the browser-side normal/non-private test is checked.
- Both browser and Sway container IDs are temporary and are not stable
  after restart, tab/window lifecycle changes or workspace recreation.
- No user tab URLs, titles or page contents are captured; no
  checkpoints, Sway commands, browser moves, RESTORE or production
  permissions are enabled.
- If the observed Sway title format is unsupported, **fail closed**;
  don't broaden the matcher to arbitrary substrings or trust guessed IDs.

## CHECKLIST

- [x] Current Syntagma rules, live GitHub PR ownership and code inspected
- [x] Existing transport and co-observation hosts preserved separately
- [x] Two-click user-controlled marker tab with explicit close
- [x] Separate read-only Sway title-matching host and exact-origin manifest
- [x] Strict disposable trial-only registration and verification
- [x] Synthetic ambiguity, privacy, rollback and protocol tests
- [ ] Exact-head GitHub CI and independent source review
- [ ] Operator-approved Fedora disposable-marker trial
- [ ] Strong per-window binding threat review, post-close invalidation
- [ ] Only then: consented checkpoint association and multi-monitor restore

## NEXT / DECISIONS

This PR is a **source-level identity experiment**. Keep it unmerged
pending source review, operator decision and explicit authorization for
the separate local trial. Treat any passing title result as temporary
and non-authorizing, with no automatic session restoration.
