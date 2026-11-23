# 🏥💜 DOC 1 // C3e local challenge ↔ C4b signed denial: never independent trust

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM / STAFF:** Universal Connections · Protected C3e Identity / DOC 1 (external Hospital-compatible, live Hospital registration unverified)  
**ASSIGNMENT:** Test the now-merged DOC 2 C4b raw challenge mapping against the **actual existing DOC 1 local SQLite challenge state and protected-HOLD gate**  
**STATE:** Disposable source/CI negative bridge. No production authority, installed service or protected custodian.

## IMPLEMENTATION

The local C3e security ledger stores an issued challenge as a 32-byte random value, plus a hash and `issued`/`consumed` state in an ordinary local SQLite file. DOC 2's [C4b PR #2283](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2283) already proved these exact raw bytes can be losslessly represented as a 43-character unpadded base64url nonce and checked in the original signed **BEGIN / UNAVAILABLE** diagnostic response.

The remaining C3e-side question is **not whether the signature matches**. It is whether a matching signed denial can mistakenly convert a rollbackable local challenge and caller-supplied public key into an independently trusted, current host witness or terminal receipt.

This milestone adds an isolated C3e test-only `inspect_ci_only` that imports and calls the **unchanged** DOC 1 storage boundary and **unchanged** DOC 2 signed-denial adapter:

1. Require one actual existing `TrustBoundary(LOCAL_DEVELOPMENT_ONLY)`, a distinct `TrustBoundary(INDEPENDENT_CUSTODIAN_REQUIRED)` with **no local adapter**, and a known 32-byte local challenge. The existing local adapter resolves a local snapshot and `issued` or `consumed` outcome from its original SQLite ledger.
2. Pass those same 32 bytes and the caller-supplied **synthetic signed DENIAL** to DOC 2's original C4b adapter, retaining its exact signed nonce verification and digest checks. No extra signing or independent enrollment occurs in DOC 1's module.
3. Validate **exact** response-field sets, status/mode/source and all inherited denial flags for the local snapshot, challenge outcome, protected HOLD and C4b diagnostic. Reject extra positive claims and malformed result types.
4. Return only a diagnostic that separates local `issued`/`consumed` and proof-of-possession correspondence from protected custody, current head, enrolled receipt signer, real host/seat, C5 TimeW consent and production Sign-In. Every authority field remains `False`; `safeToRetry=False`; `next=HOLD_NO_PROTECTED_CUSTODY_OR_SIGNIN`.

The attack case is deliberately concrete: copy the local SQLite image; commit a signed C3e test history; verify C4b's synthetic signed denial alongside the local `consumed` outcome; then **restore the old SQLite image**. The same signed C4b denial still verifies, while C3e's local outcome goes back to `issued`. This is a **successful demonstration of local rollback insecurity**, not successful production recovery or permission to replay.

A second case shows the local signed C3e history fixture can be committed again after restoring an old image, despite previously consuming it. Neither test is allowed to set a protected result to true.

## HOW TO USE

No operator workstation or NAS actions. GitHub Actions uses the existing guarded disposable `/run/c3er-ci-*` SQLite fixture and its test-only Ed25519 signer. The new changes are strictly four additional DOC 1-owned files:

- `tests/connections/c3e_release_trust/C3eC4bLocalDenialShadowCI.py`
- `tests/connections/test_connections_c3e_c4b_local_denial_shadow.py`
- `.github/workflows/connections-c3e-c4b-local-denial-shadow-ci.yml`
- This document

The original DOC 2/C4b verifier, official signed RPM, real Silverblue process probe, DOC 1 signed ledger and protected boundary are **not changed**.

## VERIFY

The new 20-case matrix exercises valid local issuance and signed denial, exact raw-to-text nonce, locally consumed state, full SQLite rollback and reuse, substituted raw challenge, unknown challenge, wrong action, forged serial bytes, fake success text, poisoned positive/extra local/remote fields, swapped modes, protected adapter exclusion and unconditional production refusal.

The CI workflow additionally reruns the DOC 2 original raw-nonce and controller signed-denial cases, and original DOC 1 cutover-negative, IPC non-settlement, real SIGKILL, storage boundary and SQLite ledger suites. The repository's existing Grammar, root-pinned release and fake signed Fedora RPM workflows should also run at the exact PR head. Nurse 2 must independently inspect source and raw logs before the operator decides any merge.

## WATCH OUT FOR

- A valid Ed25519 signature verifies **bytes and possession of a key**, not who enrolled that key, which process owns it, whether a guest was physically selected, or whether the signed result is an independently protected terminal outcome.
- The local SQLite image can be restored, replaying the identical challenge and history. A signed `UNAVAILABLE` response cannot solve this problem.
- A challenge encoded as a C4b command nonce is not a **custodian-issued protected one-use challenge**. Encoding cannot transfer root authority between DOC 1/C3e and DOC 2/C4b.
- The C4b public signer in this test is minted locally for disposable CI and **not** enrolled by the operator. The producer contract [#2283](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2283) remains a proposal; no real trust API or C4b custody transfer is accepted here.
- DOC 5's TimeW local-first quarantine [#2288](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2288) and DOC 6 Identity command settlement retain distinct signing roles, protected histories and owners. An Identity-only diagnostic challenge must not be repurposed as TimeW C5 permission.
- Future independent NAS or other-computer custodians need separate operator enrollment, real current-head/challenge/receipt custody, rollback/revocation/partition recovery, source/seat evidence and C5 consent. No local fallback.

## CHECKLIST / NEXT

- [x] Confirm DOC 1 #2282 merged with Nurse 2 pre-merge scoped PASS and four exact-head CI runs; review current DOC 2 #2283 and DOC 5 #2288 scopes.
- [x] Add test-only exact C3e local challenge → C4b signed-denial negative integration with rollback replay.
- [ ] Exact-head CI and raw test verification.
- [ ] Nurse 2 pre-merge scoped review.
- [ ] Operator merge decision; no production installation or custodian activation.

## DECISIONS

The operator has already settled **local-first normal development, independent protected hardware later**. This work tests a real owner-to-owner *development interoperability seam*, without interpreting local state as a production enrollment. No new hardware or signing-key authority is selected, no native service activated, and no protection downgraded. **PRODUCTION SIGN-IN HOLD.**
