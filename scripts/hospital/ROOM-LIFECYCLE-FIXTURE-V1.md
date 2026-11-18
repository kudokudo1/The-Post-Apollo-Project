# 🏥 Hospital Room Lifecycle // V1 in-memory SQLite rehearsal

PATIENT // The-Post-Apollo-Project
ROOM // Hospital Surgery / Registered Room lifecycle
STAFF // External DOC-compatible; no verified live Hospital Room or Session
SCOPE // Additive, in-memory prototype in Hospital-owned files only
DEPENDENCY // PX Hospital store writer owner (The-Post-Apollo-Dev-Exp); Trash++ owner

## IMPLEMENTATION

This stage demonstrates a **reversible Room Trash -> Restore record lifecycle**
using SQLite **only in RAM**, on the actual PX v10 schema instantiated by
\`bin/px-hospital-store\` for test fixtures. It does not migrate or write
the operator's persistent \`hospital.db\`, and cannot open an on-disk database.

- \`install_fixture\` refuses all file-backed or attached databases and requires
  PX schema version 10. A test-only lifecycle table records exact Room identity,
  state (\`ACTIVE\`/\`TRASHED\`), monotonic revision, frozen graph hash, and
  non-authoritative receipt metadata. No original Room row is deleted.
- \`review\` computes a digest over the Room and its linked PX records, returns
  **counts** (not private text), and checks nonterminal Assignments and Sessions.
- \`transition(TRASH)\` checks expected revision and digest under
  \`BEGIN IMMEDIATE\`; rejects unclosed Sessions, active/paused/draft/ready
  Assignments, missing Room identity and unknown linked Assignment.
- \`visible_room_ids\` demonstrates the required **PX owner-side Room query
  semantics**: omit only Room IDs with a TRASHED lifecycle record.
- \`transition(RESTORE)\` checks the same exact Room, revision, and full graph
  digest and re-exposes the unchanged Room; it refuses mutated history.
- Both transitions and their receipt are committed in one transaction.
  Simulated precommit failure rolls back the entire change.
- No \`BURN\`, \`DELETE\`, \`BURN ALL\`, external Trash++ index, local file
  path argument, production-mode flag, session termination or source-owned
  data purge exists.

## HOW TO USE

Repository CI or a disposable development checkout:

\`python3 -B -m unittest discover -s tests/hospital -p 'test_room_lifecycle_fixture_v1.py' -v\`

No operator desktop command is provided. Directly invoking the implementation
module exits with refusal. The tests import the *real current PX v10 schema*,
create only SQLite \`:memory:\` databases, and never touch XDG paths.

## VERIFY

Test matrix covers Room hide/restore, unchanged original records, linked
Sessions/messages/decisions/reports, metadata-only review, nonterminal work,
stale revisions, same-revision graph changes, changes after Trash, replay,
simulated crash rollback, on-disk/attached database refusal, invalid IDs,
and permanent Burn denial.

## WATCH OUT FOR

This is **not production authorization** and is not a deployable backend:

1. **PX does not consult the prototype lifecycle state.** Real \`rooms_list\`
   still returns every durable Room, and PX writers can continue writing to
   any existing Room. Until the PX owner adds a trusted source-level lifecycle
   state, appropriate read filters, and write denials, the prototype cannot
   safely hide a Room in the live Hospital registry.
2. The graph digest protects fixture consistency and is **not an authenticated
   witness** of source identity or human consent. No external owner/seat/
   signature grant, retention or legal hold authority, or secure backup exists.
3. Synthetic receipts are not signed custody receipts. No durable backup,
   crash/power-loss test, schema migration or actual Trash++ resource index
   handoff has been validated.
4. Protected Hospital data must never be treated as a GIO file or generic
   managed copy; **do not trash or remove hospital.db**.
5. PX owns \`bin/px-hospital-store\`; open PX Hospital staffing and first-Bed
   drafts touch the same writer. This stage deliberately does not edit PX.
6. Current Room review UI from PR #2032 remains deny-only. Do not unlock
   \`TrashLifecycleActionDeck\` because this fixture passed.

## CHECKLIST

- [x] Review current PX store, Trash++ U1/U2 and merged review UI.
- [x] Introduce synthetic, transaction-safe Room hide + restore logic.
- [x] Show linked history preservation and stale/replay refusal.
- [ ] PX source-owner decides schema, migration, writer hold and read filter.
- [ ] Independent identity/permission/retention/custody authority.
- [ ] Persistent disposable DB crash/power-loss & Restore collision tests.
- [ ] Trash++ owner integrates a source-owned index and confirmed Restore.
- [ ] Independent security review, operator native acceptance.
- [ ] Permanent Burn only after separately authorized provenance, receipt,
      retention, backup and dependency review.

## NEXT

Coordinate a PX-owned, versioned Room lifecycle contract. Develop persistent
disposable integration separately after owner approval; add source transaction
guards to **all** PX writers, not only \`rooms_list\`. Do not modify the user's
local PX store or native Hospital and do not merge without authorization.

## DECISIONS

This PR proves reversible *mechanics* in a disposable memory fixture only;
it grants no production Room delete/restore/Burn authority and does not
reassign the PX/Trash++ workers' ownership. The operator has final acceptance.
