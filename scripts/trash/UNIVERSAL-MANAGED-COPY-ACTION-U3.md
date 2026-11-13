# 🏥💜 Trash++ U3 // Managed-Copy Shared Action Integration

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External DOC-compatible GitHub worker; no verified live Hospital registration  
ASSIGNMENT // First actual U1 shared-review control in one Trash++-owned recoverable source  
BASE // `main 1f1f86dbc67608e7f7f30bf04f13ad753bc90b3f`  
SCOPE // `modules/Trash.qml`, `components/TrashLifecycleActionDeck.qml`, Trash tests/workflow, this document. No Weather, Notes, To-do, Hospital, Finance, identity, Time Machine, social, company source modification.

## IMPLEMENTATION

The Archive page has two different authorities:

1. **Original source records:** Weather event history and demo web research exports, which can be **copied** using the existing distinct SAVE COPY operation. The source data is never moved or deleted.
2. **Trash++-owned managed copies:** Local bounded copies that already support reversible `trash` and `restore` through `scripts/trash/research_records.py`, with store-wide `researchRevision` checked again by their backend. Only this second category is changed by U3.

U3 replaces the Archive row's historical single `TRASH COPY`/`RESTORE` ActionButton with the already merged `TrashLifecycleActionDeck`, enabled **only** for `SAVED RESEARCH` and `SAVED EVENT` rows. The new deck shows exactly one relevant action per state: TRASH for archived copy, RESTORE for trashed copy. Its Burn action remains hidden and unavailable.

The U1 deck's default 64-hex source revision witness is retained. U3 adds a **separately opted-in**, exact decimal `resourceRevisionKind: "store-counter"` validation for the managed-copy service. These counter tokens are not cryptographic proof and are not accepted by default. They are request data only.

The new `reviewManagedCopyAction(operation,ownerId,resourceId,expectedRevision)` in `Trash.qml` checks:

- Menu must still be open on Archive, not Trash/Burn or another view.
- Only `trashpp-managed-copy` owner identity and operations `trash` or `restore`; never a generic delete or Burn.
- Resource ID must have the exact current managed-copy 32-lowercase-hex format.
- Expected decimal store revision must exactly equal the currently indexed `researchRevision`.
- The selected record must still appear in `researchRows` with the requested state and kind.
- No busy Archive/managed/snapshot/GIO operation, modal Burn confirmation, or pending destructive state.

Only after these checks does it call the existing `trashResearchCopy(row)` or `restoreResearchCopy(row)`. They call the original `runResearch` wrapper, which passes the revision to the existing managed-copy backend for its independent update-time check.

No new or alternative delete backend, file path handling, source authority, Burn flow, Archive V2 snapshot mutation, GIO file action, records source index change or backend permission is introduced. All source SAVE COPY and existing two-click Burn buttons remain in their original places.

## HOW TO USE

Once authorized merge and local sync occur, open Trash++ → ARCHIVE, select COPIES (or ALL) and locate a managed `[MANAGED COPY]` record. It shows TRASH while archived, then RESTORE while trashed. The same item is also visible in the existing TRASH bin when trashed. Original source rows still show SAVE COPY, and a managed copy in the bin still has its separately verified BURN COPY button.

Existing menus and services are unchanged beyond this narrow action-control substitution.

## VERIFY

- GitHub Trash Bottom-Left Launcher Contracts: Python `tests/trash/test_*.py` and all existing Node regressions; U3 adds a dedicated `node --test tests/trash/test_u3_managed_copy_review.cjs` step.
- Tests extract and execute the *real* QML lifecycle adapter in Node's sandbox against synthetic managed items. They check successful routing, exact revision, wrong source, wrong state, busy states, missing item, changing revision and unsupported Burn.
- Existing Python launcher tests now assert the U1 deck integration instead of the retired archive-copy label, while continuing to check source Save Copy and two-click Burn safeguards.
- Native Quickshell geometry, focus, button glow and actual private GIO/managed-copy user data are **not** exercised by GitHub tests. Do not report desktop acceptance until operator/native evidence is available.

## WATCH OUT FOR

- UI flags `ownerApproved` and `policyReviewed` are **presentational gates**, never independently authenticated permission. The only backend authorization remains the already present, narrowly scoped managed-copy service and exact revision/row revalidation. The new shared U2 review module is deny-only and **not** an execution broker.
- A store-wide integer revision is not a per-item digest. Its stale-check is sufficient for maintaining the existing managed-copy backend's current concurrency contract, not for sensitive external source records.
- U3 does not make universal or source-owned Restore/Burn safe. Notes, tasks, Weather originals, Hospital, Finance, company, social, identity and MACHINE records remain outside the backend's write scope.
- Opening an Archive managed item that has become stale should refuse until the existing refresh updates `researchRows`.
- Do not replace native GIO bulk burn or existing Confirm UI with this deck. They implement a distinct multi-click safety protocol.

## CHECKLIST

- [x] Check Syntagma, latest main, prior U1/U2 merge and separate V3b ownership
- [x] Preserve the source- vs copy-owned record distinction
- [x] Add opt-in decimal store revision token without changing SHA default
- [x] Replace only managed-copy Archive TRASH/RESTORE action with U1 deck
- [x] Add request adapter that rechecks identity, state and revision
- [x] Add Node tests, adapt existing launcher assertions and workflow
- [ ] Exact-head CI and native Quickshell review
- [ ] Merge approval and GitHub exact-head merge status
- [ ] U4: expand owner-reviewed integration without crossing source authority

## NEXT

U4 // Validate the archived/trashed managed row visually in all four chassis sizes; then evaluate a GIO-only, separately witnessed action route in Trash view. Keep U2 strict deny-only and V3 protected Archive readiness independent.

## DECISIONS

Operator's `continue and merge approved` authorizes bounded GitHub implementation and safe PR merge after required verification, not local writes or production protected-record deletion. No Hospital worker/Room attachment is claimed. Operator's final visual acceptance remains outstanding.
