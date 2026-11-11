# MACHINE // Brave session recovery eligibility V1

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / Brave multi-window recovery  
**STAFF ROLE:** External Hospital-compatible DOC; live Hospital registration not verified  
**ASSIGNMENT:** Establish a safe data contract before permissioned tab capture and after-restart restoration  
**STATE:** Repository-only synthetic-data planning; no live access or activation

## IMPLEMENTATION

The prior MACHINE milestones have already demonstrated normal Brave window
counts, native messaging, SwayPX focus observations, live temporary
title-marker correlation across two Brave windows, and in-memory
invalidation on focus loss. The operator has reported the latter merged
and live; GitHub confirms PR #1825 is on main.

**Those IDs do not survive a restart and cannot, by themselves, recover
a browser session.** Restoring actual pages requires a separate record
of tab addresses and tab ordering, plus independent trusted association
to the correct desktop monitor/workspace. Existing TimeW checkpoints
store geometry; they do not store browser session pages.

The new pure module `session-recovery-plan.mjs` performs an isolated
**synthetic fixture** validation exercise before any live permission
expansion:

- Accepts explicitly supplied mock normal Brave windows, each labeled
  by the operator (e.g., WORK, MEDIA, PERSONAL) and an ordered list of
  tab index, pinned, active and optional URL fields.
- Never accepts temporary Chromium or Sway IDs as a permanent identity
  for a window. Labels are recognition hints, not proofs.
- Refuses ambiguous duplicate labels, invalid tab order/index, multiple
  active tabs, invalid types and oversized sessions (64 normal windows,
  2048 tabs per window, 8192 tabs total).
- Skips private windows before reading their tab contents, ignores
  non-normal windows, and refuses entries with ambiguous private state.
- Examines synthetic URLs **only in memory** and classifies each tab
  into `candidate_only`, `requires_sensitive_review` or
  `not_eligible`. Query strings and fragments are never silently
  treated as harmless because they may contain access tokens.
  URLs with embedded credentials and unsupported/internal schemes
  are not eligible. Even a plain URL path may be sensitive.
- Returns a **deep-frozen, redacted report** with only operator labels,
  tab positions, counts and risk categories. It returns no tab URL,
  title, process, profile, Sway container or browser window ID.
- A follow-up `assessRestartPairing` always returns
  `manual_pairing_required`, even when all `2 // 5 // 6` tab counts
  match after a restart. It never offers actions.

This is groundwork for a future consented session capture contract,
**not a session capture feature**. The module is deliberately not
imported into the live extension, native host, TimeW widget,
checkpoint database, SAVE or RESTORE.

## HOW TO USE

No new live UI or permission was installed. A developer may run the
synthetic fixture test from the repository:

```sh
node tests/timew/test_machine_brave_session_recovery_plan.mjs
python3 -B -I tests/timew/test_machine_brave_session_recovery_contract.py
```

The fixture uses three windows with 2, 5 and 6 tabs and deliberately
includes fake URL fragments, query tokens, private-window getters
and unsupported schemes. Test output contains only PASS or a generic
failure; never prints tab addresses or browser data.

The operator will later receive a **separate, explicit browser UI
permission prompt** before any real tab URL is read. The existing
Chrome/Brave `tabs` permission permits reading sensitive tab URL/title
properties, so that permission must be reviewed and chosen explicitly:
https://developer.chrome.com/docs/extensions/reference/api/tabs

## VERIFY

GitHub CI runs the pure Node classification/identity tests, a Python
source-security contract, and the prior Brave topology/marker
regressions. No live Fedora/SwayPX/Brave test is expected or claimed:
this module does not call Chromium, Sway, local files or network APIs.

## WATCH OUT FOR

Do not equate a redacted, synthetic recovery eligibility report with a
saved session. There are **zero** persisted tab URLs, zero installed
session permissions, no real browser address capture, and no
ready-to-execute restoration plan.

An operator-defined window label is not independently authenticated.
Actual URL storage (particularly query strings or fragments) can reveal
private authentication material; a future capture design must specify
the exact consent scope, per-window selection, encryption/access
controls, expiration and deletion/rollback behavior. Existing
browser-window and Sway container IDs must be invalidated across
restarts, never reused as stable identities. The browser may restore
its own session in parallel; duplicate prevention requires a later
existence check before any launch.

A failed validation must not echo the raw input. The current module
returns only generic refusal strings.

## CHECKLIST

- [x] Re-check merged #1825 and current source/ownership
- [x] Identify existing TimeW geometry-only storage contracts
- [x] Define synthetic normal-window, ordered-tab eligibility model
- [x] Redact URLs, titles, private windows and unstable IDs
- [x] Require manual pairing after restart even for identical tab counts
- [x] Add exact-head CI and source-security tests
- [ ] Independent security review and operator merge approval
- [ ] Explicit operator choice on permissioned tab URL capture
- [ ] Consent-bound, protected durable session storage
- [ ] Browser/desktop post-restart association and duplicate prevention
- [ ] Multi-monitor restore test and operator acceptance

## NEXT / DECISIONS

Keep the new code in a draft, unmerged PR for source review. The next
separate phase is **consent design and permissioned current-window tab
capture**, not automatic persistence. No live local browser/Quickshell
change, no new native host and no SAVE/RESTORE actuation.
