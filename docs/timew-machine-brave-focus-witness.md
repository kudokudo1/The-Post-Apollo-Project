# MACHINE // Browser-to-Sway focus witness, still **unbound**

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / browser session identity  
**STAFF ROLE:** External Hospital-compatible DOC (not registered in live Hospital)  
**PREDECESSOR:** PR #1674, zero-permission Brave topology popup, merged  
**STATE:** Draft repository implementation; no local probe or extension activation

## Actual missing mechanism

The Brave pilot can enumerate normal browser window IDs and tab counts.
Those IDs are unique only **within the running browser session**. Its
output currently has no verified mapping to Sway's focused window or
checkpoint-local geometry UUID.

On Linux, Chromium native messaging gives a host the calling
**extension origin**, not the originating native window handle.
That host argument is not a secure proof of OS-window identity.
Sway's `get_tree` can independently report a focused client,
its app ID, current workspace and output, but two nearby read events
alone cannot show that the *same* browser top-level is involved.

Sources:
- https://developer.chrome.com/docs/extensions/reference/api/windows
- https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging
- https://github.com/chromium/chromium/blob/main/extensions/docs/security_faq.md
- https://github.com/swaywm/sway/blob/master/sway/sway-ipc.7.scd

## Implementation

The new `MachineBraveFocusWitness.py` is a standalone Python CLI,
**not** registered as a browser native messaging host. On an explicit
`inspect` request it uses the existing bounded Sway reader to run
exactly two read-only `swaymsg -r -t get_tree` observations.

It traverses at most 4096 Sway nodes to locate a uniquely focused
normal leaf, checks its ephemeral container ID is stable in two reads,
and identifies an allowlisted Brave app ID and output/workspace.
The internal Sway ID is used **only** to compare those two reads.
It is never returned to the browser, saved to SQLite or passed into
a restore operation.

The underlying Sway JSON includes native fields such as window names,
PIDs, and potentially information about private browser windows.
This reader necessarily receives that full local tree in memory,
but projects only a bounded metadata summary and a random observation
UUID. The original IPC payload, process IDs, titles, X11 window IDs
and environment/socket paths are never printed, logged or persisted.

Results:
- `brave_focus_observed`: one stable Brave-class focus observed
- `not_brave_focused`: another application focused
- `focus_changed`: different client/placement between reads
- `no_focused_client`: no uniquely focused client
- `error`: unavailable, malformed or ambiguous compositor data

Each result explicitly declares `browser_window_id=null`,
`sway_window_binding_verified=false`,
`browser_session_identity_verified=false`,
`private_window_exclusion_verified=false`,
`session_restorable=false`, `action_allowed=false` and
`safe_actions=[]`.

The new pure `MachineBraveHostPairingReview.py` accepts
a strict redacted output from #1674's existing Brave topology pilot
plus this host witness. It validates both independently, rejects
private data, impossible or contradictory focus claims, duplicate
browser IDs and malformed counts, and produces at most
`unverified_focus_candidate`. It **never** outputs a verified pairing,
RESTORE permission, new executable session reference or move command.

## Why a focus match is not identity proof

Two observations can be consistent while referring to different
windows: an extension popup can have a distinct native surface; a user
can switch focus between readings; two Brave windows may have identical
tab counts; a private window can look like an ordinary Brave Sway
client; OS application IDs are not per-window authentication.
Even an operator clicking CONFIRM cannot magically prove a missing
browser-to-compositor window reference.

Therefore this milestone does **not** write a pairing into a
checkpoint, label a window as verified, or expose an executable
RESTORE path.

## Verification

Fixture tests use 17 concurrent browser windows, two consistent or
changing Sway tree frames, and malicious inputs including fake title,
cookie, private browsing hints, duplicate browser IDs and multiple
focused host leaves. They assert redaction, no actions and no
incorrect identity grant. The Sway reader is injected, and checks
the exact `get_tree` command with `shell=false`, timeout and output
bounds. The CLI invalid-action case is exercised in a real separate
Python `-B -I` process.

Source contracts prohibit extra QML processes, native-messaging
installation, application launches, Sway command IPC, filesystem
writes, network calls and modifications to v1/v2 checkpoint data.
Existing zero-permission Brave pilot and M2b/M2c/M2d/M2d2 tests run
unchanged.

This is not live Fedora/SwayPX verification. It proves the
implementation with synthetic Sway payloads, not real browser pairing.

## Next authorization gates

1. User/owner independently reviews the read-only focus observation code.
2. If specifically approved, test `inspect` against the operator's
   real SwayPX desktop **without** installing a browser native host.
   Treat the output as a diagnostic, not a pairing certificate.
3. Independently design/install a properly scoped, opt-in local browser
   transport. Native messaging is separate permission; no request to
   inspect URL/title/cookie/history data is included by this milestone.
4. Establish trustworthy *per-window* host/browser correlation. A
   Sway focus observation plus Chromium extension-origin argument alone
   do not satisfy this. Use fail-closed manual review until one
   accountable OS-window reference is proven.
5. Later, ask separately for tab/session descriptor permissions and
   support for restart-stable identity; test recovery in disposable
   profiles before any real Brave restoration.
6. Only then permit a bounded REVIVE/RESTORE action that preserves
   current browser windows, refuses uncertain duplicates and includes
   a recovery journal.

No merge, local installation, Quickshell reload, browser profile
inspection, disk write, window motion or restore by this PR.
