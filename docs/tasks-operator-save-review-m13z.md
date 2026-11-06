# 🏥💜 TASKS // M13z Operator Save Review (Example-Only UI)

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS source integrity / post-crash recovery review  
**STAFF ROLE //** DOC, Hospital-compatible external provider OPEN AI // CHATGPT; no live Hospital registration verified  
**ASSIGNMENT //** Operator-visible recovery review for the three M13y interrupted-save classes  
**CHECKPOINT //** M13y PR #1379 merged into main at `f8d02b5df10aac877a42d67cc5820121883d0cb7`; source-based project main at M13z branch creation `080b3301b5f1f721188733849c00a881dc8cf736` (November 6, 2026)  
**SCOPE/PERMISSIONS //** GitHub-only bounded QML/JS/test/CI/doc change. No local Fedora modification, no new storage writer, real source inspection, encryption activation, credentials, recovery replay, cross-owner Connections modification or automatic PR merge.

## IMPLEMENTATION

The current operator-facing location is **TASKS → SYNC → RECOVERY**. It already contains:

- M13q: shared Connections C2 **read-only keyring presence check**, with recovery/capture/preview/delete flags all denied.
- M13s: already-mounted live in-memory **unsaved NEW TASK/RENAME and TASK DETAILS** boolean signals. It does not capture or preserve task text, and explicitly excludes PROJECT/PLANNER editors.

M13y is a **test-only** Python/SQLite source-inspection fixture. It has no actual QML provider or real TASKS source journal. Simply calling a synthetic M13y classification a "real" result would falsely tell an operator that saved tasks had been verified.

**M13z therefore mounts a real operator-visible view, with an explicitly NOT-CONNECTED live source status and three selectable example cases:**

| Example tab | Original M13y classification | Operator explanation |
|---|---|---|
| UNCHANGED | `RESERVED_SOURCE_STILL_AT_BASELINE` | Source still at pre-save bytes; must not auto-replay |
| UNSETTLED | `RESERVED_SOURCE_MATCHES_EXPECTED_UNACKNOWLEDGED` | New bytes appear but the reserved stage never settled |
| SETTLED | `SETTLED_SOURCE_MATCHES_UI_UNACKNOWLEDGED` | Source and journal match but the UI acknowledgment was lost |

The original `TaskRecoveryStatusPaneM13q.qml` remains mounted once inside the existing SYNC tab. A new `TaskRecoveryReviewPaneM13z.qml` is inserted **between** the existing M13s live unsaved-editor section and the existing M13q permission-denial section. It uses existing `GohuText`, `ModeButton` and `Colors` grammar; no independent dialog, overlay, app owner or process.

The preview's only interaction is selecting which explanation to read. Every view shows **KEEP UNSAVED DRAFT**, **KEEP LAST CONFIRMED VIEW**, **MANUAL REVIEW ONLY**, **NO REPLAY / NO RESTORE / NO DRAFT DELETE**. The real source status always reads `LIVE // SOURCE REVIEW NOT CONNECTED`; examples are prominently marked `EXAMPLE ONLY // NOT A LIVE SAVE`.

The new pure `TaskRecoveryReviewPolicyM13z.js` deliberately separates:
- `current()`: unconditional, constant unconnected live status.
- `example(id)`: finite known example selection with authored safe labels.
- `syntheticResult(report)`: **test-only** display projection for exact M13y redacted schema; validates literal `fixtureOnly:true`, `journalReadOnly:true`, all 15 authorization flags false, matching class/position/pending fields and safe revision count, and rejects extra/untrusted fields. Even valid fixture results are marked `SYNTHETIC FIXTURE ONLY // NOT LIVE`. The running QML pane never calls `syntheticResult()` or imports the test inspector.

No source body, revision hash, task title, key, stage ID, writer identity, account name, user approval, journal path or raw receipt is returned in UI projections. No source-filesystem access, disk writes, keyring calls, IPC, shell subprocess, timers, automatic refresh or saved demo preference.

## HOW TO USE

After operator-reviewed merge and **separately authorized local deployment**:

1. Open **TASKS → SYNC → RECOVERY**.
2. Read the existing **LOCAL EDITORS** status for the actual current unsaved editor booleans.
3. Under **SAVE REVIEW // POST-CRASH**, note the real status **LIVE // SOURCE REVIEW NOT CONNECTED**.
4. Select **UNCHANGED**, **UNSETTLED** or **SETTLED** to inspect the corresponding illustrative crash review. The buttons do not inspect or alter a task; they only change explanatory text.
5. Read **RECOVERY PERMISSIONS // NOT ACTIVE** and the unchanged C2 keyring presence indicator below/above.

This is **not yet an actual post-crash recovery tool**. It is an honest, accessible review interface and evidence-presentation contract. A real operator-visible save result requires future source-owner authentication, native Quickshell integration and separately authorized bridge. Do not present an example as a current saved-file verification.

## VERIFY

- `tests/tasks/test_task_operator_save_review_m13z.cjs`: all three known states, constant disconnected live view, exact M13y fixture schema, malformed/fake approval rejection, no raw data or fields, QML mount order and non-actuating buttons, single writer and all false security gates.
- Existing M13q read-only C2 presence, M13s in-memory editor booleans and M13w source receipt draft-retention tests rerun.
- M13y genuine disposable OS-process crash and SQLite WAL readback suite reruns to confirm exact source-classification labels.
- Existing M11d TASKS one JSON writer and C2a Connections fail-closed tests rerun.
- `qmlformat` parses both the new review QML and its existing M13q parent in disposable CI. This does **not** prove native task menu layout/focus behavior on the operator's Fedora Silverblue.

## WATCH OUT FOR

**This screen cannot identify the actual state of an interrupted save yet.** It presents exact M13y class semantics as *examples* until live signed/verified source evidence is independently available. The existing M13s editor indicator observes only local memory and cannot recover after restart. An unconnected read-only view is not proof of no pending write, nor proof of a successful save. No control should clear a draft from a classifier alone.

M13y's fixture is not a production trusted OS source owner: same-UID tampering, source/SQLite non-atomic settlement, crash window, callback attribution, and native integration remain unsolved. Never connect M13y Python test files to production Quickshell or accept caller-supplied `saved:true` without independent authentication.

The example panel grows vertically with text and lives inside M13q's existing `Flickable`; native sizing still requires operator inspection. Existing keyring availability probe is explicit and read-only. The new panel itself never calls it.

## CHECKLIST

- [x] Recheck current Syntagma/Hospital rules, merged M13y, main HEAD and open-task ownership
- [x] Reuse existing SYNC/RECOVERY route and M13q/M13s controls rather than creating new task store or menu
- [x] Add readable operator review for unchanged, expected-but-unsettled and settled-without-UI-acknowledgment
- [x] Keep real evidence disconnected and all recovery, replay, delete and writer authority false
- [x] Add strict M13y synthetic classifier projection and rejection tests
- [x] Add targeted workflow and handoff
- [ ] Final PR-head GitHub CI, independent Nurse 2 review and operator merge
- [ ] Separately authorized native menu check and cross-screen focus/scroll acceptance
- [ ] Authenticated source-owner/native callback/readback integration
- [ ] Encrypted opt-in draft checkpoint capture, preview, delete and restore acceptance

## NEXT

Obtain independent review of M13z's UI/case mapping. Once merged and explicitly deployed, check the three example tabs and unchanged keyring/editor status in the real TASKS menu. The next separately bounded milestone should be an **independently authenticated, read-only native evidence provider**, not a copy of the M13y test script inside Quickshell. It must never automatically replay a write or clear unsaved work simply because source bytes match.

## DECISIONS

M12l accepted local-first single logical writer remains selected. M13z is a visibly honest review presentation, **not live recovery implementation**, actual draft persistence, a new storage host, or a substitute for operator approval. No worker-owned Connections changes, local Fedora writes, live Hospital registration, merger or production activation.
