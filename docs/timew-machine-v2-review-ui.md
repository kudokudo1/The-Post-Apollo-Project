# MACHINE // V2 read-only review in STORED (November 18, 2026)

PATIENT // The-Post-Apollo-Project  
ROOM // TimeW MACHINE · Desktop & Brave Recovery  
STAFF ROLE // External Hospital-compatible DOC; no live Hospital registration verified  
ASSIGNMENT // Connect merged PR #2053's deny-only V2 geometry planner to TimeW's existing STORED UI  
PRODUCTION // HOLD pending independent review, operator merge and native acceptance

## IMPLEMENTATION

Add the explicit **REVIEW V2 // READ ONLY** control in **Clock → MACHINE → STORED**, below **VERIFY SAVED GEOMETRY**. A click starts one fixed-argv Python `MachineRestoreReviewV2.py review UUID` process, with no automatic polling and no prerequisite to existing RESTORE DESKTOP. The existing **RESTORE DESKTOP** continues using its original V1-backed `MachineRestoreCheckpoint.py` and is not silently replaced.

A separate V2 status reports how many geometry observations appear to agree **without verified persistent window identity**, and how many require review. Show one saved application/output/workspace and backend classification at a time with previous/next controls. The UI labels every result as observation only, not restore permission, not tab recovery. App IDs use plain text, not markup; unavailable/legacy-only responses never disclose private paths.

The UI accepts a review only if the submitted checkpoint UUID matches the currently selected checkpoint and the response remains structurally bounded and deny-only: `read_only=true`, `restore_allowed=false`, `browser_tabs_restorable=false`, `exact_geometry_restore_verified=false`, `live_window_identity_verified=false`, `checkpoint_keys_are_live_identity=false`, `safe_actions=[]`, plus bounded counts and recognized classifications. It resets the observation on checkpoint selection/listing and on leaving MACHINE or closing TimeW. In-progress reviews block concurrent internal Save/Restore/move requests; finished reviews never authorize any action.

Only TimeW's UI and associated source contract tests are modified. There are no changes to C3e, C5, Brave, Sway, saved SQLite schema, encryption, journal or window-movement authority.

## HOW TO USE

After independently reviewed merge, separately approved local sync and Quickshell reload: **Clock → MACHINE → STORED → select checkpoint → REVIEW V2 // READ ONLY**. Read the summary and browse individual window classifications. This reads saved metadata and current Sway geometry without moving or opening anything. **RESTORE DESKTOP** is a different pre-existing V1 action and remains incomplete for exact V2 positions and Brave sessions.

## VERIFY

CI source contracts: `python3 -B -I tests/timew/test_machine_restore_review_ui.py`, existing synthetic V2 planner/SQLite Sway test, previous one-click restore, TimeW foundation, notes, move apply/confirm/review, persistent MARK, and resolver UI tests. Expected Quickshell `Process {` count changes from 15 to 16 for the explicit read-only action. Tests do not establish a rendered native Fedora/SwayPX experience.

## WATCH OUT FOR

- Matching rectangles are **untrusted geometry agreement**, not a stable window identity or restoration.
- A result becomes stale as the desktop changes; it must be requested again on demand. The UI never produces move authorization.
- Multiple Brave windows remain ambiguous, and browser tabs are not imported or reopened.
- Existing one-click RESTORE still uses the prior V1 application-level matching, its built-in security checks and limitations.
- Protected Brave archive and C3e/C5 authority remain separate and denied for production.

## CHECKLIST

- [x] Merged PR #2053 and Nurse 2 reviewed head verified
- [x] New explicit UI control and narrow process
- [x] Deny-only response validation and stale-selection invalidation
- [x] One-window-at-a-time status in STORED
- [x] Updated TimeW source contracts and dedicated CI workflow
- [ ] Exact PR-head CI and independent NRS-2 review
- [ ] Operator merge decision and separately authorized local visual acceptance
- [ ] Trusted multi-window identity and authorized V2 placement
- [ ] Protected Brave import/deduplication/session restore with trusted consent

## NEXT / DECISIONS

Keep as DRAFT, UNMERGED and PRODUCTION HOLD pending exact-head CI and independent Nurse 2 review. Only then request operator merge disposition. Actual V2 placement and multi-window Brave restoration are future security boundaries, not automatically authorized by the UI. No local workstation writes, global host registration, automatic restore, production service, or C3e/C5 ownership transfer.
