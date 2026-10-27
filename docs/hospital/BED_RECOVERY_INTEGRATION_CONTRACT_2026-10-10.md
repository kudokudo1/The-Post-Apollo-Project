# Hospital // Bed Recovery — PXD Integration Contract

STATUS: Standalone recovery UI and candidate policy; NOT yet wired, runtime-tested, merged, or installed.
OWNERS: Operator + Proxy Doctor; Head Nurse .C notified by operator.
PX guard: The-Post-Apollo-Dev-Exp draft PR #60; PR #61 is the PR #46 authority reconciliation.

## Contract
- Fail closed before a Doctor provider starts if persisted Room, Git Bed, Patient repository and branch do not agree. READ authority is not an exemption.
- A mismatch triggers a recovery window, but never a permission override.
- All UI matches are unverified candidates. Trust the PX launch-side target preflight, not old UI scan metadata.
- Preserve typed prompt draft and prior chat/report history on refusal or cancellation; never automatically resend after choosing a Bed.

## New isolated files
- widgets/HospitalBedRecoveryDialog.qml: recovery UI, with openFor(reason) method and explicit signals; no direct Git mutations, process spawn, or provider messages.
- services/hospital/HospitalBedRecoveryPolicy.js: compare known Git worktree inventory by exact branch and canonical GitHub origin; reject unknown identity, deduplicate and rank clean non-live Beds.
- tests/hospital/test_bed_recovery_policy.js: Node contract tests and read-only source-level UI checks.
- .github/workflows/hospital-bed-recovery.yml: automated tests.

## Host properties
The embedding Hospital UI provides:
- floorService: existing HospitalFloorService object containing allBeds and discover().
- roomId: selected persistent Room ID.
- expectedRepository: trusted Patient GitHub repository identity.
- expectedBranch: registered Room branch.
- currentBedPath / currentBedBranch: current selected Bed.
- operationActive: aggregate active surgery, integration and Doctor execution state.
- pendingDraft: typed message owned by composer; must not be discarded or auto-sent.
- mismatchCode: specific PX refusal reason from a failed turn.

## Signals
- selectBedRequested(candidate): Verify candidate again and select through existing Floor/Bed controls. Do not start provider automatically.
- createBedRequested(repository, branch): Create a new worktree with safe root/path, branch occupancy and active-worker checks, in a separately reviewed operation. Never overwrite a checkout.
- moveBedRequested(path, branch): Revalidate repository, dirty status, branch occupancy and worker activity. Use existing Move Bed safeguards; never git switch -f, stash, clean, reset or bypass the live Bed confirmation.
- registerBedRequested(): Operator can browse for a checkout outside known discovery roots. Verify it before adding to known Beds.
- inspectOnlyRequested(): Keep Room reports/history usable with no provider turn.
- cancelled(): Close modal; preserve current selected Bed and unsent prompt.

## Existing source seams to wire
- components/ConversationFeed.qml clears the composer only when sendSuccessSerial increases, so a refused turn can preserve typed text without modifying shared ConversationFeed.
- widgets/HospitalRoomChatView.qml sends through adapter.sendMessage and currently has no explicit targetMismatchDetected event. Add narrow signal emitting only for HOSPITAL TARGET REFUSED errors, with affected Room identity. Do not relabel unrelated failures.
- services/hospital/HospitalRoomConversationAdapter.qml already collects stderr and exposes sendError. Retain provenance and no-success behavior.
- widgets/HospitalW.qml owns selected Room/Bed, Floor discovery, Move Bed, and the chat surface. This is the eventual host for a recovery overlay.
- Open PR #53 overlaps the chat view and adapter; #31 overlaps HospitalW. Coordinate separate integration branch and preserve ongoing file ownership.

## Acceptance matrix
1. Valid Room/Bed: normal send unchanged.
2. Wrong Bed/branch/repo: refusal before provider spawn or outgoing Room message; recovery window opens.
3. Search: multiple matches shown as candidates; never autoselect, auto-launch or auto-resend.
4. Chosen Bed: explicit user action; revalidate and retry separately.
5. Dirty Bed: moving refused, existing files untouched; offer new Bed.
6. Live or busy Bed: existing two-stage confirmation AND active worker safety guard.
7. No origin / local-only / no checkout: truthful no-match and inspect/browse/create choices; local trust policy remains explicit future decision.
8. Cancellation or inspect: prompt draft and historical records preserved.
9. No backend bypass: valid authority does not waive PX target preflight.
10. Real Quickshell/Qt render, focus, keyboard and pointer behavior manually checked before merge.

## Rollback
Disconnect the new UI host bridge; retain PX's independent fail-closed target preflight once accepted. No database migration or changes to existing staff authority are involved.
