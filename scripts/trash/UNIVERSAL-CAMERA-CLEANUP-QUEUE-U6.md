# 🏥💜 Trash++ U6 // Scoped Camera Cleanup Queue TRASH Review

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // Trash++ Universal Resource Lifecycle
STAFF ROLE // External Hospital-compatible DOC, live Hospital registration not verified
ASSIGNMENT // Migrate only the **explicit final queue TRASH click** to U1 shared controls
BASE // `feat/trashpp-u5-camera-gallery-reviewed-trash-20261113` at `257447a288b1ab673c181068986133a01fe29e19`, stacked on open U5 PR #1967
SCOPE // Shared U1 request deck, CameraW queue review, CameraCleanupView final queue button, tests, workflow and docs. Camera backend and other source owners unchanged.

## IMPLEMENTATION

The existing Camera Cleanup page is hosted inside Trash++, with ONE `CameraW.qml` selection queue shared by Batch, Grid, Swipe and Hunt. The prior `MOVE N TO TRASH` button immediately called `camera.trashQueuedNow()`; that Camera controller already invokes `trash-batch-now` to generate/consume a one-use, signature-checked plan inside its backend before sending eligible files to *recoverable GIO Trash*. Queue-only gestures do **not** delete files. A click still moves the current queue with the same one-click behavior.

U6 replaces only that explicit final queue button with the existing request-only `TrashLifecycleActionDeck`, with TRASH shown and RESTORE/BURN hidden. The list of queued filenames and their count remain directly above the control, and REMOVE/VIEW QUEUE stay unchanged.

A UI-only **monotonic queue counter**, `cleanupQueueRevision`, increments whenever `batchPaths` is replaced. All existing queue-write code paths assign fresh arrays. The counter saturates at 2147483647; once saturated, the reviewer refuses until a new session, rather than accepting a wrapped stale token. `resourceRevisionKind: "queue-counter"` is explicitly opt-in; U1 default 64-hex, U3 managed store-counter and U5 camera-plan token types stay unchanged.

`reviewQueuedCameraTrash(ownerId, resourceId, expectedRevision)` refuses unless:

- The only claimed owner/target are `camera-gio` / `camera-cleanup-queue`. No generic path or operation is accepted from the deck.
- An exact bounded decimal request token equals the live queue revision, and the counter is not saturated.
- The hosted Cleanup page is active, the user explicitly opened its review queue, the queue has between 1 and 500 unique absolute-path selections, and neither Camera nor native Zoom/region operations are busy.
- The current authorized folder equals both the loaded and requested folders; the requested Gallery view is `cleanup`. Files may originate from earlier paginated Gallery pages, so current-page membership is intentionally not required.
- The final handoff is STILL the existing `trashQueuedNow()` and `run("trashBatchNow", ["trash-batch-now", JSON.stringify(batchPaths), "MOVE_TO_TRASH", "--folder", cleanupCustomFolder])`. Its backend rescans allowed folders, rejects unsanctioned paths/symlinks/stale files and uses short-lived plans. U6 neither modifies nor bypasses that backend.

The queue token is **not** a cryptographic signature, trusted authorization, or independent file custody. It is a stale-click refusal guard for a known already-owned action. Neither U2 deny-only protected resource review nor future Hospital/company/social/Finance/Weather source permissions change.

## HOW TO USE

After separately authorized U5→U6 merges and workstation synchronization:

1. Open Trash++ → CLEANUP. Mark files in Batch, Grid, Swipe or Hunt; those actions only queue them.
2. Open VIEW QUEUE, inspect the full list and remove mistakes if necessary. The queued count remains visible.
3. Click the new shared TRASH control **once**. Camera performs the same validated, recoverable GIO move as the previous `MOVE N TO TRASH` button. Skipped/failed files remain queued and show a partial receipt.

There is no new preview step or automatic deletion, no separate Camera Cleanup window and no new Burn.

## VERIFY

- `tests/trash/test_u6_camera_cleanup_queue_review.cjs` extracts and executes the exact Camera QML methods in a Node VM with synthetic paths, never GIO. It verifies the same backend command, single click, no precommit queue clearing, second-click busy refusal; stale/forged token, wrong owner, duplicate/relative/empty/malformed/over-500 queue rejection; wrong page, closed queue, mismatched folder, native busy/Zoom refusal; monotonic array reassignment; Swipe/Hunt selection-only behavior; no Restore/Burn in the deck; and unchanged U5 Gallery and Desktop flows.
- Existing `tests/trash/test_camera_cleanup_handoff.cjs` now asserts the shared reviewed queue entrypoint rather than the retired direct UI click. Full Trash Python/Node regression workflow runs both U5 and U6.
- A GitHub CI pass proves only synthetic contract behavior. Native Quickshell focus, four chassis sizes, and actual operator host filesystem actions need separately authorized acceptance.

## WATCH OUT FOR

1. The original Camera one-click queue action can move **up to 500 eligible files**. U6 does not add a second confirmation. The queue is explicitly visible and the user must open it before final action. This is a conscious preservation of the existing operator-approved behavior.
2. The counter is only a UI stale-action witness. It cannot attest all source bytes, legal retention rules or OS permissions; the original Camera backend performs file-scope checks.
3. Gallery selection queues can span pages. Requiring current-page membership would wrongly hide previously explicitly marked items, so the backend's authoritative rescan remains essential.
4. The counter increments on `batchPaths` **replacement**. All existing mutation sites use new arrays; future in-place mutations must be forbidden or covered by separate revision increment tests.
5. This PR is deliberately **stacked on U5**. U4 #1962 and U5 #1967 are unmerged drafts, so do not merge U6 into `main` before its U5 base is merged and the actual combined mainline checks pass. No protected file Burn path added.
6. No local workstation edits, Quickshell reload, real GIO moves, destructive source-owner actions, production activation or Hospital live worker registration are authorized or performed.

## CHECKLIST

- [x] Syntagma protocols and latest `main`/open PR ownership verified
- [x] U5 unmerged; U6 explicitly stacked rather than copying changes into main
- [x] Existing single-click Camera queue backend and queue-array mutation contract inspected
- [x] Add bounded monotonic queue witness and strict owner-side review gate
- [x] Migrate explicit final Cleanup queue button only
- [x] Add synthetic tests and update old direct-click test expectations
- [ ] Exact-head GitHub CI; resolve any regressions
- [ ] Independent code/owner review, U5 merge decision and subsequent U6 rebase/merge approval
- [ ] Native Camera/Trash++ visual and disposable-media Restore check

## NEXT

U7 // Review Desktop screenshot and selected-file source-specific ingress after U4/U5/U6 final integration and real native acceptance, then assess Media source ownership separately. Never apply an unrestricted `rm` or a global cross-owner Burn All.

## DECISIONS

The operator's `continue` authorizes scoped GitHub development on a new stacked draft, not merge of U4, U5 or U6. The same explicit one-click Camera queue semantics remain. Live data and protected sources remain unchanged.
