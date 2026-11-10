# MACHINE // Operator-triggered read-only Sway A/B/A continuity witness

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / Brave-to-Sway identity  
**STAFF ROLE:** DOC, external Hospital-compatible, no live session registration  
**PHASE:** Read-only host-side multiwindow continuity diagnostic  
**STATE:** Draft repository implementation; no workstation execution

## IMPLEMENTATION

The operator has already verified in a real Fedora/SwayPX session:

1. A temporary Brave profile and extension can use a private XDG native
   host registration to exchange a one-shot native-messaging challenge.
2. `MachineBraveFocusWitness.py inspect` returned
   `brave_focus_observed`, `reported_app_id=brave-browser`,
   `output=DP-3`, `workspace=1`, and
   `same_focused_client_in_two_reads=true`.

The original witness says nothing about which **browser window** was in
focus. This additional CLI is a conservative next *host-side* observation:
with **two distinct normal Brave test windows** the operator selects window
A, then B, then A again. For each step it reads the Sway tree **twice**
via `swaymsg -r -t get_tree`; the same client must be focused across
both readings and be a recognized Brave app ID.

`MachineBraveHostFocusCycle.py inspect` waits four seconds after printing
each requested focus step so the operator can select A/B/A manually.
The temporary Sway container IDs are used **only inside the process** to
compare all three steps. The final JSON reports at most:

`consistent_unverified_host_focus_cycle`

A missing, changing, non-Brave or ambiguous focus is fail-closed. An
unmatched A/B/A sequence reports `unbound_host_focus_cycle`. No
persistent host IDs, process IDs, names, titles, URLs, screenshots, raw
tree payloads or private browser data are returned.

## HOW TO USE (separate operator authorization for live Sway reading)

After the code is approved and available in the current local checkout,
open **two distinct non-private Brave test windows**. Use the normal
disposable Brave profile if it is still running. In Kitty:

```sh
python3 -B -I services/time/MachineBraveHostFocusCycle.py inspect
```

After pressing Enter, focus normal Brave test window A during the first
four-second interval, B during the second, then A during the last.
No focus is changed programmatically. The script only reads Sway's
window tree. The terminal receives only a brief action prompt on stderr,
then one result JSON record on stdout.

This is **optional**, diagnostic and should not be run against private
browser windows as a privacy assurance: Sway cannot distinguish a private
Brave top-level by trusted identity.

## VERIFY

CI injects six synthetic Sway JSON frames via the existing bounded Sway
reader. It verifies A/B/A continuity, same-window, changed-window,
non-Brave, privacy redaction, exact `get_tree` IPC command and rejection
of any CLI operation other than explicit `inspect`.

This program does not call the MACHINE native host, create a browser tab,
change application focus, capture a session or write a checkpoint.

## WATCH OUT FOR

**A stable A/B/A host sequence is not a trusted browser-to-compositor
identity proof.** The Chromium extension's temporary
`chrome.windows` ID is still unrelated to Sway's transient container
ID, and a native-messaging extension origin is not a Wayland surface
handle. Other processes or focus timing may forge or mimic the pattern.

The diagnostic always returns:

- `browser_window_id: null`
- `browser_to_sway_identity_verified: false`
- `extension_origin_authenticated: false`
- `private_window_exclusion_verified: false`
- `session_capture_allowed: false`
- `restore_allowed: false`
- `action_allowed: false`
- `safe_actions: []`

Do not promote a focus candidate to a saved checkpoint binding, permit
RESTORE, or assume restart-stable identity. A separately reviewed
browser-to-compositor binding mechanism remains necessary.

## NEXT / DECISIONS

Technical next milestone: design and verify opt-in per-window trusted
correlation between the actual browser window handle and actual Sway
surface. Preserve native host provenance, private exclusion, explicit
consent and durable session identity as independent gates.

No local execution, ordinary Brave modification, Sway actuation,
Quickshell reload, file deletion or production activation in this PR.
