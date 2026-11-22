# Forest Core B4b // Pre-Commit Authorization Recheck

STATUS: EXPERIMENTAL, synthetic-only. No live personal session or AI activation.
OWNER: Forest backend DOC lane; ForestW UI and Connections owners unchanged.

## Mechanism

B4a requires independent host-owned installed-peer verification and action/model
permission before B3 may reserve a user turn. But long-running inference could
outlive that approval. B4b adds a fresh admission decision **just before**
B3 inserts the assistant response into the synthetic SQLite journal.

Sequence:
1. The trusted host supplies its own peer evidence and checks caller + model
   permission. The request cannot choose a caller, owner, grant, or session seat.
2. B3 durably reserves the attempt and starts an explicitly approved model
   stream. All DELTA output is marked provisional.
3. After a valid COMPLETE packet and clean end of stream, B3 enters one SQLite
   transaction, checks the session revision and reservation, and invokes the
   injected pre_commit callback BEFORE writing an assistant turn.
4. B4a's callback repeats installed caller verification and operation-specific
   authorization. Owner, PID and UID must still match the original admission.
   Only the literal Python boolean True permits B3 to insert the reply, update
   revision and mark the attempt COMMITTED atomically.
5. Expired proof, revoked approval, changed caller identity or verifier errors
   refuse COMMIT. The outer B3 attempt is marked ABORTED, with no assistant turn
   and no automatic re-inference.

Both existing interfaces stay injectable. The B3 pre_commit hook is optional
for legacy disposable B3 tests. **The B4a generator always installs it.**
This is a contract seam, not proof that a live production host is correctly
wired.

## Verify

    python3 -m unittest discover -s tests/forest -p 'test_host_precommit_b4b.py' -v
    python3 -m unittest discover -s tests/forest -p 'test_host_admission_b4a.py' -v
    python3 -m unittest discover -s tests/forest -p 'test_turn_bridge_b3.py' -v

All tests use temporary synthetic plaintext SQLite files and fake model
streams. The B4b suite exercises allowed completion, revocation after DELTA
and just before COMMIT, owner/PID/UID drift, expired identity lease, verifier
and policy exceptions, callback non-boolean results, rollback, cancellation,
no-retry, and the in-transaction pre-commit ordering.

## Remaining production security blockers

- B4a VerifiedCaller is a FORGEABLE in-process dataclass, not an independently
  verified C3e/C4b installed-process witness or authenticated human.
- The injected pre_commit hook cannot by itself obtain kernel peer credentials
  or check the compositor seat. The future protected host must fetch current
  installed process/seat evidence **again** on each call.
- Rechecking an external Connections policy during SQLite BEGIN IMMEDIATE
  does not produce a globally atomic distributed transaction. Consent could
  theoretically be revoked immediately after the callback and before COMMIT.
  A production design requires a signed, short-lived fenced authorization
  or a transactionally synchronized revocation protocol with security owners.
- Provisional text may already have been displayed before permission is lost.
  A production host also needs mid-stream revocation/cancellation and
  acknowledgments, not merely a pre-commit check.
- In-memory/fake authorization callbacks are not safe to expose as service
  endpoints. There is still no production daemon, listener, host-owned disk
  storage, encrypted data at rest, identity, real user provisioning, or tool
  execution permission.
- B1/B3 use PLAINTEXT *synthetic* test fixtures. Do not connect personal
  conversations, Leaves memory, or QML to them.
- ABORTED or leftover RESERVED attempts stay replay-blocked. Manual
  recovery and actual signed receipts remain a future separate milestone.

Scope: scripts/forest/turn_bridge_b3.py, host_admission_b4a.py, this B4b
document, dedicated tests and CI only. No UI, Identity, Hospital, shell
or desktop files are modified.

NEXT: independent review, coordinate authoritative C3e/C4b/C5 security
ownership and real revocation fencing, then native fixture end-to-end test.
Operator final acceptance remains separate from passing synthetic checks.
