# 🏥💜 DOC 1 // Signed custodian candidate over an actual Unix packet still remains untrusted

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM / ASSIGNMENT:** Universal Connections · Protected C3e Identity / Bounded real-process signed-candidate verification  
**STAFF:** DOC 1, external Hospital-compatible; no verified live Hospital registration  
**PRODUCTION SIGN-IN:** HOLD

## IMPLEMENTATION

The kernel delivers a `SOCK_SEQPACKET` message from one process to another as a single packet. The receiving program checks the exact byte count, JSON fields and an Ed25519 signature over the Identity-purpose request, challenge, epoch, predecessor history and test-only `UNAVAILABLE` response. This moves the merged [#2369](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2369) signature check beyond an in-memory response: the same existing verifier now examines data **actually received across a Unix socket from a forked process**.

However, the private key originates in a disposable GitHub CI fixture, and the receiving test already holds the corresponding public key. This only verifies locally pinned **test-key** possession. There is no operator-selected independent administrator, NAS or physical host, root enrollment ceremony, authoritative current head, cryptographically authenticated installed C4b release/seat, durable one-use challenge or Identity C5 consent.

The new CI-only `C3eCustodianWireDenialCI` consumes exactly one bounded, 4-byte-length-prefixed `AF_UNIX/SOCK_SEQPACKET` response, strictly rejects duplicate JSON keys, truncated/extra bytes, non-finite data and ancillary data, and **closes any unexpected passed `SCM_RIGHTS` file descriptors before refusing the packet**. It calls the **unchanged** `C3eSignedCustodianCandidateCI.inspect_ci_only` for the actual signature and exact request binding, and then reasserts all authority fields are false. It neither creates a server/listener nor generates a signing key itself; both are confined to the GitHub-hosted test.

If the child dies before replying, closes the socket without a response, or a timeout occurs, the caller receives `UnknownAfterSend` with **UNKNOWN/HOLD, never automatic retry**. If the child sends a signed `UNAVAILABLE` and then is killed, the signature can still be verified but nothing becomes protected. Two valid contradictory signed packets from the same test key still cannot select a global head or authorize an operation.

The original protected C3e `TrustBoundary(PROTECTED_REQUIRED)` remains unmodified, requires an independently administered custodian, and refuses local SQLite fallback.

## HOW TO USE

This is a four-file, additive DOC 1 GitHub CI milestone with no workstation instructions:

- `tests/connections/c3e_release_trust/C3eCustodianWireDenialCI.py`
- `tests/connections/test_connections_c3e_custodian_wire_signed_denial.py`
- `.github/workflows/connections-c3e-custodian-wire-signed-denial-ci.yml`
- This document.

The test-only sender generates a temporary private Ed25519 key in the disposable test fixture, inherited only by forked CI children. The actual verifier receives the previously prepared test public key as a function input. **This is not a frozen production transport contract or enrollment system.**

## VERIFY

The 30 new real-process cases cover: honest signed denial, stale/advanced/forked history, two signed conflicting packets from one key, repeated duplicate signatures, wrong prior public key, wrong signing key, changed signed body, changed request ID, challenge or epoch, cross-purpose request and response, signed `COMMITTED` or spent-challenge claims, extra positive credential fields, duplicate JSON, short/trailing frames, EOF, genuine child `SIGKILL` before and after send, unexpected `SCM_RIGHTS` cleanup, non-SEQPACKET transport, invalid pin length, missing-reply timeout, hostile runner guard and unchanged protected no-local-fallback.

The new GitHub workflow additionally executes 233 inherited C3e cases: 30 signed-candidate, 32 cutover, 30 IPC nonsettlement, 24 split-store rollback, 22 split-brain, 22 per-packet Identity, 28 storage boundary, 17 real SIGKILL and 28 local ledger. Exact-head Grammar, root-pinned release and fake signed Fedora RPM/SELinux checks remain required. Independent Nurse 2 scoped review is separate from any operator merge authorization.

## WATCH OUT FOR

- **A socket does not make an independent network.** Forked processes and a shared test key still live in one disposable GitHub runner and the same administrator's control.
- **A signed denial is not terminal settlement.** Even genuine `UNAVAILABLE` cannot establish whether some other previously attempted command committed; on absent or unclear acknowledgment preserve UNKNOWN/HOLD.
- **A caller-supplied test pin is not enrollment.** Moving the public key into a function argument or comparing key fingerprints does not establish external custody, rotation, revocation or independently current history.
- **No credential actions are enabled.** No source in `services/` or any other worker's lane changes. DOC 2 still owns actual C4b Silverblue evidence, DOC 5 C5 human approval, DOC 6 native Identity command recovery, and the operator retains production acceptance.
- **No local host modifications.** All sockets and generated keys exist only in disposable GitHub-hosted CI, not the user's workstation.

## CHECKLIST / NEXT

- [x] Reconcile merged/reviewed DOC 1 #2369, DOC 2 #2360/#2366 and DOC 4 #2370.
- [x] Implement a real-process denial packet verifier using the original signed response contract.
- [ ] Verify new/inherited exact-head raw GitHub CI plus Grammar/root admission/Fedora.
- [ ] Obtain Nurse 2 independent exact-head security review.
- [ ] Obtain distinct operator merge disposition.
- [ ] Later: independently administered custodian hardware, out-of-band root enrollment, protected current history/challenge and authenticated terminal recovery.

## DECISIONS

The accepted operator direction remains **local-first development now, independently administered protected hardware later**. No particular hardware administrator, root, enrollment protocol, consent issuer, receipt semantics or production Sign-In activation is approved by this milestone. **HOLD.**
