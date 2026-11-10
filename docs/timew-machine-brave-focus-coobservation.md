# MACHINE // Brave-to-Sway opt-in focus co-observation

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / Brave window-to-desktop identification  
**STAFF ROLE:** External Hospital-compatible DOC (live registration not verified)  
**ASSIGNMENT:** Bridge one operator click to a non-authorizing Sway focus observation  
**STATE:** Source-level draft. No local registration or runtime execution.

## IMPLEMENTATION

The existing Brave extension exposes real normal/non-private browser window
counts and their temporary IDs. The separate Sway focus and host A/B/A
diagnostics have passed their source tests but cannot associate a Brave
`chrome.windows` ID with an actual Sway container/Wayland surface.

This milestone adds **one bounded, opt-in co-observation** without granting
either side the other side's identity:

1. In the extension popup, the operator presses **TEST FOCUS CANDIDATE ONCE**.
2. The extension checks that the already-optional `nativeMessaging`
   permission was granted and reads only `chrome.windows.getCurrent`
   without tab metadata. It refuses non-normal, private and invalid
   browser window references.
3. A **separate** native host,
   `org.postapollo.machine_brave_focus_observe`, receives only a
   fresh UUID challenge. **No browser window ID or tab count is sent.**
4. The host uses the existing bounded read-only Sway witness, which
   makes exactly two calls to `swaymsg -r -t get_tree`, and compares
   the focused Brave client in memory. It returns only a stable/unstable
   result and, if stable, current output/workspace labels.
5. The extension validates an exact nonce-bound response, rejects any
   claim of verified identity/restoration, and displays the browser's
   temporary window ID beside the currently observed host output and
   workspace with **CO-OBSERVED // UNLINKED // NO RESTORE**.

The user gesture makes these two observations *near-contemporaneous*, not
a cryptographic link. Chromium extensions do not expose a trusted
Wayland surface handle, the native host cannot verify the supplied
Chromium window reference, and focus may change during scheduling.
A compositor focus record cannot prove the window is not private.
The session/window ID is not restart-stable.

## HOW TO USE (future operator-approved isolated test)

This code is **not yet installed**. The new button will report
`FOCUS TEST UNAVAILABLE // CHECK ISOLATED HOST` until the separate
host is registered in an approved disposable-profile XDG_CONFIG_HOME.
Do **not** overwrite the existing transport-only host or install under
the ordinary Brave profile.

The separate pure manifest generator is:

```sh
python3 -B -I services/time/MachineBraveNativeFocusManifest.py \
  YOUR_TEST_EXTENSION_ID \
  /tmp/YOUR_APPROVED_TRIAL/MachineBraveNativeFocusObserve.py
```

It only **prints a proposed manifest**; it does not create a file.
The later authorized disposable setup would copy the host executable,
set executable permission, and register the generated JSON **only** in
`$TRIAL/xdg-config/BraveSoftware/Brave-Browser/NativeMessagingHosts/`.
An isolated test Brave must be launched with both its dedicated
`--user-data-dir` and `XDG_CONFIG_HOME` matching that trial, as in the
operator-verified earlier transport test.

After explicit local approval and registration: open a normal,
non-private test Brave window, open the extension popup, grant
**ALLOW LOCAL CONNECTION** if needed, then click
**TEST FOCUS CANDIDATE ONCE**. An observed Brave focus shows a temporary
browser ID and Sway output/workspace, **still marked UNLINKED**.
There are no background reads or automatic retries.

## VERIFY

Repository CI uses injected synthetic Sway trees and an isolated framed
native-messaging subprocess. It confirms stable/changed/non-Brave/missing
focus, malformed requests, caller format rejection, nonce handling, no
private titles, no internal Sway IDs/PIDs, output limits, no RESTORE and
no changes to the existing transport-only probe. Browser-side tests
cover an explicit click, optional permission preflight, refusal of
private/non-normal windows, exact response schema, and zero new required
permissions.

No source-level test establishes a real operator session match.
The Fedora/SwayPX disposable live test is still **pending**.

## WATCH OUT FOR

**This is a co-observation candidate, not trusted window pairing.**
The native host observes whatever top-level Brave window happens to be
focused on Sway at observation time. The extension's local browser ID
may refer to another window if the user changes focus at the wrong time,
and neither component can detect that mismatch robustly.

Always return:
- `browser_to_sway_identity_verified: false`
- `extension_origin_authenticated: false`
- `private_window_exclusion_verified_by_host: false`
- `restart_session_identity_verified: false`
- `session_capture_allowed: false`
- `restore_allowed: false`
- `safe_actions: []`

No capture of URL/title/tab contents, no monitor movement, no
file writes, no checkpoint update, no local app restart, no action on
normal Brave, and no automatic background operation.

## CHECKLIST / NEXT

- [x] Existing read-only Brave inventory and native probe retained
- [x] Existing Sway double-read witness reused
- [x] New isolated native host and pure exact-origin manifest generator
- [x] Explicit browser click with exact challenge/response validation
- [x] Safety tests, contract tests and dedicated CI workflow
- [ ] Source CI and independent review
- [ ] Operator authorization for disposable host installation and real test
- [ ] Trusted browser/compositor per-window binding design and verification
- [ ] Browser session/save integration and multi-monitor restore acceptance

## DECISIONS

Repository-only diagnostic; normal Brave, XDG registration and TimeW
checkpoint/restore code unchanged. Do not merge or activate without the
operator's required approval and review.
