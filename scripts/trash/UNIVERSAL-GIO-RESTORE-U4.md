# 🏥💜 Trash++ U4 // Shared GIO File Restore Review

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External Hospital-compatible DOC; live Hospital registration not verified  
ASSIGNMENT // Integrate the U1 shared ActionDeck with existing GIO *Restore only*  
BASE // `main 3ae32d1e4df0c4771cb10444c44d88100dc64e65`  
SCOPE // Trash UI, GIO index metadata, tests and workflow. No source-owner mutation, new delete verb, production service or protected Archive authority.

## IMPLEMENTATION

U3 (#1958, merged) used `TrashLifecycleActionDeck` to route Trash++-owned recoverable managed copies to the existing, independent managed-copy store. U4 extends its **request-only** use to GIO-owned *file Restore* in the Trash page, without modifying file Burn or Burn All.

- `scripts/trash/trash_cli.py`: each already-validated `gio trash --list` item now has a `reviewId` equal to SHA-256 of canonical JSON `[uri, original]`. The original full-inventory `revision` remains unchanged, as does the underlying accepted `restore` CLI verb. The token avoids exposing arbitrary filesystem paths through the shared generic ActionDeck. **It is not a cryptographic capability or proof of ownership**; its contents derive from existing untrusted GIO index fields.
- `modules/Trash.qml`: the read-only `trashDisplayRows` file projection carries `reviewId`. A new `reviewGioFileRestore(ownerId, resourceId, expectedRevision)` refuses unless the open screen is TRASH, the inventory was successfully indexed and not marked stale, no busy/confirmation operation is active, the owner is exactly `filesystem-gio`, and both item token and exact full index revision are valid 64-character lowercase SHA strings.
- The reviewer requires **exactly one** entry in the currently displayed `items` with the matching token, GIO URI prefix and absolute original path. It then calls the *existing* `restoreItem`, whose return value is now a boolean, ultimately executing the same existing `trash_cli.py restore uri original` path.
- The backend still performs a fresh actual GIO inventory and `_selected(rows, uri, original)` before any restore; it refuses an existing restore destination via `os.path.lexists`. Backend command authorization and all original safety checks remain unchanged.
- The file-row RESTORE button becomes `TrashLifecycleActionDeck` with `showRestore=true`, `showTrash=false`, `showBurn=false`. Managed-copy Restore still uses its own existing button and backend. Neither existing file Burn nor managed-copy Burn nor bulk Burn is routed through the new generic deck.
- Source-owned Weather, Finance, Hospital, Social, company, identity, MACHINE/Time Machine, Hub Notes and To-do data are never exposed to a new write operation.

The review gate is a **UI consistency and stale-action guard**, not a replacement for kernel/user access control, GIO or the owner backend.

## HOW TO USE

After separately approved local sync, open Trash++ → TRASH → FILES. The visible RESTORE control is the U1 reusable component. It can only request restoring a current indexed GIO file. The original Burn button still starts its established separate two-click review.

Nothing in U4 moves a new file into Trash. Camera/GIO preexisting move-to-trash functionality remains owned by its original widgets.

## VERIFY

- `tests/trash/test_gio_review_id_u4.py` constructs synthetic GIO listings without invoking the actual GIO binary, asserts exact tuple hashing, independence of listing order, row rekeying on original/URI changes, unchanged inventory revision, unchanged backend verb/scope.
- `tests/trash/test_u4_gio_restore_review.cjs` executes the real extracted QML review and existing `restoreItem` function against synthetic in-memory items, covering current-owner success, revision mismatch, fake/missing/duplicate items, wrong owner, wrong mode, busy/confirmation refusals, and unchanged Burn pathway.
- Existing `tests/trash/test_bottom_left_launcher.py` keeps the lifecycle/restore assertions aligned with the new shared control; the Trash workflow runs complete Python, U3, U4 and preexisting Node regression suites.
- Full native Quickshell acceptance of four chassis sizes, focus/geometry and actual GIO filesystem side effects remains outside GitHub tests. Never claim this PR proves live host behavior or guarantees safe recovery of protected data.

## WATCH OUT FOR

1. **Opaque hash != authorization.** The `reviewId` and SHA-256 `revision` are untrusted metadata. They merely guard against stale display interactions. The GIO backend owns the actual selection and destination safety, and the owner/user OS permissions remain unchanged.
2. The `items` list is one indexed page. Item review is scoped to that page, not an unbounded scan of the filesystem. Items not present in the current page cannot be restored through U4.
3. GIO itself may race with another process before or after Restore; the backend already reindexes and checks the exact matching tuple and target. U4 adds no atomic cross-process transaction or new guarantee.
4. An invalid or stale GIO index refuses a click. Refresh is the recovery path.
5. All burn operations remain on the original two-click-confirmation code paths. The new shared deck does not expose Burn on any file row. **No cross-owner Burn All.**
6. U2 remains deny-only and U4 does not add trusted keys, independently verified consent or real protected Archive authorization.
7. No local host edit, data operation, Quickshell restart or real file Restore is performed by this GitHub-only PR.

## CHECKLIST

- [x] Syntagma/owner preflight and current main checked
- [x] Original GIO inventory, restore, Burn safeguards inspected
- [x] New opaque GIO item review ID, independent of original path in generic UI events
- [x] Exact index revision and current row match before invoking old backend
- [x] Shared file Restore control; managed-copy and Burn paths unchanged
- [x] Dedicated Python/JS tests, existing launcher regression update and CI step
- [ ] Exact-head GitHub CI, failures/retest
- [ ] Operator-approved merge
- [ ] Native Trash++ four-size visual/host acceptance
- [ ] Separate future GIO file Trash-ingress source adapter and protected owners' authorization

## NEXT

U5 // Review owner-specific "move to Trash" entry points (Camera/media and other file-producing widgets). Only integrate sources after their own existing reversible GIO behavior and ownership have been verified. Burn must retain independently reviewed irreversible requirements. Do not expand protected Archive or source-owned record mutation under a UI-label exercise.

## DECISIONS

U4 changes an already authorized, recoverable GIO **Restore** action's UI route only. It is not a new global delete permission or live data management service. The operator is final acceptance authority; previous merge approval was for U3, and U4 is a new review/merge boundary.
