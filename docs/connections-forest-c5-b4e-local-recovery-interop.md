# 🏥💜 DOC 3 // Forest B4e local recovery ↔ Connections C5 V1 evidence boundary

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · Forest C5  
**STAFF ROLE:** DOC 3, external Hospital-compatible; no verified live Hospital registration  
**PROVIDER:** OPEN AI // CHATGPT  
**ASSIGNMENT:** Verify two independently owned recovery observations cannot become invented authority  
**STATE:** Additive CI-only reference; no installed host, issuer, writer key, personal conversation access, model execution or production use  
**PRODUCTION FOREST / SIGN-IN / TIMEW:** HOLD

## IMPLEMENTATION // Why this seam matters

Forest B4e [#2255](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2255) strengthens B4d's owner-scoped read-only inspection of actual B3 SQLite attempt rows. The local inspector can report FOREST_RESERVED, FOREST_ABORTED or FOREST_COMMITTED, and cross-check local original user/reply/model/revision/provider lineage. This means the local database contains a coherent assistant reply, not that the protected Connections C5 issuer saw a legitimate COMMIT receipt.

Connections DOC 3 V1 [#2239](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2239) can verify three distinct signed fixture records binding exact sessionId, attempt, user turn, model, grant and claimed journal counter. Its public keys, Forest binding, previous head, permit and transaction label are caller supplied. A valid fixture signature also cannot certify a real protected SQLite COMMIT, nor can a supposedly signed rollback prove an original response was absent.

Two observations should **never be equated** merely because:
1. the local row says FOREST_COMMITTED and the test receipt claims COMMIT_CONFIRMED, or
2. the local row says FOREST_ABORTED and the test receipt claims ROLLBACK_CONFIRMED.

The new Connections-owned reference ForestC5LocalRecoveryComparison.py accepts exactly those two **untrusted diagnostic objects** plus the original V1 intent bytes. It checks that the B4e attemptId and sessionId agree with the V1 claim's original signed attempt/session, and rejects extra result fields or forged positive authority flags. It emits one stable source-only UNKNOWN_HOLD with a safe diagnostic classification:

- LOCAL_RESERVED_NO_TERMINAL_PROOF_HOLD: the Forest attempt could be in progress or stranded
- LOCAL_AND_SIGNED_CLAIM_AGREE_BUT_UNTRUSTED_HOLD: the local row and alleged signed outcome match, but neither is protected
- LOCAL_AND_SIGNED_CLAIM_CONFLICT_HOLD: local COMMITTED plus claimed ROLLBACK, or local ABORTED plus claimed COMMIT

**Every output** has safeActions=[], safeToRetryInference=false, safeToReleaseRevocation=false, actualSQLiteTransactionDurabilityProven=false, independentC5IssuerOutcomeAuthenticated=false, and every previously inherited v0/v1 protected authority flag false. Output never contains the owner, prompt, reply body or session/attempt IDs. The function has no SQLite connection, model call, process observation, signer or protected network access.

This is not a production reconcile endpoint and cannot settle a permit. Even a clean source comparison cannot convert Forest B4e into an independently authenticated writer journal.

## HOW TO USE // Disposable hosted CI

    python3 -B -I -m unittest discover -s tests/connections -p 'test_connections_forest_c5_b4e_local_recovery_interop.py' -v

The interop test creates actual disposable Forest B1/B3 SQLite tables with foreign keys, reserves a real B3 test attempt, writes or aborts the attempt using the existing Forest source and then queries **the real B4e inspector**, without changing its files. It fabricates valid three-key V1 role/receipt evidence on isolated test keys, and checks that both agreeing and contradictory combinations remain C5 UNKNOWN_HOLD.

A deliberate SQLite backup/restore shows how the same V1 claim can continue to claim COMMIT while local state moves from COMMITTED back to RESERVED. Neither version of local state is a protected antirollback source. No real Ollama request is sent. Source/test files are scoped to Connections; all Forest implementation files remain untouched.

## VERIFY // Expected acceptance

- 20 new B4e ↔ C5 cross-boundary hostile cases: local commit/lost ACK, abort, signed ROLLBACK contradiction, session/attempt mismatch, fabricated authority fields, corrupt B4e reply lineage, whole local DB rollback, V0 rejection, no model calls, no private-body disclosure
- Inherited Forest B4e/B4d and DOC 3 V1/authority and Forest B4c regressions
- Syntax and no-actuation check; dedicated GitHub Actions exact-head CI and independent Nurse 2 **pre-merge** review required
- Recheck Forest B4e independent source-review status separately; a green Connections interop test cannot supply it

## WATCH OUT FOR

This fixture comparison deliberately accepts untrusted caller objects. Even if all inputs match, an attacker able to restore the local Forest DB and fabricate signatures can manufacture both views. Future production source must authenticate:
- original installed Forest writer release + process/seat + key enrollment (DOC 1 / DOC 2)
- actual original B3 attempt and persisted session, with native transaction-coupled record (Forest backend owner)
- independently current head, signer epoch, permit and revocation history (protected independent custodian)
- human C5 consent and one-use serialized grant/terminal ACK (DOC 3)
- network process identity and recovery status; local FOREST_COMMITTED is not protected COMMIT_CONFIRMED
- midstream provisional DELTA disclosure and cancellation policy (Forest owner + operator)

No automatic re-inference on lost ACK, timer expiry, local abort, fake signed ROLLBACK or unknown journal receipt. Revocation completion cannot be acknowledged while a prior admitted commit may still succeed.

## CHECKLIST / NEXT

- [x] Syntagma AGENTS + Hospital role/permission/report protocols inspected
- [x] Exact current B4e source and DOC 3 V1 source inspected
- [x] Only Connections-owned additive test/reference/doc/workflow; no Forest owner edit
- [ ] Exact-head new and inherited CI verified
- [ ] Nurse 2 independent pre-merge exact-head security review
- [ ] Forest B4e own Nurse 2 retrospective source review remains independently owned
- [ ] Forest backend, DOC 1/DOC 2 and DOC 3 approve future authenticated transaction and issuer evidence producer/consumer protocol
- [ ] Operator authorizes real protected host, keys, actual personal data and activation after native acceptance

## DECISIONS

No change to V1 signed schema, C3e custodian, Forest host B4e, Hospital, TimeW, ForestW, Quickshell, production service, or remote machine. The comparison result is **diagnostic only**, never C5 receipt settlement or authority. Future native integration still requires its own cross-owner authorization and protected trust boundary.
