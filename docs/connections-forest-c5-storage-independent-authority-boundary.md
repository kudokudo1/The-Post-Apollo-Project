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

- **authorize_list_sessions**: distinct private metadata enumeration entitlement, **refuses** in both modes (never aliases READ_SESSION, GENERATE or ForestW's presentation parser).
- **authorize_disclose_session_titles**: separately scoped private title-output consent, **refuses** in both modes (never inferred from valid listing, UI request correlation, or matching B1 rows).
- **forestListSessionsPermissionGranted** and **forestPrivateTitleDisclosureGranted**: immutable reference/status denial bits, both FALSE even if a caller tampers with a diagnostic reply.

### DOC 3 C5 list/title entitlement separation · later additive milestone

After merged ForestW #2358/#2362, Forest Core B5a #2373, B5a provenance follow-up #2377 and DOC 3 #2352, the next native API remains **unapproved**. This additive boundary change closes a local semantic gap without inventing native issuer authority or changing any Forest-owned source: listing IDs and disclosing titles are two separate C5 grants, and each must explicitly fail while the protected issuer/custodian and recipient do not exist.

A future **operator-approved** Forest host (owned by Forest Core) must independently authenticate the original user, process, active seat, release and selected canonical Tree and resolve the original protected database **before** reading. C5 must separately authorize (1) enumeration and (2) release of private titles to the authenticated recipient; current timestamp, consent epoch, revocation and storage history require independent custody. The existing B4a single-ID READ_SESSION, B1 synthetic owner filter, ForestW #2362 requestId/generation and #2352 provisional-DELTA fixture confer none of those permissions. Neither LIST nor title display implies GENERATE/SEND/voice/COMMIT. On any uncertain origin, revoked consent, wrong Tree, mixed-owner rows, unprotected DB, disconnected issuer, partial output or stale recipient, disclose **zero titles**, never fall back to synthetic B1.

**This is not a native LIST_SESSIONS wire protocol.** The new methods accept arbitrary parameters only to refuse them with distinct fixed, non-leaking errors; there is no serializer, trusted permission input, private title reader, fake positive path, key, socket or native host. Actual versioned provider semantics still require Forest Core/ForestW/Connections Nurse 2/operator ACCEPT/REVISE/HOLD. Do not enable session list or private output from source-only checks.


Two explicit modes exist: FOREST_CONTRACT_REFERENCE_ONLY and INDEPENDENT_FOREST_CUSTODIAN_REQUIRED. There is **no** trusted adapter in either mode, and no local SQLite, arbitrarily injected provider, supposed remote URL, or caller-provided trust pin may select one. The protected mode returns only INDEPENDENT_FOREST_CUSTODIAN_UNAVAILABLE_HOLD with every authority bit False; all other protected calls raise ForestC5Hold. Loss of future custodian service MUST fail closed, never switch to local state.

Reference mode has a pure diagnostic parity check for B4c's immutable SyntheticCommitBinding: 8 exact persisted fields (owner_key, tree_key, session_id, user_turn_id, attempt_id, request_id, model_key, expected_revision), compared to #2171's canonical COMMIT_GENERATE intent. Request-ID grammar is aligned with the real B4a client requirement (16–96 identifier characters). Inputs are caller-provided, NOT kernel-observed. The diagnostic never grants, spends, settles, signs, stores or authorizes.

### Newly surfaced semantic gap: signed session identity

ForestC5SignedEvidencePreflight.INTENT_FIELDS binds signed principal, tree, userTurn, attempt, request, model, revision, process and consent, **but not the B4c session_id**. Forest #2208's persisted binding includes both tree_key and session_id. Two caller-fabricated B4c bindings with different session_id values can therefore map to identical signed C5 intent bytes if all the other fields are supplied as equal. **This does not demonstrate a real B3 duplicate-attempt exploit:** Forest's persisted attempt_id is a unique database primary key. A separately authenticated lookup from that exact signed attempt to its authoritative persisted session_id could provide a valid *indirect* binding if a protected source independently proves the lookup and prevents aliasing, rollback and replay. A merely caller-provided lookup remains untrusted. This milestone reports UNTRUSTED_FOREST_BINDING_MATCHES_SESSION_UNSIGNED_HOLD and signedIntentMissingForestSessionId=true, without pretending that Tree identity alone authenticates the selected conversation session.

**Owner decision required:** Forest backend and Connections DOC 3 must ACCEPT/REVISE/HOLD between (A) adding the exact durable Forest session ID in a future **versioned** signed COMMIT intent or (B) formally proving and independently authenticating the original signed attempt_id -> persisted session_id mapping in the protected writer/issuer contract. Both require native negative tests for mismatched sessions, replay, altered persisted rows and source substitution. Do not silently alter #2171's wire schema, cross-audience grants or Forest-owned source in this PR. The current v0 signed intent cannot be promoted without this missing identity proof.

### B6 reference-boundary hardening

Following [#2427](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2427), the current deny-only C5 reference inspector now checks exact dictionary cardinality and plain string keys before building a set. It raises the same fixed malformed-intent refusal after leaving the parser exception handler, avoiding ordinary nested exception links retaining rejected JSON/Unicode inputs. This does not erase traceback locals, externally active exception context, or establish a production incident. Tests consume actual merged B6-R1/R2 reference and selected Workshop values, and verify no permission from either C5 mode. No changes to the Forest registry, wire format, protected issuer, storage or live runtime integration. Existing independent issuer/host dependencies remain HOLD.

## HOW TO USE

For source review / disposable CI only. New test:

    python3 -B -I -m unittest discover -s tests/connections -p 'test_connections_forest_c5_authority_boundary.py' -v

No UI, host installation, protected issuer, remote service, local database, key store, real chat access or operator action.

## VERIFY

Dedicated CI runs 29 hostile boundary tests, including 6 independent LIST_SESSIONS/title denial cases and 3 reference hardening/B6 regression cases, plus previous signed receipt/roles/custody/interop/two-DB fence/B4b suites (86 inherited security checks). It also runs the 15-case Forest B4c two-phase synthetic consumer test. Expected combined count: **130** if all suites complete, with independent check-run verification required. Static gate confirms no signer, SQLite connector, sockets, credential actuation, false-to-true authority change or import into the Forest runtime.

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
- [x] Explicit deny-only LIST_SESSIONS and private-title grants remain separated from READ_SESSION/GENERATE and from UI schema parsing.
- [ ] Forest Core + C5 + operator approve native private-title policy and independently protected LIST_SESSIONS provider.
- [ ] Forest backend + DOC 3 approve versioned signed-session binding contract.
- [ ] DOC 1/DOC 2 supply independently protected writer public key/release/process/seat/current-head trust.
- [ ] Forest backend emits durable terminal journal tied to actual COMMIT/ROLLBACK.
- [ ] Forest C5 issuer serializes one-use commit permit/revocation; operator approves protected custody and real consent.
- [ ] Native hostile tests, independently accepted recovery and explicit production activation.

## DECISIONS

This is a semantic interface and missing-field diagnosis, **NOT** a protected authority implementation or license to borrow the C3e Identity local-ledger adapter. No shared consent schemas or producer files changed. Separate operator approval is required for any real custodian, installed signer, Forest data, workstation change, merge or production activation.
