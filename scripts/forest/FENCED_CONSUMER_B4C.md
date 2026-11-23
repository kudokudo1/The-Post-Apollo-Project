# Forest Core B4c // Synthetic Two-Phase Held-Permit Consumer

STATE: DRAFT, synthetic-only, production Forest HOLD.
PATIENT: The-Post-Apollo-Project
STAFF: external Hospital-compatible Forest backend DOC, live registration unverified.
OWNERS: Forest scripts/forest only; Connections C3e/C4b/C5 and ForestW separately owned.

## IMPLEMENTATION

B3 creates the durable RESERVED attempt after B4a's initial authorization.
Connections #2168/#2171/#2175/#2180/#2195 establish DENY-ONLY reference
contracts for a later C5 permit serialized against revocation, bound to the
actual B3 attempt and held through Forest SQLite COMMIT/ROLLBACK plus terminal
proof. No live issuer, installed trust or real protected writer exists.

The Forest-owned consumer shape works in SYNTHETIC mode only:

1. B4a checks PREPARE_GENERATE permission before any inference.
2. B3 stores a reserved attempt with its own generated attempt ID.
3. Following complete B2 streaming, B3 derives an immutable binding from
   stored owner/Tree/session/user turn/attempt/model/revision rows. Request ID
   remains correlation only, never authentication.
4. An in-process test-only host permit factory enters a context manager
   for that exact binding. A distinct B4a COMMIT_GENERATE permission check
   and unchanged owner/PID/UID verification occur inside the B3 write
   transaction. The permit holder stays active during actual SQLite COMMIT.
5. After Forest COMMIT, the held permit receives terminal outcome.
   A literal True acknowledgement and successful permit exit are both
   required before B3 emits COMMITTED to its caller. Lost terminal ACK or
   post-commit errors produce UNKNOWN_HOLD (no re-inference). SQLite may
   already contain the reply; the denial does NOT undo that database commit.

## RECOVERY / NO AUTO-RETRY

Revoke first -> no final permit. Permit first -> revocation may enter
REVOKING but cannot be acknowledged complete before a terminal outcome.
Lost terminal result -> UNKNOWN_HOLD indefinitely until independently
authenticated recovery, never timeout-based release. Failed pre-commit policy
-> no reply, B3 attempt ABORTED, but a remote issuer may still require
independent rollback proof before settlement.

Provisional DELTA output can already have reached a client. Production
disclosure/cancellation policy remains unresolved.

## VERIFY

Run isolated suites using only temporary synthetic databases and fake streams:

    python3 -m unittest discover -s tests/forest -p 'test_fenced_commit_b4c.py' -v
    python3 -m unittest discover -s tests/forest -p 'test_turn_bridge_b3.py' -v
    python3 -m unittest discover -s tests/forest -p 'test_host_admission_b4a.py' -v
    python3 -m unittest discover -s tests/forest -p 'test_host_precommit_b4b.py' -v

## WATCH OUT FOR

The test permit is a forgeable Python object. This is NOT an independently
enrolled C3e/C4b process/seat/release witness, protected human C5 consent,
signed one-use permit, real revocation fence, authenticated writer receipt,
durable journal custody, owner-protected encrypted database or native service.

Legacy B3/B4a paths remain experimental and must not become production
fallbacks. Connections' test-only signature/receipt checks advertise
no authority and cannot unlock private Forest data. ForestW UI unchanged.
No installed service, real keys, personal prompts or desktop mutation.

## NEXT / DECISIONS

Issue #2161 remains the cross-owner checkpoint. Connections DOC 3 owns
Forest C5 producer and revocation, DOC 1 owns trusted installed source.
Forest owns this consumer and eventual protected writer. Nurse 2 must review
exact PR HEAD before any merge. Operator must approve native deployment,
private conversation storage and production authority separately.
Production authorization remains HOLD.
