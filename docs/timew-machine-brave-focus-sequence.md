# MACHINE // Brave/Sway A-B-A focus-sequence review (untrusted diagnostic)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / browser session recovery  
**STAFF ROLE:** External Hospital-compatible DOC (live Room registration not verified)  
**SCOPE:** Focus-correlation research and fail-closed pure test policy, not live pairing or browser restore  
**PREDECESSORS:** M2b-M2d2, PR #1674 window topology, #1679 host focus witness, #1682 optional local connection (merged)  
**STATE:** Repository review candidate. No browser extension activation or desktop change.

## Problem and mechanism

Brave's `chrome.windows` API has a temporary browser window ID.
Sway's `get_tree` has a different native compositor container ID.
Neither supplies the other's handle. Chromium native messaging on Linux
supplies the extension origin argument, not the native browser window handle,
and does not independently authenticate a local process.

The earlier focus witness can say a Brave-class Sway leaf was stable in two
read-only observations. It cannot say which Brave API window it is.

One possible future **operator-initiated diagnostic** is to inspect a
bounded A / B / A focus sequence. A browser-side coordinator would request
focus of selected *normal* browser windows A and B, while a separate host
observer would independently sample each focused Sway leaf twice. A matching
two-client return pattern is useful evidence, **not an identity proof**:
focus could change between observations; a private window may present the
same Sway app ID; the local sender is not authenticated by native messaging;
a malicious process can forge all of these values.

The code here implements only a **pure reviewer** for hypothetical
operator-triggered observations. The observed native container IDs remain
internal to the reviewer and are never returned. It requires:
- explicit diagnostic-only gesture claim, one canonical challenge UUID;
- exactly three steps A1, B1, A2 with two distinct temporary browser IDs;
- two distinct stable Brave-class native focused leaves returning to A;
- bounded monotonic event times and read-only two-sample witness claims;
- browser-reported private-window exclusion, but correctly **no claim**
  that the compositor independently verified private-window exclusion.

Even a perfectly matching A/B/A transcript returns
`consistent_unverified_focus_pattern`, with all verification, capture,
restore and actuation fields **false** and `safe_actions=[]`.
Malformed, overlong, ambiguous, forged, stale or conflicting evidence
refuses or returns `unbound_focus_pattern` without revealing identifiers.

## What is deliberately NOT built

- No `chrome.windows.update`, focus movement, extension permissions,
  extra native host command, background service or running coordinator.
- No Sway IPC commands, browser-window native handles, tab/URL/title/cookie
  reads, user profile inspection, persistent pairing, SQLite change,
  Quickshell Process, window reopen or RESTORE call.
- No durable identity after Brave or Sway restart.
- No security assurance from user confirmation or the shape of an A/B/A
  pattern. These are insufficient for authenticated browser-to-OS mapping.

This test contract must **not** be fed into an existing RESTORE owner to
authorize app moves. A future approved live experiment should first validate
actual Fedora/SwayPX focus behavior with a disposable Brave profile and
no private windows. The host observer must own its own samples, timestamps,
and in-memory compositor handles, not accept untrusted handles as proof.
The operator should be able to cancel without changing saved checkpoints.

## Next accepted proof boundaries

1. Independently review this pure policy and test source.
2. Separately approve an opt-in, reversible live focus diagnostic in a
   disposable profile. Confirm correct multiwindow behavior, popup focus
   behavior and immediate cancellation on user focus intervention.
3. Establish and independently review an **actual trusted cross-API
   OS-window identity mechanism**. If unavailable, keep browser windows
   unbound. A consistent focus pattern cannot substitute for this proof.
4. Only then request separate tab/session descriptor, retention, encryption
   and recovery permissions. Preserve incognito exclusion and safe duplicate
   refusal on every path.
5. Preserve original geometry checkpoints and operator-controlled RESTORE.

## Verification

`python3 -B -I tests/timew/test_machine_brave_focus_sequence_review.py`
runs synthetic A/B/A and 17-window candidates, rejects malformed/private/
stale inputs, keeps both bridge sources unchanged, and asserts zero restore
authority. The dedicated CI additionally runs prior focus and native-host
tests. These are source and synthetic checks, **not** a live identity test.

## References

- Chrome browser windows: https://developer.chrome.com/docs/extensions/reference/api/windows
- Chrome native messaging: https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging
- Sway IPC: https://github.com/swaywm/sway/blob/master/sway/sway-ipc.7.scd

**DECISION:** This remains a non-authoritative diagnostic foundation.
No local installation, activation, merge or capture consent is implied.
