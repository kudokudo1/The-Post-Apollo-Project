# 🏥💜 Trash++ U7 // Desktop Screenshot Preview-to-TRASH Review

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External Hospital-compatible DOC; live Hospital registration not verified  
ASSIGNMENT // Reuse shared Trash UI for *previewed Desktop screenshot-like images only*  
BASE // U6 branch `feat/trashpp-u6-camera-cleanup-queue-review-20261113` at `7336e6e694674523b6325c6c3a99dc62e518a8ed` (U6 draft PR #1972 stacked on U5 draft PR #1967)  
SCOPE // `widgets/CameraW.qml`, `widgets/CameraCleanupView.qml`, Trash tests/workflow and this runbook. No changes to `scripts/camera/camera_cli.py`, `modules/Trash.qml`, `scripts/trash/trash_cli.py`, or source-owned resources.

## IMPLEMENTATION

Camera Desktop Cleanup already has two explicit user actions: **PREVIEW MATCHES** calls `preview_desktop_trash()`, then an independent confirmation calls `trash_plan(planId, "MOVE_TO_TRASH")` through the existing Camera controller. Backend preview selects only direct Desktop screenshot-like PNG/JPEG/WEBP regular files, refuses more than 20,000, records their device/inode/size/mtime signatures in an owner-only plan, and issues a short-lived (10 minute) random 32-lowercase-hex ID. The backend's final action separately validates the plan, exact Desktop root, TTL, each file path/name/signature, regular file type and GIO result. It does not recursively scan/delete or use a permanent-delete fallback.

U7 changes only the final confirmation control:

- `widgets/CameraCleanupView.qml` replaces its bespoke `MOVE N TO TRASH` / `TRASH REQUIRES PREVIEW` ActionButton with the already reused `TrashLifecycleActionDeck` **TRASH** action. The PREVIEW MATCHES button remains unchanged and the on-screen matching count, byte count and sample list remain visible above it. The shared component displays no RESTORE or BURN action.
- `widgets/CameraW.qml` adds `reviewDesktopCameraTrash(ownerId, resourceId, expectedRevision)`. It refuses unless the exact owner/target are `camera-gio` and `camera-desktop-screenshots`, the revision is a strict 32-lowercase-hex Camera plan ID equal to the currently displayed `trashPreview.planId`, and the preview has the exact Desktop screenshot source metadata, an integer positive count no greater than 20,000, finite nonnegative byte size, and the host is actively showing Cleanup/Desktop, with no queue modal or Camera/Zoom/region operation in flight. It then calls the **original unchanged** `confirmCleanup()` and `run("trash",["trash",planId,"MOVE_TO_TRASH"])`.
- No filesystem paths or arbitrary source identifiers pass through the generic ActionDeck event. Its `ownerApproved`/`policyReviewed` booleans are only presentational gates; trusted authorization remains the source-owned Camera backend. U5's existing opt-in `resourceRevisionKind: "camera-plan"` is reused. No new token type, file IO, backend verb, service or protected delete authority is added.
- The independent Camera Gallery U5 single-selected-file action, U6 Batch/Grid/Swipe/Hunt queue, managed copies, GIO Restore, Desktop's original preview process, all GIO/managed Burn paths, and V3 protected Archive remain unchanged.

## HOW TO USE

After U5, U6 and U7 obtain independent merge approval and are synchronized onto the operator's host:

1. Open **Trash++ → CLEANUP → DESKTOP**.
2. Click **PREVIEW MATCHES**. Read the actual screenshot count and sample filenames shown in the existing review display.
3. Click the shared **TRASH** action. That is the second explicit action; the original Camera backend revalidates the short-lived plan and moves only eligible, unchanged files to recoverable GIO Trash. An expired or no-match plan refuses.
4. Use the existing Trash++ GIO Restore process to recover ordinary files. The separately proposed U4 shared Restore control remains a draft PR.

## VERIFY

- `tests/trash/test_u7_desktop_screenshot_review.cjs` executes the **actual** extracted Camera `confirmCleanup` and `reviewDesktopCameraTrash` QML methods in a synthetic Node VM, without invoking user files or GIO. Cases cover exact plan delegation once, second-click busy refusal, absent/zero-count plan, stale/wrong owner/revision, inactive host, wrong view/technique, busy region/Zoom, incorrect source metadata, oversized/malformed count and invalid bytes, plus no Restore/Burn request and preserved Gallery/queue/Desktop preview routes.
- The existing Trash workflow now runs U7's Node test alongside U3/U5/U6, existing Camera cleanup and all Burn protections.
- Existing Camera backend Python tests already mock GIO and verify unchanged Desktop regular-file/screenshot scope, expiry, changed signatures and confirmation. Re-run the full Camera suite with this PR.
- Exact-head GitHub CI can establish synthetic behavior, NOT all-size live Quickshell visuals, real GIO host recovery, or production protected data permissions.

## WATCH OUT FOR

1. Desktop can include **up to 20,000 screenshot-like files**. The second explicit click can move many eligible files. U7 retains the previous confirmation cadence, 10-minute TTL, and existing bounded backend. The user sees the count before final confirmation. The UI does not silently auto-execute based on entering the page.
2. An arbitrary GUI `planId` is not a source authorization grant. The backend verifies its locally stored one-use plan and independent file metadata. Direct filesystem deletes, permanent Burn, protected data and arbitrary directory paths are outside this change.
3. Desktop no-match previews produce an empty plan ID and count zero; the shared control must remain unavailable and the reviewer refuses.
4. If Desktop Cleanup is hidden or mode changed, the reviewer refuses. A subsequent eligible preview must be explicitly requested again when prior token expires.
5. This PR is **stacked on U6**, which is stacked on U5, while U4 is an independent open draft. U7 must not be merged independently into `main` or collapsed into another owner's changes without approval and combined mainline checks.
6. No local workstation edits/reloads or real user file operations were performed by this GitHub work. Operator final visual acceptance remains outstanding.

## CHECKLIST

- [x] Re-read Syntagma/Hospital, current `main` and U4/U5/U6 states/owners
- [x] Verify existing Desktop preview/confirm backend and no permanent-delete fallback
- [x] Reuse U1 shared deck and U5 Camera-plan request revision
- [x] Add strict Desktop-only review adapter, preserving original backend
- [x] Add synthetic regression and Trash workflow step
- [ ] Exact-head CI, legacy test updates if needed, failure diagnosis
- [ ] Operator decision on stacked U5 → U6 → U7 merges; U4 separately
- [ ] Native all-size Camera/Trash++ visual and disposable-file end-to-end Restore acceptance
- [ ] U8 independently audit Media owner delete/clear/trash paths before integration

## NEXT

U8 // Begin read-only Media deletion inventory with actual source owner and storage backend mapping. Only permit later Media changes under that owner's scope, with recoverability, confirmation and retention checks. No blanket cross-owner Burn.

## DECISIONS

U7 is a new bounded **draft** stacked on U6. `continue` authorizes code development, not merge approval, local host modification, real file operations, protected-source deletion or live Hospital registration. Recovery: revert the two scoped Camera UI edits and U7 test/workflow/docs; Camera CLI was never modified.
