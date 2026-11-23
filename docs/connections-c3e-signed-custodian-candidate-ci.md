# 🏥💜 DOC 1 // Signed synthetic C3e custodian response is not independent custody

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** Universal Connections · Protected C3e Identity  
**STAFF:** DOC 1, external Hospital-compatible; no verified live registration  
**ASSIGNMENT:** Test a cryptographic future-custodian *response candidate* without granting production root, current history or Sign-In permissions  
**STATE:** Disposable GitHub-hosted CI only · **PRODUCTION SIGN-IN HOLD**

## IMPLEMENTATION

A signature authenticates a precisely defined byte string **under a specified public key**. It does not establish who independently enrolled the key, whether the signer was a physically separate machine, whether the key is revoked, or whether the signed state is current. This experiment makes that distinction executable using existing C3e security context.

The new pure CI-only module validates one strict Identity-purpose request with a fresh *synthetic* request identifier, exact 32-byte challenge encoding, epoch and expected head/sequence. A candidate response must repeat those fields exactly and can report only `UNAVAILABLE`, `settlement=NONE`, `challengeState=UNKNOWN`. It contains a candidate head/sequence plus a canonical unpadded URL-safe Ed25519 signature over a domain-prefixed canonical JSON body. The verifier is provided a **locally generated test public key by its caller**, not an operator-approved enrolled root.

An authentic test signature can be evaluated against the query's expected history checkpoint and classified as stale, ahead, equal or same-sequence fork. Every classification remains HOLD. A second classifier accepts two individually valid signed candidates and refuses to elect a winner: two different signed heads with the same sequence are a **split-brain risk even when both signatures match the same test key**, while identical signed reports may be duplicates rather than independent witnesses.

**Positive cryptographic observation:** `cryptographicTestSignatureValid=True` means only that the signature matches the supplied **test key** and body. Every source/authority field remains FALSE, including `operatorEnrolledHistoryRootVerified`, `independentCurrentHistoryVerified`, `independentChallengeSpentVerified`, `authenticatedRemoteTransportVerified`, `nativeGatewayHostReleaseSeatVerified`, `protectedTerminalReceiptVerified`, `identityC5ConsentVerified`, `safeToRetry` and `productionSignInAllowed`. Both report types set `winner=None`, `safeActions=[]` and `HOLD_NO_INDEPENDENT_CUSTODIAN_OR_TERMINAL_SETTLEMENT`.

The input is a **proposed, untrusted candidate shape**, not a frozen wire protocol. No socket, remote service, disk storage, autonomous key provisioning, native C4b producer, protected Sign-In command, protected challenge issuance, actual independently settled receipt or approval hook exists here.

## HOW TO USE

GitHub Actions runs one disposable root-guarded Python test process with a transient Ed25519 private key generated **inside the test suite only**. The verifier imports only public verification. Nothing is written to the user's workstation, NAS, installed gateway, real keyring or production SQLite store.

The change is exactly four new DOC 1-owned files:

- `tests/connections/c3e_release_trust/C3eSignedCustodianCandidateCI.py`
- `tests/connections/test_connections_c3e_signed_custodian_candidate_ci.py`
- `.github/workflows/connections-c3e-signed-custodian-candidate-ci.yml`
- This document.

The module's `protected_admission` unconditionally raises refusal. The merged `TrustBoundary(PROTECTED_REQUIRED)` retains its no-local-fallback rule and is not changed.

## VERIFY

30 new tests cover valid test-key signature with zero authority, stale and forward history, equal-sequence fork, two conflicting candidates signed by the **same** test key, duplicate signed reply posing as a quorum, differing sequence without winner, wrong public key, post-signature body modification, changed challenge/request ID/epoch, cross-purpose request/response, fake enrolled signer role, `COMMITTED` or spent-challenge claims, added `signInAllowed` fields, noncanonical padded signatures, mutated signature, boolean/zero counters, wrong public-key length, attempts to replace the receipt policy, unconditional production admission denial and hosted-runner guard.

Exact-head CI also reruns 203 inherited tests: 32 custodian cutover, 30 IPC nonsettlement, 24 split-store rollback, 22 split-brain comparison, 22 real Identity packet-origin integration, 28 storage trust boundary, 17 real SIGKILL, and 28 original local SQLite ledger. Additional exact-head Grammar, root-pinned release, and Fedora test RPM/SELinux checks are separate gates.

Nurse 2 independently reviews the exact source head and raw logs, then the operator separately decides whether to merge.

## WATCH OUT FOR

- **Unenrolled test key:** Valid signed bytes do not authenticate an operator-approved independent custodian. A caller-supplied public key is not a trust root.
- **No rollback resistance:** The caller also supplies the expected head/epoch. Local state can be restored or forked as shown in reviewed #2334/#2348. This experiment does not authenticate a durable remotely held current checkpoint.
- **No guaranteed one-use challenge:** Exact challenge binding is not challenge issuance, authoritative consumption or revocation.
- **No settlement:** `UNAVAILABLE` and `NONE` cannot settle a previous attempted native command, even if correctly signed. Ambiguous command outcomes remain UNKNOWN/HOLD and cannot be automatically retried.
- **No native producer or consent:** DOC 2's current Silverblue gateway, DOC 5's C5 human authorization and DOC 6's Identity command recovery remain separate owners. Signature correctness cannot replace host/seat/process measurements or human consent.
- **No external hardware selected:** Local-first development and later independent hardware/NAS are established direction, but actual admin, root ceremony, key rotation/revocation, challenge store, operator acceptance, transport and recovery policy are unresolved.

## CHECKLIST / NEXT

- [x] Reconcile reviewed and merged #2361 source, all 4/4 CI and C3e ownership.
- [x] Add signed request/response candidate shape and dual signed fork negative classifier.
- [ ] Verify exact-head 30 +203 CI tests and Fedora/Grammar/root runs.
- [ ] Request independent Nurse 2 scoped review.
- [ ] Operator merge decision separate.
- [ ] Subsequent protected custodian design needs independently administered authenticated source, root enrollment and recovery policy. **PRODUCTION SIGN-IN HOLD.**

## DECISIONS

A test-key signature can be valid while the entire operation remains untrusted. This milestone advances **cryptographic field binding** in DOC 1's lane without choosing, installing, or activating a real protected custodian. No production Sign-In.
