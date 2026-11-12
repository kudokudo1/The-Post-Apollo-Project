# Trash++ // U1 Universal Deletion Interface Foundation

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External DOC-compatible; no verified live Hospital attachment  
ASSIGNMENT // Build toward one Post-Apollo Trash / Restore / Burn system, including eventual replacement of eligible Delete buttons.  
STATE // U1 proposed for review; existing runtime remains unchanged.

## IMPLEMENTATION

There are three distinct operations, not synonyms:

- **TRASH:** owner-authorized, recoverable removal from the active view/state, preserving everything necessary for Restore.
- **RESTORE:** owner-authorized rehydration with resource generation/revision, identity and dependency verification. Never silently overwrite an existing newer object.
- **BURN:** explicit, separately authorized *irreversible* purge of eligible resources. Requires a separate confirmation/receipt contract; the request button itself never commits deletion.

Existing primitives remain authoritative inside their scopes: GIO owns ordinary filesystem Trash; Trash++ managed research/Weather copies own their own recoverable state; immutable V2 Archive snapshots are read-only; source-owned widgets keep their record writers. No universal rm, owner-bypassing transaction or shared cross-source Burn All.

### U1 implementation artifacts

1. `components/TrashLifecycleActionDeck.qml` uses the existing `ActionButton` component. An owner may show TRASH, RESTORE, BURN, any combination, or none. All actions start hidden and disabled. Resource identity, exact SHA-256 revision, reviewed owner and policy, retention hold and protected-resource flags gate visibility/availability. A click emits only a named **review request** with owner ID, resource ID and expected revision; it never runs a backend.
2. `scripts/trash/universal_delete_inventory_u1.py` scans fixed repository source families for potential Delete/Remove/Clear/Trash/Burn action sites. It reports file path, line and match type only, never code payload or user data, and never claims that a hit is safe to replace or that missing hits prove absence.
3. `tests/trash/test_universal_lifecycle_u1.py` checks deny-by-default controls, request-only event wiring, bounded read-only source scanning and refusal of unsafe links/files.

These are **preparation for actual integrations**, not a new desktop page or active global deletion authority. The existing Trash++ UI and its current Burn confirmations are unchanged.

### Classification before migration

| Existing operation | Proposed Post-Apollo lifecycle | Scope and ownership |
| --- | --- | --- |
| GIO-managed ordinary files | TRASH -> RESTORE or reviewed BURN | Existing scoped GIO file adapter |
| Trash++ managed disposable copies | TRASH -> RESTORE or reviewed BURN | Existing managed-copy store |
| Source-owned mutable record | Owner-specific reversible TRASH only after snapshot and dependency/retention contract | Each Notes, To-do, Weather, Media or other owner |
| Immutable V2 Archive copy | READ-ONLY until independently authorized retention/Restore/Burn | Protected Archive owner |
| Disposable derived cache | CLEAR may remain correct; evaluate whether recoverable Trash is meaningful | Cache owner |
| Hospital evidence, Time Machine checkpoints, Identity trust history, Finance transactions, legal/audit records | Protected by default; no generic Burn | Separate owner / custody / legal hold approval |

**Delete-button migration is not a global text replacement.** Each original button must be classified: what bytes change, what object is targeted, whether it is reversible, which other resources reference it, who approves it, what happens after crash, and how to undo or verify. The scanner yields review candidates, never permissions.

## HOW TO USE

Developers can run the read-only repository inventory:

`python3 -I -B scripts/trash/universal_delete_inventory_u1.py`

It emits a bounded JSON location index. `incompletePaths` and `INCOMPLETE_REVIEW_REQUIRED` mean the result is not comprehensive. A zero-hit result **never** certifies that a widget has no deletion path; text search cannot identify every dynamically composed action.

To use the new control in a future owner-reviewed widget, place `TrashLifecycleActionDeck` in that owner's UI, supply verified resource identity/revision and reviewed policy state, opt in to the supported actions, and connect each `*ReviewRequested` event to that owner's existing confirmation/permission workflow. The receiving backend must revalidate all evidence at commit time. Passing `ownerApproved: true` in QML is not authority.

## VERIFY

GitHub CI: Trash Bottom-Left Launcher Contracts Python suite plus Meta Apollo Grammar. A native Quickshell load/interaction review remains separately necessary. Scanner evidence is a source audit, not a runtime deletion test.

## WATCH OUT FOR

- The old `post-apollo.trash-resource.v1` discovery contract advertises abilities, not signed owner authority. U1 does not promote those booleans into permission.
- Original resource revisions may be integers or timestamps rather than SHA-256. The future owner adapter must produce an exact 64-hex source witness before this U1 review deck can enable actions.
- Neither a UI signal nor an inventory row can authorize Restore or Burn. Real protected capture/backup migration still depends on V3a source trust, keys, release history, backup custody, safe cutover and owner approvals.
- Files, Notes and task/project links need different recovery semantics. Replacing every DELETE/CLEAR label mechanically would be unsafe and potentially misleading.
- The source scan is intentionally broad and may include false positives. Keep each finding marked `OWNER_REVIEW_REQUIRED` until its module owner classifies it.
- No local machine, service, real user data, foreign widget, source-owner module, or production permission is modified by U1.

## CHECKLIST

- [x] Recover prior V2z merged checkpoint and current main / open PR ownership.
- [x] Reuse existing `ActionButton` instead of creating another visual primitive.
- [x] Add request-only universal action deck, disabled by default.
- [x] Add bounded repository-wide candidate inventory.
- [x] Add fail-closed tests; run CI and correct any failures.
- [ ] Complete per-widget Delete/Clear/Remove owner classification using the scanner and source code.
- [ ] Choose first owner-approved live UI integration without bypassing its existing confirmation path.
- [ ] Continue V3a protected source authorization and production migration design in separate scoped work.
- [ ] Coordinate retention, custody, protected Restore/Burn and cross-module user acceptance.
- [ ] Operator approval before merge, local Quickshell changes or real production activation.

## NEXT

U2 // Classify the candidate list and integrate Trash/Restore/Burn review requests into one owner-approved, already-recoverable workflow. Prefer GIO or Trash++'s managed copies first; coordinate module owners before changing their Delete buttons. V3a source trust and backup readiness remains a parallel blocker for protected resources.

## DECISIONS

The operator expanded Trash++'s *product objective* to a Post-Apollo-wide deletion/recovery interface. This does not transfer code ownership, source permissions, production keys, PR merge permission or authority to mutate the local host. U1 is a request-only integration surface and investigation tool. Final acceptance remains with the operator.
