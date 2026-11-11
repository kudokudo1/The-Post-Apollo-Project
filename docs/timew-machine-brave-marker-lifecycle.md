# MACHINE // Ephemeral Brave/Sway window-candidate lifecycle

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / browser-to-desktop window matching  
**STAFF ROLE:** External Hospital-compatible DOC, live Hospital registration not verified  
**ASSIGNMENT:** Bound a successful temporary title-marker correlation to its browser page lifetime and explicit revalidation  
**SCOPE:** Disposable Brave marker page and its read-only tests only  
**STATE:** Repository implementation, local desktop unmodified

## IMPLEMENTATION

The operator's live disposable Brave tests have demonstrated that two
different normal Brave windows can each display their own transient
Chromium window ID and separate SwayPX container ID after a unique title
marker check. That is **temporary correlation**, not authentication
against malicious local clients and not a restart-stable identity.

Previously, the marker page left its last successful status on screen
even after the focused browser window could have changed. A stale
success was not an acceptable basis for a future RESTORE operation.

`marker-lifecycle.mjs` now retains the current candidate **in memory
inside the temporary extension tab only**. It does not use a background
worker, storage, persistence, a timer, polling or a new host command.

The page's existing **COMPARE THIS WINDOW WITH SWAY ONCE** button:
1. Verifies its own tab is active, normal and non-private and its Brave
   window is focused; confirms the already-granted optional native
   connection permission.
2. Starts a versioned, cancellable observation attempt.
3. Calls the **existing read-only title-marker native host**.
4. Checks the exact nonce and no-action reply schema, then checks its
   own Brave tab and window **again** after the asynchronous reply.
5. Accepts the match only if no focus/visibility invalidation happened
   during the request, and the tab ID/window ID/marker token remain
   identical.
6. On an explicit repeat check, requires the **same** Sway container ID,
   output and workspace; if any change, revokes the candidate.
7. Shows that the result is temporary, kept only in memory, and
   invalidated when browser focus is lost.

The candidate is revoked immediately when:
- The browser window loses focus (`window.blur`).
- The marker test tab becomes hidden (`visibilitychange`).
- The marker page exits/reloads (`pagehide`).
- The test tab's close button is clicked, before removing the tab.
- A native reply fails validation, the title is not found, the browser
  tab/window changed, or a subsequent explicit recheck sees a new
  Sway container/output/workspace.

Any native response arriving after such revocation is ignored.
Returning focus **never automatically restores** a candidate. The
operator must explicitly click COMPARE again.

## HOW TO USE (after code review and separate local approval)

No host files or manifests need to change for this milestone. The same
read-only title-marker host already used in the disposable Brave trial
can be reused, if the exact trial still exists and passes
`MachineBraveTitleTrial.py verify ROOT`.

Once a reviewed version is available in the local checkout:
1. Reload the Post-Apollo MACHINE unpacked extension in the **temporary
   Brave test profile only** via `brave://extensions` → Reload.
2. In the popup select **OPEN TEMPORARY WINDOW CHECK TAB**, then in the
   new tab press **COMPARE THIS WINDOW WITH SWAY ONCE**.
3. Expect the familiar `TITLE MARKER MATCHED // TEMPORARY // NO RESTORE`
   plus `IN MEMORY ONLY // INVALIDATED ON FOCUS LOSS`.
4. Focus another Brave window or tab. The old page invalidates its
   candidate. On returning, press COMPARE once more. A hidden or
   old result must not be silently reused.
5. With the same marker tab still focused, press COMPARE again to
   explicitly recheck the same transient ID. A new container/output/
   workspace is a refusal, not a silent rebind.
6. Use **CLOSE THIS TEST TAB** to close only the temporary tab.

Do **not** install, configure or reload normal Brave or Quickshell
to perform this experiment. No persisted browser data is created.

## VERIFY

Dedicated CI checks `MarkerCandidateLifecycle` directly and simulates
the actual marker page with controlled Chromium API results, browser
focus/visibility events and an in-flight native-host reply that arrives
after invalidation. It tests acceptance, stable explicit recheck,
changed Sway container, output, workspace, tab/window IDs, malformed
identity, loss of focus, tab hiding, native refusal and self-close.

Existing temporary title-marker host, disposable native registration
and extension privacy tests are retained. No real Sway or Brave runtime
was exercised by CI.

## WATCH OUT FOR

**This does not continuously certify the window association.** Between
explicit checks, the host is not monitoring Sway. A compositor-side
change can remain unknown until the next check. Loss of browser focus,
however, revokes the page's candidate immediately.

There is no background service, no durable pairing, no verified
host-origin authentication, no proof of host-side private exclusion,
and no permission to move or restore windows. A title can still be
spoofed by another local process. Successful revalidation supplies
only a temporary diagnostic candidate.

The browser can destroy the page if a window closes; since no state is
ever written to disk, there is no saved mapping to clear or resurrect.
No new permissions, user tab content reads, web requests, file writes,
checkpoint changes, session capture, Sway actuation or RESTORE actions.

## CHECKLIST / NEXT

- [x] Identify stale-page candidate after live two-window test
- [x] Implement per-page in-memory lifecycle and versioned async rejection
- [x] Invalidate on focus, tab visibility, page exit and close
- [x] Recheck same con ID / output / workspace, refuse silent rebinding
- [x] Synthetic unit + simulated browser-page regression tests
- [ ] Exact-head CI verification and independent source review
- [ ] Operator-approved disposable Brave visual test
- [ ] Design authenticated per-window binding / native-origin trust
- [ ] Develop explicit session and multi-monitor restore contracts later

## DECISIONS

No local installation, file mutation, PR merge, or production activation.
The existing MACHINE Room, DOC role and ownership boundaries remain.
