# 🏥💜 Connections ↔ Forest B4c // Two-store revocation ordering reference

**PATIENT //** The-Post-Apollo-Project
**ROOM //** Connections C3e/C4b ↔ Forest Core B4c · C5 decision seam
**ROLE //** External Hospital-compatible Connections DOC; live registration unverified
**STATE //** PROPOSED reference model only · no approved Forest-specific C5 issuer · production HOLD
**HANDOFF //** https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161

## IMPLEMENTATION

B4b checks a synthetic permission callback immediately before inserting an assistant response inside Forest's own SQLite transaction. If that permission is revoked concurrently in a separate security database or service, the callback cannot order the revocation acknowledgment with the durable Forest COMMIT.

**Proposed rule:** A separately protected issuer owns a durable one-operation fence, serialized in the same authority as grant revocation. The installed Forest commit service acquires a scope-bound permit before the final durable write. If revocation wins the issuer transaction first, no new permit is issued. If the fence wins first, a revocation may enter REVOKING but **must not acknowledge completion** while the earlier permitted commit can still succeed. The fence remains unresolved until an authenticated durable terminal outcome is known. A short-lived token or a pre-commit boolean alone cannot guarantee this ordering.

The isolated test in tests/connections/test_connections_forest_b4c_fence_reference.py uses a **disposable issuer SQLite file** separate from a **disposable Forest SQLite file**. Real BEGIN IMMEDIATE transactions serialize fixture admission and revocation in one issuer store. The independent Forest write does NOT atomically update the issuer. A lost receipt is UNKNOWN_HOLD even when the Forest fixture shows a committed row. The model never guesses the grant is unused or retries model inference.

**Proposed issuer states (not accepted):** ACTIVE, REVOKING (new permits prohibited, revocation acknowledgment pending), REVOKED (no unresolved permitted commits).

**Proposed permit states (not accepted):** PENDING, UNKNOWN_HOLD, COMMIT_CONFIRMED, ROLLBACK_CONFIRMED. In production, only independently authenticated crash-durable evidence from the protected Forest writer could resolve an uncertain outcome.

The test method named fixture_terminal_receipt is NOT a real receipt verifier. Any test can call it. This is a demonstration of an ordering invariant, not a cryptographic or human authorization grant.

## BINDING // semantic proposal, NOT an approved wire schema

A future issuer would need separately verified principal and Tree identity, exact GENERATE action, B3 user turn, attempt, request, grant, model, revision, consent epoch, expiry and witness digest under an isolated Forest conversation audience (postapollo.forest.conversation.v1). In tests these are synthetic strings subject only to exact binding/replay checks. They are NOT authenticated inputs.

C3e/C4b must independently authenticate installed requester AND commit host release/process, Linux original peer lifetime, active seat/session and signer-history trust. C5 must independently authorize the exact operation and own revocation/receipt custody.

READ_SESSION is intentionally not covered by this commit-fence reference. Reading stored conversation history, private Trees, or Leaves memories requires a separate reviewed policy and confidentiality controls. A GENERATE grant must never authorize model tool execution.

## VERIFY // isolated real SQLite tests

Run:
python3 -B -I -m unittest discover -s tests/connections -p 'test_connections_forest_b4c_fence_reference.py' -v

The test suite exercises:
- Permit first then revocation: final revocation acknowledgment waits for permitted commit settlement
- Revocation first: subsequent permit denied
- Crash or lost receipt: unresolved permit remains UNKNOWN_HOLD, never auto-retried
- Two separate real SQLite stores: a Forest write does not establish a trusted issuer receipt
- Wrong principal, Tree, attempt, model, user turn, epoch, revision and misbound result denied
- Duplicate attempt/grant/request, expired grant, wrong audience and missing scope denied
- Two concurrent SQLite connections and threads racing permit vs revocation: both possible orderings preserve safety

The dedicated GitHub CI runs only the isolated reference test. Green CI proves only the fixture-level ordering invariant, not native trust.

## WATCH OUT FOR

1. No globally atomic transaction exists between C5 and Forest. Source-owner and protected-store receipts plus a durable reconciliation contract remain to be designed. A crash can leave UNKNOWN_HOLD indefinitely until independently approved recovery; **never release a fence merely because its TTL expired**.
2. In-memory witness strings, developer-provided IDs, Python dataclasses, caller-selected roots or same-UID Unix socket credentials do not authenticate the requester or unlocked human seat. The fixture can create fake scopes and cannot be shipped as an issuer.
3. Real receipts must be protected against an attacker-controlled Forest process, replacement, replay, key rotation, history rollback and receipt loss. The fixture does none of this.
4. B4b streams provisional DELTA before final authorization. Mid-stream revocation/cancellation, confidentiality and terminal acknowledgment are still owner decisions.
5. The separate Forest test database writes only a dummy attempt ID. **No private chats, models, prompt text or personal data are processed.**
6. Protected C3e/Identity signer enrollment remains PAUSED under Issue #2018. C4b is separately accepted. This reference neither resumes that Room nor edits a C5 source file.

## NEXT / OWNER ACCEPTANCE REQUESTS

**Connections C3e/C4b:** ACCEPT / REVISE / HOLD for independently authenticated installed Forest requester/commit host and active-seat/release/issuer evidence. Process SHA snapshots alone are diagnostic.

**C5:** ACCEPT / REVISE / HOLD on a separate Forest audience, exact scoped grant and consent, durable permit/revocation serialization, crash-unknown result and protected receipt verification. An equivalent alternative fencing model may be proposed; the test fixture does not dictate production storage choice.

**Forest backend:** confirm exact turn/attempt/revision/commit receipt seam after issuer contract approval. Current synthetic pre_commit callback does not hold a protected fence across SQLite COMMIT. Forest-owned files remain untouched here.

**Nurse 2:** independently review exact-source test and later native C5 integration before merge. **Operator:** separately approve production signing-key custody, real private storage and deployment.

**DECISION //** PROPOSAL ONLY · REVISE / HOLD. No protected C5/Forest/Identity/SwayPX/TimeW code changes, service activation, keys, enrollment or live desktop writes. No production authorization.
