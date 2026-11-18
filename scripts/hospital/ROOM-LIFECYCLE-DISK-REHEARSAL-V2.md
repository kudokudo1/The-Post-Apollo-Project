# 🏥 Hospital Room lifecycle // V2 disposable disk restart and writer guards

PATIENT // The-Post-Apollo-Project
ROOM // Hospital Room Trash++ integration
STAFF // External Hospital-compatible DOC, no live registration claimed
ASSIGNMENT // Test persistent source-owned Room Trash/Restore without crossing PX owner files
SCOPE // Additive Hospital-owned CI fixtures only

## IMPLEMENTATION
- Uses pinned PX v10 schema from \`The-Post-Apollo-Dev-Exp@c856f6ed\`.
- Creates a **new, private, random-named SQLite DB only within GitHub Actions RUNNER_TEMP**, never accepts a user-supplied database path, never opens the host's hospital.db, and refuses direct CLI invocation.
- Adds in-fixture Room state + monotonic revision + graph digest and atomic transition receipts.
- Proves Room visibility and Restore across fresh SQLite file connections; preserves the entire original Room, Session, message, event, checkpoint, report and chart rows.
- Simulates a separate process dying mid-WAL transaction before commit. After reopen, both lifecycle state and receipt roll back.
- Tests lost-acknowledgement replay, stale graph data, two competing TRASH requests, active Assignments and unclosed Sessions.
- In the **synthetic database only**, installs guard triggers for existing PX v10 Room-related tables and session events, covering insertion, mutation and deletion of records tied to a TRASHED Room. This tests desired future backend semantics, not a deployed PX change.
- BURN and DELETE remain completely unsupported. No operator grant, no signing, no protected Archive capture, no Trash++ production index.

## HOW TO USE
GitHub workflow **Hospital Room Disk Restore Rehearsal** only. No desktop terminal commands or service integration. Tests create and clean up their private database in the ephemeral GitHub runner.

## VERIFY
- Read-only source inspection and 9 disposable-disk test cases, including restart, WAL rollback, concurrent requests, write-denial triggers, history retention, replay refusal, fail-closed burn, and PX visibility mismatch.

## WATCH OUT FOR
1. **Real PX still neither installs these triggers nor filters its own rooms_list.** The test explicitly proves that a trashed fixture Room is still returned by the real current PX rooms_list routine. Shipping only a UI filter is insufficient: the PX owner must coordinate schema migration and all writer/read paths before any live Room Trash is allowed.
2. The harness is not an authenticated source owner or production permission engine. CI environmental gates restrict accidental use but are not security credentials. No retention/custody/legal hold, signed receipts, quotas, safe permanent Burn, or cross-owner Trash++ index.
3. Related-object enumeration reuses v1's graph selector and does not guarantee all cross-Room references: the PX owner must review every foreign key and durable artifact, especially linked external Git state and indirect references.
4. While triggers are useful as fixtures, a protected deployed adapter must use a centralized, versioned writer lock/authority. Broad triggers may collide with valid migrations and require explicit owner tests.
5. No PR merge, local Quickshell install, data cleanup, or production activation is authorized. Live review buttons stay locked.

## NEXT
- Independent PX owner review of lifecycle schema, true DB-origin identity and multi-writer locking, all write/read gates and reversible state.
- Test rollback using actual owner-reviewed persistent PX migration in disposable VM/test stores.
- Trash++ owner registers verified source-owned Room resources to bin, including permissioned Restore; maintain separate protected Burn track.
- Cross-owner security review and operator native final acceptance.

## DECISIONS
This is a **source-only disposable CI rehearsal**, not deployment or owner transfer. All synthetic receipts and counters are untrusted test evidence.
