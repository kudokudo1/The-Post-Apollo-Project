# 🏥💜 DOC 3 // Forest C5 storage-independent authority boundary (NO AUTHORITY)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Connections C3e/C4b/C5 ↔ Forest B4c  
**STAFF:** DOC 3 · external Hospital-compatible; no verified live registration  
**SCOPE:** Connections-side semantic boundary and deny-only reference diagnostics  
**BASE:** DOC 1 #2229 (C3e storage-independent test client), Forest B4c #2208, DOC 3 #2168/#2171/#2175/#2180/#2195  
**STATE:** Source-only, not installed; production Forest READ/GENERATE/tool and Sign-In HOLD

## IMPLEMENTATION // Mechanism and ownership

DOC 1's #2229 exposes a C3e local-development SQLite adapter and a protected-custodian-required mode that deliberately refuses. Its tests/connections/c3e_release_trust code is not an enrolled Forest C5 backend and must not be imported as production authority. Forest #2208 provides a synthetic two-phase B4c consumer using an actual persisted B3 reserved attempt, but its context-manager permit and terminal ACK are forgeable fixtures.

The new Connections-owned services/connections/forest/ForestC5AuthorityBoundary.py defines a storage-neutral Forest boundary, without importing local ledger source or selecting a network endpoint:

- **read_current_trust_snapshot**: future independently authenticated Forest audience/host/release/role/epoch/current-head and revocation-state lookup; **refuses** today
- **prepare_generate**: future permission before inference with actual requester/seat/current owner; **refuses** today
- **acquire_commit_permit**: future exact B3 attempt-bound, issuer-serialized one-use fence held through Forest SQLite COMMIT; **refuses** today
- **lookup_terminal_outcome**: future independently trusted read-only crash reconciliation; **refuses** today, not a retry
- **settle_terminal_receipt**: future verifiable durable writer record tied to original exact grant/attempt and issuer-held journal floor; **refuses** today
- **request_revocation**: future durable revocation serialization; **refuses** today, never ACKs revoked while a prior permit might still commit
- **authorize_read_session**, **authorize_tool_execution**, **production_admission**: **refuse** all operations; read and tools need separate explicit policy

Two explicit modes exist: FOREST_CONTRACT_REFERENCE_ONLY and INDEPENDENT_FOREST_CUSTODIAN_REQUIRED. There is **no** trusted adapter in either mode, and no local SQLite, arbitrarily injected provider, supposed remote URL, or caller-provided trust pin may select one. The protected mode returns only INDEPENDENT_FOREST_CUSTODIAN_UNAVAILABLE_HOLD with every authority bit False; all other protected calls raise ForestC5Hold. Loss of future custodian service MUST fail closed, never switch to local state.

Reference mode has a pure diagnostic parity check for B4c's immutable SyntheticCommitBinding: 8 exact persisted fields (owner_key, tree_key, session_id, user_turn_id, attempt_id, request_id, model_key, expected_revision), compared to #2171's canonical COMMIT_GENERATE intent. Request-ID grammar is aligned with the real B4a client requirement (16–96 identifier characters). Inputs are caller-provided, NOT kernel-observed. The diagnostic never grants, spends, settles, signs, stores or authorizes.

### Newly surfaced semantic gap: signed session identity

ForestC5SignedEvidencePreflight.INTENT_FIELDS binds signed principal, tree, userTurn, attempt, request, model, revision, process and consent, **but not the B4c session_id**. Forest #2208's persisted binding includes both tree_key and session_id. Two differing session_id values can therefore map to identical signed C5 intent bytes if the other fields match. This milestone explicitly reports UNTRUSTED_FOREST_BINDING_MATCHES_SESSION_UNSIGNED_HOLD and signedIntentMissingForestSessionId=true, without pretending that Tree identity substitutes for the actual selected conversation session.

**Owner decision required:** Forest backend and Connections DOC 3 must ACCEPT/REVISE/HOLD on making the exact durable Forest session ID part of a future **versioned** signed COMMIT intent. Do not silently alter #2171's existing wire schema, cross-audience grants or Forest-owned source in this PR. The current v0 signed schema cannot become production C5 authority as-is.

## HOW TO USE

For source review / disposable CI only. New test:

    python3 -B -I -m unittest discover -s tests/connections -p 'test_connections_forest_c5_authority_boundary.py' -v

No UI, host installation, protected issuer, remote service, local database, key store, real chat access or operator action.

## VERIFY

Dedicated CI runs 20 new hostile boundary tests plus previous signed receipt/roles/custody/interop/two-DB fence/B4b suites (86 inherited security checks). It also runs the 15-case Forest B4c two-phase synthetic consumer test. Expected combined count: **121** if all suites complete, with independent check-run verification required. Static gate confirms no signer, SQLite connector, sockets, credential actuation, false-to-true authority change or import into the Forest runtime.

Checks cover:
- protected mode never accepting an injected caller backend, local development ledger, URL or public root
- every semantic operation refusing even when supplied plausible production arguments
- equal signed bytes for two different Forest session IDs, with both diagnostics still HOLD
- exact wrong principal, Tree, user turn, actual B3 attempt, request, model and revision refusal
- missing/extra binding fields, bool-as-int, ID grammar, wrong domain/phase, duplicate or noncanonical JSON
- late historical inspection never granting new permissions
- immutable source denial flags and no stateful permission escalation after tampered diagnostic objects

Green CI is **not** a trusted custodian, real human consent, native writer journal or signed storage transaction.

## WATCH OUT FOR

- **Local atomicity is not rollback resistance.** DOC 1 #2224 demonstrates replay after whole local SQLite restore. A future independent custodian must hold an operator-enrolled root, actual current head and revocation state that the Forest host cannot restore or forge together with its own DB.
- **A fake remote hostname or same-user socket is not an attestation.** Process/release/seat and original peer lifetime need DOC 1/DOC 2's trusted source contract and independent verification, not caller-provided records.
- **Session ID is currently unsigned.** Merging this deny-only boundary does not fix that wire-level omission.
- **Forest B4c is still synthetic.** The Forest backend owner must produce genuine durable writer transaction receipts, preserving unknown post-COMMIT crash windows and no-auto-retry.
- **Revocation ACK remains withheld for unresolved permits.** Unknown or contradictory terminal outcomes stay UNKNOWN_HOLD, never expire into presumed rollback.
- **Provisional DELTA disclosure and real READ_SESSION confidentiality** remain separate Forest/security owner decisions.

## CHECKLIST / NEXT

- [x] Re-read DOC 1 #2229 and Forest B4c #2208 current source before creating scope.
- [x] Preserve DOC 3/Forest/C3e ownership and refuse caller backend injection.
- [x] Add exact Forest binding diagnostic and explicit unsigned session HOLD.
- [ ] Verify exact-head CI and obtain independent Nurse 2 review **before merging**.
- [ ] Forest backend + DOC 3 approve versioned signed-session binding contract.
- [ ] DOC 1/DOC 2 supply independently protected writer public key/release/process/seat/current-head trust.
- [ ] Forest backend emits durable terminal journal tied to actual COMMIT/ROLLBACK.
- [ ] Forest C5 issuer serializes one-use commit permit/revocation; operator approves protected custody and real consent.
- [ ] Native hostile tests, independently accepted recovery and explicit production activation.

## DECISIONS

This is a semantic interface and missing-field diagnosis, **NOT** a protected authority implementation or license to borrow the C3e Identity local-ledger adapter. No shared consent schemas or producer files changed. Separate operator approval is required for any real custodian, installed signer, Forest data, workstation change, merge or production activation.
