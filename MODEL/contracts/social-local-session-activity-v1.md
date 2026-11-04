# Social Organizations / Current Session Activity v1

PATIENT: kudokudo1/The-Post-Apollo-Project
PROVIDER: OPEN AI // CHATGPT, external Hospital-compatible, no verified live Room/Role/Assignment.
ASSIGNMENT: Control 7 of the operator's single-page Organization Manager usability roadmap.
STATE: Repository change pending exact-head CI, merge and deferred live acceptance.

## IMPLEMENTATION

Keep Social → USER → SETTINGS → ORGANIZATIONS inline. Add **CURRENT SESSION ACTIVITY // OBSERVED OUTCOMES** near the existing Save Status, Refresh All, and Private Backup controls. No separate page, service, persistent data file or new permission. Existing button dimensions remain 28px high.

Original local JSON records expose revisions but **do not contain historic per-operation timestamps or actor identity**. It would be untrue to reconstruct past user edits from these data. Therefore v1 is explicitly a **bounded in-memory history** of outcomes *observed by this screen* while the Organizations tab is open. It is not persistent across a shell restart and is not an enterprise audit log.

The existing Save Feedback emits a signal only upon a local writer's confirmed revision advancement, failure/revision conflict, unconfirmed reply or load error/recovery. A queued save is NOT recorded as a successful write. Refresh All emits on completion, partial completion or error, not on repeated/blocked click. Private Backup emits after create/list/validate result or error, never claiming Restore. The new panel listens via three QML Connections, timestamps **observation time** (not original event time), keeps up to 40 in-memory events, displays newest six by default with SHOW SESSION EVENTS / SHOW RECENT SIX and CLEAR SESSION VIEW. Clear only changes this view; it cannot change any saved organization, backup or credential. No event is emitted while the Organizations tab is closed.

Records include only store name, status/error code, revision or allowed backup filename from the already existing UI status; no raw directory documents, credentials, provider tokens or trusted company access. The permanent activity/audit design is separate and would need audited writer-level hooks, retention and privacy review; it is **not** silently deemed complete.

## HOW TO USE

After operator-controlled merge and separately authorized local update: Social → USER → SETTINGS → ORGANIZATIONS → CURRENT SESSION ACTIVITY. Complete a normal edit/Save, Refresh All, BACK UP NOW or VALIDATE FOR RESTORE action, then read the session event and observed time. SHOW SESSION EVENTS expands beyond the latest six when needed. CLEAR SESSION VIEW hides these in-memory observations only. Older operations from before opening this screen cannot appear.

## VERIFY

New source tests check the one-page layout, outcome-only signals, bounded event buffer, live backup acceptance tracking, disabled Restore, no persistence or privileged new functions. A real Qt6 offscreen test injects fictional store revision transitions, an actual backup response in the existing QML Process stub and checks that success/conflict/reload/backup results appear in the session history without file changes. Existing local Save, Refresh, Backups and private store regressions remain. Live operator testing remains deferred.

## WATCH OUT FOR

This is **current-session activity**, not a historical forensic log. It cannot identify a specific employee or reconstruct which field changed. A timestamp marks when the UI observed a backend result. No UI outcome proves verified organization permission. A session reset clears history. Never use this as compliance or security auditing.

## CHECKLIST

- [x] Verify current main, Syntagma/Hospital rules and open PR ownership
- [x] Preserve original local stores, existing one-page controls and geometry
- [x] Wire signals from accepted Save, Refresh, Backup outcomes
- [x] Bound in-memory events and add clear/expand controls
- [x] Record operator-verified live Backup create/list/validate
- [ ] Exact-head CI green
- [ ] Operator merge authorization and live acceptance
- [ ] Permanent writer-level audit trail separately scoped, if required

## NEXT

Finish CI and hand off. The **semantic color coordination** phase can proceed as a separate PR when the operator authorizes it: red close/destructive, green refresh/check, yellow save/archive, orange contextual primary, magenta/purple active user intent, blue/cyan secondary navigation and white neutral. Existing button dimensions remain frozen. Multi-file Restore still requires separately verified transactional safety and is not enabled by Activity v1.

## DECISIONS

Do not falsely claim historical events from revision counters. Current view evidence only, clearly labeled. The user's earlier live Backup UI verification is operator-confirmed; all other deferred click tests remain deferred. No workstation writes, restart, self-merge or authorization expansion.
